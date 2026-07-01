"""ComplaintHandoffService 测试

测试客诉语义的 handoff 编排如何联动 ticket、conversation 和工作台广播。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import ComplaintStatus
from app.services.complaint.handoff_service import ComplaintHandoffService


def build_ticket(status: str = ComplaintStatus.IN_PROGRESS.value) -> ComplaintTicket:
    """构造基础问题单对象，服务于 handoff 编排测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=status,
        is_primary_active=True,
        unresolved_turns=1,
        rework_count=0,
        handoff_required=False,
        secondary_issue_tags=[],
        secondary_issues=[],
        slot_data={},
        timeline=[],
        version=1,
    )


def build_task() -> ComplaintTask:
    """构造最近任务对象，服务于转人工摘要测试。"""
    return ComplaintTask(
        id="task_123",
        ticket_id="ticket_123",
        task_type="review",
        agent_tag="quality_reviewer_agent",
        status="done",
        goal="审查候选回复",
        success_criteria=["给出是否通过结论"],
        review_required=False,
        output_payload={"status": "escalated", "reasons": ["高风险赔付"]},
        retry_count=0,
    )


def build_review() -> ComplaintReview:
    """构造最近审查对象，服务于转人工摘要测试。"""
    return ComplaintReview(
        id="review_123",
        ticket_id="ticket_123",
        task_id="task_123",
        reviewer_agent_tag="quality_reviewer_agent",
        status="escalated",
        score=45,
        risk_level="high",
        reasons=["高风险赔付"],
        suggested_next_agent="human_support",
    )


class TestComplaintHandoffService:
    """测试 ComplaintHandoffService 核心业务行为。"""

    @pytest.mark.anyio
    async def test_request_handoff_for_ticket_marks_pending(self):
        """测试对 ticket 发起 handoff 会同步进入 pending。"""
        service = ComplaintHandoffService(MagicMock())
        ticket = build_ticket()
        ticket.primary_issue_tag = "refund_request"
        ticket.priority_level = "urgent"
        ticket.risk_level = "high"
        ticket.slot_data = {"order_id": "123456"}
        ticket.timeline = [{"event_type": "review.rejected", "summary": "高风险赔付"}]
        pending_ticket = build_ticket(status=ComplaintStatus.HANDOFF_PENDING.value)
        pending_ticket.handoff_required = True

        service.task_repo.list_by_ticket_id = AsyncMock(return_value=[build_task()])
        service.review_repo.get_latest_by_ticket_id = AsyncMock(return_value=build_review())
        service.ticket_service.mark_handoff_pending = AsyncMock(return_value=pending_ticket)
        service.support_handoff_service.request_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "pending"}
        )
        service._broadcast_ticket_update = AsyncMock()
        service._broadcast_conversation_state = AsyncMock()
        service._broadcast_support_queue_change = AsyncMock()

        result = await service.request_handoff_for_ticket(
            ticket,
            handoff_reason="高风险投诉",
            handoff_summary={"reason": "高风险投诉"},
        )

        assert result.requested is True
        assert result.ticket_id == "ticket_123"
        assert result.handoff_state == "pending"
        assert result.handoff_summary["primary_issue_tag"] == "refund_request"
        assert result.handoff_summary["slot_data"]["order_id"] == "123456"
        assert result.handoff_summary["latest_review"]["status"] == "escalated"
        assert result.handoff_summary["recent_tasks"][0]["task_type"] == "review"
        service.ticket_service.mark_handoff_pending.assert_awaited_once()
        service._broadcast_support_queue_change.assert_awaited_once_with(
            conversation_id="conv_123",
            handoff_state="pending",
            reason="高风险投诉",
            source="complaint_ticket_request_handoff",
        )

    @pytest.mark.anyio
    async def test_accept_handoff_marks_ticket_handed_off(self):
        """测试客服接入会把 ticket 从 pending 改成 handed_off。"""
        service = ComplaintHandoffService(MagicMock())
        ticket = build_ticket(status=ComplaintStatus.HANDOFF_PENDING.value)

        service.support_handoff_service.start_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "human"}
        )
        service._get_current_ticket = AsyncMock(return_value=ticket)
        service.ticket_service.mark_handed_off = AsyncMock(return_value=ticket)
        service._broadcast_ticket_update = AsyncMock()
        service._broadcast_conversation_state = AsyncMock()
        service._broadcast_support_queue_change = AsyncMock()

        result = await service.accept_handoff(
            conversation_id="conv_123",
            operator="agent_a",
            reason="客服接手",
        )

        assert result["success"] is True
        service.ticket_service.mark_handed_off.assert_awaited_once_with(ticket, operator="agent_a")
        service._broadcast_support_queue_change.assert_awaited_once_with(
            conversation_id="conv_123",
            handoff_state="human",
            reason="客服接手",
            source="accept_handoff",
        )

    @pytest.mark.anyio
    async def test_finish_handoff_with_summary_marks_resolved(self):
        """测试人工结束并填写总结时会默认把 ticket 标记为 resolved。"""
        service = ComplaintHandoffService(MagicMock())
        ticket = build_ticket(status=ComplaintStatus.HANDED_OFF.value)

        service.support_handoff_service.end_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "ai"}
        )
        service._get_current_ticket = AsyncMock(return_value=ticket)
        service.ticket_service.mark_resolved = AsyncMock(return_value=ticket)
        service._broadcast_ticket_update = AsyncMock()
        service._broadcast_conversation_state = AsyncMock()
        service._broadcast_support_queue_change = AsyncMock()

        result = await service.finish_handoff(
            conversation_id="conv_123",
            operator="agent_a",
            summary="人工已补充处理完成",
        )

        assert result["success"] is True
        service.ticket_service.mark_resolved.assert_awaited_once_with(
            ticket,
            summary="人工已补充处理完成",
        )
        service._broadcast_support_queue_change.assert_awaited_once_with(
            conversation_id="conv_123",
            handoff_state="ai",
            reason="人工已补充处理完成",
            source="finish_handoff",
        )

    @pytest.mark.anyio
    async def test_transfer_handoff_broadcasts_conversation_state(self):
        """测试人工转接只更新会话状态广播，不修改当前主 ticket。"""
        service = ComplaintHandoffService(MagicMock())

        service.support_handoff_service.transfer_handoff = AsyncMock(
            return_value={
                "success": True,
                "conversation_id": "conv_123",
                "operator": "agent_b",
                "previous_operator": "agent_a",
                "handoff_state": "human",
                "transferred": True,
            }
        )
        service._broadcast_conversation_state = AsyncMock()
        service._broadcast_ticket_update = AsyncMock()
        service._broadcast_support_queue_change = AsyncMock()

        result = await service.transfer_handoff(
            conversation_id="conv_123",
            operator="agent_b",
            reason="转给赔付专员",
        )

        assert result["success"] is True
        service._broadcast_conversation_state.assert_awaited_once_with("conv_123")
        service._broadcast_ticket_update.assert_not_called()
        service._broadcast_support_queue_change.assert_awaited_once_with(
            conversation_id="conv_123",
            handoff_state="human",
            reason="转给赔付专员",
            source="transfer_handoff",
        )
