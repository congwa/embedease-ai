"""Agent 管理 API

提供 Agent、KnowledgeConfig、FAQ 的 CRUD 接口。
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.models.agent import Agent, AgentTool, FAQEntry, KnowledgeConfig
from app.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentToolCreate,
    AgentToolResponse,
    AgentToolUpdate,
    AgentUpdate,
    FAQEntryCreate,
    FAQEntryResponse,
    FAQEntryUpdate,
    FAQImportRequest,
    FAQImportResponse,
    KnowledgeConfigCreate,
    KnowledgeConfigResponse,
    KnowledgeConfigUpdate,
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
    stmt = select(Agent).where(Agent.id == agent_id)
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


@faq_router.get("", response_model=list[FAQEntryResponse])
async def list_faq_entries(
    skip: int = 0,
    limit: int = 50,
    agent_id: str | None = None,
    category: str | None = None,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 FAQ 条目列表"""
    stmt = select(FAQEntry)

    if agent_id:
        stmt = stmt.where(FAQEntry.agent_id == agent_id)
    if category:
        stmt = stmt.where(FAQEntry.category == category)

    stmt = (
        stmt.order_by(FAQEntry.priority.desc(), FAQEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

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


@faq_router.post("", response_model=FAQEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_faq_entry(
    data: FAQEntryCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建 FAQ 条目"""
    entry = FAQEntry(
        id=str(uuid.uuid4()),
        agent_id=data.agent_id,
        question=data.question,
        answer=data.answer,
        category=data.category,
        tags=data.tags,
        source=data.source,
        priority=data.priority,
        enabled=data.enabled,
    )

    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    logger.info("创建 FAQ 条目", entry_id=entry.id)
    return FAQEntryResponse.model_validate(entry)


@faq_router.patch("/{entry_id}", response_model=FAQEntryResponse)
async def update_faq_entry(
    entry_id: str,
    data: FAQEntryUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """更新 FAQ 条目"""
    stmt = select(FAQEntry).where(FAQEntry.id == entry_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="FAQ 条目不存在")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(entry, key, value)

    await db.flush()

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
