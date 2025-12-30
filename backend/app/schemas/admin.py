"""管理后台 Schema"""

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class DashboardStats(BaseModel):
    """仪表盘统计"""

    total_products: int
    total_conversations: int
    total_users: int
    total_messages: int
    # 爬虫统计
    total_crawl_sites: int
    total_crawl_tasks: int
    crawl_success_rate: float
    # 今日统计
    today_conversations: int
    today_messages: int
    # 会话状态分布
    ai_conversations: int
    pending_conversations: int
    human_conversations: int


class ProductListItem(BaseModel):
    """商品列表项"""

    id: str
    name: str
    summary: str | None
    price: float | None
    category: str | None
    brand: str | None
    source_site_id: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    """会话列表项"""

    id: str
    user_id: str
    title: str
    handoff_state: str
    handoff_operator: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListItem(BaseModel):
    """用户列表项"""

    id: str
    conversation_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlTaskListItem(BaseModel):
    """爬取任务列表项"""

    id: int
    site_id: str
    site_name: str | None
    status: str
    pages_crawled: int
    pages_parsed: int
    pages_failed: int
    products_found: int
    products_created: int
    products_updated: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class CrawlPageListItem(BaseModel):
    """爬取页面列表项"""

    id: int
    site_id: str
    task_id: int | None
    url: str
    depth: int
    status: str
    is_product_page: bool | None
    product_id: str | None
    parse_error: str | None
    crawled_at: datetime
    parsed_at: datetime | None

    class Config:
        from_attributes = True
