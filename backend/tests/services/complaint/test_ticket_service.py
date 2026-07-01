"""TicketService 测试

测试问题单服务对会话快照的一致性维护，确保主活动 ticket 的状态始终能被聊天页和工作台读取。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_ticket import ComplaintTicket
from app.models.conversation import Conversation, ConversationMode
from app.schemas.complaint import ComplaintReviewStatus, ComplaintStatus
from app.services.complaint.ticket_service import TicketService


def build_conversation() -> Conversation:
    """构造一个基础会话对象，服务于会话快照同步测试。"""
    return Conversation(
        id="conv_123",
        user_id="user_123",
        title="物流投诉",
        conversation_mode=ConversationMode.AI.value,
    )


def build_ticket() -> ComplaintTicket:
    """构造一个基础问题单对象，服务于状态推进测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=ComplaintStatus.NEW.value,
        is_primary_active=True,
        primary_issue_tag="delivery_delay",
        current_agent_tag="planner",
        current_node_key="triage",
        priority_level="high",
        risk_level="medium",
        unresolved_turns=1,
        secondary_issue_tags=[],
        secondary_issues=[],
        slot_data={},
        timeline=[],
        version=1,
        rework_count=0,
        handoff_required=False,
    )


class TestTicketServiceInit:
    """测试 TicketService 初始化。"""

    def test_init_with_session(self):
        """测试问题单服务会绑定会话和仓储。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)

        assert service.session is mock_session
        assert service.ticket_repo is not None
        assert service.conversation_repo is not None


class TestTicketServiceBehavior:
    """测试 TicketService 核心业务规则。"""

    @pytest.mark.anyio
    async def test_create_ticket_syncs_initial_snapshot(self):
        """测试新建问题单时会立刻同步会话主问题快照。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.create = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=build_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda conversation: conversation)
        ticket = build_ticket()

        result = await service.create_ticket(ticket)

        assert result.id == "ticket_123"
        conversation = service.conversation_repo.get_by_id.await_args_list[0].args
        assert conversation == ("conv_123",)
        updated_conversation = service.conversation_repo.update.await_args.args[0]
        assert updated_conversation.current_ticket_id == "ticket_123"
        assert updated_conversation.complaint_status == ComplaintStatus.NEW.value
        assert ticket.version == 1

    @pytest.mark.anyio
    async def test_update_snapshot_syncs_fields_and_bumps_version(self):
        """测试更新问题单时会刷新会话快照并递增版本号。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=build_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda conversation: conversation)
        ticket = build_ticket()

        result = await service.update_snapshot(ticket)

        assert result.version == 2
        updated_conversation = service.conversation_repo.update.await_args.args[0]
        assert updated_conversation.primary_issue_tag == "delivery_delay"
        assert updated_conversation.current_agent_tag == "planner"
        assert updated_conversation.current_node_key == "triage"
        assert updated_conversation.priority_level == "high"
        assert updated_conversation.risk_level == "medium"
        assert updated_conversation.unresolved_turns == 1

    @pytest.mark.anyio
    async def test_update_classification_updates_ticket_and_conversation(self):
        """测试 triage 分类结果会同步到 ticket 与 conversation。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=build_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda conversation: conversation)
        ticket = build_ticket()

        result = await service.update_classification(
            ticket,
            primary_issue_tag="refund_delay",
            priority_level="urgent",
            risk_level="high",
            sentiment="angry",
            severity="severe",
        )

        assert result.primary_issue_tag == "refund_delay"
        assert result.priority_level == "urgent"
        assert result.risk_level == "high"
        assert result.sentiment == "angry"
        assert result.severity == "severe"

    @pytest.mark.anyio
    async def test_set_current_node_syncs_node_snapshot(self):
        """测试编排节点变化会同步到会话快照。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=build_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda conversation: conversation)
        ticket = build_ticket()

        result = await service.set_current_node(ticket, "review")

        assert result.current_node_key == "review"
        updated_conversation = service.conversation_repo.update.await_args.args[0]
        assert updated_conversation.current_node_key == "review"

    @pytest.mark.anyio
    async def test_mark_rework_required_records_block_reason(self):
        """测试 review 驳回后 ticket 会进入返工态并留下阻塞原因。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        conversation = build_conversation()
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.conversation_repo.update = AsyncMock(side_effect=lambda item: item)
        ticket = build_ticket()

        result = await service.mark_rework_required(ticket, block_reason="review_rejected")

        assert result.status == ComplaintStatus.REWORK_REQUIRED.value
        assert result.rework_count == 1
        assert conversation.block_reason == "review_rejected"

    @pytest.mark.anyio
    async def test_mark_handoff_pending_updates_ticket_and_conversation(self):
        """测试转人工待接入时会同步 ticket 状态和会话模式。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        conversation = build_conversation()
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.conversation_repo.update = AsyncMock(side_effect=lambda item: item)
        ticket = build_ticket()

        result = await service.mark_handoff_pending(
            ticket,
            handoff_reason="高风险赔付",
            handoff_summary={"reason": "高风险赔付"},
        )

        assert result.status == ComplaintStatus.HANDOFF_PENDING.value
        assert result.handoff_required is True
        assert conversation.conversation_mode == ConversationMode.PENDING.value
        assert conversation.handoff_state == ConversationMode.PENDING.value
        assert conversation.handoff_reason == "高风险赔付"

    @pytest.mark.anyio
    async def test_mark_resolved_sets_resolution_time(self):
        """测试问题单解决后会退出主活动状态并写入解决时间。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=build_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda conversation: conversation)
        ticket = build_ticket()

        result = await service.mark_resolved(ticket, summary="已补发优惠券")

        assert result.status == ComplaintStatus.RESOLVED.value
        assert result.is_primary_active is False
        assert result.resolved_summary == "已补发优惠券"
        assert result.resolved_at is not None

    @pytest.mark.anyio
    async def test_recover_from_blocked_clears_block_reason_and_returns_planned(self):
        """测试巡查自动恢复会清理阻塞原因并把 ticket 恢复为 planned。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        conversation = build_conversation()
        conversation.block_reason = "模型工具调用失败"
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.conversation_repo.update = AsyncMock(side_effect=lambda item: item)
        ticket = build_ticket()
        ticket.status = ComplaintStatus.BLOCKED.value

        result = await service.recover_from_blocked(
            ticket,
            summary="巡查发现长时间阻塞，已自动恢复",
        )

        assert result.status == ComplaintStatus.PLANNED.value
        assert conversation.block_reason is None
        assert result.timeline[-1]["event_type"] == "patrol.auto_recovered"

    @pytest.mark.anyio
    async def test_mark_closed_sets_close_time(self):
        """测试问题单关闭时会写入关闭时间并退出主活动状态。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=build_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda conversation: conversation)
        ticket = build_ticket()

        result = await service.mark_closed(ticket, summary="人工已归档")

        assert result.status == ComplaintStatus.CLOSED.value
        assert result.is_primary_active is False

    @pytest.mark.anyio
    async def test_reopen_ticket_restores_active_snapshot(self):
        """测试手动重开会恢复主活动状态并切回 AI 模式。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        conversation = build_conversation()
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.conversation_repo.update = AsyncMock(side_effect=lambda item: item)
        ticket = build_ticket()
        ticket.status = ComplaintStatus.RESOLVED.value
        ticket.is_primary_active = False
        ticket.resolved_at = None

        result = await service.reopen_ticket(
            ticket,
            reason="用户反馈问题仍未解决",
            agent_tag="resolution_execution_agent",
            node_key="resolution",
        )

        assert result.status == ComplaintStatus.IN_PROGRESS.value
        assert result.is_primary_active is True
        assert result.current_agent_tag == "resolution_execution_agent"
        assert conversation.conversation_mode == ConversationMode.AI.value
        assert conversation.handoff_state == ConversationMode.AI.value
        assert result.timeline[-1]["event_type"] == "ticket.reopened"
        assert result.closed_at is None

    @pytest.mark.anyio
    async def test_sync_review_snapshot_updates_conversation(self):
        """测试 review 快照会同步到会话层，便于工作台直接展示。"""
        mock_session = MagicMock()
        service = TicketService(mock_session)
        conversation = build_conversation()
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.conversation_repo.update = AsyncMock(side_effect=lambda item: item)
        ticket = build_ticket()

        await service.sync_review_snapshot(
            ticket,
            review_status=ComplaintReviewStatus.PASSED,
            review_score=96,
        )

        assert conversation.review_status == ComplaintReviewStatus.PASSED.value
        assert conversation.review_score == 96
