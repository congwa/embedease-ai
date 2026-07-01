"""PatrolService 测试

本文件的业务职责，是验证客诉巡查能识别卡住 ticket，
并按规则执行自动恢复、升级人工和提醒节流。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import ComplaintStatus, ComplaintTaskStatus
from app.services.complaint.patrol_service import PatrolService


def build_ticket(
    *,
    status: str,
    updated_at: datetime,
    rework_count: int = 0,
) -> ComplaintTicket:
    """构造一个基础巡查 ticket。

    这个方法服务于巡查场景测试，快速表达 blocked、pending_review 和 handoff_pending 的停滞状态。
    """
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=status,
        is_primary_active=True,
        primary_issue_tag="refund_request",
        current_agent_tag="resolution_execution_agent",
        current_task_id="task_123",
        current_node_key="resolution",
        priority_level="urgent",
        risk_level="high",
        unresolved_turns=3,
        rework_count=rework_count,
        handoff_required=False,
        secondary_issue_tags=[],
        secondary_issues=[],
        slot_data={},
        timeline=[],
        version=1,
        created_at=updated_at - timedelta(minutes=5),
        updated_at=updated_at,
    )


def build_task(*, status: str) -> ComplaintTask:
    """构造一个基础巡查 task。

    这个方法服务于巡查恢复和超时升级测试，模拟当前 ticket 最近一条执行任务。
    """
    return ComplaintTask(
        id="task_123",
        ticket_id="ticket_123",
        task_type="resolution",
        agent_tag="resolution_execution_agent",
        status=status,
        retry_count=0,
    )


class TestPatrolServiceBehavior:
    """测试巡查服务核心业务行为。"""

    @pytest.mark.anyio
    async def test_run_patrol_auto_recovers_stale_blocked_ticket(self):
        """测试长时间 blocked 的 ticket 会被巡查自动恢复。"""
        mock_session = MagicMock()
        service = PatrolService(mock_session)
        now = datetime(2026, 4, 2, 21, 0, 0)
        blocked_ticket = build_ticket(
            status=ComplaintStatus.BLOCKED.value,
            updated_at=now - timedelta(minutes=40),
        )
        blocked_task = build_task(status=ComplaintTaskStatus.BLOCKED.value)
        recovered_ticket = build_ticket(
            status=ComplaintStatus.PLANNED.value,
            updated_at=now,
        )

        service.ticket_repo.list_primary_active_by_statuses = AsyncMock(return_value=[blocked_ticket])
        service.ticket_repo.list_primary_active_with_rework_at_least = AsyncMock(return_value=[])
        service.task_repo.get_latest_by_ticket_id = AsyncMock(return_value=blocked_task)
        service.task_service.resume_blocked_task = AsyncMock(return_value=blocked_task)
        service.ticket_service.recover_from_blocked = AsyncMock(return_value=recovered_ticket)
        service.patrol_repo.create = AsyncMock(side_effect=lambda event: event)

        outcomes = await service.run_patrol(now=now)

        service.task_service.resume_blocked_task.assert_awaited_once()
        service.ticket_service.recover_from_blocked.assert_awaited_once()
        assert len(outcomes) == 1
        assert outcomes[0].ticket_status == ComplaintStatus.PLANNED.value
        assert outcomes[0].patrol_status == "auto_recovered"
        assert outcomes[0].event_type == "blocked_timeout"

    @pytest.mark.anyio
    async def test_run_patrol_escalates_pending_review_timeout(self):
        """测试长时间 pending_review 的 ticket 会被巡查升级人工。"""
        mock_session = MagicMock()
        service = PatrolService(mock_session)
        now = datetime(2026, 4, 2, 21, 10, 0)
        pending_review_ticket = build_ticket(
            status=ComplaintStatus.PENDING_REVIEW.value,
            updated_at=now - timedelta(minutes=20),
        )
        waiting_review_task = build_task(status=ComplaintTaskStatus.WAITING_REVIEW.value)
        escalated_ticket = build_ticket(
            status=ComplaintStatus.HANDOFF_PENDING.value,
            updated_at=now,
        )

        service.ticket_repo.list_primary_active_by_statuses = AsyncMock(return_value=[pending_review_ticket])
        service.ticket_repo.list_primary_active_with_rework_at_least = AsyncMock(return_value=[])
        service.task_repo.get_latest_by_ticket_id = AsyncMock(return_value=waiting_review_task)
        service.task_service.block_task = AsyncMock(return_value=waiting_review_task)
        service.ticket_service.mark_handoff_pending = AsyncMock(return_value=escalated_ticket)
        service.ticket_service.append_timeline_entry = AsyncMock(return_value=escalated_ticket)
        service.patrol_repo.create = AsyncMock(side_effect=lambda event: event)

        outcomes = await service.run_patrol(now=now)

        service.task_service.block_task.assert_awaited_once_with(
            waiting_review_task,
            reason="pending_review_timeout",
        )
        service.ticket_service.mark_handoff_pending.assert_awaited_once()
        assert len(outcomes) == 1
        assert outcomes[0].ticket_status == ComplaintStatus.HANDOFF_PENDING.value
        assert outcomes[0].handoff_state == "pending"
        assert outcomes[0].event_type == "pending_review_timeout"

    @pytest.mark.anyio
    async def test_run_patrol_skips_duplicate_handoff_pending_alert_within_cooldown(self):
        """测试 handoff_pending 提醒在冷却时间内不会重复发送。"""
        mock_session = MagicMock()
        service = PatrolService(mock_session)
        now = datetime(2026, 4, 2, 21, 20, 0)
        handoff_ticket = build_ticket(
            status=ComplaintStatus.HANDOFF_PENDING.value,
            updated_at=now - timedelta(minutes=20),
        )

        service.ticket_repo.list_primary_active_by_statuses = AsyncMock(return_value=[handoff_ticket])
        service.ticket_repo.list_primary_active_with_rework_at_least = AsyncMock(return_value=[])
        service.patrol_repo.has_recent_event = AsyncMock(return_value=True)
        service.ticket_service.append_timeline_entry = AsyncMock(return_value=handoff_ticket)
        service.patrol_repo.create = AsyncMock(side_effect=lambda event: event)

        with patch(
            "app.services.complaint.patrol_service.notification_dispatcher.notify_waiting_reminder",
            new=AsyncMock(return_value=[]),
        ) as mock_notify_waiting:
            outcomes = await service.run_patrol(now=now)

        service.patrol_repo.has_recent_event.assert_awaited_once()
        service.ticket_service.append_timeline_entry.assert_not_awaited()
        mock_notify_waiting.assert_not_awaited()
        assert outcomes == []

    @pytest.mark.anyio
    async def test_run_patrol_escalates_rework_loop_before_other_rules(self):
        """测试返工死循环会优先被升级人工，而不是继续自动恢复。"""
        mock_session = MagicMock()
        service = PatrolService(mock_session)
        now = datetime(2026, 4, 2, 21, 30, 0)
        rework_ticket = build_ticket(
            status=ComplaintStatus.REWORK_REQUIRED.value,
            updated_at=now - timedelta(minutes=5),
            rework_count=3,
        )
        escalated_ticket = build_ticket(
            status=ComplaintStatus.HANDOFF_PENDING.value,
            updated_at=now,
            rework_count=3,
        )

        service.ticket_repo.list_primary_active_by_statuses = AsyncMock(return_value=[rework_ticket])
        service.ticket_repo.list_primary_active_with_rework_at_least = AsyncMock(return_value=[rework_ticket])
        service.ticket_service.mark_handoff_pending = AsyncMock(return_value=escalated_ticket)
        service.ticket_service.append_timeline_entry = AsyncMock(return_value=escalated_ticket)
        service.patrol_repo.create = AsyncMock(side_effect=lambda event: event)

        outcomes = await service.run_patrol(now=now, rework_limit=3)

        service.ticket_service.mark_handoff_pending.assert_awaited_once()
        assert len(outcomes) == 1
        assert outcomes[0].event_type == "rework_loop"
        assert outcomes[0].handoff_state == "pending"
