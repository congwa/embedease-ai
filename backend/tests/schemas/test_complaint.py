"""客诉 Schema 测试

测试投诉域核心状态枚举和结构化返回对象，确保后续编排链路依赖的状态值稳定可用。
"""

import pytest
from pydantic import ValidationError

from app.schemas.complaint import (
    ACTIVE_COMPLAINT_STATUSES,
    ActiveTicketResolution,
    ComplaintReviewStatus,
    ComplaintStatus,
    ComplaintTaskStatus,
    IssueContinuity,
    ReviewDecision,
    TicketResolutionDecision,
)


class TestComplaintStatusEnum:
    """测试问题单状态枚举。"""

    def test_active_statuses_include_phase1_core_states(self):
        """测试 Phase 1 主链路要求的活动状态都已纳入。"""
        assert ComplaintStatus.NEW in ACTIVE_COMPLAINT_STATUSES
        assert ComplaintStatus.PLANNED in ACTIVE_COMPLAINT_STATUSES
        assert ComplaintStatus.HANDOFF_PENDING in ACTIVE_COMPLAINT_STATUSES

    def test_closed_status_not_marked_active(self):
        """测试关闭态不会再被当作主活动问题单。"""
        assert ComplaintStatus.CLOSED not in ACTIVE_COMPLAINT_STATUSES


class TestComplaintTaskStatusEnum:
    """测试任务状态枚举。"""

    def test_waiting_review_value(self):
        """测试待审查任务状态值稳定。"""
        assert ComplaintTaskStatus.WAITING_REVIEW.value == "waiting_review"


class TestActiveTicketResolution:
    """测试 ticket 归并结果模型。"""

    def test_resolution_accepts_valid_payload(self):
        """测试主链路能生成合法的 ticket 决策结果。"""
        resolution = ActiveTicketResolution(
            decision=TicketResolutionDecision.REUSE_ACTIVE_TICKET,
            ticket_id="ticket_123",
            reason="当前消息仍属于同一问题",
            issue_continuity=IssueContinuity.SAME_ISSUE,
            confidence=0.92,
        )

        assert resolution.ticket_id == "ticket_123"
        assert resolution.decision == TicketResolutionDecision.REUSE_ACTIVE_TICKET

    def test_resolution_rejects_invalid_confidence(self):
        """测试置信度超出范围时会被拒绝，避免上层使用脏数据。"""
        with pytest.raises(ValidationError):
            ActiveTicketResolution(
                decision=TicketResolutionDecision.CREATE_NEW_TICKET,
                ticket_id="ticket_123",
                reason="错误数据",
                issue_continuity=IssueContinuity.NEW_ISSUE,
                confidence=1.5,
            )


class TestReviewDecision:
    """测试审查决策模型。"""

    def test_review_decision_keeps_business_fields(self):
        """测试 reviewer 输出的核心业务字段能够被结构化承载。"""
        decision = ReviewDecision(
            status=ComplaintReviewStatus.REJECTED,
            score=58,
            risk_level="high",
            reasons=["缺少退款承诺"],
            suggested_next_agent="planner",
            should_handoff=False,
        )

        assert decision.status == ComplaintReviewStatus.REJECTED
        assert decision.reasons == ["缺少退款承诺"]

    def test_review_decision_defaults(self):
        """测试默认值满足最小审查输出要求。"""
        decision = ReviewDecision(status=ComplaintReviewStatus.PASSED)

        assert decision.reasons == []
        assert decision.should_handoff is False
