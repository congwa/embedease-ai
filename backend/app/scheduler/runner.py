"""任务执行器

负责执行具体任务，处理超时、重试、异常捕获，并记录执行结果。
"""

import asyncio
import uuid
from datetime import datetime

from app.core.logging import get_logger
from app.scheduler.state.models import TaskExecutionRecord, TaskState, TaskStatus
from app.scheduler.tasks.base import BaseTask, TaskResultStatus

logger = get_logger("scheduler.runner")


class TaskRunner:
    """任务执行器

    职责：
    1. 执行任务并捕获异常
    2. 记录执行时间和结果
    3. 更新任务状态
    4. 支持超时控制

    Attributes:
        default_timeout: 默认超时时间（秒）
        max_retries: 最大重试次数
    """

    def __init__(self, default_timeout: int = 3600, max_retries: int = 0):
        self.default_timeout = default_timeout
        self.max_retries = max_retries
        self._task_states: dict[str, TaskState] = {}
        self._execution_history: list[TaskExecutionRecord] = []
        self._running_tasks: set[str] = set()

    def get_state(self, task_name: str) -> TaskState:
        """获取任务状态

        Args:
            task_name: 任务名称

        Returns:
            任务状态，不存在则创建默认状态
        """
        if task_name not in self._task_states:
            self._task_states[task_name] = TaskState(task_name=task_name)
        return self._task_states[task_name]

    def update_next_run(self, task_name: str, next_run_at: datetime) -> None:
        """更新下次执行时间

        Args:
            task_name: 任务名称
            next_run_at: 下次执行时间
        """
        state = self.get_state(task_name)
        state.next_run_at = next_run_at

    def is_running(self, task_name: str) -> bool:
        """检查任务是否正在运行

        Args:
            task_name: 任务名称

        Returns:
            是否正在运行
        """
        return task_name in self._running_tasks

    async def execute(
        self, task: BaseTask, timeout: int | None = None
    ) -> TaskExecutionRecord:
        """执行任务

        Args:
            task: 任务实例
            timeout: 超时时间（秒），为 None 则使用默认值

        Returns:
            执行记录
        """
        task_name = task.name
        state = self.get_state(task_name)
        timeout = timeout or self.default_timeout

        # 检查是否允许并发
        if not task.schedule.allow_concurrent and self.is_running(task_name):
            logger.warning("任务正在运行，跳过", task_name=task_name)
            record = TaskExecutionRecord(
                id=str(uuid.uuid4()),
                task_name=task_name,
                started_at=datetime.now(),
                finished_at=datetime.now(),
                duration_ms=0,
                status=TaskResultStatus.SKIPPED.value,
                message="任务正在运行，跳过本次执行",
            )
            self._execution_history.append(record)
            return record

        # 创建执行记录
        record = TaskExecutionRecord(
            id=str(uuid.uuid4()),
            task_name=task_name,
            started_at=datetime.now(),
        )

        # 更新状态为运行中
        state.status = TaskStatus.RUNNING
        self._running_tasks.add(task_name)

        logger.info("开始执行任务", task_name=task_name, record_id=record.id)

        try:
            # 执行任务（带超时）
            result = await asyncio.wait_for(task.run(), timeout=timeout)

            # 更新执行记录
            record.finished_at = datetime.now()
            record.duration_ms = int(
                (record.finished_at - record.started_at).total_seconds() * 1000
            )
            record.status = result.status.value
            record.message = result.message
            record.data = result.data
            record.error = result.error

            # 更新任务状态
            state.last_run_at = record.started_at
            state.last_result = result.status.value
            state.last_error = result.error
            state.run_count += 1
            if result.status == TaskResultStatus.FAILED:
                state.fail_count += 1

            logger.info(
                "任务执行完成",
                task_name=task_name,
                status=result.status.value,
                duration_ms=record.duration_ms,
            )

        except asyncio.TimeoutError:
            record.finished_at = datetime.now()
            record.duration_ms = int(
                (record.finished_at - record.started_at).total_seconds() * 1000
            )
            record.status = TaskResultStatus.FAILED.value
            record.message = "执行超时"
            record.error = f"任务执行超过 {timeout} 秒"

            state.last_run_at = record.started_at
            state.last_result = TaskResultStatus.FAILED.value
            state.last_error = record.error
            state.run_count += 1
            state.fail_count += 1

            logger.error("任务执行超时", task_name=task_name, timeout=timeout)

        except Exception as e:
            record.finished_at = datetime.now()
            record.duration_ms = int(
                (record.finished_at - record.started_at).total_seconds() * 1000
            )
            record.status = TaskResultStatus.FAILED.value
            record.message = "执行异常"
            record.error = str(e)

            state.last_run_at = record.started_at
            state.last_result = TaskResultStatus.FAILED.value
            state.last_error = str(e)
            state.run_count += 1
            state.fail_count += 1

            logger.exception("任务执行异常", task_name=task_name, error=str(e))

        finally:
            state.status = TaskStatus.IDLE
            self._running_tasks.discard(task_name)
            self._execution_history.append(record)

        return record

    def get_history(
        self, task_name: str | None = None, limit: int = 10
    ) -> list[TaskExecutionRecord]:
        """获取执行历史

        Args:
            task_name: 任务名称，为 None 则返回所有任务
            limit: 返回条数

        Returns:
            执行记录列表（按时间倒序）
        """
        records = self._execution_history
        if task_name:
            records = [r for r in records if r.task_name == task_name]
        return sorted(records, key=lambda r: r.started_at, reverse=True)[:limit]

    def get_all_states(self) -> list[TaskState]:
        """获取所有任务状态"""
        return list(self._task_states.values())
