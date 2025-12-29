"""爬取模块 Repository"""

import hashlib
from datetime import datetime

from sqlalchemy import delete, func, select, update
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

    async def get_by_domain(self, domain: str) -> CrawlSite | None:
        """根据域名获取站点"""
        result = await self.session.execute(
            select(CrawlSite).where(CrawlSite.domain == domain)
        )
        return result.scalar_one_or_none()

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

    async def has_running_task_for_site(self, site_id: str) -> bool:
        """检查站点是否有运行中的任务（用于并发控制）"""
        result = await self.session.execute(
            select(func.count(CrawlTask.id)).where(
                CrawlTask.site_id == site_id,
                CrawlTask.status == CrawlTaskStatus.RUNNING.value,
            )
        )
        count = result.scalar() or 0
        return count > 0

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
        pages_skipped_duplicate: int = 0,
        products_found: int = 0,
        products_created: int = 0,
        products_updated: int = 0,
        products_skipped: int = 0,
    ) -> None:
        """增量更新任务统计"""
        await self.session.execute(
            update(CrawlTask)
            .where(CrawlTask.id == task_id)
            .values(
                pages_crawled=CrawlTask.pages_crawled + pages_crawled,
                pages_parsed=CrawlTask.pages_parsed + pages_parsed,
                pages_failed=CrawlTask.pages_failed + pages_failed,
                pages_skipped_duplicate=CrawlTask.pages_skipped_duplicate + pages_skipped_duplicate,
                products_found=CrawlTask.products_found + products_found,
                products_created=CrawlTask.products_created + products_created,
                products_updated=CrawlTask.products_updated + products_updated,
                products_skipped=CrawlTask.products_skipped + products_skipped,
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

    async def create_or_update_page(
        self,
        site_id: str,
        task_id: int | None,
        url: str,
        depth: int,
        html_content: str | None = None,
    ) -> tuple[CrawlPage, bool, bool]:
        """创建或更新页面记录（增量模式）
        
        通过 content_hash 检测内容变化：
        - 若页面不存在：创建新记录
        - 若页面存在且内容未变：标记 SKIPPED_DUPLICATE，跳过解析
        - 若页面存在且内容已变：version += 1，更新内容，重新解析
        
        Returns:
            tuple: (page, is_new, content_changed)
            - page: 页面对象
            - is_new: 是否为新页面
            - content_changed: 内容是否变化（新页面或内容更新时为 True）
        """
        url_hash = hashlib.sha256(url.encode()).hexdigest()
        new_content_hash = None
        if html_content:
            new_content_hash = hashlib.sha256(html_content.encode()).hexdigest()

        # 查找现有页面
        existing_page = await self.get_by_url_hash(site_id, url_hash)
        
        if existing_page is None:
            # 新页面：创建记录
            page = CrawlPage(
                site_id=site_id,
                task_id=task_id,
                url=url,
                url_hash=url_hash,
                depth=depth,
                html_content=html_content,
                content_hash=new_content_hash,
                version=1,
                status=CrawlPageStatus.PENDING.value,
            )
            page = await self.create(page)
            return page, True, True
        
        # 页面已存在，检查内容是否变化
        if existing_page.content_hash == new_content_hash:
            # 内容未变化：标记为重复跳过
            await self.session.execute(
                update(CrawlPage)
                .where(CrawlPage.id == existing_page.id)
                .values(
                    task_id=task_id,  # 更新关联的任务 ID
                    status=CrawlPageStatus.SKIPPED_DUPLICATE.value,
                    crawled_at=datetime.now(),
                )
            )
            await self.session.flush()
            # 重新获取更新后的页面
            await self.session.refresh(existing_page)
            return existing_page, False, False
        
        # 内容已变化：更新页面，版本号 +1
        new_version = existing_page.version + 1
        await self.session.execute(
            update(CrawlPage)
            .where(CrawlPage.id == existing_page.id)
            .values(
                task_id=task_id,
                html_content=html_content,
                content_hash=new_content_hash,
                version=new_version,
                status=CrawlPageStatus.PENDING.value,  # 重新解析
                crawled_at=datetime.now(),
                parsed_at=None,  # 清除旧的解析时间
                parsed_data=None,  # 清除旧的解析结果
                parse_error=None,
            )
        )
        await self.session.flush()
        await self.session.refresh(existing_page)
        return existing_page, False, True

    async def create_page(
        self,
        site_id: str,
        task_id: int | None,
        url: str,
        depth: int,
        html_content: str | None = None,
    ) -> CrawlPage:
        """创建页面记录（强制模式，不检查重复）"""
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
            version=1,
            status=CrawlPageStatus.PENDING.value,
        )
        return await self.create(page)

    async def delete_pages_by_task(self, task_id: int) -> int:
        """根据任务删除页面，返回删除数量"""
        result = await self.session.execute(
            delete(CrawlPage).where(CrawlPage.task_id == task_id)
        )
        await self.session.flush()
        return result.rowcount or 0

    async def delete_pages_by_site(self, site_id: str) -> int:
        """删除站点的所有页面，返回删除数量"""
        result = await self.session.execute(
            delete(CrawlPage).where(CrawlPage.site_id == site_id)
        )
        await self.session.flush()
        return result.rowcount or 0

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
