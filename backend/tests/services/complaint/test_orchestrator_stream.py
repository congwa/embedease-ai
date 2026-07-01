"""ComplaintChatStreamOrchestrator 测试

测试客诉流式编排器如何在 review 通过和未通过时输出不同事件序列。
"""

from __future__ import annotations

import asyncio

import pytest

from app.schemas.complaint import (
    ComplaintReviewStatus,
    ComplaintTriageResult,
    HandoffRequestResult,
    IssueContinuity,
    PlannerDecision,
    ReviewDecision,
    TicketStreamSummary,
)
from app.services.complaint.orchestrator import ComplaintChatStreamOrchestrator, ComplaintRunContext


class FakeConversationService:
    """模拟 ConversationService，避免真实落库。"""

    def __init__(self) -> None:
        """初始化模拟服务。"""
        self.saved_messages: list[dict] = []

    async def add_message(self, **kwargs: object) -> None:
        """记录 assistant 落库调用，用于验证是否真正保存消息。"""
        self.saved_messages.append(dict(kwargs))


def build_run_context(**overrides: object) -> ComplaintRunContext:
    """构造基础 ComplaintRunContext，服务于 complaint stream 测试。"""
    payload = {
        "conversation_id": "conv_123",
        "user_id": "user_123",
        "user_message_id": "msg_123",
        "ticket_id": "ticket_123",
        "ticket_summary": TicketStreamSummary(id="ticket_123", status="in_progress"),
        "triage_result": ComplaintTriageResult(
            primary_issue_tag="delivery_delay",
            priority_level="medium",
            risk_level="low",
            sentiment="neutral",
            severity="normal",
            emotional_intensity="normal",
            continuity=IssueContinuity.SAME_ISSUE,
            requested_human=False,
            missing_slots=[],
            extracted_slots={},
            summary="默认 triage",
        ),
        "planner_decision": PlannerDecision(
            assigned_agent_tag="resolution_execution_agent",
            task_type="resolution",
            goal="推进处理",
            success_criteria=["用户知道下一步动作"],
            should_handoff=False,
            next_node_key="resolution",
            reasoning="默认 planner",
        ),
        "review_decision": ReviewDecision(
            status=ComplaintReviewStatus.PASSED,
            score=90,
            risk_level="low",
            reasons=[],
        ),
        "assistant_candidate_content": "我已经为您记录并继续推进处理。",
        "should_emit_assistant_final": True,
        "handoff_result": None,
        "pre_stream_events": [{"type": "complaint.task.started", "payload": {"task": {"id": "task_1"}}}],
        "post_stream_events": [{"type": "complaint.review.passed", "payload": {"status": "passed"}}],
        "assistant_extra_metadata": {"complaint_ticket_id": "ticket_123"},
    }
    payload.update(overrides)
    return ComplaintRunContext(**payload)


async def collect_events(orchestrator: ComplaintChatStreamOrchestrator) -> list[dict]:
    """收集 complaint stream 编排器产生的全部事件。"""
    events: list[dict] = []

    async def _collect() -> None:
        async for event in orchestrator.run():
            events.append(event.model_dump() if hasattr(event, "model_dump") else dict(event))

    await asyncio.wait_for(_collect(), timeout=10)
    return events


@pytest.mark.anyio
class TestComplaintChatStreamOrchestrator:
    """测试 ComplaintChatStreamOrchestrator 关键事件流。"""

    async def test_passed_review_emits_assistant_final_and_saves_message(self):
        """测试 review 通过时会输出 delta/final 并保存 assistant 消息。"""
        conversation_service = FakeConversationService()
        orchestrator = ComplaintChatStreamOrchestrator(
            conversation_service=conversation_service,
            run_context=build_run_context(),
            assistant_message_id="assistant_123",
        )

        events = await collect_events(orchestrator)

        event_types = [event["type"] for event in events]
        assert event_types[0] == "meta.start"
        assert "assistant.delta" in event_types
        assert event_types[-1] == "assistant.final"
        assert conversation_service.saved_messages[0]["content"] == "我已经为您记录并继续推进处理。"

    async def test_handoff_context_does_not_emit_assistant_final(self):
        """测试 handoff 场景不会输出 assistant.final 正文。"""
        conversation_service = FakeConversationService()
        run_context = build_run_context(
            review_decision=ReviewDecision(
                status=ComplaintReviewStatus.ESCALATED,
                score=40,
                risk_level="high",
                reasons=["高风险，需人工接手"],
                should_handoff=True,
            ),
            should_emit_assistant_final=False,
            handoff_result=HandoffRequestResult(
                requested=True,
                conversation_id="conv_123",
                ticket_id="ticket_123",
                handoff_reason="高风险，需人工接手",
                handoff_summary={"reasons": ["高风险，需人工接手"]},
                conversation_mode="pending",
                handoff_state="pending",
            ),
            post_stream_events=[
                {
                    "type": "complaint.review.rejected",
                    "payload": {"status": "escalated"},
                },
                {
                    "type": "complaint.handoff_requested",
                    "payload": {"ticket_id": "ticket_123"},
                },
            ],
        )
        orchestrator = ComplaintChatStreamOrchestrator(
            conversation_service=conversation_service,
            run_context=run_context,
            assistant_message_id="assistant_123",
        )

        events = await collect_events(orchestrator)

        event_types = [event["type"] for event in events]
        assert "assistant.final" not in event_types
        assert "complaint.handoff_requested" in event_types
        assert conversation_service.saved_messages == []
