"""SupportStateService 测试

测试客服工作台状态组装服务能否把 conversation、ticket 和 review 拼成统一状态结构。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.models.conversation import Conversation, ConversationMode, HandoffState
from app.services.support.state_service import SupportStateService


def build_conversation() -> Conversation:
    """构造一个基础会话对象，服务于客服状态组装测试。"""
    return Conversation(
        id="conv_123",
        user_id="user_123",
        title="退款投诉",
        handoff_state=HandoffState.PENDING.value,
        handoff_operator=None,
        handoff_reason="用户要求人工",
        conversation_mode=ConversationMode.PENDING.value,
        current_ticket_id="ticket_123",
        user_online=True,
    )


def build_ticket() -> ComplaintTicket:
    """构造一个基础主问题单对象，服务于客服状态组装测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status="handoff_pending",
        is_primary_active=True,
        primary_issue_tag="refund_delay",
        secondary_issue_tags=["secondary_issue"],
        secondary_issues=[{"issue_tag": "secondary_issue"}],
        current_agent_tag="handoff_orchestrator_agent",
        priority_level="high",
        risk_level="high",
        unresolved_turns=4,
        handoff_required=True,
        handoff_reason="用户要求人工",
        handoff_summary={"known_slots": ["order_id"], "emotion": "high"},
        updated_at=datetime(2026, 3, 31, 11, 0, 0),
        rework_count=0,
        slot_data={},
        timeline=[],
        version=1,
    )


def build_task(
    *,
    task_id: str,
    task_type: str,
    status: str,
    agent_tag: str,
    output_payload: dict | None = None,
) -> ComplaintTask:
    """构造一个基础任务对象，服务于最近任务链展示测试。"""
    task = ComplaintTask(
        id=task_id,
        ticket_id="ticket_123",
        task_type=task_type,
        agent_tag=agent_tag,
        status=status,
        goal=f"{task_type} 任务目标",
        success_criteria=["目标明确"],
        input_payload={},
        output_payload=output_payload or {},
        review_required=task_type not in {"triage", "plan"},
        review_status=None,
        retry_count=0,
    )
    task.created_at = datetime(2026, 3, 31, 11, 1, 0)
    task.started_at = datetime(2026, 3, 31, 11, 1, 10)
    task.finished_at = datetime(2026, 3, 31, 11, 1, 30)
    return task


def build_review() -> ComplaintReview:
    """构造一个基础审查记录对象，服务于客服状态组装测试。"""
    return ComplaintReview(
        id="review_123",
        ticket_id="ticket_123",
        task_id="task_123",
        reviewer_agent_tag="reviewer",
        status="escalated",
        score=55,
        risk_level="high",
        reasons=["赔付金额超限"],
        suggested_next_agent="human_support",
    )


class TestSupportStateServiceInit:
    """测试 SupportStateService 初始化。"""

    def test_init_with_session(self):
        """测试客服状态组装服务会初始化仓储依赖。"""
        mock_session = MagicMock()
        service = SupportStateService(mock_session)

        assert service.session is mock_session
        assert service.conversation_repo is not None
        assert service.ticket_repo is not None
        assert service.task_repo is not None
        assert service.review_repo is not None


class TestSupportStateServiceBehavior:
    """测试 SupportStateService 核心业务行为。"""

    @pytest.mark.anyio
    async def test_build_conversation_state_contains_ticket_and_review(self):
        """测试客服详情状态会带上当前主问题单和最近 review 摘要。"""
        mock_session = MagicMock()
        service = SupportStateService(mock_session)
        conversation = build_conversation()
        ticket = build_ticket()
        review = build_review()
        triage_task = build_task(
            task_id="task_triage",
            task_type="triage",
            status="done",
            agent_tag="front_desk_agent",
            output_payload={"summary": "主问题=refund_delay，风险=high，缺少订单号"},
        )
        review_task = build_task(
            task_id="task_review",
            task_type="review",
            status="done",
            agent_tag="quality_reviewer_agent",
            output_payload={"status": "escalated", "reasons": ["赔付金额超限"]},
        )
        review.created_at = datetime(2026, 3, 31, 11, 5, 0)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=None)
        service.task_repo.list_by_ticket_id = AsyncMock(return_value=[triage_task, review_task])
        service.review_repo.get_latest_by_ticket_id = AsyncMock(return_value=review)

        result = await service.build_conversation_state(
            conversation,
            unread_count=3,
            peer_last_online_at=datetime(2026, 3, 31, 11, 10, 0),
        )

        assert result.conversation_mode == ConversationMode.PENDING.value
        assert result.current_ticket is not None
        assert result.current_ticket.id == "ticket_123"
        assert result.current_ticket.secondary_issue_detected is True
        assert len(result.recent_tasks) == 2
        assert result.recent_tasks[0].business_summary == "主问题=refund_delay，风险=high，缺少订单号"
        assert result.secondary_issues[0].issue_tag == "secondary_issue"
        assert result.handoff_summary == {"known_slots": ["order_id"], "emotion": "high"}
        assert result.review_summary is not None
        assert result.latest_review is not None
        assert result.review_summary.status == "escalated"
        assert result.review_summary.reasons == ["赔付金额超限"]
        assert result.unread_count == 3

    @pytest.mark.anyio
    async def test_get_conversation_state_returns_none_when_missing(self):
        """测试会话不存在时返回空结果，避免工作台读取脏状态。"""
        mock_session = MagicMock()
        service = SupportStateService(mock_session)
        service.conversation_repo.get_by_id = AsyncMock(return_value=None)

        result = await service.get_conversation_state("missing")

        assert result is None

    @pytest.mark.anyio
    async def test_build_websocket_state_payload_uses_json_ready_shapes(self):
        """测试 WebSocket payload 会输出前端可以直接消费的 JSON 结构。"""
        mock_session = MagicMock()
        service = SupportStateService(mock_session)
        conversation = build_conversation()
        ticket = build_ticket()
        review = build_review()
        task = build_task(
            task_id="task_triage",
            task_type="triage",
            status="done",
            agent_tag="front_desk_agent",
            output_payload={"summary": "主问题=refund_delay，风险=high，缺少订单号"},
        )
        review.created_at = datetime(2026, 3, 31, 11, 5, 0)
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=None)
        service.task_repo.list_by_ticket_id = AsyncMock(return_value=[task])
        service.review_repo.get_latest_by_ticket_id = AsyncMock(return_value=review)

        payload = await service.build_websocket_state_payload(
            "conv_123",
            unread_count=2,
            peer_last_online_at=datetime(2026, 3, 31, 11, 10, 0),
        )

        assert payload["conversation_mode"] == "pending"
        assert payload["handoff_state"] == "pending"
        assert payload["current_ticket"]["id"] == "ticket_123"
        assert payload["review_summary"]["status"] == "escalated"
        assert payload["recent_tasks"][0]["task_type"] == "triage"
        assert payload["secondary_issues"][0]["issue_tag"] == "secondary_issue"
        assert payload["handoff_summary"] == {"known_slots": ["order_id"], "emotion": "high"}
        assert payload["unread_count"] == 2
