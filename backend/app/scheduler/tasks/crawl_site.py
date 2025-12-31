"""站点爬取任务

封装 CrawlerService，作为定时任务执行。
"""

from app.core.config import settings
from app.core.crawler_database import get_crawler_db
from app.core.logging import get_logger
from app.repositories.crawler import CrawlSiteRepository
from app.scheduler.tasks.base import (
    BaseTask,
    ScheduleType,
    TaskResult,
    TaskSchedule,
)
from app.services.crawler.crawler_service import CrawlerService

logger = get_logger("scheduler.tasks.crawl_site")


class CrawlSiteTask(BaseTask):
    """站点爬取任务

    定时触发站点爬取，调用 CrawlerService 执行实际爬取逻辑。

    Attributes:
        site_id: 站点 ID（单站点场景下可固定或从配置读取）
    """

    name = "crawl_site"
    description = "定时爬取站点内容"

    def __init__(
        self,
        site_id: str | None = None,
        cron_expression: str = "0 2 * * *",  # 默认每天凌晨2点
        run_on_start: bool | None = None,
    ):
        """初始化爬取任务

        Args:
            site_id: 站点 ID，为 None 时自动获取第一个活跃站点
            cron_expression: cron 表达式
        """
        self.site_id = site_id
        schedule_run_on_start = (
            run_on_start if run_on_start is not None else settings.CRAWLER_RUN_ON_START
        )

        self.schedule = TaskSchedule(
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            allow_concurrent=False,  # 不允许并发爬取
            run_on_start=schedule_run_on_start,
        )
        self.enabled = settings.CRAWLER_ENABLED

    async def run(self) -> TaskResult:
        """执行爬取任务

        Returns:
            TaskResult: 执行结果
        """
        if not settings.CRAWLER_ENABLED:
            return TaskResult.skipped("爬虫模块未启用")

        async with get_crawler_db() as session:
            site_repo = CrawlSiteRepository(session)

            # 确定要爬取的站点
            site_id = self.site_id
            if not site_id:
                # 单站点场景：获取第一个活跃站点
                sites = await site_repo.get_active_sites()
                if not sites:
                    return TaskResult.skipped("没有活跃的站点配置")
                site_id = sites[0].id

            # 检查站点是否存在
            site = await site_repo.get_by_id(site_id)
            if not site:
                return TaskResult.failed(f"站点不存在: {site_id}")

            logger.info("开始爬取站点", site_id=site_id, site_name=site.name)

            # 执行爬取
            crawler = CrawlerService(session)
            try:
                task_id = await crawler.crawl_site(site_id)
                logger.info("爬取任务已创建", site_id=site_id, task_id=task_id)
                return TaskResult.success(
                    f"爬取任务已启动: {site.name}",
                    site_id=site_id,
                    task_id=task_id,
                )
            except Exception as e:
                logger.error("爬取任务失败", site_id=site_id, error=str(e))
                return TaskResult.failed(str(e), f"爬取失败: {site.name}")
            finally:
                await crawler.close()
