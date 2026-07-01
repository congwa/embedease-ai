"""PlannerService 测试

测试 planner 如何根据 triage 结果决定当前轮应该进入哪个岗位处理。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import ComplaintStatus, ComplaintTriageResult, IssueContinuity
from app.services.complaint.planner_service import PlannerService


def build_ticket() -> ComplaintTicket:
    """构造基础问题单对象，服务于 planner 规则测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=ComplaintStatus.TRIAGED.value,
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


def build_triage_result(**overrides: object) -> ComplaintTriageResult:
    """构造基础 triage 结果，服务于 planner 规则测试。"""
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
        "summary": "默认 triage 结果",
    }
    payload.update(overrides)
    return ComplaintTriageResult(**payload)


class TestPlannerService:
    """测试 PlannerService 的规则分派能力（LLM 不可用时的降级路径）。"""

    @pytest.mark.anyio
    async def test_high_risk_routes_to_handoff(self):
        """测试高风险场景会优先转给 handoff 岗位（LLM 不可用降级为规则引擎）。"""
        service = PlannerService(MagicMock())

        with patch.object(service, "_plan_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            decision = await service.plan(
                ticket=build_ticket(),
                triage_result=build_triage_result(risk_level="high"),
                last_user_message="我要投诉到 12315",
            )

        assert decision.assigned_agent_tag == "handoff_orchestrator_agent"
        assert decision.should_handoff is True
        assert decision.task_type == "handoff"

    @pytest.mark.anyio
    async def test_high_emotion_routes_to_emotion_agent(self):
        """测试强情绪场景会优先分派情绪安抚岗位（LLM 不可用降级为规则引擎）。"""
        service = PlannerService(MagicMock())

        with patch.object(service, "_plan_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            decision = await service.plan(
                ticket=build_ticket(),
                triage_result=build_triage_result(emotional_intensity="high", sentiment="angry"),
                last_user_message="你们太过分了，我真的气炸了",
            )

        assert decision.assigned_agent_tag == "emotion_deescalation_agent"
        assert decision.task_type == "emotion"

    @pytest.mark.anyio
    async def test_missing_slots_routes_to_case_collect(self):
        """测试信息缺失场景会进入 case_collect（LLM 不可用降级为规则引擎）。"""
        service = PlannerService(MagicMock())

        with patch.object(service, "_plan_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            decision = await service.plan(
                ticket=build_ticket(),
                triage_result=build_triage_result(missing_slots=["order_id", "evidence"]),
                last_user_message="东西坏了",
            )

        assert decision.assigned_agent_tag == "case_intake_agent"
        assert decision.task_type == "case_collect"
        assert "order_id 已补齐" in decision.success_criteria

    @pytest.mark.anyio
    async def test_policy_message_routes_to_faq(self):
        """测试规则解释类消息会进入 FAQ 岗位（LLM 不可用降级为规则引擎）。"""
        service = PlannerService(MagicMock())

        with patch.object(service, "_plan_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            decision = await service.plan(
                ticket=build_ticket(),
                triage_result=build_triage_result(primary_issue_tag="refund_request"),
                last_user_message="为什么不能直接退款，规则到底是什么",
            )

        assert decision.assigned_agent_tag == "faq_policy_agent"
        assert decision.task_type == "faq"

    @pytest.mark.anyio
    async def test_default_routes_to_resolution(self):
        """测试信息齐全时会走常规处理推进岗位（LLM 不可用降级为规则引擎）。"""
        service = PlannerService(MagicMock())
        ticket = build_ticket()
        ticket.slot_data = {"order_id": "12345678"}

        with patch.object(service, "_plan_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            decision = await service.plan(
                ticket=ticket,
                triage_result=build_triage_result(extracted_slots={"order_id": "12345678"}),
                last_user_message="订单号 12345678 一直没发货",
            )

        assert decision.assigned_agent_tag == "resolution_execution_agent"
        assert decision.task_type == "resolution"
