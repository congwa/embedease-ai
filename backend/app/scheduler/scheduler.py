"""调度器核心

基于 APScheduler 实现的轻量级任务调度器。
遍历注册的任务，根据 cron/interval 配置触发执行。
"""

import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from croniter import croniter

from app.core.logging import get_logger
from app.scheduler.registry import TaskRegistry, task_registry
from app.scheduler.runner import TaskRunner
from app.scheduler.tasks.base import BaseTask, ScheduleType

logger = get_logger("scheduler.core")


class TaskScheduler:
    """任务调度器

    职责：
    1. 管理调度器生命周期（启动/停止）
    2. 为每个注册的任务创建调度 job
    3. 支持手动触发任务
    4. 提供调度器状态查询

    Example:
        scheduler = TaskScheduler(task_registry)
        await scheduler.start()
        # ... 运行中 ...
        await scheduler.stop()
    """

    def __init__(
        self,
        registry: TaskRegistry | None = None,
        runner: TaskRunner | None = None,
    ):
        self.registry = registry or task_registry
        self.runner = runner or TaskRunner()
        self._scheduler = AsyncIOScheduler()
        self._running = False
        self._job_ids: dict[str, str] = {}  # task_name -> job_id

    @property
    def is_running(self) -> bool:
        """调度器是否正在运行"""
        return self._running

    async def start(self) -> None:
        """启动调度器

        加载所有注册任务并创建调度 job。
        """
        if self._running:
            logger.warning("调度器已在运行")
            return

        # 启动 APScheduler
        self._scheduler.start()
        self._running = True
        logger.info("任务调度器已启动")

        # 为每个任务创建调度 job
        for task in self.registry.list_all():
            await self._add_task_job(task)

    async def stop(self) -> None:
        """停止调度器"""
        if not self._running:
            return

        self._scheduler.shutdown(wait=True)
        self._running = False
        self._job_ids.clear()
        logger.info("任务调度器已停止")

    async def _add_task_job(self, task: BaseTask) -> None:
        """为任务创建调度 job

        Args:
            task: 任务实例
        """
        try:
            # 移除旧 job（如果存在）
            if task.name in self._job_ids:
                self._scheduler.remove_job(self._job_ids[task.name])

            # 根据调度类型创建 trigger
            if task.schedule.schedule_type == ScheduleType.CRON:
                trigger = CronTrigger.from_crontab(task.schedule.cron_expression)
            else:
                trigger = IntervalTrigger(seconds=task.schedule.interval_seconds)

            # 添加 job
            job = self._scheduler.add_job(
                self._execute_task,
                trigger=trigger,
                args=[task.name],
                id=f"task_{task.name}",
                replace_existing=True,
            )

            self._job_ids[task.name] = job.id

            # 更新下次执行时间
            if job.next_run_time:
                self.runner.update_next_run(
                    task.name, job.next_run_time.replace(tzinfo=None)
                )

            logger.info(
                "添加任务调度",
                task_name=task.name,
                schedule_type=task.schedule.schedule_type.value,
                next_run=job.next_run_time,
            )

        except Exception as e:
            logger.error("添加任务调度失败", task_name=task.name, error=str(e))

    async def _remove_task_job(self, task_name: str) -> None:
        """移除任务调度 job

        Args:
            task_name: 任务名称
        """
        if task_name in self._job_ids:
            try:
                self._scheduler.remove_job(self._job_ids[task_name])
                del self._job_ids[task_name]
                logger.info("移除任务调度", task_name=task_name)
            except Exception as e:
                logger.error("移除任务调度失败", task_name=task_name, error=str(e))

    async def _execute_task(self, task_name: str) -> None:
        """执行任务（由调度器触发）

        Args:
            task_name: 任务名称
        """
        task = self.registry.get(task_name)
        if not task:
            logger.warning("任务不存在", task_name=task_name)
            return

        if not task.enabled:
            logger.debug("任务已禁用，跳过", task_name=task_name)
            return

        logger.info("调度触发任务", task_name=task_name)
        await self.runner.execute(task)

        # 更新下次执行时间
        job = self._scheduler.get_job(self._job_ids.get(task_name, ""))
        if job and job.next_run_time:
            self.runner.update_next_run(task_name, job.next_run_time.replace(tzinfo=None))

    async def trigger(self, task_name: str) -> bool:
        """手动触发任务

        Args:
            task_name: 任务名称

        Returns:
            是否成功触发
        """
        task = self.registry.get(task_name)
        if not task:
            logger.warning("任务不存在", task_name=task_name)
            return False

        logger.info("手动触发任务", task_name=task_name)
        asyncio.create_task(self.runner.execute(task))
        return True

    async def refresh_task(self, task_name: str) -> None:
        """刷新任务调度（任务配置变更后调用）

        Args:
            task_name: 任务名称
        """
        task = self.registry.get(task_name)
        if task:
            await self._add_task_job(task)
        else:
            await self._remove_task_job(task_name)

    def get_next_run(self, task_name: str) -> datetime | None:
        """获取任务下次执行时间

        Args:
            task_name: 任务名称

        Returns:
            下次执行时间，不存在则返回 None
        """
        job_id = self._job_ids.get(task_name)
        if job_id:
            job = self._scheduler.get_job(job_id)
            if job and job.next_run_time:
                return job.next_run_time.replace(tzinfo=None)
        return None

    def get_status(self) -> dict:
        """获取调度器状态

        Returns:
            包含运行状态、任务数、各任务状态的字典
        """
        tasks = []
        for task in self.registry.list_all():
            state = self.runner.get_state(task.name)
            tasks.append({
                "name": task.name,
                "description": task.description,
                "enabled": task.enabled,
                "schedule_type": task.schedule.schedule_type.value,
                "cron_expression": task.schedule.cron_expression,
                "interval_seconds": task.schedule.interval_seconds,
                "status": state.status.value,
                "next_run_at": (
                    state.next_run_at.isoformat() if state.next_run_at else None
                ),
                "last_run_at": (
                    state.last_run_at.isoformat() if state.last_run_at else None
                ),
                "last_result": state.last_result,
                "run_count": state.run_count,
                "fail_count": state.fail_count,
            })

        return {
            "running": self._running,
            "task_count": len(self._job_ids),
            "tasks": tasks,
        }


def calculate_next_run(
    schedule_type: ScheduleType,
    cron_expression: str | None = None,
    interval_seconds: int | None = None,
    base_time: datetime | None = None,
) -> datetime:
    """计算下次执行时间

    Args:
        schedule_type: 调度类型
        cron_expression: cron 表达式（CRON 类型必填）
        interval_seconds: 间隔秒数（INTERVAL 类型必填）
        base_time: 基准时间，默认为当前时间

    Returns:
        下次执行时间
    """
    if base_time is None:
        base_time = datetime.now()

    if schedule_type == ScheduleType.CRON:
        cron = croniter(cron_expression, base_time)
        return cron.get_next(datetime)
    else:
        from datetime import timedelta

        return base_time + timedelta(seconds=interval_seconds)


# 全局调度器实例
task_scheduler = TaskScheduler()
