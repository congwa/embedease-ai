"""爬取模块相关 Schema"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CrawlSiteStatus(str, Enum):
    """站点状态"""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


class CrawlTaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlPageStatus(str, Enum):
    """页面状态"""

    PENDING = "pending"
    PARSED = "parsed"
    FAILED = "failed"
    SKIPPED = "skipped"
    SKIPPED_DUPLICATE = "skipped_duplicate"  # 跳过（内容未变化）


class RetryMode(str, Enum):
    """重试模式"""

    INCREMENTAL = "incremental"  # 增量模式：不清空页面，仅重新触发任务（根据 content_hash 跳过未变化的页面）
    FORCE = "force"  # 强制模式：清空所有页面后重新爬取


class ExtractionMode(str, Enum):
    """字段提取模式"""

    SELECTOR = "selector"  # CSS/XPath 选择器
    LLM = "llm"  # LLM 智能解析


class FieldExtractionConfig(BaseModel):
    """字段提取配置（选择器模式）"""

    name: str | None = Field(None, description="商品名称选择器")
    price: str | None = Field(None, description="价格选择器")
    summary: str | None = Field(None, description="摘要选择器")
    description: str | None = Field(None, description="描述选择器")
    category: str | None = Field(None, description="分类选择器")
    tags: str | None = Field(None, description="标签选择器")
    brand: str | None = Field(None, description="品牌选择器")
    image_urls: str | None = Field(None, description="图片选择器")
    specs: str | None = Field(None, description="规格选择器")


class ExtractionConfig(BaseModel):
    """提取配置"""

    mode: ExtractionMode = Field(
        ExtractionMode.LLM, description="提取模式：selector 或 llm"
    )
    fields: FieldExtractionConfig | None = Field(
        None, description="选择器模式的字段配置"
    )
    prompt: str | None = Field(None, description="LLM 模式的提取提示词")
    product_page_indicator: str | None = Field(
        None, description="商品页判断标识（CSS 选择器或关键词）"
    )


class CrawlSiteCreate(BaseModel):
    """创建站点配置"""

    id: str = Field(..., description="站点 ID（唯一标识）")
    name: str = Field(..., description="站点名称")
    start_url: str = Field(..., description="起始 URL")
    status: CrawlSiteStatus = Field(CrawlSiteStatus.ACTIVE, description="站点状态")

    # 爬取规则
    link_pattern: str | None = Field(
        None, description="商品链接正则/glob 模式，如 /product/*"
    )
    max_depth: int = Field(3, description="最大爬取深度")
    max_pages: int = Field(500, description="最大页面数")
    crawl_delay: float = Field(1.0, description="请求间隔（秒）")

    # SPA 支持
    is_spa: bool = Field(True, description="是否为 SPA 网站")
    wait_for_selector: str | None = Field(None, description="SPA 等待的 CSS 选择器")
    wait_timeout: int = Field(10, description="SPA 等待超时（秒）")

    # 字段提取配置
    extraction_config: ExtractionConfig | None = Field(
        None, description="字段提取配置"
    )

    # 调度配置
    cron_expression: str | None = Field(
        None, description="定时任务 cron 表达式，如 0 2 * * *"
    )


class CrawlSiteUpdate(BaseModel):
    """更新站点配置"""

    name: str | None = None
    start_url: str | None = None
    status: CrawlSiteStatus | None = None
    link_pattern: str | None = None
    max_depth: int | None = None
    max_pages: int | None = None
    crawl_delay: float | None = None
    is_spa: bool | None = None
    wait_for_selector: str | None = None
    wait_timeout: int | None = None
    extraction_config: ExtractionConfig | None = None
    cron_expression: str | None = None


class CrawlSiteResponse(BaseModel):
    """站点配置响应"""

    id: str
    name: str
    start_url: str
    status: CrawlSiteStatus
    link_pattern: str | None
    max_depth: int
    max_pages: int
    crawl_delay: float
    is_spa: bool
    wait_for_selector: str | None
    wait_timeout: int
    extraction_config: ExtractionConfig | None
    cron_expression: str | None
    last_crawl_at: datetime | None
    next_crawl_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CrawlSiteRetryResponse(BaseModel):
    """站点重试结果"""

    site_id: str
    deleted_pages: int
    task: CrawlTaskResponse


class CrawlTaskRetryResponse(BaseModel):
    """任务重试结果"""

    site_id: str
    original_task_id: int
    deleted_pages: int
    task: CrawlTaskResponse


class CrawlTaskCreate(BaseModel):
    """创建爬取任务"""

    site_id: str = Field(..., description="站点 ID")


class CrawlTaskResponse(BaseModel):
    """爬取任务响应"""

    id: int
    site_id: str
    status: CrawlTaskStatus
    pages_crawled: int
    pages_parsed: int
    pages_failed: int
    products_found: int
    products_created: int
    products_updated: int
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CrawlPageResponse(BaseModel):
    """爬取页面响应"""

    id: int
    site_id: str
    task_id: int | None
    url: str
    depth: int
    status: CrawlPageStatus
    is_product_page: bool | None
    product_id: str | None
    crawled_at: datetime
    parsed_at: datetime | None
    parse_error: str | None

    model_config = {"from_attributes": True}


class ParsedProductData(BaseModel):
    """解析后的商品数据"""

    id: str | None = Field(None, description="商品 ID（可从 URL 提取）")
    name: str = Field(..., description="商品名称")
    summary: str | None = Field(None, description="核心卖点")
    description: str | None = Field(None, description="详细描述")
    price: float | None = Field(None, description="价格")
    category: str | None = Field(None, description="分类")
    url: str | None = Field(None, description="商品链接")
    tags: list[str] | None = Field(None, description="标签列表")
    brand: str | None = Field(None, description="品牌")
    image_urls: list[str] | None = Field(None, description="图片 URL 列表")
    specs: dict[str, str] | None = Field(None, description="规格")
    extra_metadata: dict | None = Field(None, description="其他信息")


class CrawlStats(BaseModel):
    """爬取统计"""

    total_sites: int = Field(0, description="站点总数")
    active_sites: int = Field(0, description="活跃站点数")
    total_tasks: int = Field(0, description="任务总数")
    running_tasks: int = Field(0, description="运行中任务数")
    total_pages: int = Field(0, description="页面总数")
    total_products: int = Field(0, description="商品总数")
