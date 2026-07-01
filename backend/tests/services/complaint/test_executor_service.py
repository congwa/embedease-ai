"""ExecutorService 测试

测试 executor 如何根据岗位类型产出候选回复和槽位补齐结果。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import (
    ComplaintStatus,
    ComplaintTriageResult,
    IssueContinuity,
    PlannerDecision,
)
from app.services.complaint.executor_service import ExecutorService


def build_ticket() -> ComplaintTicket:
    """构造基础问题单对象，服务于 executor 结果测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=ComplaintStatus.IN_PROGRESS.value,
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
    """构造基础 triage 结果，服务于 executor 结果测试。"""
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


def build_planner_decision(**overrides: object) -> PlannerDecision:
    """构造基础 planner 决策，服务于 executor 结果测试。"""
    payload = {
        "assigned_agent_tag": "case_intake_agent",
        "task_type": "case_collect",
        "goal": "补齐关键信息",
        "success_criteria": ["order_id 已补齐"],
        "should_handoff": False,
        "next_node_key": "case_collect",
        "reasoning": "默认 planner 决策",
    }
    payload.update(overrides)
    return PlannerDecision(**payload)


class TestExecutorService:
    """测试 ExecutorService 的确定性执行规则（LLM 不可用时的降级路径）。"""

    @pytest.mark.anyio
    async def test_case_collect_requests_missing_order_id(self):
        """测试 case_collect 会明确要求用户补充订单号（LLM 不可用降级为规则模板）。"""
        service = ExecutorService(MagicMock())

        with patch.object(service, "_execute_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            result = await service.execute(
                ticket=build_ticket(),
                triage_result=build_triage_result(missing_slots=["order_id"]),
                planner_decision=build_planner_decision(),
                last_user_message="订单一直没处理",
            )

        assert result.task_completed is False
        assert "订单号" in result.content

    @pytest.mark.anyio
    async def test_resolution_with_order_id_completes_task(self):
        """测试 resolution 在有订单号时会给出推进型回复（LLM 不可用降级为规则模板）。"""
        service = ExecutorService(MagicMock())
        ticket = build_ticket()
        ticket.slot_data = {"order_id": "12345678"}

        with patch.object(service, "_execute_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            result = await service.execute(
                ticket=ticket,
                triage_result=build_triage_result(),
                planner_decision=build_planner_decision(
                    assigned_agent_tag="resolution_execution_agent",
                    task_type="resolution",
                    goal="推进处理",
                    success_criteria=["用户知道下一步动作"],
                    next_node_key="resolution",
                ),
                last_user_message="订单号 12345678 一直没发货",
            )

        assert result.task_completed is True
        assert "12345678" in result.content
        assert result.handoff_recommended is False

    @pytest.mark.anyio
    async def test_handoff_executor_marks_handoff_recommended(self):
        """测试 handoff 岗位输出会直接建议人工接入（LLM 不可用降级为规则模板）。"""
        service = ExecutorService(MagicMock())

        with patch.object(service, "_execute_with_llm", new_callable=AsyncMock, side_effect=RuntimeError("LLM not available")):
            result = await service.execute(
                ticket=build_ticket(),
                triage_result=build_triage_result(requested_human=True),
                planner_decision=build_planner_decision(
                    assigned_agent_tag="handoff_orchestrator_agent",
                    task_type="handoff",
                    should_handoff=True,
                    next_node_key="handoff",
                ),
                last_user_message="我要人工客服处理",
            )

        assert result.handoff_recommended is True
        assert "人工客服" in result.content
