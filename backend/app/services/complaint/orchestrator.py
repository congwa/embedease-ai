"""客诉主链路编排器

本文件的业务职责是把一条用户消息转换成完整的客诉处理闭环：
ticket 归并、triage、plan、execute、review、handoff 与事件输出都在这里统一编排。
"""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from langgraph_agent_kit import make_event
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.repositories.conversation import ConversationRepository
from app.schemas.complaint import (
    ComplaintMessageIntakeResult,
    ComplaintReviewStatus,
    ComplaintTriageResult,
    HandoffRequestResult,
    PlannerDecision,
    ReviewDecision,
    TicketStreamSummary,
)
from app.schemas.websocket import WSAction, WSRole
from app.services.complaint.executor_service import ExecutorService
from app.services.complaint.handoff_service import ComplaintHandoffService
from app.services.complaint.message_intake_service import ComplaintMessageIntakeService
from app.services.complaint.planner_service import PlannerService
from app.services.complaint.review_service import ReviewService
from app.services.complaint.task_service import TaskService
from app.services.complaint.ticket_service import TicketService
from app.services.conversation import ConversationService
from app.services.support.state_service import SupportStateService
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import ws_manager

ORDER_RELATED_ISSUES = {
    "delivery_delay",
    "refund_request",
    "return_exchange",
    "damaged_item",
    "wrong_item",
    "payment_issue",
    "invoice_issue",
}
SERVICE_ISSUES = {"service_attitude", "manual_request"}
LEGAL_RISK_MARKERS = ("投诉平台", "监管", "12315", "起诉", "曝光", "律师", "法院", "报警")
ANGER_MARKERS = ("气死", "太差", "离谱", "垃圾", "生气", "投诉", "不满", "骗人", "发泄", "失望")
HIGH_EMOTION_MARKERS = ("气炸", "忍无可忍", "立刻处理", "马上给我", "太过分")


@dataclass
class PreparedComplaintRun:
    """prepare_run 阶段的中间上下文。

    这个对象服务于 prepare 与 execute 两段式编排，避免 execute 再次查询和重复建 task。
    """

    conversation_id: str
    user_id: str
    user_message_id: str
    user_message: str
    ticket: ComplaintTicket
    intake_result: ComplaintMessageIntakeResult
    triage_result: ComplaintTriageResult
    planner_decision: PlannerDecision
    executor_task: ComplaintTask
    pre_stream_events: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ComplaintRunContext:
    """可直接交给流式层消费的客诉运行结果。

    这个对象只保留已序列化的结果，避免流式阶段依赖已经关闭的数据库 session。
    """

    conversation_id: str
    user_id: str
    user_message_id: str
    ticket_id: str
    ticket_summary: TicketStreamSummary
    triage_result: ComplaintTriageResult
    planner_decision: PlannerDecision
    review_decision: ReviewDecision
    assistant_candidate_content: str
    should_emit_assistant_final: bool
    handoff_result: HandoffRequestResult | None
    pre_stream_events: list[dict[str, Any]]
    post_stream_events: list[dict[str, Any]]
    assistant_extra_metadata: dict[str, Any] = field(default_factory=dict)


class ComplaintConversationOrchestrator:
    """客诉消息主链路编排器。

    这个编排器把 router 入口从“直接回答消息”改成“围绕当前主 ticket 推进处理闭环”。
    """

    def __init__(self, session: AsyncSession):
        """初始化客诉编排器。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.ticket_repo = ComplaintTicketRepository(session)
        self.ticket_service = TicketService(session)
        self.task_service = TaskService(session)
        self.review_service = ReviewService(session)
        self.message_intake_service = ComplaintMessageIntakeService(session)
        self.planner_service = PlannerService(session)
        self.executor_service = ExecutorService(session)
        self.complaint_handoff_service = ComplaintHandoffService(session)
        self.support_state_service = SupportStateService(session)

    async def handle_user_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        user_message_id: str,
        user_message: str,
    ) -> ComplaintRunContext:
        """处理一条用户消息的完整客诉闭环。

        这个方法是 router 层唯一需要依赖的 complaint 主入口。
        """
        prepared = await self.prepare_run(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message_id=user_message_id,
            user_message=user_message,
        )
        return await self.execute_run(prepared)

    async def prepare_run(
        self,
        *,
        conversation_id: str,
        user_id: str,
        user_message_id: str,
        user_message: str,
    ) -> PreparedComplaintRun:
        """准备一条客诉运行上下文。

        这个阶段只做 ticket 归并、triage、planner 和 executor task 建立，不直接执行候选回复。
        """
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise ValueError(f"会话不存在: {conversation_id}")

        intake_result = await self.message_intake_service.process_user_message(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message=user_message,
            user_message_id=user_message_id,
        )
        ticket = await self.ticket_repo.get_by_id(intake_result.ticket.id)
        if ticket is None:
            raise ValueError(f"投诉编排未找到主问题单: {intake_result.ticket.id}")

        triage_task = await self.task_service.create_task(
            ticket_id=ticket.id,
            task_type="triage",
            agent_tag="front_desk_agent",
            input_payload={
                "message": user_message,
                "ticket_resolution": intake_result.resolution.model_dump(mode="json"),
            },
            goal="识别主问题、情绪、风险和当前缺失信息",
            success_criteria=["主问题标签明确", "风险等级明确", "缺失槽位明确"],
            review_required=False,
        )
        pre_stream_events = list(intake_result.events)
        pre_stream_events.append(self._build_task_event("complaint.task.created", triage_task))

        triage_task = await self.task_service.start_task(triage_task)
        pre_stream_events.append(self._build_task_event("complaint.task.started", triage_task))

        triage_result = self._run_front_desk(
            ticket=ticket,
            user_message=user_message,
            intake_result=intake_result,
        )

        ticket = await self.ticket_service.set_current_agent(ticket, "front_desk_agent")
        ticket = await self.ticket_service.set_current_node(ticket, "triage")
        ticket = await self.ticket_service.update_classification(
            ticket,
            primary_issue_tag=triage_result.primary_issue_tag,
            priority_level=triage_result.priority_level,
            risk_level=triage_result.risk_level,
            sentiment=triage_result.sentiment,
            severity=triage_result.severity,
        )
        ticket = await self.ticket_service.merge_slot_data(ticket, triage_result.extracted_slots)
        ticket = await self.ticket_service.mark_triaged(ticket)
        ticket = await self.ticket_service.append_timeline_entry(
            ticket,
            event_type="triage.completed",
            summary=triage_result.summary,
            extra=triage_result.model_dump(mode="json"),
        )
        triage_task = await self.task_service.complete_task(
            triage_task,
            output_payload=triage_result.model_dump(mode="json"),
        )
        pre_stream_events.append(self._build_task_event("complaint.task.completed", triage_task))
        pre_stream_events.append(self._build_ticket_updated_event(ticket))

        plan_task = await self.task_service.create_task(
            ticket_id=ticket.id,
            task_type="plan",
            agent_tag="service_planner_agent",
            input_payload={
                "triage": triage_result.model_dump(mode="json"),
                "ticket": self.ticket_service.build_stream_summary(ticket).model_dump(mode="json"),
            },
            goal="决定当前应该由哪个岗位处理本轮问题",
            success_criteria=["assigned_agent_tag 明确", "next_node_key 明确"],
            review_required=False,
        )
        pre_stream_events.append(self._build_task_event("complaint.task.created", plan_task))

        plan_task = await self.task_service.start_task(plan_task)
        pre_stream_events.append(self._build_task_event("complaint.task.started", plan_task))

        planner_decision = await self.planner_service.plan(
            ticket=ticket,
            triage_result=triage_result,
            last_user_message=user_message,
        )

        ticket = await self.ticket_service.set_current_agent(ticket, planner_decision.assigned_agent_tag)
        ticket = await self.ticket_service.set_current_node(ticket, planner_decision.next_node_key)
        ticket = await self.ticket_service.mark_planned(ticket)
        ticket = await self.ticket_service.append_timeline_entry(
            ticket,
            event_type="plan.completed",
            summary=planner_decision.reasoning,
            extra=planner_decision.model_dump(mode="json"),
        )
        plan_task = await self.task_service.complete_task(
            plan_task,
            output_payload=planner_decision.model_dump(mode="json"),
        )
        pre_stream_events.append(self._build_task_event("complaint.task.completed", plan_task))
        pre_stream_events.append(self._build_ticket_updated_event(ticket))

        executor_task = await self.task_service.create_task(
            ticket_id=ticket.id,
            task_type=planner_decision.task_type,
            agent_tag=planner_decision.assigned_agent_tag,
            input_payload={
                "triage": triage_result.model_dump(mode="json"),
                "planner": planner_decision.model_dump(mode="json"),
                "message": user_message,
            },
            goal=planner_decision.goal,
            success_criteria=planner_decision.success_criteria,
            review_required=True,
        )
        pre_stream_events.append(self._build_task_event("complaint.task.created", executor_task))

        executor_task = await self.task_service.start_task(executor_task)
        ticket = await self.ticket_service.set_current_task(ticket, executor_task.id)
        ticket = await self.ticket_service.set_current_agent(ticket, planner_decision.assigned_agent_tag)
        ticket = await self.ticket_service.set_current_node(ticket, planner_decision.next_node_key)
        ticket = await self.ticket_service.mark_in_progress(ticket)
        pre_stream_events.append(self._build_task_event("complaint.task.started", executor_task))
        pre_stream_events.append(self._build_ticket_updated_event(ticket))

        await self._broadcast_ticket_update(ticket)
        await self._broadcast_conversation_state(conversation_id)

        return PreparedComplaintRun(
            conversation_id=conversation_id,
            user_id=user_id,
            user_message_id=user_message_id,
            user_message=user_message,
            ticket=ticket,
            intake_result=intake_result,
            triage_result=triage_result,
            planner_decision=planner_decision,
            executor_task=executor_task,
            pre_stream_events=pre_stream_events,
        )

    async def execute_run(self, prepared: PreparedComplaintRun) -> ComplaintRunContext:
        """执行 prepared context 的 executor、review 和 handoff 分支。

        这个阶段会真正产出候选回复，并决定是否允许对外回复。
        """
        ticket = prepared.ticket
        executor_task = prepared.executor_task
        post_stream_events: list[dict[str, Any]] = []

        executor_result = await self.executor_service.execute(
            ticket=ticket,
            triage_result=prepared.triage_result,
            planner_decision=prepared.planner_decision,
            last_user_message=prepared.user_message,
        )

        ticket = await self.ticket_service.merge_slot_data(ticket, executor_result.collected_slots)
        ticket = await self.ticket_service.mark_pending_review(ticket)
        executor_task = await self.task_service.update_output_payload(
            executor_task,
            executor_result.model_dump(mode="json"),
        )
        executor_task = await self.task_service.mark_waiting_review(executor_task)
        post_stream_events.append(self._build_task_event("complaint.task.completed", executor_task))
        post_stream_events.append(self._build_ticket_updated_event(ticket))

        review_task = await self.task_service.create_task(
            ticket_id=ticket.id,
            task_type="review",
            agent_tag="quality_reviewer_agent",
            input_payload={
                "executor_result": executor_result.model_dump(mode="json"),
                "planner": prepared.planner_decision.model_dump(mode="json"),
                "triage": prepared.triage_result.model_dump(mode="json"),
            },
            goal="审查当前候选结果能否安全且完整地对外输出",
            success_criteria=["review status 明确", "reasons 明确"],
            review_required=False,
        )
        post_stream_events.append(self._build_task_event("complaint.task.created", review_task))

        review_task = await self.task_service.start_task(review_task)
        post_stream_events.append(self._build_task_event("complaint.task.started", review_task))

        review = await self.review_service.create_pending_review(
            ticket_id=ticket.id,
            task_id=executor_task.id,
            reviewer_agent_tag="quality_reviewer_agent",
        )
        post_stream_events.append(
            {
                "type": "complaint.review.pending",
                "payload": {
                    "ticket_id": ticket.id,
                    "task_id": executor_task.id,
                    "review_id": review.id,
                },
            }
        )

        review_decision = self.review_service.run_review(
            ticket=ticket,
            task=executor_task,
            triage_result=prepared.triage_result,
            planner_decision=prepared.planner_decision,
            executor_result=executor_result,
        )
        await self.review_service.apply_review_result(
            review=review,
            task=executor_task,
            ticket=ticket,
            decision=review_decision,
        )
        review_task = await self.task_service.complete_task(
            review_task,
            output_payload=review_decision.model_dump(mode="json"),
        )
        post_stream_events.append(self._build_task_event("complaint.task.completed", review_task))

        handoff_result: HandoffRequestResult | None = None
        should_emit_assistant_final = False

        if review_decision.status == ComplaintReviewStatus.PASSED:
            if prepared.planner_decision.task_type == "resolution" and executor_result.task_completed:
                ticket = await self.ticket_service.mark_resolved(
                    ticket,
                    summary=executor_result.next_hint or executor_result.content,
                )
            else:
                ticket = await self.ticket_service.mark_in_progress(ticket)
                if executor_result.task_completed:
                    ticket = await self.ticket_service.reset_unresolved_turns(ticket)

            post_stream_events.append(
                {
                    "type": "complaint.review.passed",
                    "payload": self._build_review_payload(review, review_decision),
                }
            )
            post_stream_events.append(self._build_ticket_updated_event(ticket))
            should_emit_assistant_final = bool(executor_result.content.strip())

        elif review_decision.status == ComplaintReviewStatus.REJECTED:
            post_stream_events.append(
                {
                    "type": "complaint.review.rejected",
                    "payload": self._build_review_payload(review, review_decision),
                }
            )
            post_stream_events.append(self._build_ticket_updated_event(ticket))
            if self.review_service.should_escalate_after_reject(ticket):
                handoff_result = await self.complaint_handoff_service.request_handoff_for_ticket(
                    ticket,
                    handoff_reason="连续 review 驳回后升级人工",
                    handoff_summary={
                        "reasons": review_decision.reasons,
                        "suggested_next_agent": review_decision.suggested_next_agent,
                    },
                    requested_by="complaint_reviewer",
                )

        else:
            post_stream_events.append(
                {
                    "type": "complaint.review.rejected",
                    "payload": self._build_review_payload(review, review_decision),
                }
            )
            handoff_result = await self.complaint_handoff_service.request_handoff_for_ticket(
                ticket,
                handoff_reason=review_decision.reasons[0] if review_decision.reasons else "review escalated",
                handoff_summary={
                    "reasons": review_decision.reasons,
                    "suggested_next_agent": review_decision.suggested_next_agent,
                },
                requested_by="complaint_reviewer",
            )

        if handoff_result is not None and handoff_result.requested:
            post_stream_events.append(
                {
                    "type": "complaint.handoff_requested",
                    "payload": {
                        "conversation_id": handoff_result.conversation_id,
                        "ticket_id": handoff_result.ticket_id,
                        "handoff_reason": handoff_result.handoff_reason,
                        "handoff_summary": handoff_result.handoff_summary,
                        "message": executor_result.content,
                    },
                }
            )

        await self._broadcast_ticket_update(ticket)
        await self._broadcast_review_update(review)
        await self._broadcast_conversation_state(prepared.conversation_id)

        ticket_summary = self.ticket_service.build_stream_summary(ticket)
        assistant_extra_metadata = {
            "complaint_ticket_id": ticket.id,
            "planner": prepared.planner_decision.model_dump(mode="json"),
            "review": review_decision.model_dump(mode="json"),
        }

        return ComplaintRunContext(
            conversation_id=prepared.conversation_id,
            user_id=prepared.user_id,
            user_message_id=prepared.user_message_id,
            ticket_id=ticket.id,
            ticket_summary=ticket_summary,
            triage_result=prepared.triage_result,
            planner_decision=prepared.planner_decision,
            review_decision=review_decision,
            assistant_candidate_content=executor_result.content,
            should_emit_assistant_final=should_emit_assistant_final and handoff_result is None,
            handoff_result=handoff_result,
            pre_stream_events=prepared.pre_stream_events,
            post_stream_events=post_stream_events,
            assistant_extra_metadata=assistant_extra_metadata,
        )

    def _run_front_desk(
        self,
        *,
        ticket: ComplaintTicket,
        user_message: str,
        intake_result: ComplaintMessageIntakeResult,
    ) -> ComplaintTriageResult:
        """执行第一阶段的 front desk 识别。

        这个内部方法负责把原始用户消息压缩成 planner 可直接使用的 triage 结果。
        """
        primary_issue_tag = self._detect_primary_issue_tag(
            user_message=user_message,
            existing_issue_tag=ticket.primary_issue_tag,
        )
        extracted_slots = self._extract_triage_slots(user_message)
        sentiment = self._detect_sentiment(user_message)
        emotional_intensity = self._detect_emotional_intensity(user_message)
        requested_human = any(marker in user_message for marker in ("人工", "真人", "客服", "转人工", "专员"))
        risk_level = self._detect_risk_level(
            user_message=user_message,
            requested_human=requested_human,
            unresolved_turns=ticket.unresolved_turns,
        )
        priority_level = self._detect_priority_level(
            risk_level=risk_level,
            emotional_intensity=emotional_intensity,
            unresolved_turns=ticket.unresolved_turns,
            requested_human=requested_human,
        )
        severity = self._detect_severity(
            risk_level=risk_level,
            emotional_intensity=emotional_intensity,
            unresolved_turns=ticket.unresolved_turns,
        )
        missing_slots = self._detect_missing_slots(
            issue_tag=primary_issue_tag,
            current_slots={**(ticket.slot_data or {}), **extracted_slots},
        )
        summary = (
            f"主问题={primary_issue_tag}，风险={risk_level}，情绪={sentiment}，"
            f"缺失信息={','.join(missing_slots) if missing_slots else '无'}"
        )

        return ComplaintTriageResult(
            primary_issue_tag=primary_issue_tag,
            priority_level=priority_level,
            risk_level=risk_level,
            sentiment=sentiment,
            severity=severity,
            emotional_intensity=emotional_intensity,
            continuity=intake_result.resolution.issue_continuity,
            requested_human=requested_human,
            missing_slots=missing_slots,
            extracted_slots=extracted_slots,
            summary=summary,
        )

    def _detect_primary_issue_tag(
        self,
        *,
        user_message: str,
        existing_issue_tag: str | None,
    ) -> str:
        """识别当前主问题标签。

        这个内部方法服务于 triage 分类，让 planner 能围绕明确问题类型做决策。
        """
        issue_rules = [
            ("refund_request", ("退款", "退钱", "赔付", "补偿")),
            ("delivery_delay", ("没发货", "未发货", "物流", "延迟", "超时", "一直没到")),
            ("return_exchange", ("退货", "换货", "换新")),
            ("damaged_item", ("破损", "坏了", "碎了", "损坏")),
            ("wrong_item", ("发错", "错货", "不是这个商品")),
            ("payment_issue", ("支付", "扣款", "重复扣费")),
            ("invoice_issue", ("发票", "开票")),
            ("service_attitude", ("态度差", "客服态度", "服务差", "敷衍")),
            ("manual_request", ("人工", "真人", "客服", "专员")),
        ]
        for issue_tag, markers in issue_rules:
            if any(marker in user_message for marker in markers):
                return issue_tag
        return existing_issue_tag or "general_complaint"

    def _extract_triage_slots(self, user_message: str) -> dict[str, Any]:
        """抽取 triage 级别的基础槽位。

        这个内部方法服务于第一阶段的订单号、凭证等关键信息识别。
        """
        extracted_slots: dict[str, Any] = {}
        order_match = re.search(r"(?:订单号?|单号)[：:\s#-]*([A-Za-z0-9-]{6,})", user_message)
        if order_match:
            extracted_slots["order_id"] = order_match.group(1)
        elif plain_order_match := re.search(r"\b\d{6,20}\b", user_message):
            extracted_slots["order_id"] = plain_order_match.group(0)

        if any(marker in user_message for marker in ("截图", "照片", "图片", "凭证")):
            extracted_slots["evidence"] = True
        return extracted_slots

    def _detect_sentiment(self, user_message: str) -> str:
        """识别用户当前情绪方向。

        这个内部方法服务于 planner 判断是否要先走情绪安抚岗位。
        """
        if any(marker in user_message for marker in HIGH_EMOTION_MARKERS):
            return "angry"
        if any(marker in user_message for marker in ANGER_MARKERS):
            return "negative"
        if any(marker in user_message for marker in ("谢谢", "麻烦", "辛苦")):
            return "calm"
        return "neutral"

    def _detect_emotional_intensity(self, user_message: str) -> str:
        """识别情绪强度。

        这个内部方法服务于 planner 区分普通不满和需要优先安抚的强情绪场景。
        """
        if user_message.count("!") >= 2 or any(marker in user_message for marker in HIGH_EMOTION_MARKERS):
            return "high"
        if any(marker in user_message for marker in ANGER_MARKERS):
            return "medium"
        return "normal"

    def _detect_risk_level(
        self,
        *,
        user_message: str,
        requested_human: bool,
        unresolved_turns: int,
    ) -> str:
        """识别当前业务风险等级。

        这个内部方法服务于 handoff 规则和工作台高风险提醒。
        """
        if any(marker in user_message for marker in LEGAL_RISK_MARKERS):
            return "high"
        if requested_human and unresolved_turns >= 1:
            return "high"
        if any(marker in user_message for marker in ("退款", "赔付", "投诉")) or unresolved_turns >= 2:
            return "medium"
        return "low"

    def _detect_priority_level(
        self,
        *,
        risk_level: str,
        emotional_intensity: str,
        unresolved_turns: int,
        requested_human: bool,
    ) -> str:
        """识别当前优先级。

        这个内部方法服务于支持台排序和 planner 的执行优先级判断。
        """
        if risk_level == "high" or requested_human:
            return "urgent"
        if emotional_intensity == "high" or unresolved_turns >= 2:
            return "high"
        if risk_level == "medium":
            return "medium"
        return "low"

    def _detect_severity(
        self,
        *,
        risk_level: str,
        emotional_intensity: str,
        unresolved_turns: int,
    ) -> str:
        """识别问题严重程度。

        这个内部方法服务于 ticket 快照和人工接手摘要。
        """
        if risk_level == "high":
            return "severe"
        if emotional_intensity == "high" or unresolved_turns >= 3:
            return "major"
        if risk_level == "medium":
            return "moderate"
        return "normal"

    def _detect_missing_slots(
        self,
        *,
        issue_tag: str,
        current_slots: dict[str, Any],
    ) -> list[str]:
        """识别当前处理仍缺失的业务槽位。

        这个内部方法服务于 planner 决定是否进入 case_collect。
        """
        missing_slots: list[str] = []
        if issue_tag in ORDER_RELATED_ISSUES and not current_slots.get("order_id"):
            missing_slots.append("order_id")
        if issue_tag in {"damaged_item", "wrong_item"} and not current_slots.get("evidence"):
            missing_slots.append("evidence")
        if issue_tag in SERVICE_ISSUES and not current_slots.get("contact_expectation"):
            missing_slots.append("contact_expectation")
        return missing_slots

    def _build_task_event(self, event_type: str, task: ComplaintTask) -> dict[str, Any]:
        """构建 complaint task 事件。

        这个内部方法服务于 SSE 和前端任务阶段展示，保持所有 task 事件结构一致。
        """
        return {
            "type": event_type,
            "payload": {
                "task": {
                    "id": task.id,
                    "ticket_id": task.ticket_id,
                    "task_type": task.task_type,
                    "agent_tag": task.agent_tag,
                    "status": task.status,
                    "goal": task.goal,
                    "success_criteria": list(task.success_criteria or []),
                    "output_payload": task.output_payload,
                    "failure_reason": task.failure_reason,
                }
            },
        }

    def _build_ticket_updated_event(self, ticket: ComplaintTicket) -> dict[str, Any]:
        """构建 complaint.ticket.updated 事件。

        这个内部方法服务于前端在每个关键阶段刷新当前主问题单摘要。
        """
        return {
            "type": "complaint.ticket.updated",
            "payload": {
                "ticket": self.ticket_service.build_stream_summary(ticket).model_dump(mode="json"),
            },
        }

    def _build_review_payload(
        self,
        review: ComplaintReview,
        review_decision: ReviewDecision,
    ) -> dict[str, Any]:
        """构建 review 事件 payload。

        这个内部方法服务于工作台和用户聊天页理解“为什么本轮通过、驳回或升级人工”。
        """
        return {
            "review_id": review.id,
            "ticket_id": review.ticket_id,
            "task_id": review.task_id,
            "status": review_decision.status.value,
            "score": review_decision.score,
            "risk_level": review_decision.risk_level,
            "reasons": review_decision.reasons,
            "suggested_next_agent": review_decision.suggested_next_agent,
            "should_handoff": review_decision.should_handoff,
        }

    async def _broadcast_ticket_update(self, ticket: ComplaintTicket) -> None:
        """广播 ticket 更新到当前会话的 WebSocket 连接。

        这个内部方法服务于客服工作台和用户端实时感知 ticket 状态变化。
        """
        message = build_server_message(
            action=WSAction.SERVER_TICKET_UPDATED,
            payload={"ticket": self.ticket_service.build_stream_summary(ticket).model_dump(mode="json")},
            conversation_id=ticket.conversation_id,
        )
        await ws_manager.broadcast_to_conversation(ticket.conversation_id, message)

    async def _broadcast_review_update(self, review: ComplaintReview) -> None:
        """广播最近一次 review 结果。

        这个内部方法服务于工作台详情页实时刷新最近审查状态。
        """
        review_summary = self.support_state_service.build_review_summary(review)
        if review_summary is None:
            return
        ticket = await self.ticket_repo.get_by_id(review.ticket_id)
        if ticket is None:
            return
        message = build_server_message(
            action=WSAction.SERVER_REVIEW_UPDATED,
            payload={"review_summary": review_summary.model_dump(mode="json")},
            conversation_id=ticket.conversation_id,
        )
        await ws_manager.broadcast_to_conversation(ticket.conversation_id, message)

    async def _broadcast_conversation_state(self, conversation_id: str) -> None:
        """广播完整 conversation 状态。

        这个内部方法服务于支持台列表和详情页同步当前模式、ticket 与 review 快照。
        """
        state_payload = await self.support_state_service.build_websocket_state_payload(conversation_id)
        message = build_server_message(
            action=WSAction.SERVER_CONVERSATION_STATE,
            payload=state_payload,
            conversation_id=conversation_id,
        )
        await ws_manager.broadcast_to_conversation(conversation_id, message)

        queue_changed_message = build_server_message(
            action=WSAction.SERVER_SUPPORT_QUEUE_CHANGED,
            payload={
                "conversation_id": conversation_id,
                "handoff_state": state_payload["handoff_state"],
                "reason": (
                    state_payload["current_ticket"]["status"]
                    if state_payload.get("current_ticket")
                    else None
                ),
                "source": "complaint_orchestrator_state",
            },
            conversation_id=conversation_id,
        )
        await ws_manager.broadcast_to_role_global(WSRole.AGENT, queue_changed_message)


class ComplaintChatStreamOrchestrator:
    """投诉域流式输出编排器。

    这个类把 ComplaintRunContext 转换成最终 SSE 事件流，并在 review 通过时落库 assistant 消息。
    """

    def __init__(
        self,
        *,
        conversation_service: ConversationService,
        run_context: ComplaintRunContext,
        assistant_message_id: str,
    ) -> None:
        """初始化 complaint 流式编排器。

        Args:
            conversation_service: 用于落库 assistant 消息的会话服务。
            run_context: 已经执行完成的 complaint 运行结果。
            assistant_message_id: 当前响应的 assistant 消息 ID。
        """
        self._conversation_service = conversation_service
        self._run_context = run_context
        self._assistant_message_id = assistant_message_id
        self._seq = 0

    def _next_seq(self) -> int:
        """生成当前流内的递增序号。

        这个内部方法服务于 SSE 事件保持严格递增顺序。
        """
        self._seq += 1
        return self._seq

    async def run(self) -> AsyncGenerator[dict[str, Any], None]:
        """输出 complaint 流式事件。

        review 通过时会补充 assistant.delta / assistant.final；未通过时只输出 complaint 状态事件。
        """
        yield make_event(
            seq=self._next_seq(),
            conversation_id=self._run_context.conversation_id,
            message_id=self._assistant_message_id,
            type="meta.start",
            payload={
                "user_message_id": self._run_context.user_message_id,
                "assistant_message_id": self._assistant_message_id,
            },
        )

        for event in self._run_context.pre_stream_events:
            yield self._make_stream_event(event)

        if self._run_context.should_emit_assistant_final and self._run_context.assistant_candidate_content:
            yield make_event(
                seq=self._next_seq(),
                conversation_id=self._run_context.conversation_id,
                message_id=self._assistant_message_id,
                type="llm.call.start",
                payload={"message_count": 1},
            )
            for chunk in self._chunk_text(self._run_context.assistant_candidate_content):
                yield make_event(
                    seq=self._next_seq(),
                    conversation_id=self._run_context.conversation_id,
                    message_id=self._assistant_message_id,
                    type="assistant.delta",
                    payload={"delta": chunk},
                )
            yield make_event(
                seq=self._next_seq(),
                conversation_id=self._run_context.conversation_id,
                message_id=self._assistant_message_id,
                type="llm.call.end",
                payload={"elapsed_ms": 0, "message_count": 1},
            )

        for event in self._run_context.post_stream_events:
            yield self._make_stream_event(event)

        if self._run_context.should_emit_assistant_final and self._run_context.assistant_candidate_content:
            yield make_event(
                seq=self._next_seq(),
                conversation_id=self._run_context.conversation_id,
                message_id=self._assistant_message_id,
                type="assistant.final",
                payload={"content": self._run_context.assistant_candidate_content},
            )
            await self._save_assistant_message()

    def _make_stream_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """把 complaint 事件包装成标准 stream event。

        这个内部方法服务于统一挂上 seq、conversation_id 和 message_id。
        """
        return make_event(
            seq=self._next_seq(),
            conversation_id=self._run_context.conversation_id,
            message_id=self._assistant_message_id,
            type=event["type"],
            payload=event.get("payload", {}),
        )

    def _chunk_text(self, content: str, chunk_size: int = 18) -> list[str]:
        """按固定长度切分候选回复。

        这个内部方法服务于第一阶段的伪流式输出，让前端仍然按 delta 方式渲染。
        """
        return [content[index : index + chunk_size] for index in range(0, len(content), chunk_size)]

    async def _save_assistant_message(self) -> None:
        """把 review 通过的 assistant 回复落库。

        这个内部方法保证真正对外发送的回复能够和消息列表保持一致。
        """
        await self._conversation_service.add_message(
            conversation_id=self._run_context.conversation_id,
            role="assistant",
            content=self._run_context.assistant_candidate_content,
            message_id=self._assistant_message_id,
            extra_metadata=self._run_context.assistant_extra_metadata or None,
        )
