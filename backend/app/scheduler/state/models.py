"""任务状态模型

定义任务运行状态和执行记录的数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TaskStatus(str, Enum):
    """任务当前状态"""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class TaskState:
    """任务运行时状态

    Attributes:
        task_name: 任务名称
        status: 当前状态
        enabled: 是否启用
        next_run_at: 下次执行时间
        last_run_at: 上次执行时间
        last_result: 上次执行结果（success/failed/skipped）
        last_error: 上次错误信息
        run_count: 累计执行次数
        fail_count: 累计失败次数
    """

    task_name: str
    status: TaskStatus = TaskStatus.IDLE
    enabled: bool = True
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_result: str | None = None
    last_error: str | None = None
    run_count: int = 0
    fail_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_name": self.task_name,
            "status": self.status.value,
            "enabled": self.enabled,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_result": self.last_result,
            "last_error": self.last_error,
            "run_count": self.run_count,
            "fail_count": self.fail_count,
        }


@dataclass
class TaskExecutionRecord:
    """任务执行记录

    Attributes:
        id: 记录 ID
        task_name: 任务名称
        started_at: 开始时间
        finished_at: 结束时间
        duration_ms: 耗时（毫秒）
        status: 执行结果状态
        message: 结果描述
        error: 错误信息
        data: 附加数据
    """

    id: str
    task_name: str
    started_at: datetime
    finished_at: datetime | None = None
    duration_ms: int | None = None
    status: str = "running"
    message: str = ""
    error: str | None = None
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "task_name": self.task_name,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "message": self.message,
            "error": self.error,
            "data": self.data,
        }
