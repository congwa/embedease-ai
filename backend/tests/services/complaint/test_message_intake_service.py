"""ComplaintMessageIntakeService 测试

测试用户消息进入投诉域后，ticket 决策、未解决轮次和 complaint SSE 事件是否按规则输出。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import (
    ActiveTicketResolution,
    ComplaintStatus,
    IssueContinuity,
    TicketResolutionDecision,
)
from app.services.complaint.message_intake_service import ComplaintMessageIntakeService


def build_ticket() -> ComplaintTicket:
    """构造一个基础问题单对象，服务于消息接入测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=ComplaintStatus.NEW.value,
        is_primary_active=True,
        unresolved_turns=0,
        rework_count=0,
        handoff_required=False,
        secondary_issue_tags=[],
        secondary_issues=[],
        slot_data={},
        timeline=[],
        version=1,
        updated_at=datetime(2026, 3, 31, 10, 0, 0),
    )


class TestComplaintMessageIntakeServiceInit:
    """测试消息接入服务初始化。"""

    def test_init_with_session(self):
        """测试接入服务会初始化投诉域依赖。"""
        mock_session = MagicMock()
        service = ComplaintMessageIntakeService(mock_session)

        assert service.session is mock_session
        assert service.ticket_repo is not None
        assert service.ticket_merge_service is not None
        assert service.ticket_service is not None


class TestComplaintMessageIntakeServiceBehavior:
    """测试消息接入服务业务行为。"""

    @pytest.mark.anyio
    async def test_create_initial_ticket_emits_created_event(self):
        """测试首条投诉消息会创建 ticket 并发送 created 事件。"""
        mock_session = MagicMock()
        service = ComplaintMessageIntakeService(mock_session)
        ticket = build_ticket()
        resolution = ActiveTicketResolution(
            decision=TicketResolutionDecision.CREATE_INITIAL_TICKET,
            ticket_id="ticket_123",
            reason="当前会话没有主活动问题单",
            issue_continuity=IssueContinuity.NEW_ISSUE,
            confidence=1.0,
        )
        service.ticket_merge_service.resolve_ticket_for_message = AsyncMock(return_value=resolution)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_service.increment_unresolved_turns = AsyncMock(return_value=ticket)

        result = await service.process_user_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="订单一直没发货",
            user_message_id="msg_123",
        )

        assert result.ticket.id == "ticket_123"
        assert result.events[0]["type"] == "complaint.ticket.created"
        service.ticket_service.increment_unresolved_turns.assert_not_called()

    @pytest.mark.anyio
    async def test_reuse_active_ticket_increments_unresolved_turns(self):
        """测试持续围绕同一问题发言会累加未解决轮次并发送 merged 事件。"""
        mock_session = MagicMock()
        service = ComplaintMessageIntakeService(mock_session)
        ticket = build_ticket()
        updated_ticket = build_ticket()
        updated_ticket.unresolved_turns = 3
        resolution = ActiveTicketResolution(
            decision=TicketResolutionDecision.REUSE_ACTIVE_TICKET,
            ticket_id="ticket_123",
            reason="当前消息仍在围绕主问题继续沟通",
            issue_continuity=IssueContinuity.SAME_ISSUE,
            confidence=0.92,
        )
        service.ticket_merge_service.resolve_ticket_for_message = AsyncMock(return_value=resolution)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_service.increment_unresolved_turns = AsyncMock(return_value=updated_ticket)

        result = await service.process_user_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="你们到底什么时候处理",
            user_message_id="msg_123",
        )

        assert result.ticket.unresolved_turns == 3
        assert result.ticket.merged_from_latest_message is True
        assert result.events[0]["type"] == "complaint.ticket.merged"
        assert result.events[0]["payload"]["merged_message_id"] == "msg_123"
        assert result.events[1]["type"] == "complaint.ticket.updated"

    @pytest.mark.anyio
    async def test_secondary_issue_emits_detected_event(self):
        """测试次级问题场景会输出 secondary_issue.detected 和 ticket.updated。"""
        mock_session = MagicMock()
        service = ComplaintMessageIntakeService(mock_session)
        ticket = build_ticket()
        ticket.secondary_issue_tags = ["secondary_issue"]
        ticket.secondary_issues = [
            {
                "issue_tag": "secondary_issue",
                "raw_message": "另外我还要投诉客服态度差",
                "reason": "用户引入了新的次要诉求",
            }
        ]
        updated_ticket = build_ticket()
        updated_ticket.unresolved_turns = 2
        updated_ticket.secondary_issue_tags = ["secondary_issue"]
        updated_ticket.secondary_issues = ticket.secondary_issues
        resolution = ActiveTicketResolution(
            decision=TicketResolutionDecision.RECORD_SECONDARY_ISSUE,
            ticket_id="ticket_123",
            reason="消息中识别到次级诉求",
            issue_continuity=IssueContinuity.UNCERTAIN,
            confidence=0.78,
        )
        service.ticket_merge_service.resolve_ticket_for_message = AsyncMock(return_value=resolution)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_service.increment_unresolved_turns = AsyncMock(return_value=updated_ticket)

        result = await service.process_user_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="另外我还要投诉客服态度差",
            user_message_id="msg_123",
        )

        assert result.ticket.secondary_issue_detected is True
        assert result.events[0]["type"] == "complaint.secondary_issue.detected"
        assert result.events[0]["payload"]["secondary_issue"]["issue_tag"] == "secondary_issue"
        assert result.events[1]["type"] == "complaint.ticket.updated"
