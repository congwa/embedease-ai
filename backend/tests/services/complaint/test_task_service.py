"""TaskService 测试

测试问题单任务服务在 Phase 1 中的任务创建、执行推进和失败阻塞规则。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_task import ComplaintTask
from app.schemas.complaint import ComplaintTaskStatus
from app.services.complaint.task_service import TaskService


def build_task() -> ComplaintTask:
    """构造一个基础任务对象，服务于任务状态推进测试。"""
    return ComplaintTask(
        id="task_123",
        ticket_id="ticket_123",
        task_type="triage",
        agent_tag="planner",
        status=ComplaintTaskStatus.QUEUED.value,
        retry_count=0,
    )


class TestTaskServiceInit:
    """测试 TaskService 初始化。"""

    def test_init_with_session(self):
        """测试任务服务会绑定当前数据库会话。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)

        assert service.session is mock_session
        assert service.task_repo is not None


class TestTaskServiceBehavior:
    """测试 TaskService 核心业务行为。"""

    @pytest.mark.anyio
    async def test_create_task_sets_phase1_defaults(self):
        """测试创建任务时会写入 Phase 1 约定的默认状态。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)
        service.task_repo.create = AsyncMock(side_effect=lambda task: task)

        task = await service.create_task(
            ticket_id="ticket_123",
            task_type="triage",
            agent_tag="planner",
            input_payload={"message": "用户继续投诉"},
            goal="识别主问题",
            success_criteria=["输出标签"],
            review_required=True,
        )

        assert task.ticket_id == "ticket_123"
        assert task.status == ComplaintTaskStatus.QUEUED.value
        assert task.review_required is True
        assert task.retry_count == 0

    @pytest.mark.anyio
    async def test_start_task_marks_running(self):
        """测试任务开始执行后进入 running 状态。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)
        service.task_repo.update = AsyncMock(side_effect=lambda task: task)
        task = build_task()

        result = await service.start_task(task)

        assert result.status == ComplaintTaskStatus.RUNNING.value
        assert result.started_at is not None

    @pytest.mark.anyio
    async def test_mark_waiting_review_sets_waiting_review(self):
        """测试任务提交审查时进入 waiting_review 状态。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)
        service.task_repo.update = AsyncMock(side_effect=lambda task: task)
        task = build_task()

        result = await service.mark_waiting_review(task)

        assert result.status == ComplaintTaskStatus.WAITING_REVIEW.value

    @pytest.mark.anyio
    async def test_complete_task_writes_output(self):
        """测试任务完成后保存业务输出并写入完成时间。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)
        service.task_repo.update = AsyncMock(side_effect=lambda task: task)
        task = build_task()

        result = await service.complete_task(task, output_payload={"reply": "已补发优惠券"})

        assert result.status == ComplaintTaskStatus.DONE.value
        assert result.output_payload == {"reply": "已补发优惠券"}
        assert result.finished_at is not None

    @pytest.mark.anyio
    async def test_fail_task_records_reason(self):
        """测试任务失败时会留下失败原因，便于返工解释。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)
        service.task_repo.update = AsyncMock(side_effect=lambda task: task)
        task = build_task()

        result = await service.fail_task(task, reason="review_rejected")

        assert result.status == ComplaintTaskStatus.FAILED.value
        assert result.failure_reason == "review_rejected"
        assert result.finished_at is not None

    @pytest.mark.anyio
    async def test_block_task_records_reason(self):
        """测试任务被阻塞时会留下阻塞原因。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)
        service.task_repo.update = AsyncMock(side_effect=lambda task: task)
        task = build_task()

        result = await service.block_task(task, reason="等待人工接入")

        assert result.status == ComplaintTaskStatus.BLOCKED.value
        assert result.failure_reason == "等待人工接入"

    @pytest.mark.anyio
    async def test_resume_blocked_task_marks_running_and_records_patrol_reason(self):
        """测试巡查恢复阻塞任务后会回到 running 并累计恢复次数。"""
        mock_session = MagicMock()
        service = TaskService(mock_session)
        service.task_repo.update = AsyncMock(side_effect=lambda task: task)
        task = build_task()
        task.status = ComplaintTaskStatus.BLOCKED.value
        task.failure_reason = "等待人工接入"

        result = await service.resume_blocked_task(
            task,
            reason="operations_patrol_agent 自动恢复阻塞任务",
        )

        assert result.status == ComplaintTaskStatus.RUNNING.value
        assert result.retry_count == 1
        assert result.failure_reason is None
        assert result.output_payload == {
            "patrol_resume_reason": "operations_patrol_agent 自动恢复阻塞任务",
        }
