"""Agent 管理 API

提供 Agent、KnowledgeConfig、FAQ 的 CRUD 接口。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.models.agent import Agent, AgentTool, FAQEntry, KnowledgeConfig, SuggestedQuestion
from app.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentToolCreate,
    AgentToolResponse,
    AgentToolUpdate,
    AgentUpdate,
    FAQCategoryStats,
    FAQEntryCreate,
    FAQEntryResponse,
    FAQEntryUpdate,
    FAQImportRequest,
    FAQImportResponse,
    FAQRecentUpdate,
    FAQStatsResponse,
    FAQUpsertResponse,
    GreetingConfigSchema,
    GreetingConfigUpdate,
    KnowledgeConfigCreate,
    KnowledgeConfigResponse,
    KnowledgeConfigUpdate,
)
from app.schemas.suggested_question import (
    SuggestedQuestionBatchCreate,
    SuggestedQuestionCreate,
    SuggestedQuestionImportFromFAQ,
    SuggestedQuestionReorder,
    SuggestedQuestionResponse,
    SuggestedQuestionUpdate,
)
from app.services.agent.core.service import agent_service

router = APIRouter(prefix="/api/v1/admin/agents", tags=["agents"])
logger = get_logger("routers.agents")


# ========== Agent CRUD ==========


@router.get("", response_model=AgentListResponse)
async def list_agents(
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    type_filter: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 列表"""
    stmt = select(Agent).options(selectinload(Agent.knowledge_config))

    if status_filter:
        stmt = stmt.where(Agent.status == status_filter)
    if type_filter:
        stmt = stmt.where(Agent.type == type_filter)

    stmt = stmt.order_by(Agent.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    agents = result.scalars().all()

    # 获取总数
    count_stmt = select(func.count(Agent.id))
    if status_filter:
        count_stmt = count_stmt.where(Agent.status == status_filter)
    if type_filter:
        count_stmt = count_stmt.where(Agent.type == type_filter)

    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    return AgentListResponse(
        items=[AgentResponse.model_validate(a) for a in agents],
        total=total,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取单个 Agent"""
    stmt = select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.knowledge_config))
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    return AgentResponse.model_validate(agent)


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    data: AgentCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建 Agent"""
    # 如果设为默认，先取消其他默认
    if data.is_default:
        await db.execute(
            Agent.__table__.update().where(Agent.is_default == True).values(is_default=False)  # noqa: E712
        )

    agent = Agent(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        type=data.type,
        system_prompt=data.system_prompt,
        mode_default=data.mode_default,
        middleware_flags=data.middleware_flags,
        tool_policy=data.tool_policy,
        tool_categories=data.tool_categories,
        knowledge_config_id=data.knowledge_config_id,
        response_format=data.response_format,
        status=data.status,
        is_default=data.is_default,
    )

    db.add(agent)
    await db.flush()
    await db.refresh(agent)

    logger.info("创建 Agent", agent_id=agent.id, name=agent.name, type=agent.type)
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新 Agent"""
    from sqlalchemy.orm import selectinload

    stmt = select(Agent).options(selectinload(Agent.knowledge_config)).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    # 如果设为默认，先取消其他默认
    if data.is_default:
        await db.execute(
            Agent.__table__.update()
            .where(Agent.is_default == True, Agent.id != agent_id)  # noqa: E712
            .values(is_default=False)
        )

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    await db.flush()

    # 清除会话缓存并重新查询（避免 MissingGreenlet 错误）
    db.expire_all()
    stmt = select(Agent).options(selectinload(Agent.knowledge_config)).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one()

    # 使缓存失效
    agent_service.invalidate_agent(agent_id)

    logger.info("更新 Agent", agent_id=agent_id)
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除 Agent"""
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    if agent.is_default:
        raise HTTPException(status_code=400, detail="不能删除默认 Agent")

    await db.delete(agent)

    # 使缓存失效
    agent_service.invalidate_agent(agent_id)

    logger.info("删除 Agent", agent_id=agent_id)


@router.post("/{agent_id}/refresh", status_code=status.HTTP_204_NO_CONTENT)
async def refresh_agent(agent_id: str):
    """刷新 Agent 缓存"""
    agent_service.invalidate_agent(agent_id)
    logger.info("刷新 Agent 缓存", agent_id=agent_id)


# ========== Memory Config ==========


class MemoryConfigResponse(BaseModel):
    """记忆配置响应"""

    inject_profile: bool = True
    inject_facts: bool = True
    inject_graph: bool = True
    max_facts: int = 5
    max_graph_entities: int = 5
    memory_enabled: bool = False
    store_enabled: bool = False
    fact_enabled: bool = False
    graph_enabled: bool = False


@router.get("/{agent_id}/memory-config", response_model=MemoryConfigResponse)
async def get_agent_memory_config(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 记忆配置"""
    from app.core.config import settings

    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    middleware_flags = agent.middleware_flags or {}

    return MemoryConfigResponse(
        inject_profile=middleware_flags.get("inject_profile", True),
        inject_facts=middleware_flags.get("inject_facts", True),
        inject_graph=middleware_flags.get("inject_graph", True),
        max_facts=middleware_flags.get("max_facts", 5),
        max_graph_entities=middleware_flags.get("max_graph_entities", 5),
        memory_enabled=settings.MEMORY_ENABLED,
        store_enabled=settings.MEMORY_STORE_ENABLED,
        fact_enabled=settings.MEMORY_FACT_ENABLED,
        graph_enabled=settings.MEMORY_GRAPH_ENABLED,
    )


class PromptPreviewRequest(BaseModel):
    """提示词预览请求"""

    user_id: str | None = None
    mode: str = "natural"


class PromptPreviewResponse(BaseModel):
    """提示词预览响应"""

    base_prompt: str
    mode_suffix: str
    memory_context: str
    full_prompt: str


@router.post("/{agent_id}/preview-prompt", response_model=PromptPreviewResponse)
async def preview_agent_prompt(
    agent_id: str,
    request: PromptPreviewRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """预览 Agent 完整提示词（含记忆注入）"""
    from app.core.config import settings
    from app.services.agent.core.config import AgentConfigLoader
    from app.services.agent.core.factory import MODE_PROMPT_SUFFIX

    loader = AgentConfigLoader(db)
    config = await loader.load_config(agent_id, request.mode)

    if not config:
        raise HTTPException(status_code=404, detail="Agent 不存在或已禁用")

    base_prompt = config.system_prompt
    mode_suffix = MODE_PROMPT_SUFFIX.get(request.mode, "")

    memory_context = ""
    if request.user_id and settings.MEMORY_ENABLED:
        try:
            from app.services.memory.middleware.orchestration import (
                MemoryOrchestrationMiddleware,
            )

            middleware = MemoryOrchestrationMiddleware()
            memory_context = await middleware._get_memory_context(
                request.user_id, "预览查询"
            )
        except Exception as e:
            memory_context = f"[获取记忆上下文失败: {e}]"

    full_prompt_parts = [base_prompt]
    if mode_suffix:
        full_prompt_parts.append(mode_suffix)
    if memory_context:
        full_prompt_parts.append(f"\n\n{memory_context}")

    return PromptPreviewResponse(
        base_prompt=base_prompt,
        mode_suffix=mode_suffix,
        memory_context=memory_context,
        full_prompt="".join(full_prompt_parts),
    )


# ========== Effective Config ==========


@router.get("/{agent_id}/effective-config")
async def get_agent_effective_config(
    agent_id: str,
    mode: str | None = None,
    include_filtered: bool = True,
    test_message: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 运行态配置

    返回 Agent 最终生效的配置，包括：
    - 最终系统提示词（含来源追踪）
    - 技能清单（always_apply + 条件触发）
    - 工具清单（启用的 + 被过滤的）
    - 中间件链（按执行顺序）
    - 知识源配置
    - 策略配置
    - 配置健康度
    """
    from app.schemas.effective_config import EffectiveConfigResponse
    from app.services.agent.effective_config import EffectiveConfigBuilder

    stmt = select(Agent).where(Agent.id == agent_id).options(selectinload(Agent.knowledge_config))
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    builder = EffectiveConfigBuilder(db)
    config = await builder.build(
        agent=agent,
        mode=mode,
        include_filtered=include_filtered,
        test_message=test_message,
    )

    return config


class AgentUserItem(BaseModel):
    """Agent 用户项"""

    user_id: str
    conversation_count: int
    last_active: str | None = None


class AgentUsersResponse(BaseModel):
    """Agent 用户列表响应"""

    total: int
    items: list[AgentUserItem] = Field(default_factory=list)


@router.get("/{agent_id}/users", response_model=AgentUsersResponse)
async def get_agent_users(
    agent_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    """获取与 Agent 有对话记录的用户列表"""
    from app.models.conversation import Conversation

    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    stmt = (
        select(
            Conversation.user_id,
            func.count(Conversation.id).label("conversation_count"),
            func.max(Conversation.updated_at).label("last_active"),
        )
        .where(Conversation.agent_id == agent_id)
        .group_by(Conversation.user_id)
        .order_by(func.max(Conversation.updated_at).desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        AgentUserItem(
            user_id=row.user_id,
            conversation_count=row.conversation_count,
            last_active=row.last_active.isoformat() if row.last_active else None,
        )
        for row in rows
    ]

    count_stmt = (
        select(func.count(func.distinct(Conversation.user_id)))
        .where(Conversation.agent_id == agent_id)
    )
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    return AgentUsersResponse(total=total, items=items)


# ========== Greeting Config ==========


@router.get("/{agent_id}/greeting", response_model=GreetingConfigSchema | None)
async def get_agent_greeting(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 开场白配置"""
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    if agent.greeting_config:
        return GreetingConfigSchema.model_validate(agent.greeting_config)
    return None


@router.patch("/{agent_id}/greeting", response_model=GreetingConfigSchema)
async def update_agent_greeting(
    agent_id: str,
    data: GreetingConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新 Agent 开场白配置"""
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")

    # 获取现有配置或创建默认配置
    current_config = agent.greeting_config or {
        "enabled": False,
        "trigger": "first_visit",
        "delay_ms": 1000,
        "channels": {},
        "cta": None,
        "variables": None,
    }

    # 更新字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if value is not None:
            current_config[key] = value
        elif key in current_config and value is None:
            # 允许显式设置为 None
            current_config[key] = None

    # 校验：如果启用开场白，至少需要一个渠道配置
    if current_config.get("enabled") and not current_config.get("channels"):
        raise HTTPException(
            status_code=400,
            detail="启用开场白时至少需要配置一个渠道",
        )

    agent.greeting_config = current_config
    await db.flush()

    # 使缓存失效
    agent_service.invalidate_agent(agent_id)

    logger.info("更新 Agent 开场白配置", agent_id=agent_id, enabled=current_config.get("enabled"))
    return GreetingConfigSchema.model_validate(current_config)


# ========== Agent Tools ==========


@router.get("/{agent_id}/tools", response_model=list[AgentToolResponse])
async def list_agent_tools(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 工具白名单"""
    stmt = select(AgentTool).where(AgentTool.agent_id == agent_id)
    result = await db.execute(stmt)
    tools = result.scalars().all()
    return [AgentToolResponse.model_validate(t) for t in tools]


@router.post(
    "/{agent_id}/tools", response_model=AgentToolResponse, status_code=status.HTTP_201_CREATED
)
async def add_agent_tool(
    agent_id: str,
    data: AgentToolCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """添加 Agent 工具白名单"""
    # 检查 Agent 是否存在
    stmt = select(Agent).where(Agent.id == agent_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent 不存在")

    tool = AgentTool(
        agent_id=agent_id,
        tool_name=data.tool_name,
        enabled=data.enabled,
    )
    db.add(tool)
    await db.flush()
    await db.refresh(tool)

    # 使缓存失效
    agent_service.invalidate_agent(agent_id)

    return AgentToolResponse.model_validate(tool)


@router.patch("/{agent_id}/tools/{tool_id}", response_model=AgentToolResponse)
async def update_agent_tool(
    agent_id: str,
    tool_id: int,
    data: AgentToolUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新 Agent 工具开关"""
    stmt = select(AgentTool).where(AgentTool.id == tool_id, AgentTool.agent_id == agent_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(status_code=404, detail="工具配置不存在")

    tool.enabled = data.enabled
    await db.flush()

    # 使缓存失效
    agent_service.invalidate_agent(agent_id)

    return AgentToolResponse.model_validate(tool)


@router.delete("/{agent_id}/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent_tool(
    agent_id: str,
    tool_id: int,
    db: AsyncSession = Depends(get_db_session),
):
    """删除 Agent 工具白名单"""
    stmt = select(AgentTool).where(AgentTool.id == tool_id, AgentTool.agent_id == agent_id)
    result = await db.execute(stmt)
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(status_code=404, detail="工具配置不存在")

    await db.delete(tool)

    # 使缓存失效
    agent_service.invalidate_agent(agent_id)


# ========== Knowledge Config ==========

knowledge_router = APIRouter(prefix="/api/v1/admin/knowledge-configs", tags=["knowledge"])


@knowledge_router.get("", response_model=list[KnowledgeConfigResponse])
async def list_knowledge_configs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session),
):
    """获取知识源配置列表"""
    stmt = (
        select(KnowledgeConfig)
        .order_by(KnowledgeConfig.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    configs = result.scalars().all()
    return [KnowledgeConfigResponse.model_validate(c) for c in configs]


@knowledge_router.get("/{config_id}", response_model=KnowledgeConfigResponse)
async def get_knowledge_config(
    config_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取单个知识源配置"""
    stmt = select(KnowledgeConfig).where(KnowledgeConfig.id == config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="知识源配置不存在")

    return KnowledgeConfigResponse.model_validate(config)


@knowledge_router.post(
    "", response_model=KnowledgeConfigResponse, status_code=status.HTTP_201_CREATED
)
async def create_knowledge_config(
    data: KnowledgeConfigCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建知识源配置"""
    config = KnowledgeConfig(
        id=str(uuid.uuid4()),
        name=data.name,
        type=data.type,
        index_name=data.index_name,
        collection_name=data.collection_name,
        embedding_model=data.embedding_model,
        top_k=data.top_k,
        similarity_threshold=data.similarity_threshold,
        rerank_enabled=data.rerank_enabled,
        filters=data.filters,
    )

    db.add(config)
    await db.flush()
    await db.refresh(config)

    logger.info("创建知识源配置", config_id=config.id, name=config.name, type=config.type)
    return KnowledgeConfigResponse.model_validate(config)


@knowledge_router.patch("/{config_id}", response_model=KnowledgeConfigResponse)
async def update_knowledge_config(
    config_id: str,
    data: KnowledgeConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新知识源配置"""
    stmt = select(KnowledgeConfig).where(KnowledgeConfig.id == config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="知识源配置不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)

    await db.flush()

    # 使关联的 Agent 缓存失效
    stmt = select(Agent.id).where(Agent.knowledge_config_id == config_id)
    result = await db.execute(stmt)
    agent_ids = result.scalars().all()
    for agent_id in agent_ids:
        agent_service.invalidate_agent(agent_id)

    logger.info("更新知识源配置", config_id=config_id)
    return KnowledgeConfigResponse.model_validate(config)


@knowledge_router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_config(
    config_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除知识源配置"""
    stmt = select(KnowledgeConfig).where(KnowledgeConfig.id == config_id)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="知识源配置不存在")

    await db.delete(config)
    logger.info("删除知识源配置", config_id=config_id)


# ========== FAQ ==========

faq_router = APIRouter(prefix="/api/v1/admin/faq", tags=["faq"])


@faq_router.get("/stats", response_model=FAQStatsResponse)
async def get_faq_stats(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 FAQ 统计信息

    返回指定 Agent 的 FAQ 统计数据，包括：
    - 总数、启用/禁用数量、未索引数量
    - 分类分布
    - 最近更新的条目
    """
    from sqlalchemy import func

    # 基础统计
    base_filter = FAQEntry.agent_id == agent_id

    # 总数
    total_stmt = select(func.count()).select_from(FAQEntry).where(base_filter)
    total_result = await db.execute(total_stmt)
    total = total_result.scalar() or 0

    # 启用数量
    enabled_stmt = select(func.count()).select_from(FAQEntry).where(
        base_filter, FAQEntry.enabled == True  # noqa: E712
    )
    enabled_result = await db.execute(enabled_stmt)
    enabled_count = enabled_result.scalar() or 0

    # 未索引数量
    unindexed_stmt = select(func.count()).select_from(FAQEntry).where(
        base_filter, FAQEntry.vector_id.is_(None)
    )
    unindexed_result = await db.execute(unindexed_stmt)
    unindexed_count = unindexed_result.scalar() or 0

    # 分类分布
    category_stmt = (
        select(FAQEntry.category, func.count().label("count"))
        .where(base_filter, FAQEntry.category.isnot(None))
        .group_by(FAQEntry.category)
        .order_by(func.count().desc())
    )
    category_result = await db.execute(category_stmt)
    categories = [
        FAQCategoryStats(name=row.category, count=row.count)
        for row in category_result.fetchall()
    ]

    # 最近更新的条目
    recent_stmt = (
        select(FAQEntry)
        .where(base_filter)
        .order_by(FAQEntry.updated_at.desc())
        .limit(5)
    )
    recent_result = await db.execute(recent_stmt)
    recent_entries = recent_result.scalars().all()
    recent_updates = [
        FAQRecentUpdate(
            id=e.id,
            question=e.question[:100] if len(e.question) > 100 else e.question,
            source=e.source,
            updated_at=e.updated_at,
        )
        for e in recent_entries
    ]

    return FAQStatsResponse(
        total=total,
        enabled=enabled_count,
        disabled=total - enabled_count,
        unindexed=unindexed_count,
        categories=categories,
        recent_updates=recent_updates,
    )


@faq_router.get("", response_model=list[FAQEntryResponse])
async def list_faq_entries(
    skip: int = 0,
    limit: int = 50,
    agent_id: str | None = None,
    category: str | None = None,
    source: str | None = None,
    enabled: bool | None = None,
    priority_min: int | None = None,
    priority_max: int | None = None,
    tags: str | None = None,
    order_by: str = "updated_desc",
    db: AsyncSession = Depends(get_db_session),
):
    """获取 FAQ 条目列表

    支持多条件筛选和排序：
    - source: 来源关键字模糊匹配
    - enabled: 启用状态过滤
    - priority_min/priority_max: 优先级区间
    - tags: 标签过滤（逗号分隔）
    - order_by: 排序方式 (priority_desc, priority_asc, updated_desc, updated_asc, unindexed_first)
    """
    stmt = select(FAQEntry)

    # 筛选条件
    if agent_id:
        stmt = stmt.where(FAQEntry.agent_id == agent_id)
    if category:
        stmt = stmt.where(FAQEntry.category == category)
    if source:
        stmt = stmt.where(FAQEntry.source.ilike(f"%{source}%"))
    if enabled is not None:
        stmt = stmt.where(FAQEntry.enabled == enabled)
    if priority_min is not None:
        stmt = stmt.where(FAQEntry.priority >= priority_min)
    if priority_max is not None:
        stmt = stmt.where(FAQEntry.priority <= priority_max)
    if tags:
        # 标签过滤：检查是否包含任一指定标签
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            from sqlalchemy import or_
            tag_conditions = [FAQEntry.tags.contains([tag]) for tag in tag_list]
            stmt = stmt.where(or_(*tag_conditions))

    # 排序
    if order_by == "priority_desc":
        stmt = stmt.order_by(FAQEntry.priority.desc(), FAQEntry.updated_at.desc())
    elif order_by == "priority_asc":
        stmt = stmt.order_by(FAQEntry.priority.asc(), FAQEntry.updated_at.desc())
    elif order_by == "updated_asc":
        stmt = stmt.order_by(FAQEntry.updated_at.asc())
    elif order_by == "unindexed_first":
        # 未索引的排在前面
        stmt = stmt.order_by(
            FAQEntry.vector_id.is_(None).desc(),
            FAQEntry.updated_at.desc()
        )
    else:  # updated_desc (default)
        stmt = stmt.order_by(FAQEntry.updated_at.desc())

    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    entries = result.scalars().all()
    return [FAQEntryResponse.model_validate(e) for e in entries]


@faq_router.get("/{entry_id}", response_model=FAQEntryResponse)
async def get_faq_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取单个 FAQ 条目"""
    stmt = select(FAQEntry).where(FAQEntry.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="FAQ 条目不存在")

    return FAQEntryResponse.model_validate(entry)


@faq_router.post("", response_model=FAQUpsertResponse, status_code=status.HTTP_201_CREATED)
async def create_faq_entry(
    data: FAQEntryCreate,
    auto_merge: bool = True,
    db: AsyncSession = Depends(get_db_session),
):
    """创建 FAQ 条目（支持自动合并）

    当 auto_merge=True 时，会自动检索相似 FAQ：
    - 如果找到高相似度条目，则合并到已有条目
    - 否则创建新条目

    响应中包含 merged 字段指示是否执行了合并。
    """
    from app.services.knowledge.faq_service import (
        refresh_knowledge_config,
        upsert_faq_entry,
    )

    result = await upsert_faq_entry(
        data={
            "question": data.question,
            "answer": data.answer,
            "category": data.category,
            "tags": data.tags,
            "source": data.source,
            "priority": data.priority,
            "enabled": data.enabled,
            "agent_id": data.agent_id,
        },
        db=db,
        auto_merge=auto_merge,
        auto_index=True,
    )

    # 刷新 KnowledgeConfig 版本
    if result.entry.agent_id:
        await refresh_knowledge_config(result.entry.agent_id, db)

    logger.info(
        "FAQ 条目已处理",
        entry_id=result.entry.id,
        merged=result.merged,
        target_id=result.target_id,
    )

    response_data = FAQEntryResponse.model_validate(result.entry).model_dump()
    response_data["merged"] = result.merged
    response_data["target_id"] = result.target_id
    response_data["similarity_score"] = result.similarity_score

    return FAQUpsertResponse.model_validate(response_data)


@faq_router.patch("/{entry_id}", response_model=FAQEntryResponse)
async def update_faq_entry(
    entry_id: str,
    data: FAQEntryUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新 FAQ 条目"""
    from app.services.knowledge.faq_service import index_faq_entry, refresh_knowledge_config

    stmt = select(FAQEntry).where(FAQEntry.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="FAQ 条目不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    await db.flush()

    # 重新索引更新后的条目
    await index_faq_entry(entry, entry.agent_id)

    # 刷新 KnowledgeConfig 版本
    if entry.agent_id:
        await refresh_knowledge_config(entry.agent_id, db)

    logger.info("更新 FAQ 条目", entry_id=entry_id)
    return FAQEntryResponse.model_validate(entry)


@faq_router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_faq_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除 FAQ 条目"""
    stmt = select(FAQEntry).where(FAQEntry.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="FAQ 条目不存在")

    await db.delete(entry)
    logger.info("删除 FAQ 条目", entry_id=entry_id)


@faq_router.post("/import", response_model=FAQImportResponse)
async def import_faq(
    data: FAQImportRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """批量导入 FAQ"""
    imported_count = 0
    skipped_count = 0
    errors: list[str] = []

    for entry_data in data.entries:
        try:
            entry = FAQEntry(
                id=str(uuid.uuid4()),
                agent_id=data.agent_id,
                question=entry_data.question,
                answer=entry_data.answer,
                category=entry_data.category,
                tags=entry_data.tags,
                source=entry_data.source,
                priority=entry_data.priority,
                enabled=entry_data.enabled,
            )
            db.add(entry)
            imported_count += 1
        except Exception as e:
            skipped_count += 1
            errors.append(f"导入失败: {entry_data.question[:50]}... - {str(e)}")

    await db.flush()

    # 重建索引
    if data.rebuild_index and imported_count > 0:
        try:
            from app.services.knowledge.faq_retriever import FAQRetriever

            # 获取所有需要索引的 FAQ
            stmt = select(FAQEntry).where(FAQEntry.enabled == True)  # noqa: E712
            if data.agent_id:
                stmt = stmt.where(FAQEntry.agent_id == data.agent_id)

            result = await db.execute(stmt)
            entries = result.scalars().all()

            # 转换为字典列表
            entries_data = [
                {
                    "id": e.id,
                    "question": e.question,
                    "answer": e.answer,
                    "category": e.category,
                    "tags": e.tags,
                    "source": e.source,
                    "enabled": e.enabled,
                }
                for e in entries
            ]

            # 索引到向量库
            retriever = FAQRetriever(agent_id=data.agent_id)
            indexed = await retriever.index_entries(entries_data)

            logger.info("FAQ 索引完成", indexed_count=indexed, agent_id=data.agent_id)

            # 更新 knowledge_config 的 data_version
            if data.agent_id:
                stmt = select(Agent).where(Agent.id == data.agent_id)
                result = await db.execute(stmt)
                agent = result.scalar_one_or_none()
                if agent and agent.knowledge_config_id:
                    kc_stmt = select(KnowledgeConfig).where(
                        KnowledgeConfig.id == agent.knowledge_config_id
                    )
                    kc_result = await db.execute(kc_stmt)
                    kc = kc_result.scalar_one_or_none()
                    if kc:
                        kc.data_version = str(uuid.uuid4())[:8]
                        await db.flush()
                        agent_service.invalidate_agent(data.agent_id)

        except Exception as e:
            errors.append(f"索引重建失败: {str(e)}")
            logger.error("FAQ 索引重建失败", error=str(e))

    logger.info(
        "FAQ 导入完成",
        imported_count=imported_count,
        skipped_count=skipped_count,
        error_count=len(errors),
    )

    return FAQImportResponse(
        imported_count=imported_count,
        skipped_count=skipped_count,
        errors=errors,
    )


@faq_router.post("/rebuild-index", status_code=status.HTTP_204_NO_CONTENT)
async def rebuild_faq_index(
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """重建 FAQ 索引"""
    from app.services.knowledge.faq_retriever import FAQRetriever

    stmt = select(FAQEntry).where(FAQEntry.enabled == True)  # noqa: E712
    if agent_id:
        stmt = stmt.where(FAQEntry.agent_id == agent_id)

    result = await db.execute(stmt)
    entries = result.scalars().all()

    entries_data = [
        {
            "id": e.id,
            "question": e.question,
            "answer": e.answer,
            "category": e.category,
            "tags": e.tags,
            "source": e.source,
            "enabled": e.enabled,
        }
        for e in entries
    ]

    retriever = FAQRetriever(agent_id=agent_id)
    indexed = await retriever.index_entries(entries_data)

    logger.info("FAQ 索引重建完成", indexed_count=indexed, agent_id=agent_id)


@faq_router.get("/export", response_model=list[FAQEntryResponse])
async def export_faq_entries(
    agent_id: str | None = None,
    category: str | None = None,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """导出 FAQ 条目

    支持按 Agent、分类、启用状态过滤导出。
    返回完整的 FAQ 条目列表，可用于训练数据准备。

    训练数据格式建议：
    - JSONL: {"prompt": question, "completion": answer, "metadata": {...}}
    """
    stmt = select(FAQEntry)

    if agent_id:
        stmt = stmt.where(FAQEntry.agent_id == agent_id)
    if category:
        stmt = stmt.where(FAQEntry.category == category)
    if enabled is not None:
        stmt = stmt.where(FAQEntry.enabled == enabled)

    stmt = stmt.order_by(FAQEntry.priority.desc(), FAQEntry.created_at.desc())

    result = await db.execute(stmt)
    entries = result.scalars().all()

    logger.info(
        "FAQ 导出",
        count=len(entries),
        agent_id=agent_id,
        category=category,
        enabled=enabled,
    )

    return [FAQEntryResponse.model_validate(e) for e in entries]


# ========== Suggested Questions (Admin) ==========

suggested_questions_router = APIRouter(
    prefix="/api/v1/admin/agents/{agent_id}/suggested-questions",
    tags=["suggested-questions"],
)


@suggested_questions_router.get("", response_model=list[SuggestedQuestionResponse])
async def list_suggested_questions(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 的推荐问题列表"""
    stmt = (
        select(SuggestedQuestion)
        .where(SuggestedQuestion.agent_id == agent_id)
        .order_by(SuggestedQuestion.weight.desc(), SuggestedQuestion.click_count.desc())
    )
    result = await db.execute(stmt)
    questions = result.scalars().all()
    return [SuggestedQuestionResponse.model_validate(q) for q in questions]


@suggested_questions_router.post("", response_model=SuggestedQuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_suggested_question(
    agent_id: str,
    data: SuggestedQuestionCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建推荐问题"""
    # 验证 Agent 存在
    agent_stmt = select(Agent).where(Agent.id == agent_id)
    agent_result = await db.execute(agent_stmt)
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent 不存在")

    question = SuggestedQuestion(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        question=data.question,
        source=data.source,
        faq_entry_id=data.faq_entry_id,
        weight=data.weight,
        display_position=data.display_position,
        enabled=data.enabled,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(question)
    await db.flush()
    await db.refresh(question)

    logger.info("创建推荐问题", question_id=question.id, agent_id=agent_id)
    return SuggestedQuestionResponse.model_validate(question)


@suggested_questions_router.post("/batch", response_model=list[SuggestedQuestionResponse])
async def batch_create_suggested_questions(
    agent_id: str,
    data: SuggestedQuestionBatchCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """批量创建推荐问题"""
    # 验证 Agent 存在
    agent_stmt = select(Agent).where(Agent.id == agent_id)
    agent_result = await db.execute(agent_stmt)
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent 不存在")

    questions = []
    for i, q_text in enumerate(data.questions):
        question = SuggestedQuestion(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            question=q_text,
            source="manual",
            weight=len(data.questions) - i,  # 按顺序设置权重
            display_position=data.display_position,
            enabled=True,
        )
        db.add(question)
        questions.append(question)

    await db.flush()
    for q in questions:
        await db.refresh(q)

    logger.info("批量创建推荐问题", count=len(questions), agent_id=agent_id)
    return [SuggestedQuestionResponse.model_validate(q) for q in questions]


@suggested_questions_router.post("/import-from-faq", response_model=list[SuggestedQuestionResponse])
async def import_from_faq(
    agent_id: str,
    data: SuggestedQuestionImportFromFAQ,
    db: AsyncSession = Depends(get_db_session),
):
    """从 FAQ 导入热门问题"""
    # 验证 Agent 存在
    agent_stmt = select(Agent).where(Agent.id == agent_id)
    agent_result = await db.execute(agent_stmt)
    if not agent_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Agent 不存在")

    # 查询 FAQ（按优先级排序）
    faq_stmt = (
        select(FAQEntry)
        .where(FAQEntry.agent_id == agent_id, FAQEntry.enabled == True)  # noqa: E712
    )
    if data.category:
        faq_stmt = faq_stmt.where(FAQEntry.category == data.category)

    faq_stmt = faq_stmt.order_by(FAQEntry.priority.desc()).limit(data.limit)

    faq_result = await db.execute(faq_stmt)
    faq_entries = faq_result.scalars().all()

    if not faq_entries:
        raise HTTPException(status_code=404, detail="未找到符合条件的 FAQ")

    questions = []
    for i, faq in enumerate(faq_entries):
        # 检查是否已存在
        existing_stmt = select(SuggestedQuestion).where(
            SuggestedQuestion.agent_id == agent_id,
            SuggestedQuestion.faq_entry_id == faq.id,
        )
        existing_result = await db.execute(existing_stmt)
        if existing_result.scalar_one_or_none():
            continue

        question = SuggestedQuestion(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            question=faq.question[:200],  # 截断以符合长度限制
            source="faq",
            faq_entry_id=faq.id,
            weight=len(faq_entries) - i,
            display_position=data.display_position,
            enabled=True,
        )
        db.add(question)
        questions.append(question)

    await db.flush()
    for q in questions:
        await db.refresh(q)

    logger.info("从 FAQ 导入推荐问题", count=len(questions), agent_id=agent_id)
    return [SuggestedQuestionResponse.model_validate(q) for q in questions]


@suggested_questions_router.post("/reorder", status_code=status.HTTP_204_NO_CONTENT)
async def reorder_suggested_questions(
    agent_id: str,
    data: SuggestedQuestionReorder,
    db: AsyncSession = Depends(get_db_session),
):
    """重新排序推荐问题"""
    for i, question_id in enumerate(data.question_ids):
        stmt = select(SuggestedQuestion).where(
            SuggestedQuestion.id == question_id,
            SuggestedQuestion.agent_id == agent_id,
        )
        result = await db.execute(stmt)
        question = result.scalar_one_or_none()
        if question:
            question.weight = len(data.question_ids) - i

    await db.flush()
    logger.info("重新排序推荐问题", agent_id=agent_id, count=len(data.question_ids))


# 单个问题操作路由
suggested_question_item_router = APIRouter(
    prefix="/api/v1/admin/suggested-questions",
    tags=["suggested-questions"],
)


@suggested_question_item_router.get("/{question_id}", response_model=SuggestedQuestionResponse)
async def get_suggested_question(
    question_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取单个推荐问题"""
    stmt = select(SuggestedQuestion).where(SuggestedQuestion.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="推荐问题不存在")

    return SuggestedQuestionResponse.model_validate(question)


@suggested_question_item_router.patch("/{question_id}", response_model=SuggestedQuestionResponse)
async def update_suggested_question(
    question_id: str,
    data: SuggestedQuestionUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新推荐问题"""
    stmt = select(SuggestedQuestion).where(SuggestedQuestion.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="推荐问题不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(question, key, value)

    await db.flush()
    await db.refresh(question)

    logger.info("更新推荐问题", question_id=question_id)
    return SuggestedQuestionResponse.model_validate(question)


@suggested_question_item_router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suggested_question(
    question_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除推荐问题"""
    stmt = select(SuggestedQuestion).where(SuggestedQuestion.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="推荐问题不存在")

    await db.delete(question)
    logger.info("删除推荐问题", question_id=question_id)
