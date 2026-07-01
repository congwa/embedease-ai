"""问题单任务服务

本文件的业务职责是统一创建和推进 ticket 下的 triage、plan、execute、review 任务，
确保每一轮消息处理都能留下结构化任务记录。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_task import ComplaintTask
from app.repositories.complaint_task import ComplaintTaskRepository
from app.schemas.complaint import ComplaintTaskStatus
from app.services.complaint.state_machine import can_transition_task, require_transition


class TaskService:
    """问题单任务推进服务。"""

    def __init__(self, session: AsyncSession):
        """初始化任务服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.task_repo = ComplaintTaskRepository(session)

    async def create_task(
        self,
        *,
        ticket_id: str,
        task_type: str,
        agent_tag: str,
        input_payload: dict | None = None,
        goal: str | None = None,
        success_criteria: list[str] | None = None,
        review_required: bool = False,
    ) -> ComplaintTask:
        """创建业务任务。

        这个方法服务于 triage、plan、executor、review 的统一任务落库。
        """
        task = ComplaintTask(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            task_type=task_type,
            agent_tag=agent_tag,
            status=ComplaintTaskStatus.QUEUED.value,
            input_payload=input_payload,
            goal=goal,
            success_criteria=success_criteria,
            review_required=review_required,
            retry_count=0,
        )
        return await self.task_repo.create(task)

    async def start_task(self, task: ComplaintTask) -> ComplaintTask:
        """标记任务进入执行中。

        这个动作表示当前岗位已经正式开始处理该问题单任务。
        """
        require_transition(
            entity_name="task",
            from_status=task.status,
            to_status=ComplaintTaskStatus.RUNNING.value,
            checker=can_transition_task,
        )
        task.status = ComplaintTaskStatus.RUNNING.value
        task.started_at = datetime.now()
        return await self.task_repo.update(task)

    async def mark_waiting_review(self, task: ComplaintTask) -> ComplaintTask:
        """标记任务进入待审查状态。

        当 executor 完成候选输出但尚未通过 reviewer 时，应进入 waiting_review。
        """
        require_transition(
            entity_name="task",
            from_status=task.status,
            to_status=ComplaintTaskStatus.WAITING_REVIEW.value,
            checker=can_transition_task,
        )
        task.status = ComplaintTaskStatus.WAITING_REVIEW.value
        return await self.task_repo.update(task)

    async def update_output_payload(
        self,
        task: ComplaintTask,
        output_payload: dict | None,
    ) -> ComplaintTask:
        """写入任务输出负载。

        这个方法服务于 executor 和 reviewer 在状态尚未终结前先保存阶段性产出。
        """
        task.output_payload = output_payload
        return await self.task_repo.update(task)

    async def complete_task(self, task: ComplaintTask, output_payload: dict | None = None) -> ComplaintTask:
        """完成任务并写入业务输出。

        这个动作表示某一阶段任务已经产出了可交付结果。
        """
        require_transition(
            entity_name="task",
            from_status=task.status,
            to_status=ComplaintTaskStatus.DONE.value,
            checker=can_transition_task,
        )
        task.status = ComplaintTaskStatus.DONE.value
        task.output_payload = output_payload
        task.finished_at = datetime.now()
        return await self.task_repo.update(task)

    async def fail_task(self, task: ComplaintTask, reason: str) -> ComplaintTask:
        """标记任务失败。

        这个动作服务于 review 驳回、执行失败或无法继续推进等场景。
        """
        require_transition(
            entity_name="task",
            from_status=task.status,
            to_status=ComplaintTaskStatus.FAILED.value,
            checker=can_transition_task,
        )
        task.status = ComplaintTaskStatus.FAILED.value
        task.failure_reason = reason
        task.finished_at = datetime.now()
        return await self.task_repo.update(task)

    async def block_task(self, task: ComplaintTask, reason: str) -> ComplaintTask:
        """标记任务被阻塞。

        这个动作服务于信息不足、系统异常或等待人工介入等场景。
        """
        require_transition(
            entity_name="task",
            from_status=task.status,
            to_status=ComplaintTaskStatus.BLOCKED.value,
            checker=can_transition_task,
        )
        task.status = ComplaintTaskStatus.BLOCKED.value
        task.failure_reason = reason
        return await self.task_repo.update(task)

    async def resume_blocked_task(self, task: ComplaintTask, reason: str) -> ComplaintTask:
        """恢复被阻塞的任务执行。

        这个动作服务于巡查 Agent 发现“任务其实还能继续推进”时的自动自愈。
        它不会伪造任务完成，而是把任务重新放回 running，并累计一次恢复重试。
        """
        require_transition(
            entity_name="task",
            from_status=task.status,
            to_status=ComplaintTaskStatus.RUNNING.value,
            checker=can_transition_task,
        )
        task.status = ComplaintTaskStatus.RUNNING.value
        task.failure_reason = None
        task.retry_count += 1
        task.started_at = datetime.now()
        task.finished_at = None
        task.output_payload = {
            **(task.output_payload or {}),
            "patrol_resume_reason": reason,
        }
        return await self.task_repo.update(task)
