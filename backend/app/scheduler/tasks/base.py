"""任务抽象基类

定义所有定时任务必须实现的接口，确保调度器能统一处理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ScheduleType(str, Enum):
    """调度类型"""

    CRON = "cron"
    INTERVAL = "interval"


@dataclass
class TaskSchedule:
    """任务调度配置

    Attributes:
        schedule_type: 调度类型（cron 或 interval）
        cron_expression: cron 表达式，如 "0 2 * * *"（每天凌晨2点）
        interval_seconds: 间隔秒数
        allow_concurrent: 是否允许并发执行（同一任务重叠运行）
        run_on_start: 调度器启动时是否立即执行一次
    """

    schedule_type: ScheduleType
    cron_expression: str | None = None
    interval_seconds: int | None = None
    allow_concurrent: bool = False
    run_on_start: bool = False

    def __post_init__(self):
        if self.schedule_type == ScheduleType.CRON and not self.cron_expression:
            raise ValueError("CRON 类型必须提供 cron_expression")
        if self.schedule_type == ScheduleType.INTERVAL and not self.interval_seconds:
            raise ValueError("INTERVAL 类型必须提供 interval_seconds")


class TaskResultStatus(str, Enum):
    """任务执行结果状态"""

    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """任务执行结果

    Attributes:
        status: 执行状态
        message: 结果描述
        data: 附加数据（如爬取的页面数、耗时等）
        error: 错误信息（失败时）
    """

    status: TaskResultStatus
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def success(cls, message: str = "执行成功", **data) -> "TaskResult":
        return cls(status=TaskResultStatus.SUCCESS, message=message, data=data)

    @classmethod
    def failed(cls, error: str, message: str = "执行失败") -> "TaskResult":
        return cls(status=TaskResultStatus.FAILED, message=message, error=error)

    @classmethod
    def skipped(cls, message: str = "跳过执行") -> "TaskResult":
        return cls(status=TaskResultStatus.SKIPPED, message=message)


class BaseTask(ABC):
    """任务抽象基类

    所有定时任务必须继承此类并实现 run 方法。

    Example:
        class MyTask(BaseTask):
            name = "my_task"
            description = "我的任务"
            schedule = TaskSchedule(
                schedule_type=ScheduleType.CRON,
                cron_expression="0 * * * *"  # 每小时
            )

            async def run(self) -> TaskResult:
                # 执行任务逻辑
                return TaskResult.success("完成", count=10)
    """

    name: str
    description: str
    schedule: TaskSchedule
    enabled: bool = True

    @abstractmethod
    async def run(self) -> TaskResult:
        """执行任务

        Returns:
            TaskResult: 任务执行结果
        """
        pass

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name}>"
