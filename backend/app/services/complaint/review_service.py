"""问题单审查服务

本文件的业务职责是把 reviewer 的结构化输出转换成 ticket 和 task 的可执行状态，
确保候选回复在业务上合规后才能真正对用户输出。
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.repositories.complaint_review import ComplaintReviewRepository
from app.schemas.complaint import (
    ComplaintReviewStatus,
    ComplaintTriageResult,
    ExecutorResult,
    PlannerDecision,
    ReviewDecision,
)
from app.services.complaint.task_service import TaskService
from app.services.complaint.ticket_service import TicketService


class ReviewService:
    """问题单审查服务。"""

    def __init__(self, session: AsyncSession):
        """初始化审查服务。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.review_repo = ComplaintReviewRepository(session)
        self.task_service = TaskService(session)
        self.ticket_service = TicketService(session)

    async def create_pending_review(
        self,
        *,
        ticket_id: str,
        task_id: str,
        reviewer_agent_tag: str,
    ) -> ComplaintReview:
        """创建待审查记录。

        这个方法服务于 executor 输出之后、reviewer 正式判定之前的中间状态。
        """
        review = ComplaintReview(
            id=str(uuid.uuid4()),
            ticket_id=ticket_id,
            task_id=task_id,
            reviewer_agent_tag=reviewer_agent_tag,
            status=ComplaintReviewStatus.PENDING.value,
            reasons=[],
        )
        return await self.review_repo.create(review)

    async def apply_review_result(
        self,
        *,
        review: ComplaintReview,
        task: ComplaintTask,
        ticket: ComplaintTicket,
        decision: ReviewDecision,
    ) -> ComplaintReview:
        """应用审查结果并同步 ticket/task 状态。

        业务规则：
        - passed: 任务完成，ticket 保持推进或进入 resolved
        - rejected: 任务失败，ticket 进入 rework_required
        - escalated: ticket 直接进入 handoff_pending
        """
        review.status = decision.status.value
        review.score = decision.score
        review.risk_level = decision.risk_level
        review.reasons = decision.reasons
        review.suggested_next_agent = decision.suggested_next_agent
        review.review_payload = decision.model_dump()
        await self.review_repo.update(review)

        task.review_status = decision.status.value
        await self.ticket_service.sync_review_snapshot(
            ticket,
            review_status=decision.status,
            review_score=decision.score,
        )

        if decision.status == ComplaintReviewStatus.PASSED:
            await self.task_service.complete_task(task, output_payload=task.output_payload)
            return review

        if decision.status == ComplaintReviewStatus.REJECTED:
            await self.task_service.fail_task(task, reason="review_rejected")
            await self.ticket_service.mark_rework_required(
                ticket,
                block_reason="review_rejected",
            )
            return review

        await self.task_service.block_task(task, reason="review_escalated")
        await self.ticket_service.mark_handoff_pending(
            ticket,
            handoff_reason="review_escalated",
            handoff_summary={
                "reasons": decision.reasons,
                "suggested_next_agent": decision.suggested_next_agent,
            },
        )
        return review

    def run_review(
        self,
        *,
        ticket: ComplaintTicket,
        task: ComplaintTask,
        triage_result: ComplaintTriageResult,
        planner_decision: PlannerDecision,
        executor_result: ExecutorResult,
    ) -> ReviewDecision:
        """执行第一阶段的确定性 review 决策。

        这个方法先用保守业务规则判断候选输出是否可外发，后续再替换成真正 reviewer Agent。
        """
        reject_reasons: list[str] = []

        if planner_decision.should_handoff or executor_result.handoff_recommended:
            return ReviewDecision(
                status=ComplaintReviewStatus.ESCALATED,
                score=40,
                risk_level=triage_result.risk_level,
                reasons=[
                    executor_result.handoff_reason or "当前场景已触发人工接入规则",
                ],
                suggested_next_agent="human_support",
                should_handoff=True,
            )

        if triage_result.requested_human:
            return ReviewDecision(
                status=ComplaintReviewStatus.ESCALATED,
                score=45,
                risk_level=triage_result.risk_level,
                reasons=["用户已明确要求人工客服接手"],
                suggested_next_agent="human_support",
                should_handoff=True,
            )

        if triage_result.risk_level == "high":
            return ReviewDecision(
                status=ComplaintReviewStatus.ESCALATED,
                score=35,
                risk_level="high",
                reasons=["当前风险等级过高，第一阶段必须转人工兜底"],
                suggested_next_agent="human_support",
                should_handoff=True,
            )

        if not executor_result.content.strip():
            reject_reasons.append("候选回复为空，不能直接对外发送")

        if planner_decision.task_type == "resolution":
            has_order_id = bool((ticket.slot_data or {}).get("order_id") or executor_result.collected_slots.get("order_id"))
            if not has_order_id:
                reject_reasons.append("缺少订单号，不能直接进入处理承诺")

        if planner_decision.task_type == "case_collect" and not triage_result.missing_slots:
            reject_reasons.append("信息收集任务没有明确指出缺失信息")

        if reject_reasons:
            return ReviewDecision(
                status=ComplaintReviewStatus.REJECTED,
                score=max(55, 80 - len(reject_reasons) * 10),
                risk_level=triage_result.risk_level,
                reasons=reject_reasons,
                suggested_next_agent="case_intake_agent",
                should_handoff=False,
            )

        completion_bonus = 10 if executor_result.task_completed else 0
        return ReviewDecision(
            status=ComplaintReviewStatus.PASSED,
            score=min(96, 82 + completion_bonus),
            risk_level=triage_result.risk_level,
            reasons=[],
            suggested_next_agent=None,
            should_handoff=False,
        )

    def should_escalate_after_reject(self, ticket: ComplaintTicket) -> bool:
        """判断多次驳回后是否应直接升级人工。

        第一阶段采用简单业务规则：返工次数达到 2 次后，默认建议升级人工。
        """
        return ticket.rework_count >= 2
