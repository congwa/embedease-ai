"""管理后台 API 路由"""

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.crawler_database import get_crawler_db_dep
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.conversation import Conversation, HandoffState
from app.models.crawler import CrawlPage, CrawlSite, CrawlTask, CrawlTaskStatus
from app.models.message import Message
from app.models.product import Product
from app.models.user import User
from app.schemas.admin import (
    ConversationListItem,
    CrawlPageListItem,
    CrawlTaskListItem,
    DashboardStats,
    PaginatedResponse,
    ProductListItem,
    UserListItem,
)

logger = get_logger("router.admin")
router = APIRouter(prefix="/admin", tags=["admin"])


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
        total_pages=(total or 0 + page_size - 1) // page_size,
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
        total_pages=(total or 0 + page_size - 1) // page_size,
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
        total_pages=(total or 0 + page_size - 1) // page_size,
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
    total = await crawler_session.scalar(count_query)

    # 分页
    query = query.order_by(CrawlTask.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await crawler_session.execute(query)
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
        total_pages=(total or 0 + page_size - 1) // page_size,
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
    total = await crawler_session.scalar(count_query)

    # 分页
    query = query.order_by(CrawlPage.crawled_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await crawler_session.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[CrawlPageListItem.model_validate(item) for item in items],
        total=total or 0,
        page=page,
        page_size=page_size,
        total_pages=(total or 0 + page_size - 1) // page_size,
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
