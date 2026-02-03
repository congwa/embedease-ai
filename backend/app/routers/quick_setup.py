"""Quick Setup 快捷配置中心 API

提供 Quick Setup 向导的所有接口，包括：
- 状态管理
- 配置检查清单
- Agent 类型配置
- 健康检查
"""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.models.agent import Agent, FAQEntry, KnowledgeConfig
from app.schemas.quick_setup import (
    AgentTypeConfig,
    AgentTypeConfigListResponse,
    ChecklistResponse,
    EssentialSetupRequest,
    EssentialSetupResponse,
    EssentialValidationResponse,
    HealthCheckResponse,
    QuickSetupState,
    QuickSetupStateUpdate,
    ServiceHealthItem,
    SetupLevel,
)
from app.services.quick_setup.checklist import get_checklist_service
from app.services.quick_setup.configurators import get_all_configurators, get_configurator
from app.services.quick_setup.state_manager import get_state_manager

router = APIRouter(prefix="/api/v1/admin/quick-setup", tags=["quick-setup"])
logger = get_logger("routers.quick_setup")


# ========== State Management ==========


@router.get("/state", response_model=QuickSetupState)
async def get_setup_state():
    """获取 Quick Setup 状态"""
    state_manager = get_state_manager()
    return state_manager.get_state()


@router.patch("/state", response_model=QuickSetupState)
async def update_setup_state(data: QuickSetupStateUpdate):
    """更新 Quick Setup 状态"""
    state_manager = get_state_manager()
    state = state_manager.update_state(data)
    logger.info("更新 Quick Setup 状态", current_step=state.current_step, completed=state.completed)
    return state


@router.post("/state/reset", response_model=QuickSetupState)
async def reset_setup_state():
    """重置 Quick Setup 状态（重新运行向导）"""
    state_manager = get_state_manager()
    state = state_manager.reset()
    logger.info("重置 Quick Setup 状态")
    return state


@router.post("/state/step/{step_index}/complete", response_model=QuickSetupState)
async def complete_step(step_index: int, data: dict[str, Any] | None = None):
    """完成指定步骤"""
    state_manager = get_state_manager()
    state = state_manager.complete_step(step_index, data)
    logger.info("完成步骤", step_index=step_index)
    return state


@router.post("/state/step/{step_index}/skip", response_model=QuickSetupState)
async def skip_step(step_index: int):
    """跳过指定步骤"""
    state_manager = get_state_manager()
    state = state_manager.skip_step(step_index)
    logger.info("跳过步骤", step_index=step_index)
    return state


@router.post("/state/step/{step_index}/goto", response_model=QuickSetupState)
async def goto_step(step_index: int):
    """跳转到指定步骤"""
    state_manager = get_state_manager()
    state = state_manager.go_to_step(step_index)
    logger.info("跳转到步骤", step_index=step_index)
    return state


@router.post("/state/agent/{agent_id}", response_model=QuickSetupState)
async def set_current_agent(agent_id: str, db: AsyncSession = Depends(get_db_session)):
    """设置当前配置的 Agent"""
    # 验证 Agent 存在
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    state_manager = get_state_manager()
    state = state_manager.set_agent(agent_id)
    logger.info("设置当前 Agent", agent_id=agent_id)
    return state


@router.post("/state/mode/{mode}", response_model=QuickSetupState)
async def set_setup_mode(mode: str, db: AsyncSession = Depends(get_db_session)):
    """设置向导模式（单 Agent / Supervisor）
    
    Args:
        mode: "single" | "supervisor"
    """
    if mode not in ("single", "supervisor"):
        raise HTTPException(status_code=400, detail="无效的模式，必须是 'single' 或 'supervisor'")
    
    state_manager = get_state_manager()
    state = state_manager.set_mode(mode)
    
    # 更新全局 Supervisor 配置
    from app.services.system_config import SupervisorGlobalConfigService
    from app.schemas.system_config import SupervisorGlobalConfigUpdate
    
    supervisor_service = SupervisorGlobalConfigService(db)
    await supervisor_service.update_config(
        SupervisorGlobalConfigUpdate(enabled=(mode == "supervisor"))
    )
    await db.commit()
    
    logger.info("设置向导模式", mode=mode, supervisor_enabled=(mode == "supervisor"))
    return state


@router.get("/state/mode")
async def get_current_mode() -> dict[str, str | None]:
    """获取当前向导模式"""
    state_manager = get_state_manager()
    mode = state_manager.get_current_mode()
    return {"mode": mode}


# ========== Essential Setup ==========


@router.post("/essential/complete", response_model=EssentialSetupResponse)
async def complete_essential_setup(data: EssentialSetupRequest):
    """完成精简配置（最小可用配置）
    
    执行以下操作：
    1. 设置运行模式（single/supervisor）
    2. 验证 LLM API 连通性（外部 HTTP，不持有 db）
    3. 保存 LLM 配置到系统配置（需要 db）
    4. 创建默认 Agent（需要 db）
    5. 更新 Quick Setup 状态
    """
    import uuid
    from app.core.database import get_db_context
    from app.services.system_config import SystemConfigService, SupervisorGlobalConfigService
    from app.schemas.system_config import PROVIDER_PRESETS, SupervisorGlobalConfigUpdate, FullConfigUpdate
    from app.services.agent.core.config import DEFAULT_PROMPTS, DEFAULT_TOOL_CATEGORIES, DEFAULT_TOOL_POLICIES
    
    try:
        state_manager = get_state_manager()
        
        # 1. 设置模式（不需要 db）
        state_manager.set_mode(data.mode)
        
        # 2. 验证 LLM API（外部 HTTP 请求，不持有 db 连接）
        llm_ok = await _validate_llm_api(
            provider=data.llm_provider,
            api_key=data.llm_api_key,
            base_url=data.llm_base_url,
        )
        if not llm_ok:
            return EssentialSetupResponse(
                success=False,
                message="LLM API 连接失败，请检查 API Key 和配置",
            )
        
        # 准备配置数据（不需要 db）
        provider_urls = {
            "openai": "https://api.openai.com/v1",
            "siliconflow": "https://api.siliconflow.cn/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
        }
        base_url = data.llm_base_url or provider_urls.get(data.llm_provider, settings.LLM_BASE_URL)
        embedding_api_key = data.embedding_api_key if data.embedding_api_key else None
        embedding_base_url = data.embedding_base_url if data.embedding_base_url else None
        
        agent_name = data.agent_name or f"默认{_get_agent_type_name(data.agent_type)}助手"
        system_prompt = DEFAULT_PROMPTS.get(data.agent_type, DEFAULT_PROMPTS.get("custom", ""))
        tool_categories = DEFAULT_TOOL_CATEGORIES.get(data.agent_type)
        tool_policy = DEFAULT_TOOL_POLICIES.get(data.agent_type)
        
        agent_id = str(uuid.uuid4())
        
        # 3. 数据库操作：验证通过后才获取 db session，快速写入后释放
        async with get_db_context() as db:
            # 保存 LLM 配置
            config_service = SystemConfigService(db)
            await config_service.update_full_config(FullConfigUpdate(
                llm_provider=data.llm_provider,
                llm_api_key=data.llm_api_key,
                llm_base_url=base_url,
                llm_chat_model=data.llm_model,
                embedding_provider=data.llm_provider,
                embedding_api_key=embedding_api_key,
                embedding_base_url=embedding_base_url,
                embedding_model=data.embedding_model,
                embedding_dimension=data.embedding_dimension,
                rerank_enabled=False,
            ))
            
            # 设置运行模式
            supervisor_service = SupervisorGlobalConfigService(db)
            await supervisor_service.update_config(
                SupervisorGlobalConfigUpdate(enabled=(data.mode == "supervisor"))
            )
            
            # 创建默认 Agent
            agent = Agent(
                id=agent_id,
                name=agent_name,
                description=f"通过快速配置创建的{_get_agent_type_name(data.agent_type)} Agent",
                type=data.agent_type,
                system_prompt=system_prompt,
                tool_categories=tool_categories,
                tool_policy=tool_policy,
                status="enabled",
                is_default=True,
            )
            
            # 取消其他默认 Agent
            await db.execute(
                Agent.__table__.update().where(Agent.is_default == True).values(is_default=False)  # noqa: E712
            )
            
            db.add(agent)
            # get_db_context 会自动 commit
        
        logger.info(
            "已保存 LLM 和 Embedding 配置",
            provider=data.llm_provider,
            llm_model=data.llm_model,
            embedding_model=data.embedding_model,
            base_url=base_url,
        )
        
        # 4. 更新 Quick Setup 状态（不需要 db）
        essential_data = {
            "mode": data.mode,
            "llm_provider": data.llm_provider,
            "llm_model": data.llm_model,
            "agent_type": data.agent_type,
            "agent_id": agent_id,
        }
        state = state_manager.complete_essential(agent_id, essential_data)
        
        logger.info(
            "完成精简配置",
            mode=data.mode,
            agent_id=agent_id,
            agent_type=data.agent_type,
        )
        
        return EssentialSetupResponse(
            success=True,
            agent_id=agent_id,
            message="精简配置完成，系统已可正常使用",
            state=state,
        )
        
    except Exception as e:
        logger.error("精简配置失败", error=str(e))
        return EssentialSetupResponse(
            success=False,
            message=f"配置失败: {str(e)}",
        )


@router.post("/essential/validate", response_model=EssentialValidationResponse)
async def validate_essential_setup(data: EssentialSetupRequest):
    """验证精简配置是否满足最小要求"""
    missing_items: list[str] = []
    warnings: list[str] = []
    
    # 检查必需项
    if not data.mode:
        missing_items.append("运行模式未选择")
    
    if not data.llm_api_key:
        missing_items.append("LLM API Key 未配置")
    
    if not data.llm_model:
        missing_items.append("LLM 模型未选择")
    
    # 验证 LLM 连通性
    if data.llm_api_key and data.llm_model:
        llm_ok = await _validate_llm_api(
            provider=data.llm_provider,
            api_key=data.llm_api_key,
            base_url=data.llm_base_url,
        )
        if not llm_ok:
            missing_items.append("LLM API 连接失败")
    
    # 警告项
    if not data.agent_name:
        warnings.append("未指定 Agent 名称，将使用默认名称")
    
    return EssentialValidationResponse(
        can_proceed=len(missing_items) == 0,
        missing_items=missing_items,
        warnings=warnings,
    )


async def _validate_llm_api(
    provider: str,
    api_key: str,
    base_url: str | None = None,
) -> bool:
    """验证 LLM API 连通性"""
    try:
        import httpx
        
        # 根据 provider 确定 base_url
        if not base_url:
            provider_urls = {
                "openai": "https://api.openai.com/v1",
                "siliconflow": "https://api.siliconflow.cn/v1",
                "openrouter": "https://openrouter.ai/api/v1",
                "deepseek": "https://api.deepseek.com/v1",
            }
            base_url = provider_urls.get(provider, settings.LLM_BASE_URL)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return response.status_code == 200
    except Exception:
        return False


def _get_agent_type_name(agent_type: str) -> str:
    """获取 Agent 类型中文名称"""
    names = {
        "product": "商品推荐",
        "faq": "FAQ 问答",
        "kb": "知识库",
        "custom": "自定义",
    }
    return names.get(agent_type, "自定义")


# ========== Models Discovery ==========


@router.get("/providers")
async def get_available_providers() -> list[dict[str, str]]:
    """获取可用的 LLM 提供商列表"""
    return [
        {"id": "siliconflow", "name": "SiliconFlow", "base_url": "https://api.siliconflow.cn/v1"},
        {"id": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1"},
        {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com/v1"},
        {"id": "openrouter", "name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1"},
        {"id": "anthropic", "name": "Anthropic", "base_url": "https://api.anthropic.com/v1"},
        {"id": "custom", "name": "自定义", "base_url": ""},
    ]


@router.get("/providers/{provider_id}/models")
async def get_provider_models(provider_id: str) -> list[dict[str, Any]]:
    """从 models.dev 获取指定提供商的模型列表
    
    返回格式：
    [
        {
            "id": "moonshotai/Kimi-K2-Thinking",
            "name": "Kimi K2 Thinking",
            "reasoning": true,
            "tool_call": true,
            ...
        }
    ]
    """
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://models.dev/api.json")
            response.raise_for_status()
            all_data = response.json()
    except Exception as e:
        logger.warning("获取 models.dev 失败", error=str(e))
        # 返回默认模型列表
        return _get_fallback_models(provider_id)
    
    if not isinstance(all_data, dict):
        return _get_fallback_models(provider_id)
    
    provider_data = all_data.get(provider_id)
    if not isinstance(provider_data, dict):
        return _get_fallback_models(provider_id)
    
    models = provider_data.get("models")
    if not isinstance(models, dict):
        return _get_fallback_models(provider_id)
    
    result = []
    for model_id, model_data in models.items():
        if not isinstance(model_data, dict):
            continue
        model_name = model_data.get("name")
        if not model_name:
            continue
        
        result.append({
            "id": model_name,
            "name": _format_model_name(model_name),
            "reasoning": model_data.get("reasoning", False),
            "tool_call": model_data.get("tool_call", False),
            "structured_output": model_data.get("structured_output", False),
            "context_limit": (model_data.get("limit") or {}).get("context"),
        })
    
    # 按名称排序
    result.sort(key=lambda x: x["name"])
    
    logger.info("获取模型列表成功", provider_id=provider_id, count=len(result))
    return result


def _format_model_name(model_id: str) -> str:
    """格式化模型名称为人类可读形式"""
    # moonshotai/Kimi-K2-Thinking -> Kimi K2 Thinking
    name = model_id.split("/")[-1]
    name = name.replace("-", " ").replace("_", " ")
    return name


def _get_fallback_models(provider_id: str) -> list[dict[str, Any]]:
    """当 models.dev 不可用时返回的默认模型列表"""
    fallback = {
        "siliconflow": [
            {"id": "moonshotai/Kimi-K2-Thinking", "name": "Kimi K2 Thinking", "reasoning": True, "tool_call": True},
            {"id": "Qwen/Qwen3-235B-A22B", "name": "Qwen3 235B", "reasoning": False, "tool_call": True},
            {"id": "deepseek-ai/DeepSeek-V3", "name": "DeepSeek V3", "reasoning": False, "tool_call": True},
        ],
        "openai": [
            {"id": "gpt-4o", "name": "GPT-4o", "reasoning": False, "tool_call": True},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "reasoning": False, "tool_call": True},
            {"id": "o1", "name": "O1", "reasoning": True, "tool_call": False},
        ],
        "deepseek": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "reasoning": False, "tool_call": True},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "reasoning": True, "tool_call": False},
        ],
        "openrouter": [
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "reasoning": False, "tool_call": True},
            {"id": "openai/gpt-4o", "name": "GPT-4o", "reasoning": False, "tool_call": True},
        ],
        "anthropic": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "reasoning": False, "tool_call": True},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "reasoning": False, "tool_call": True},
        ],
    }
    return fallback.get(provider_id, [])


# ========== Checklist ==========


@router.get("/checklist", response_model=ChecklistResponse)
async def get_checklist():
    """获取配置检查清单"""
    checklist_service = get_checklist_service()
    return checklist_service.get_checklist()


@router.get("/checklist/summary")
async def get_checklist_summary() -> dict[str, dict[str, int]]:
    """获取检查清单分类摘要"""
    checklist_service = get_checklist_service()
    return checklist_service.get_category_summary()


# ========== Agent Type Configs ==========


@router.get("/agent-types", response_model=AgentTypeConfigListResponse)
async def get_agent_types():
    """获取所有 Agent 类型配置"""
    configurators = get_all_configurators()
    configs = [c.get_config() for c in configurators]
    return AgentTypeConfigListResponse(items=configs)


@router.get("/agent-types/{agent_type}", response_model=AgentTypeConfig)
async def get_agent_type_config(agent_type: str):
    """获取指定 Agent 类型的配置"""
    try:
        configurator = get_configurator(agent_type)
        return configurator.get_config()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/agent-types/{agent_type}/defaults")
async def get_agent_type_defaults(agent_type: str) -> dict[str, Any]:
    """获取指定 Agent 类型的默认值"""
    try:
        configurator = get_configurator(agent_type)
        return {
            "tool_categories": configurator.default_tool_categories,
            "middleware_flags": configurator.default_middleware_flags,
            "knowledge_type": configurator.default_knowledge_type,
            "system_prompt_template": configurator.system_prompt_template,
            "greeting_template": configurator.greeting_template,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ========== Health Check ==========


class QdrantCheckRequest(BaseModel):
    """Qdrant 连接检查请求"""
    host: str = Field(default="localhost")
    port: int = Field(default=6333)


class QdrantCheckResponse(BaseModel):
    """Qdrant 连接检查响应"""
    success: bool
    message: str
    latency_ms: float | None = None


@router.post("/health/qdrant", response_model=QdrantCheckResponse)
async def check_qdrant_connection(data: QdrantCheckRequest):
    """检查 Qdrant 连接（支持自定义地址）"""
    try:
        import httpx
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = f"http://{data.host}:{data.port}/collections"
            start = asyncio.get_event_loop().time()
            response = await client.get(url)
            latency = (asyncio.get_event_loop().time() - start) * 1000
            
            if response.status_code == 200:
                return QdrantCheckResponse(
                    success=True,
                    message=f"Qdrant 连接成功 ({data.host}:{data.port})",
                    latency_ms=round(latency, 2),
                )
            else:
                return QdrantCheckResponse(
                    success=False,
                    message=f"Qdrant 返回状态码 {response.status_code}",
                )
    except Exception as e:
        return QdrantCheckResponse(
            success=False,
            message=f"无法连接 Qdrant: {str(e)}",
        )


@router.get("/health", response_model=HealthCheckResponse)
async def check_services_health():
    """检查各服务的健康状态"""
    services: list[ServiceHealthItem] = []

    # 检查 Qdrant
    qdrant_status = await _check_qdrant_health()
    services.append(qdrant_status)

    # 检查 LLM API（简单的连通性测试）
    llm_status = await _check_llm_health()
    services.append(llm_status)

    # 检查数据库
    db_status = ServiceHealthItem(
        name="database",
        status="ok",
        message="SQLite 数据库可用",
    )
    services.append(db_status)

    all_ok = all(s.status == "ok" for s in services)

    return HealthCheckResponse(services=services, all_ok=all_ok)


async def _check_qdrant_health() -> ServiceHealthItem:
    """检查 Qdrant 服务状态"""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            url = f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/collections"
            start = asyncio.get_event_loop().time()
            response = await client.get(url)
            latency = (asyncio.get_event_loop().time() - start) * 1000

            if response.status_code == 200:
                return ServiceHealthItem(
                    name="qdrant",
                    status="ok",
                    message=f"Qdrant 服务正常 ({settings.QDRANT_HOST}:{settings.QDRANT_PORT})",
                    latency_ms=round(latency, 2),
                )
            else:
                return ServiceHealthItem(
                    name="qdrant",
                    status="error",
                    message=f"Qdrant 返回状态码 {response.status_code}",
                )
    except Exception as e:
        return ServiceHealthItem(
            name="qdrant",
            status="error",
            message=f"无法连接 Qdrant: {str(e)}",
        )


async def _check_llm_health() -> ServiceHealthItem:
    """检查 LLM API 状态（仅检查连通性）"""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{settings.LLM_BASE_URL}/models"
            headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}"}
            start = asyncio.get_event_loop().time()
            response = await client.get(url, headers=headers)
            latency = (asyncio.get_event_loop().time() - start) * 1000

            if response.status_code in (200, 401, 403):
                # 200 = 成功, 401/403 = API Key 问题但服务可达
                return ServiceHealthItem(
                    name="llm",
                    status="ok" if response.status_code == 200 else "error",
                    message=f"LLM API 可达 ({settings.LLM_PROVIDER})"
                    if response.status_code == 200
                    else "API Key 可能无效",
                    latency_ms=round(latency, 2),
                )
            else:
                return ServiceHealthItem(
                    name="llm",
                    status="error",
                    message=f"LLM API 返回状态码 {response.status_code}",
                )
    except Exception as e:
        return ServiceHealthItem(
            name="llm",
            status="error",
            message=f"无法连接 LLM API: {str(e)}",
        )


# ========== Quick Stats ==========


@router.get("/stats")
async def get_quick_stats(db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    """获取快速统计数据（用于欢迎页展示）"""
    # Agent 统计
    agent_count = await db.scalar(select(func.count(Agent.id)))
    default_agent = await db.scalar(select(Agent).where(Agent.is_default == True))  # noqa: E712

    # FAQ 统计
    faq_total = await db.scalar(select(func.count(FAQEntry.id)))
    faq_unindexed = await db.scalar(
        select(func.count(FAQEntry.id)).where(FAQEntry.vector_id.is_(None))
    )

    # Knowledge Config 统计
    kc_count = await db.scalar(select(func.count(KnowledgeConfig.id)))

    return {
        "agents": {
            "total": agent_count or 0,
            "default_id": default_agent.id if default_agent else None,
            "default_name": default_agent.name if default_agent else None,
            "default_type": default_agent.type if default_agent else None,
        },
        "faq": {
            "total": faq_total or 0,
            "unindexed": faq_unindexed or 0,
        },
        "knowledge_configs": {
            "total": kc_count or 0,
        },
        "settings": {
            "llm_provider": settings.LLM_PROVIDER,
            "llm_model": settings.LLM_CHAT_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
            "qdrant_collection": settings.QDRANT_COLLECTION,
            "memory_enabled": settings.MEMORY_ENABLED,
            "crawler_enabled": settings.CRAWLER_ENABLED,
        },
    }


# ========== Validate Step ==========


@router.post("/validate/{step_key}")
async def validate_step(
    step_key: str,
    data: dict[str, Any],
    agent_type: str | None = None,
) -> dict[str, Any]:
    """验证步骤数据"""
    errors: list[str] = []

    # 如果指定了 agent_type，使用对应的配置器验证
    if agent_type:
        try:
            configurator = get_configurator(agent_type)
            errors = configurator.validate_step_data(step_key, data)
        except ValueError:
            pass

    # 通用验证
    if step_key == "greeting":
        if data.get("enabled") and not data.get("channels"):
            errors.append("启用开场白时至少需要配置一个渠道")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
