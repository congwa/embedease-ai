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
    HealthCheckResponse,
    QuickSetupState,
    QuickSetupStateUpdate,
    ServiceHealthItem,
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
