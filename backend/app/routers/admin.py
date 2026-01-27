"""管理后台 API 路由"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crawler_database import get_crawler_db_dep
from app.core.database import get_db
from app.core.errors import raise_service_unavailable
from app.core.logging import get_logger
from app.models.conversation import Conversation, HandoffState
from app.models.crawler import CrawlPage, CrawlSite, CrawlTask, CrawlTaskStatus
from app.models.message import Message
from app.models.product import Product
from app.models.user import User
from app.schemas.admin import (
    AgentStatsInfo,
    ConversationListItem,
    CrawlPageListItem,
    CrawlTaskListItem,
    DashboardStats,
    PaginatedResponse,
    ProductListItem,
    UserListItem,
)
from app.models.agent import Agent

logger = get_logger("router.admin")
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ========== Settings API ==========


class SettingsOverview(BaseModel):
    """系统设置概览"""

    # LLM 配置
    llm_provider: str
    llm_model: str
    llm_base_url: str
    llm_api_key_masked: str

    # Embedding 配置
    embedding_provider: str
    embedding_model: str
    embedding_dimension: int
    embedding_base_url: str | None

    # Rerank 配置
    rerank_enabled: bool
    rerank_provider: str | None
    rerank_model: str | None

    # Memory 配置
    memory_enabled: bool
    memory_store_enabled: bool
    memory_fact_enabled: bool
    memory_graph_enabled: bool

    # Agent 中间件配置
    agent_todo_enabled: bool
    agent_tool_limit_enabled: bool
    agent_tool_retry_enabled: bool
    agent_summarization_enabled: bool

    # Crawler 配置
    crawler_enabled: bool

    # 数据库配置
    database_backend: str  # sqlite, postgres
    database_path: str | None  # SQLite 路径（仅 sqlite）
    database_host: str | None  # PostgreSQL 主机（仅 postgres）
    database_pool_size: int | None  # 连接池大小（仅 postgres）
    checkpoint_db_path: str | None  # Checkpoint 路径（仅 sqlite）

    # Qdrant 配置
    qdrant_host: str
    qdrant_port: int
    qdrant_collection: str

    # MinIO 存储配置
    minio_enabled: bool
    minio_endpoint: str | None
    minio_bucket: str | None
    image_max_size_mb: int
    image_max_count: int


class MiddlewareDefaultsResponse(BaseModel):
    """全局中间件默认值"""

    todo_enabled: bool
    tool_limit_enabled: bool
    tool_limit_run: int | None
    tool_limit_thread: int | None
    tool_retry_enabled: bool
    tool_retry_max_retries: int
    summarization_enabled: bool
    summarization_trigger_messages: int
    summarization_keep_messages: int


class SupervisorConfigResponse(BaseModel):
    """Supervisor 全局配置"""

    enabled: bool
    default_agent_id: str | None
    default_agent_name: str | None
    intent_timeout: float
    allow_multi_agent: bool
    supervisor_agents: list[dict]  # 所有 Supervisor Agent 列表


@router.get("/settings/overview", response_model=SettingsOverview)
async def get_settings_overview():
    """获取系统设置概览"""

    def mask_api_key(key: str) -> str:
        if not key or len(key) < 8:
            return "***"
        return f"{key[:4]}...{key[-4:]}"

    return SettingsOverview(
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_CHAT_MODEL,
        llm_base_url=settings.LLM_BASE_URL,
        llm_api_key_masked=mask_api_key(settings.LLM_API_KEY),
        embedding_provider=settings.EMBEDDING_PROVIDER,
        embedding_model=settings.EMBEDDING_MODEL,
        embedding_dimension=settings.EMBEDDING_DIMENSION,
        embedding_base_url=settings.effective_embedding_base_url,
        rerank_enabled=settings.RERANK_ENABLED,
        rerank_provider=settings.effective_rerank_provider if settings.RERANK_ENABLED else None,
        rerank_model=settings.RERANK_MODEL,
        memory_enabled=settings.MEMORY_ENABLED,
        memory_store_enabled=settings.MEMORY_STORE_ENABLED,
        memory_fact_enabled=settings.MEMORY_FACT_ENABLED,
        memory_graph_enabled=settings.MEMORY_GRAPH_ENABLED,
        agent_todo_enabled=settings.AGENT_TODO_ENABLED,
        agent_tool_limit_enabled=settings.AGENT_TOOL_LIMIT_ENABLED,
        agent_tool_retry_enabled=settings.AGENT_TOOL_RETRY_ENABLED,
        agent_summarization_enabled=settings.AGENT_SUMMARIZATION_ENABLED,
        crawler_enabled=settings.CRAWLER_ENABLED,
        database_backend=settings.DATABASE_BACKEND,
        database_path=settings.DATABASE_PATH if settings.DATABASE_BACKEND == "sqlite" else None,
        database_host=settings.POSTGRES_HOST if settings.DATABASE_BACKEND == "postgres" else None,
        database_pool_size=settings.DATABASE_POOL_SIZE if settings.DATABASE_BACKEND == "postgres" else None,
        checkpoint_db_path=settings.CHECKPOINT_DB_PATH if settings.DATABASE_BACKEND == "sqlite" else None,
        qdrant_host=settings.QDRANT_HOST,
        qdrant_port=settings.QDRANT_PORT,
        qdrant_collection=settings.QDRANT_COLLECTION,
        minio_enabled=settings.MINIO_ENABLED,
        minio_endpoint=settings.MINIO_ENDPOINT if settings.MINIO_ENABLED else None,
        minio_bucket=settings.MINIO_BUCKET_NAME if settings.MINIO_ENABLED else None,
        image_max_size_mb=settings.IMAGE_MAX_SIZE_MB,
        image_max_count=settings.IMAGE_MAX_COUNT_PER_MESSAGE,
    )


@router.get("/settings/middleware-defaults", response_model=MiddlewareDefaultsResponse)
async def get_middleware_defaults():
    """获取全局中间件默认配置"""
    return MiddlewareDefaultsResponse(
        todo_enabled=settings.AGENT_TODO_ENABLED,
        tool_limit_enabled=settings.AGENT_TOOL_LIMIT_ENABLED,
        tool_limit_run=settings.AGENT_TOOL_LIMIT_RUN,
        tool_limit_thread=settings.AGENT_TOOL_LIMIT_THREAD,
        tool_retry_enabled=settings.AGENT_TOOL_RETRY_ENABLED,
        tool_retry_max_retries=settings.AGENT_TOOL_RETRY_MAX_RETRIES,
        summarization_enabled=settings.AGENT_SUMMARIZATION_ENABLED,
        summarization_trigger_messages=settings.AGENT_SUMMARIZATION_TRIGGER_MESSAGES,
        summarization_keep_messages=settings.AGENT_SUMMARIZATION_KEEP_MESSAGES,
    )


@router.get("/settings/supervisor", response_model=SupervisorConfigResponse)
async def get_supervisor_config(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """获取 Supervisor 全局配置"""
    # 获取默认 Supervisor Agent 信息
    default_agent_name = None
    if settings.SUPERVISOR_DEFAULT_AGENT_ID:
        default_agent = await session.scalar(
            select(Agent).where(Agent.id == settings.SUPERVISOR_DEFAULT_AGENT_ID)
        )
        if default_agent:
            default_agent_name = default_agent.name

    # 获取所有 Supervisor Agent
    supervisor_agents_result = await session.execute(
        select(Agent).where(Agent.is_supervisor == True)  # noqa: E712
    )
    supervisor_agents = supervisor_agents_result.scalars().all()

    return SupervisorConfigResponse(
        enabled=settings.SUPERVISOR_ENABLED,
        default_agent_id=settings.SUPERVISOR_DEFAULT_AGENT_ID,
        default_agent_name=default_agent_name,
        intent_timeout=settings.SUPERVISOR_INTENT_TIMEOUT,
        allow_multi_agent=settings.SUPERVISOR_ALLOW_MULTI_AGENT,
        supervisor_agents=[
            {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description,
                "sub_agent_count": len(agent.sub_agents or []),
                "is_default": agent.is_default,
            }
            for agent in supervisor_agents
        ],
    )


@router.get("/settings/raw-config")
async def get_raw_config() -> dict[str, Any]:
    """获取原始配置（只读，用于排查）"""
    return {
        "llm": {
            "provider": settings.LLM_PROVIDER,
            "model": settings.LLM_CHAT_MODEL,
            "base_url": settings.LLM_BASE_URL,
        },
        "embedding": {
            "provider": settings.EMBEDDING_PROVIDER,
            "model": settings.EMBEDDING_MODEL,
            "dimension": settings.EMBEDDING_DIMENSION,
        },
        "rerank": {
            "enabled": settings.RERANK_ENABLED,
            "provider": settings.effective_rerank_provider,
            "model": settings.RERANK_MODEL,
            "top_n": settings.RERANK_TOP_N,
        },
        "memory": {
            "enabled": settings.MEMORY_ENABLED,
            "store_enabled": settings.MEMORY_STORE_ENABLED,
            "fact_enabled": settings.MEMORY_FACT_ENABLED,
            "graph_enabled": settings.MEMORY_GRAPH_ENABLED,
        },
        "agent_middleware": {
            "todo_enabled": settings.AGENT_TODO_ENABLED,
            "tool_limit_enabled": settings.AGENT_TOOL_LIMIT_ENABLED,
            "tool_limit_run": settings.AGENT_TOOL_LIMIT_RUN,
            "tool_retry_enabled": settings.AGENT_TOOL_RETRY_ENABLED,
            "tool_retry_max_retries": settings.AGENT_TOOL_RETRY_MAX_RETRIES,
            "summarization_enabled": settings.AGENT_SUMMARIZATION_ENABLED,
            "summarization_trigger_messages": settings.AGENT_SUMMARIZATION_TRIGGER_MESSAGES,
        },
        "qdrant": {
            "host": settings.QDRANT_HOST,
            "port": settings.QDRANT_PORT,
            "collection": settings.QDRANT_COLLECTION,
        },
        "crawler": {
            "enabled": settings.CRAWLER_ENABLED,
        },
    }


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
    crawler_session: Annotated[AsyncSession, Depends(get_crawler_db_dep)],
):
    """获取仪表盘统计数据"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 基础统计（主数据库 app.db）
    total_products = await session.scalar(select(func.count(Product.id)))
    total_conversations = await session.scalar(select(func.count(Conversation.id)))
    total_users = await session.scalar(select(func.count(User.id)))
    total_messages = await session.scalar(select(func.count(Message.id)))

    # 爬虫统计（爬虫数据库 crawler.db）
    total_crawl_sites = 0
    total_crawl_tasks = 0
    crawl_success_rate = 0.0

    if settings.CRAWLER_ENABLED:
        total_crawl_sites = await crawler_session.scalar(select(func.count(CrawlSite.id)))
        total_crawl_tasks = await crawler_session.scalar(select(func.count(CrawlTask.id)))

        # 计算爬取成功率
        completed_tasks = await crawler_session.scalar(
            select(func.count(CrawlTask.id)).where(
                CrawlTask.status == CrawlTaskStatus.COMPLETED.value
            )
        )
        failed_tasks = await crawler_session.scalar(
            select(func.count(CrawlTask.id)).where(
                CrawlTask.status == CrawlTaskStatus.FAILED.value
            )
        )
        total_finished = (completed_tasks or 0) + (failed_tasks or 0)
        crawl_success_rate = (
            (completed_tasks or 0) / total_finished * 100 if total_finished > 0 else 0
        )

    # 今日统计（主数据库）
    today_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(Conversation.created_at >= today)
    )
    today_messages = await session.scalar(
        select(func.count(Message.id)).where(Message.created_at >= today)
    )

    # 会话状态分布（主数据库）
    ai_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.handoff_state == HandoffState.AI.value
        )
    )
    pending_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.handoff_state == HandoffState.PENDING.value
        )
    )
    human_conversations = await session.scalar(
        select(func.count(Conversation.id)).where(
            Conversation.handoff_state == HandoffState.HUMAN.value
        )
    )

    # Agent 统计
    total_agents = await session.scalar(select(func.count(Agent.id)))
    enabled_agents = await session.scalar(
        select(func.count(Agent.id)).where(Agent.status == "enabled")
    )

    # 获取默认 Agent 信息
    default_agent = await session.scalar(
        select(Agent).where(Agent.is_default == True)  # noqa: E712
    )
    agent_stats = AgentStatsInfo(
        total_agents=total_agents or 0,
        enabled_agents=enabled_agents or 0,
        default_agent_id=default_agent.id if default_agent else None,
        default_agent_name=default_agent.name if default_agent else None,
    )

    return DashboardStats(
        total_products=total_products or 0,
        total_conversations=total_conversations or 0,
        total_users=total_users or 0,
        total_messages=total_messages or 0,
        total_crawl_sites=total_crawl_sites or 0,
        total_crawl_tasks=total_crawl_tasks or 0,
        crawl_success_rate=round(crawl_success_rate, 1),
        today_conversations=today_conversations or 0,
        today_messages=today_messages or 0,
        ai_conversations=ai_conversations or 0,
        pending_conversations=pending_conversations or 0,
        human_conversations=human_conversations or 0,
        agent_stats=agent_stats,
    )


@router.get("/products", response_model=PaginatedResponse[ProductListItem])
async def list_products(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    brand: str | None = None,
    search: str | None = None,
):
    """获取商品列表"""
    query = select(Product)

    # 筛选条件
    if category:
        query = query.where(Product.category == category)
    if brand:
        query = query.where(Product.brand == brand)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # 分页
    query = query.order_by(Product.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ProductListItem.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=((total or 0) + page_size - 1) // page_size,
    )


@router.get("/conversations", response_model=PaginatedResponse[ConversationListItem])
async def list_conversations(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    handoff_state: str | None = None,
    user_id: str | None = None,
):
    """获取会话列表"""
    # 子查询：统计每个会话的消息数
    message_count_subq = (
        select(Message.conversation_id, func.count(Message.id).label("message_count"))
        .group_by(Message.conversation_id)
        .subquery()
    )

    query = select(
        Conversation,
        func.coalesce(message_count_subq.c.message_count, 0).label("message_count"),
    ).outerjoin(
        message_count_subq,
        Conversation.id == message_count_subq.c.conversation_id,
    )

    # 筛选条件
    if handoff_state:
        query = query.where(Conversation.handoff_state == handoff_state)
    if user_id:
        query = query.where(Conversation.user_id == user_id)

    # 总数
    count_query = select(func.count(Conversation.id))
    if handoff_state:
        count_query = count_query.where(Conversation.handoff_state == handoff_state)
    if user_id:
        count_query = count_query.where(Conversation.user_id == user_id)
    total = await session.scalar(count_query)

    # 分页
    query = query.order_by(Conversation.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rows = result.all()

    items = [
        ConversationListItem(
            id=row.Conversation.id,
            user_id=row.Conversation.user_id,
            title=row.Conversation.title,
            handoff_state=row.Conversation.handoff_state,
            handoff_operator=row.Conversation.handoff_operator,
            message_count=row.message_count,
            created_at=row.Conversation.created_at,
            updated_at=row.Conversation.updated_at,
        )
        for row in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=((total or 0) + page_size - 1) // page_size,
    )


@router.get("/users", response_model=PaginatedResponse[UserListItem])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取用户列表"""
    # 子查询：统计每个用户的会话数
    conv_count_subq = (
        select(
            Conversation.user_id, func.count(Conversation.id).label("conversation_count")
        )
        .group_by(Conversation.user_id)
        .subquery()
    )

    query = select(
        User,
        func.coalesce(conv_count_subq.c.conversation_count, 0).label(
            "conversation_count"
        ),
    ).outerjoin(conv_count_subq, User.id == conv_count_subq.c.user_id)

    # 总数
    total = await session.scalar(select(func.count(User.id)))

    # 分页
    query = query.order_by(User.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(query)
    rows = result.all()

    items = [
        UserListItem(
            id=row.User.id,
            conversation_count=row.conversation_count,
            created_at=row.User.created_at,
        )
        for row in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=((total or 0) + page_size - 1) // page_size,
    )


@router.get("/crawl-tasks", response_model=PaginatedResponse[CrawlTaskListItem])
async def list_crawl_tasks(
    crawler_session: Annotated[AsyncSession, Depends(get_crawler_db_dep)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    site_id: str | None = None,
    status: str | None = None,
):
    """获取爬取任务列表（从爬虫数据库 crawler.db）"""
    if not settings.CRAWLER_ENABLED:
        raise_service_unavailable("crawler", "爬虫模块未启用")

    query = select(CrawlTask, CrawlSite.name.label("site_name")).outerjoin(
        CrawlSite, CrawlTask.site_id == CrawlSite.id
    )

    # 筛选条件
    if site_id:
        query = query.where(CrawlTask.site_id == site_id)
    if status:
        query = query.where(CrawlTask.status == status)

    # 总数
    count_query = select(func.count(CrawlTask.id))
    if site_id:
        count_query = count_query.where(CrawlTask.site_id == site_id)
    if status:
        count_query = count_query.where(CrawlTask.status == status)
    try:
        total = await crawler_session.scalar(count_query)
    except OperationalError as exc:
        raise_service_unavailable("crawler", "爬虫数据库不可用", cause=exc)

    # 分页
    query = query.order_by(CrawlTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    try:
        result = await crawler_session.execute(query)
    except OperationalError as exc:
        raise_service_unavailable("crawler", "爬虫数据库不可用", cause=exc)
    rows = result.all()

    items = [
        CrawlTaskListItem(
            id=row.CrawlTask.id,
            site_id=row.CrawlTask.site_id,
            site_name=row.site_name,
            status=row.CrawlTask.status,
            pages_crawled=row.CrawlTask.pages_crawled,
            pages_parsed=row.CrawlTask.pages_parsed,
            pages_failed=row.CrawlTask.pages_failed,
            products_found=row.CrawlTask.products_found,
            products_created=row.CrawlTask.products_created,
            products_updated=row.CrawlTask.products_updated,
            started_at=row.CrawlTask.started_at,
            finished_at=row.CrawlTask.finished_at,
            created_at=row.CrawlTask.created_at,
        )
        for row in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=((total or 0) + page_size - 1) // page_size,
    )


@router.get("/crawl-pages", response_model=PaginatedResponse[CrawlPageListItem])
async def list_crawl_pages(
    crawler_session: Annotated[AsyncSession, Depends(get_crawler_db_dep)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    site_id: str | None = None,
    task_id: int | None = None,
    status: str | None = None,
):
    """获取爬取页面列表（从爬虫数据库 crawler.db）"""
    if not settings.CRAWLER_ENABLED:
        raise_service_unavailable("crawler", "爬虫模块未启用")

    query = select(CrawlPage)

    # 筛选条件
    if site_id:
        query = query.where(CrawlPage.site_id == site_id)
    if task_id:
        query = query.where(CrawlPage.task_id == task_id)
    if status:
        query = query.where(CrawlPage.status == status)

    # 总数
    count_query = select(func.count(CrawlPage.id))
    if site_id:
        count_query = count_query.where(CrawlPage.site_id == site_id)
    if task_id:
        count_query = count_query.where(CrawlPage.task_id == task_id)
    if status:
        count_query = count_query.where(CrawlPage.status == status)
    try:
        total = await crawler_session.scalar(count_query)
    except OperationalError as exc:
        raise_service_unavailable("crawler", "爬虫数据库不可用", cause=exc)

    # 分页
    query = query.order_by(CrawlPage.crawled_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    try:
        result = await crawler_session.execute(query)
        items = result.scalars().all()
    except OperationalError as exc:
        raise_service_unavailable("crawler", "爬虫数据库不可用", cause=exc)

    return PaginatedResponse(
        items=[CrawlPageListItem.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=((total or 0) + page_size - 1) // page_size,
    )


@router.get("/categories")
async def list_categories(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """获取所有商品分类"""
    result = await session.execute(
        select(Product.category)
        .where(Product.category.isnot(None))
        .distinct()
        .order_by(Product.category)
    )
    return [row[0] for row in result.all()]


@router.get("/brands")
async def list_brands(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """获取所有品牌"""
    result = await session.execute(
        select(Product.brand)
        .where(Product.brand.isnot(None))
        .distinct()
        .order_by(Product.brand)
    )
    return [row[0] for row in result.all()]
