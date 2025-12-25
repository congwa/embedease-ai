"""任务注册中心

管理所有定时任务的注册与查询。
调度器通过 Registry 获取任务列表进行调度。
"""

from app.core.logging import get_logger
from app.scheduler.tasks.base import BaseTask

logger = get_logger("scheduler.registry")


class TaskRegistry:
    """任务注册中心

    职责：
    1. 注册任务实例
    2. 提供任务查询接口
    3. 支持动态启用/禁用任务

    Example:
        registry = TaskRegistry()
        registry.register(CrawlSiteTask())
        registry.register(SyncInventoryTask())

        for task in registry.list_enabled_tasks():
            print(task.name)
    """

    def __init__(self):
        self._tasks: dict[str, BaseTask] = {}

    def register(self, task: BaseTask) -> None:
        """注册任务

        Args:
            task: 任务实例

        Raises:
            ValueError: 任务名称已存在
        """
        if task.name in self._tasks:
            raise ValueError(f"任务已注册: {task.name}")

        self._tasks[task.name] = task
        logger.info("注册任务", task_name=task.name, description=task.description)

    def unregister(self, task_name: str) -> None:
        """注销任务

        Args:
            task_name: 任务名称
        """
        if task_name in self._tasks:
            del self._tasks[task_name]
            logger.info("注销任务", task_name=task_name)

    def get(self, task_name: str) -> BaseTask | None:
        """获取任务

        Args:
            task_name: 任务名称

        Returns:
            任务实例，不存在则返回 None
        """
        return self._tasks.get(task_name)

    def list_all(self) -> list[BaseTask]:
        """列出所有任务"""
        return list(self._tasks.values())

    def list_enabled(self) -> list[BaseTask]:
        """列出所有启用的任务"""
        return [t for t in self._tasks.values() if t.enabled]

    def enable(self, task_name: str) -> bool:
        """启用任务

        Args:
            task_name: 任务名称

        Returns:
            是否成功
        """
        task = self._tasks.get(task_name)
        if task:
            task.enabled = True
            logger.info("启用任务", task_name=task_name)
            return True
        return False

    def disable(self, task_name: str) -> bool:
        """禁用任务

        Args:
            task_name: 任务名称

        Returns:
            是否成功
        """
        task = self._tasks.get(task_name)
        if task:
            task.enabled = False
            logger.info("禁用任务", task_name=task_name)
            return True
        return False

    def __len__(self) -> int:
        return len(self._tasks)

    def __contains__(self, task_name: str) -> bool:
        return task_name in self._tasks


# 全局任务注册中心实例
task_registry = TaskRegistry()
