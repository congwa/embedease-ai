"""ReviewService 测试

测试 reviewer 决策如何驱动 task 与 ticket 的后续流转，保证低质量结果不会直接外发。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import (
    ComplaintReviewStatus,
    ComplaintStatus,
    ComplaintTaskStatus,
    ComplaintTriageResult,
    ExecutorResult,
    IssueContinuity,
    PlannerDecision,
    ReviewDecision,
)
from app.services.complaint.review_service import ReviewService


def build_review() -> ComplaintReview:
    """构造一个基础审查对象，服务于审查状态推进测试。"""
    return ComplaintReview(
        id="review_123",
        ticket_id="ticket_123",
        task_id="task_123",
        reviewer_agent_tag="reviewer",
        status=ComplaintReviewStatus.PENDING.value,
        reasons=[],
    )


def build_task() -> ComplaintTask:
    """构造一个基础任务对象，服务于 review 结果联动测试。"""
    return ComplaintTask(
        id="task_123",
        ticket_id="ticket_123",
        task_type="resolution",
        agent_tag="executor",
        status=ComplaintTaskStatus.WAITING_REVIEW.value,
        retry_count=0,
    )


def build_ticket() -> ComplaintTicket:
    """构造一个基础问题单对象，服务于 review 结果联动测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=ComplaintStatus.PENDING_REVIEW.value,
        is_primary_active=True,
        unresolved_turns=0,
        rework_count=0,
        handoff_required=False,
        secondary_issue_tags=[],
        secondary_issues=[],
        slot_data={},
        timeline=[],
        version=1,
    )


def build_triage_result(**overrides: object) -> ComplaintTriageResult:
    """构造基础 triage 结果，服务于 run_review 规则测试。"""
    payload = {
        "primary_issue_tag": "delivery_delay",
        "priority_level": "medium",
        "risk_level": "low",
        "sentiment": "neutral",
        "severity": "normal",
        "emotional_intensity": "normal",
        "continuity": IssueContinuity.SAME_ISSUE,
        "requested_human": False,
        "missing_slots": [],
        "extracted_slots": {},
        "summary": "默认 triage",
    }
    payload.update(overrides)
    return ComplaintTriageResult(**payload)


def build_planner_decision(**overrides: object) -> PlannerDecision:
    """构造基础 planner 决策，服务于 run_review 规则测试。"""
    payload = {
        "assigned_agent_tag": "resolution_execution_agent",
        "task_type": "resolution",
        "goal": "推进处理",
        "success_criteria": ["用户知道下一步动作"],
        "should_handoff": False,
        "next_node_key": "resolution",
        "reasoning": "默认 planner",
    }
    payload.update(overrides)
    return PlannerDecision(**payload)


def build_executor_result(**overrides: object) -> ExecutorResult:
    """构造基础 executor 结果，服务于 run_review 规则测试。"""
    payload = {
        "content": "默认候选回复",
        "task_completed": True,
        "collected_slots": {"order_id": "12345678"},
        "handoff_recommended": False,
        "handoff_reason": None,
        "next_hint": "默认 next_hint",
    }
    payload.update(overrides)
    return ExecutorResult(**payload)


class TestReviewServiceInit:
    """测试 ReviewService 初始化。"""

    def test_init_with_session(self):
        """测试审查服务会初始化 review、task、ticket 依赖。"""
        mock_session = MagicMock()
        service = ReviewService(mock_session)

        assert service.session is mock_session
        assert service.review_repo is not None
        assert service.task_service is not None
        assert service.ticket_service is not None


class TestReviewServiceBehavior:
    """测试 ReviewService 核心业务行为。"""

    @pytest.mark.anyio
    async def test_create_pending_review_defaults_to_pending(self):
        """测试 executor 输出后创建的 review 默认处于 pending。"""
        mock_session = MagicMock()
        service = ReviewService(mock_session)
        service.review_repo.create = AsyncMock(side_effect=lambda review: review)

        review = await service.create_pending_review(
            ticket_id="ticket_123",
            task_id="task_123",
            reviewer_agent_tag="reviewer",
        )

        assert review.status == ComplaintReviewStatus.PENDING.value
        assert review.reasons == []

    @pytest.mark.anyio
    async def test_apply_review_result_passed_completes_task(self):
        """测试 review 通过后任务会完成，ticket 只同步 review 快照。"""
        mock_session = MagicMock()
        service = ReviewService(mock_session)
        service.review_repo.update = AsyncMock(side_effect=lambda review: review)
        service.task_service.complete_task = AsyncMock()
        service.task_service.fail_task = AsyncMock()
        service.task_service.block_task = AsyncMock()
        service.ticket_service.sync_review_snapshot = AsyncMock()
        service.ticket_service.mark_rework_required = AsyncMock()
        service.ticket_service.mark_handoff_pending = AsyncMock()
        review = build_review()
        task = build_task()
        task.output_payload = {"reply": "已处理完成"}
        ticket = build_ticket()
        decision = ReviewDecision(status=ComplaintReviewStatus.PASSED, score=95, reasons=[])

        result = await service.apply_review_result(
            review=review,
            task=task,
            ticket=ticket,
            decision=decision,
        )

        assert result.status == ComplaintReviewStatus.PASSED.value
        service.task_service.complete_task.assert_awaited_once_with(
            task,
            output_payload={"reply": "已处理完成"},
        )
        service.task_service.fail_task.assert_not_called()

    @pytest.mark.anyio
    async def test_apply_review_result_rejected_marks_rework(self):
        """测试 review 驳回后任务失败且问题单进入返工。"""
        mock_session = MagicMock()
        service = ReviewService(mock_session)
        service.review_repo.update = AsyncMock(side_effect=lambda review: review)
        service.task_service.complete_task = AsyncMock()
        service.task_service.fail_task = AsyncMock()
        service.task_service.block_task = AsyncMock()
        service.ticket_service.sync_review_snapshot = AsyncMock()
        service.ticket_service.mark_rework_required = AsyncMock()
        service.ticket_service.mark_handoff_pending = AsyncMock()
        review = build_review()
        task = build_task()
        ticket = build_ticket()
        decision = ReviewDecision(
            status=ComplaintReviewStatus.REJECTED,
            score=56,
            reasons=["赔付承诺不明确"],
        )

        await service.apply_review_result(
            review=review,
            task=task,
            ticket=ticket,
            decision=decision,
        )

        service.task_service.fail_task.assert_awaited_once_with(task, reason="review_rejected")
        service.ticket_service.mark_rework_required.assert_awaited_once_with(
            ticket,
            block_reason="review_rejected",
        )
        service.task_service.block_task.assert_not_called()

    @pytest.mark.anyio
    async def test_apply_review_result_escalated_marks_handoff_pending(self):
        """测试高风险 review 会阻塞任务并转入人工接入。"""
        mock_session = MagicMock()
        service = ReviewService(mock_session)
        service.review_repo.update = AsyncMock(side_effect=lambda review: review)
        service.task_service.complete_task = AsyncMock()
        service.task_service.fail_task = AsyncMock()
        service.task_service.block_task = AsyncMock()
        service.ticket_service.sync_review_snapshot = AsyncMock()
        service.ticket_service.mark_rework_required = AsyncMock()
        service.ticket_service.mark_handoff_pending = AsyncMock()
        review = build_review()
        task = build_task()
        ticket = build_ticket()
        decision = ReviewDecision(
            status=ComplaintReviewStatus.ESCALATED,
            score=40,
            risk_level="high",
            reasons=["赔付金额超限"],
            suggested_next_agent="human_support",
        )

        await service.apply_review_result(
            review=review,
            task=task,
            ticket=ticket,
            decision=decision,
        )

        service.task_service.block_task.assert_awaited_once_with(task, reason="review_escalated")
        service.ticket_service.mark_handoff_pending.assert_awaited_once_with(
            ticket,
            handoff_reason="review_escalated",
            handoff_summary={
                "reasons": ["赔付金额超限"],
                "suggested_next_agent": "human_support",
            },
        )

    def test_should_escalate_after_reject_uses_rework_threshold(self):
        """测试连续返工达到阈值后会建议升级人工。"""
        mock_session = MagicMock()
        service = ReviewService(mock_session)
        ticket = build_ticket()
        ticket.rework_count = 2

        assert service.should_escalate_after_reject(ticket) is True

    def test_run_review_high_risk_escalates(self):
        """测试高风险 triage 会直接升级人工。"""
        service = ReviewService(MagicMock())
        ticket = build_ticket()

        decision = service.run_review(
            ticket=ticket,
            task=build_task(),
            triage_result=build_triage_result(risk_level="high"),
            planner_decision=build_planner_decision(),
            executor_result=build_executor_result(),
        )

        assert decision.status == ComplaintReviewStatus.ESCALATED
        assert decision.should_handoff is True

    def test_run_review_missing_order_id_rejects_resolution(self):
        """测试 resolution 缺订单号时会被 review 驳回。"""
        service = ReviewService(MagicMock())
        ticket = build_ticket()
        ticket.slot_data = {}

        decision = service.run_review(
            ticket=ticket,
            task=build_task(),
            triage_result=build_triage_result(),
            planner_decision=build_planner_decision(),
            executor_result=build_executor_result(collected_slots={}, content="我会继续处理"),
        )

        assert decision.status == ComplaintReviewStatus.REJECTED
        assert "缺少订单号" in decision.reasons[0]
