"""爬取模块数据模型

表结构设计：
1. CrawlSite - 站点配置表：存储目标网站的爬取规则
2. CrawlPage - 原始页面表：存储爬取的原始 HTML 内容
3. CrawlTask - 爬取任务表：记录每次爬取任务的执行状态和日志

注意：爬虫模型使用独立的 CrawlerBase，存储在 crawler.db 中，
与主应用数据库 (app.db) 分离，避免死锁和阻塞用户查询。
"""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class CrawlerBase(DeclarativeBase):
    """爬虫模块独立的基础模型类
    
    使用独立的 metadata，对应独立的 crawler.db 数据库
    """

    pass


class CrawlSiteStatus(str, Enum):
    """站点状态"""

    ACTIVE = "active"  # 启用
    PAUSED = "paused"  # 暂停
    DISABLED = "disabled"  # 禁用


class CrawlTaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"  # 待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 取消


class CrawlPageStatus(str, Enum):
    """页面状态"""

    PENDING = "pending"  # 待解析
    PARSED = "parsed"  # 已解析
    FAILED = "failed"  # 解析失败
    SKIPPED = "skipped"  # 跳过（非商品页）
    SKIPPED_DUPLICATE = "skipped_duplicate"  # 跳过（内容未变化）


class CrawlSite(CrawlerBase):
    """站点配置表

    存储目标网站的爬取配置，包括：
    - 基本信息：名称、起始 URL
    - 爬取规则：链接选择器、最大深度、页面限制
    - 字段提取规则：CSS/XPath 选择器或 LLM 解析提示词
    - 调度配置：定时任务 cron 表达式
    """

    __tablename__ = "crawl_sites"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="站点名称")
    start_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="起始 URL")
    domain: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True, comment="站点域名（规范化后，用于去重）"
    )
    status: Mapped[str] = mapped_column(
        String(20), default=CrawlSiteStatus.ACTIVE.value, comment="站点状态"
    )
    is_system_site: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否为系统配置站点（不可通过 API 删除）"
    )

    # 爬取规则
    link_pattern: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="商品链接正则/glob 模式，如 /product/*"
    )
    max_depth: Mapped[int] = mapped_column(Integer, default=3, comment="最大爬取深度")
    max_pages: Mapped[int] = mapped_column(Integer, default=500, comment="最大页面数")
    crawl_delay: Mapped[float] = mapped_column(
        Float, default=1.0, comment="请求间隔（秒）"
    )

    # SPA 支持
    is_spa: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="是否为 SPA 网站（需要 JS 渲染）"
    )
    wait_for_selector: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="SPA 等待的 CSS 选择器"
    )
    wait_timeout: Mapped[int] = mapped_column(
        Integer, default=10, comment="SPA 等待超时（秒）"
    )

    # 字段提取规则（JSON 格式，支持 CSS 选择器或 LLM 提示词）
    # 格式示例：
    # {
    #   "mode": "selector",  # selector 或 llm
    #   "fields": {
    #     "name": ".product-title::text",
    #     "price": ".product-price::text",
    #     "description": ".product-desc::text"
    #   }
    # }
    # 或 LLM 模式：
    # {
    #   "mode": "llm",
    #   "prompt": "从以下 HTML 中提取商品信息..."
    # }
    extraction_config: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="字段提取配置（JSON）"
    )

    # 调度配置
    cron_expression: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="定时任务 cron 表达式，如 0 2 * * *"
    )
    last_crawl_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="上次爬取时间"
    )
    next_crawl_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="下次计划爬取时间"
    )

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # 关系
    tasks: Mapped[list["CrawlTask"]] = relationship(
        "CrawlTask", back_populates="site", lazy="dynamic"
    )
    pages: Mapped[list["CrawlPage"]] = relationship(
        "CrawlPage", back_populates="site", lazy="dynamic"
    )


class CrawlTask(CrawlerBase):
    """爬取任务表

    记录每次爬取任务的执行状态、统计信息和日志
    """

    __tablename__ = "crawl_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("crawl_sites.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=CrawlTaskStatus.PENDING.value, comment="任务状态"
    )

    # 统计信息
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, comment="已爬取页面数")
    pages_parsed: Mapped[int] = mapped_column(Integer, default=0, comment="成功解析页面数")
    pages_failed: Mapped[int] = mapped_column(Integer, default=0, comment="解析失败页面数")
    pages_skipped_duplicate: Mapped[int] = mapped_column(Integer, default=0, comment="跳过的重复页面数")
    products_found: Mapped[int] = mapped_column(Integer, default=0, comment="发现商品数")
    products_created: Mapped[int] = mapped_column(Integer, default=0, comment="新增商品数")
    products_updated: Mapped[int] = mapped_column(Integer, default=0, comment="更新商品数")
    products_skipped: Mapped[int] = mapped_column(Integer, default=0, comment="跳过的重复商品数")

    # 执行时间
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 错误信息
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    # 关系
    site: Mapped["CrawlSite"] = relationship("CrawlSite", back_populates="tasks")
    pages: Mapped[list["CrawlPage"]] = relationship(
        "CrawlPage", back_populates="task", lazy="dynamic"
    )


class CrawlPage(CrawlerBase):
    """原始页面表

    存储爬取的原始 HTML 内容，用于：
    - 调试和回溯
    - 重新解析（当提取规则更新时）
    - 数据审计
    """

    __tablename__ = "crawl_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("crawl_sites.id"), nullable=False
    )
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("crawl_tasks.id"), nullable=True
    )

    # 页面信息
    url: Mapped[str] = mapped_column(String(1000), nullable=False, comment="页面 URL")
    url_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True, comment="URL 哈希（用于去重）"
    )
    depth: Mapped[int] = mapped_column(Integer, default=0, comment="爬取深度")

    # 原始内容
    html_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始 HTML")
    content_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="内容哈希（用于检测变化）"
    )
    version: Mapped[int] = mapped_column(Integer, default=1, comment="页面版本号（内容变化时递增）")

    # 解析状态
    status: Mapped[str] = mapped_column(
        String(20), default=CrawlPageStatus.PENDING.value, comment="页面状态"
    )
    is_product_page: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, comment="是否为商品页"
    )

    # 解析结果（JSON 格式，存储提取的商品数据）
    parsed_data: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="解析结果（JSON）"
    )
    parse_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="解析错误信息"
    )

    # 关联的商品 ID（如果成功解析并入库）
    product_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="关联商品 ID"
    )

    # 时间戳
    crawled_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False, comment="爬取时间"
    )
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="解析时间"
    )

    # 关系
    site: Mapped["CrawlSite"] = relationship("CrawlSite", back_populates="pages")
    task: Mapped["CrawlTask | None"] = relationship("CrawlTask", back_populates="pages")
