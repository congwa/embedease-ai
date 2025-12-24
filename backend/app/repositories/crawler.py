"""爬取模块 Repository"""

import hashlib
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawler import (
    CrawlPage,
    CrawlPageStatus,
    CrawlSite,
    CrawlSiteStatus,
    CrawlTask,
    CrawlTaskStatus,
)
from app.repositories.base import BaseRepository


class CrawlSiteRepository(BaseRepository[CrawlSite]):
    """站点配置数据访问"""

    model = CrawlSite

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_active_sites(self) -> list[CrawlSite]:
        """获取所有活跃站点"""
        result = await self.session.execute(
            select(CrawlSite).where(CrawlSite.status == CrawlSiteStatus.ACTIVE.value)
        )
        return list(result.scalars().all())

    async def get_sites_due_for_crawl(self, now: datetime) -> list[CrawlSite]:
        """获取需要执行爬取的站点（next_crawl_at <= now）"""
        result = await self.session.execute(
            select(CrawlSite).where(
                CrawlSite.status == CrawlSiteStatus.ACTIVE.value,
                CrawlSite.cron_expression.isnot(None),
                CrawlSite.next_crawl_at <= now,
            )
        )
        return list(result.scalars().all())

    async def update_crawl_time(
        self, site_id: str, last_crawl_at: datetime, next_crawl_at: datetime | None
    ) -> None:
        """更新爬取时间"""
        await self.session.execute(
            update(CrawlSite)
            .where(CrawlSite.id == site_id)
            .values(last_crawl_at=last_crawl_at, next_crawl_at=next_crawl_at)
        )
        await self.session.flush()

    async def count_by_status(self) -> dict[str, int]:
        """按状态统计站点数量"""
        result = await self.session.execute(
            select(CrawlSite.status, func.count(CrawlSite.id)).group_by(CrawlSite.status)
        )
        return {row[0]: row[1] for row in result.all()}


class CrawlTaskRepository(BaseRepository[CrawlTask]):
    """爬取任务数据访问"""

    model = CrawlTask

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: int) -> CrawlTask | None:  # type: ignore[override]
        """根据 ID 获取任务"""
        return await self.session.get(CrawlTask, id)

    async def get_running_tasks(self) -> list[CrawlTask]:
        """获取运行中的任务"""
        result = await self.session.execute(
            select(CrawlTask).where(CrawlTask.status == CrawlTaskStatus.RUNNING.value)
        )
        return list(result.scalars().all())

    async def get_tasks_by_site(
        self, site_id: str, limit: int = 10
    ) -> list[CrawlTask]:
        """获取站点的任务列表"""
        result = await self.session.execute(
            select(CrawlTask)
            .where(CrawlTask.site_id == site_id)
            .order_by(CrawlTask.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_task(self, site_id: str) -> CrawlTask:
        """创建新任务"""
        task = CrawlTask(site_id=site_id, status=CrawlTaskStatus.PENDING.value)
        return await self.create(task)

    async def update_task_status(
        self,
        task_id: int,
        status: CrawlTaskStatus,
        error_message: str | None = None,
    ) -> None:
        """更新任务状态"""
        values: dict = {"status": status.value}
        if status == CrawlTaskStatus.RUNNING:
            values["started_at"] = datetime.now()
        elif status in (
            CrawlTaskStatus.COMPLETED,
            CrawlTaskStatus.FAILED,
            CrawlTaskStatus.CANCELLED,
        ):
            values["finished_at"] = datetime.now()
        if error_message:
            values["error_message"] = error_message

        await self.session.execute(
            update(CrawlTask).where(CrawlTask.id == task_id).values(**values)
        )
        await self.session.flush()

    async def update_task_stats(
        self,
        task_id: int,
        pages_crawled: int | None = None,
        pages_parsed: int | None = None,
        pages_failed: int | None = None,
        products_found: int | None = None,
        products_created: int | None = None,
        products_updated: int | None = None,
    ) -> None:
        """更新任务统计"""
        values: dict = {}
        if pages_crawled is not None:
            values["pages_crawled"] = pages_crawled
        if pages_parsed is not None:
            values["pages_parsed"] = pages_parsed
        if pages_failed is not None:
            values["pages_failed"] = pages_failed
        if products_found is not None:
            values["products_found"] = products_found
        if products_created is not None:
            values["products_created"] = products_created
        if products_updated is not None:
            values["products_updated"] = products_updated

        if values:
            await self.session.execute(
                update(CrawlTask).where(CrawlTask.id == task_id).values(**values)
            )
            await self.session.flush()

    async def increment_task_stats(
        self,
        task_id: int,
        pages_crawled: int = 0,
        pages_parsed: int = 0,
        pages_failed: int = 0,
        products_found: int = 0,
        products_created: int = 0,
        products_updated: int = 0,
    ) -> None:
        """增量更新任务统计"""
        await self.session.execute(
            update(CrawlTask)
            .where(CrawlTask.id == task_id)
            .values(
                pages_crawled=CrawlTask.pages_crawled + pages_crawled,
                pages_parsed=CrawlTask.pages_parsed + pages_parsed,
                pages_failed=CrawlTask.pages_failed + pages_failed,
                products_found=CrawlTask.products_found + products_found,
                products_created=CrawlTask.products_created + products_created,
                products_updated=CrawlTask.products_updated + products_updated,
            )
        )
        await self.session.flush()

    async def count_by_status(self) -> dict[str, int]:
        """按状态统计任务数量"""
        result = await self.session.execute(
            select(CrawlTask.status, func.count(CrawlTask.id)).group_by(CrawlTask.status)
        )
        return {row[0]: row[1] for row in result.all()}


class CrawlPageRepository(BaseRepository[CrawlPage]):
    """爬取页面数据访问"""

    model = CrawlPage

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_id(self, id: int) -> CrawlPage | None:  # type: ignore[override]
        """根据 ID 获取页面"""
        return await self.session.get(CrawlPage, id)

    async def get_by_url_hash(self, site_id: str, url_hash: str) -> CrawlPage | None:
        """根据 URL 哈希获取页面（用于去重）"""
        result = await self.session.execute(
            select(CrawlPage).where(
                CrawlPage.site_id == site_id, CrawlPage.url_hash == url_hash
            )
        )
        return result.scalar_one_or_none()

    async def page_exists(self, site_id: str, url: str) -> bool:
        """检查页面是否已存在"""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        page = await self.get_by_url_hash(site_id, url_hash)
        return page is not None

    async def create_page(
        self,
        site_id: str,
        task_id: int | None,
        url: str,
        depth: int,
        html_content: str | None = None,
    ) -> CrawlPage:
        """创建页面记录"""
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        content_hash = None
        if html_content:
            content_hash = hashlib.sha256(html_content.encode()).hexdigest()

        page = CrawlPage(
            site_id=site_id,
            task_id=task_id,
            url=url,
            url_hash=url_hash,
            depth=depth,
            html_content=html_content,
            content_hash=content_hash,
            status=CrawlPageStatus.PENDING.value,
        )
        return await self.create(page)

    async def update_page_content(
        self, page_id: int, html_content: str
    ) -> None:
        """更新页面内容"""
        content_hash = hashlib.sha256(html_content.encode()).hexdigest()
        await self.session.execute(
            update(CrawlPage)
            .where(CrawlPage.id == page_id)
            .values(html_content=html_content, content_hash=content_hash)
        )
        await self.session.flush()

    async def update_page_parsed(
        self,
        page_id: int,
        status: CrawlPageStatus,
        is_product_page: bool,
        parsed_data: str | None = None,
        parse_error: str | None = None,
        product_id: str | None = None,
    ) -> None:
        """更新页面解析结果"""
        await self.session.execute(
            update(CrawlPage)
            .where(CrawlPage.id == page_id)
            .values(
                status=status.value,
                is_product_page=is_product_page,
                parsed_data=parsed_data,
                parse_error=parse_error,
                product_id=product_id,
                parsed_at=datetime.now(),
            )
        )
        await self.session.flush()

    async def get_pending_pages(
        self, site_id: str, task_id: int | None = None, limit: int = 100
    ) -> list[CrawlPage]:
        """获取待解析的页面"""
        query = select(CrawlPage).where(
            CrawlPage.site_id == site_id,
            CrawlPage.status == CrawlPageStatus.PENDING.value,
        )
        if task_id:
            query = query.where(CrawlPage.task_id == task_id)
        query = query.order_by(CrawlPage.crawled_at).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pages_by_task(
        self, task_id: int, limit: int = 100, offset: int = 0
    ) -> list[CrawlPage]:
        """获取任务的页面列表"""
        result = await self.session.execute(
            select(CrawlPage)
            .where(CrawlPage.task_id == task_id)
            .order_by(CrawlPage.crawled_at)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_status(self, site_id: str | None = None) -> dict[str, int]:
        """按状态统计页面数量"""
        query = select(CrawlPage.status, func.count(CrawlPage.id)).group_by(
            CrawlPage.status
        )
        if site_id:
            query = query.where(CrawlPage.site_id == site_id)
        result = await self.session.execute(query)
        return {row[0]: row[1] for row in result.all()}

    async def count_total(self) -> int:
        """统计总页面数"""
        result = await self.session.execute(select(func.count(CrawlPage.id)))
        return result.scalar() or 0
