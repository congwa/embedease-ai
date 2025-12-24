"""爬取定时调度器

基于 APScheduler 实现的定时任务调度器，支持：
1. 根据站点配置的 cron 表达式自动触发爬取
2. 手动触发爬取任务
3. 任务状态监控
"""

import asyncio
from datetime import datetime
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.repositories.crawler import CrawlSiteRepository, CrawlTaskRepository
from app.services.crawler.crawler_service import CrawlerService

logger = get_logger("crawler.scheduler")


class CrawlScheduler:
    """爬取定时调度器

    管理所有站点的定时爬取任务
    """

    _instance: "CrawlScheduler | None" = None

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._running = False
        self._job_ids: dict[str, str] = {}  # site_id -> job_id

    @classmethod
    def get_instance(cls) -> "CrawlScheduler":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = CrawlScheduler()
        return cls._instance

    async def start(self) -> None:
        """启动调度器"""
        if self._running:
            logger.warning("调度器已在运行")
            return

        if not settings.CRAWLER_ENABLED:
            logger.info("爬取模块未启用，跳过调度器启动")
            return

        # 启动调度器
        self.scheduler.start()
        self._running = True
        logger.info("爬取调度器已启动")

        # 加载站点配置
        await self._load_site_schedules()

        # 添加定期检查任务
        self.scheduler.add_job(
            self._check_and_update_schedules,
            "interval",
            minutes=settings.CRAWLER_SCHEDULE_CHECK_INTERVAL,
            id="schedule_checker",
        )

    async def stop(self) -> None:
        """停止调度器"""
        if not self._running:
            return

        self.scheduler.shutdown(wait=True)
        self._running = False
        self._job_ids.clear()
        logger.info("爬取调度器已停止")

    async def _load_site_schedules(self) -> None:
        """加载所有站点的定时配置"""
        async with get_db_context() as session:
            site_repo = CrawlSiteRepository(session)
            sites = await site_repo.get_active_sites()

            for site in sites:
                if site.cron_expression:
                    await self._add_site_job(site.id, site.cron_expression)

    async def _add_site_job(self, site_id: str, cron_expression: str) -> None:
        """为站点添加定时任务

        Args:
            site_id: 站点 ID
            cron_expression: cron 表达式
        """
        try:
            # 移除旧任务
            if site_id in self._job_ids:
                self.scheduler.remove_job(self._job_ids[site_id])

            # 解析 cron 表达式
            trigger = CronTrigger.from_crontab(cron_expression)

            # 添加新任务
            job = self.scheduler.add_job(
                self._execute_crawl_job,
                trigger=trigger,
                args=[site_id],
                id=f"crawl_{site_id}",
                replace_existing=True,
            )

            self._job_ids[site_id] = job.id
            logger.info(
                "添加站点定时任务",
                site_id=site_id,
                cron=cron_expression,
                next_run=job.next_run_time,
            )

            # 更新站点的下次执行时间
            if job.next_run_time:
                async with get_db_context() as session:
                    site_repo = CrawlSiteRepository(session)
                    site = await site_repo.get_by_id(site_id)
                    if site:
                        await site_repo.update_crawl_time(
                            site_id,
                            site.last_crawl_at or datetime.now(),
                            job.next_run_time.replace(tzinfo=None),
                        )

        except Exception as e:
            logger.error("添加站点定时任务失败", site_id=site_id, error=str(e))

    async def _remove_site_job(self, site_id: str) -> None:
        """移除站点定时任务"""
        if site_id in self._job_ids:
            try:
                self.scheduler.remove_job(self._job_ids[site_id])
                del self._job_ids[site_id]
                logger.info("移除站点定时任务", site_id=site_id)
            except Exception as e:
                logger.error("移除站点定时任务失败", site_id=site_id, error=str(e))

    async def _execute_crawl_job(self, site_id: str) -> None:
        """执行爬取任务（由调度器调用）"""
        logger.info("定时任务触发爬取", site_id=site_id)
        try:
            async with get_db_context() as session:
                crawler = CrawlerService(session)
                try:
                    task_id = await crawler.crawl_site(site_id)
                    logger.info("定时爬取任务已启动", site_id=site_id, task_id=task_id)
                finally:
                    await crawler.close()

        except Exception as e:
            logger.error("定时爬取任务失败", site_id=site_id, error=str(e))

    async def _check_and_update_schedules(self) -> None:
        """检查并更新站点调度配置"""
        try:
            async with get_db_context() as session:
                site_repo = CrawlSiteRepository(session)
                sites = await site_repo.get_active_sites()

                current_site_ids = set()
                for site in sites:
                    current_site_ids.add(site.id)
                    if site.cron_expression:
                        # 检查是否需要更新
                        if site.id not in self._job_ids:
                            await self._add_site_job(site.id, site.cron_expression)
                    else:
                        # 移除无 cron 配置的任务
                        await self._remove_site_job(site.id)

                # 移除已删除站点的任务
                for site_id in list(self._job_ids.keys()):
                    if site_id not in current_site_ids:
                        await self._remove_site_job(site_id)

        except Exception as e:
            logger.error("检查调度配置失败", error=str(e))

    async def trigger_crawl(self, site_id: str) -> int:
        """手动触发爬取任务

        Args:
            site_id: 站点 ID

        Returns:
            任务 ID
        """
        async with get_db_context() as session:
            crawler = CrawlerService(session)
            try:
                task_id = await crawler.crawl_site(site_id)
                return task_id
            finally:
                await crawler.close()

    async def update_site_schedule(
        self, site_id: str, cron_expression: str | None
    ) -> None:
        """更新站点调度配置

        Args:
            site_id: 站点 ID
            cron_expression: cron 表达式，为 None 时移除定时任务
        """
        if cron_expression:
            await self._add_site_job(site_id, cron_expression)
        else:
            await self._remove_site_job(site_id)

    def get_next_run_time(self, site_id: str) -> datetime | None:
        """获取站点下次执行时间"""
        if site_id in self._job_ids:
            job = self.scheduler.get_job(self._job_ids[site_id])
            if job and job.next_run_time:
                return job.next_run_time.replace(tzinfo=None)
        return None

    def get_status(self) -> dict:
        """获取调度器状态"""
        jobs = []
        for site_id, job_id in self._job_ids.items():
            job = self.scheduler.get_job(job_id)
            if job:
                jobs.append({
                    "site_id": site_id,
                    "job_id": job_id,
                    "next_run_time": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                })

        return {
            "running": self._running,
            "job_count": len(self._job_ids),
            "jobs": jobs,
        }


def calculate_next_run(cron_expression: str, base_time: datetime | None = None) -> datetime:
    """计算下次执行时间

    Args:
        cron_expression: cron 表达式
        base_time: 基准时间，默认为当前时间

    Returns:
        下次执行时间
    """
    if base_time is None:
        base_time = datetime.now()
    cron = croniter(cron_expression, base_time)
    return cron.get_next(datetime)


# 全局调度器实例
scheduler = CrawlScheduler.get_instance()
