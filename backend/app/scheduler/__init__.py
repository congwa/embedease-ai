"""统一任务调度模块

提供单站点多任务的调度能力：
- TaskScheduler: 调度器核心，管理所有定时任务
- TaskRegistry: 任务注册中心
- TaskRunner: 任务执行器
- BaseTask: 任务抽象基类

使用方式：
    from app.scheduler import task_scheduler, task_registry
    from app.scheduler.tasks import CrawlSiteTask

    # 注册任务
    task_registry.register(CrawlSiteTask())

    # 启动调度器
    await task_scheduler.start()
"""

from app.scheduler.registry import TaskRegistry, task_registry
from app.scheduler.runner import TaskRunner
from app.scheduler.scheduler import TaskScheduler, task_scheduler

__all__ = [
    "TaskRegistry",
    "TaskRunner",
    "TaskScheduler",
    "task_registry",
    "task_scheduler",
]
