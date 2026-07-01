"""TicketMergeService 测试

测试主问题单归并、拆单和次级问题记录规则，确保一个会话默认只有一张主活动问题单。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_ticket import ComplaintTicket
from app.schemas.complaint import ComplaintStatus, TicketResolutionDecision
from app.services.complaint.ticket_merge_service import TicketMergeService


def build_ticket(*, status: str = ComplaintStatus.NEW.value) -> ComplaintTicket:
    """构造一个基础问题单对象，服务于归并决策测试。"""
    return ComplaintTicket(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status=status,
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


class TestTicketMergeServiceInit:
    """测试 TicketMergeService 初始化。"""

    def test_init_with_session(self):
        """测试归并服务会初始化仓储和 ticket 服务。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)

        assert service.session is mock_session
        assert service.ticket_repo is not None
        assert service.ticket_service is not None


class TestTicketMergeDecision:
    """测试 ticket 归并决策。"""

    @pytest.mark.anyio
    async def test_no_active_ticket_creates_initial_ticket(self):
        """测试会话没有主活动问题单时会创建首张 ticket。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=None)
        service.create_initial_ticket = AsyncMock(return_value=build_ticket())

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="我的订单一直没发货",
        )

        assert resolution.decision == TicketResolutionDecision.CREATE_INITIAL_TICKET
        assert resolution.ticket_id == "ticket_123"

    @pytest.mark.anyio
    async def test_resolved_ticket_creates_new_primary_ticket(self):
        """测试已结束的旧 ticket 会在新问题出现时被替换。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        old_ticket = build_ticket(status=ComplaintStatus.RESOLVED.value)
        new_ticket = build_ticket()
        new_ticket.id = "ticket_456"
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=old_ticket)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.create_initial_ticket = AsyncMock(return_value=new_ticket)

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="新的问题是退款一直不到账",
        )

        assert resolution.decision == TicketResolutionDecision.CREATE_NEW_TICKET
        assert resolution.ticket_id == "ticket_456"
        assert old_ticket.is_primary_active is False
        assert old_ticket.superseded_by_ticket_id == "ticket_456"

    @pytest.mark.anyio
    async def test_explicit_new_issue_splits_ticket(self):
        """测试高置信度新问题表达会触发拆单。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        old_ticket = build_ticket()
        new_ticket = build_ticket()
        new_ticket.id = "ticket_456"
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=old_ticket)
        service.ticket_repo.update = AsyncMock(side_effect=lambda ticket: ticket)
        service.create_initial_ticket = AsyncMock(return_value=new_ticket)

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="我还有一个新的问题，是另一个订单少发货了",
        )

        assert resolution.decision == TicketResolutionDecision.CREATE_NEW_TICKET
        assert resolution.previous_ticket_id == "ticket_123"
        assert resolution.ticket_id == "ticket_456"

    @pytest.mark.anyio
    async def test_secondary_issue_records_on_current_ticket(self):
        """测试不确定的新诉求会先挂到当前主问题单下。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        active_ticket = build_ticket()
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=active_ticket)
        service.attach_secondary_issue = AsyncMock(return_value=active_ticket)

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="顺便我还有个问题，客服态度也很差",
        )

        assert resolution.decision == TicketResolutionDecision.RECORD_SECONDARY_ISSUE
        service.attach_secondary_issue.assert_awaited_once_with(
            active_ticket,
            "顺便我还有个问题，客服态度也很差",
        )

    @pytest.mark.anyio
    async def test_same_issue_reuses_active_ticket(self):
        """测试持续发泄和补充信息默认归并到当前主问题单。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        active_ticket = build_ticket()
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=active_ticket)

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="这个订单我昨天就说过了，你们到底什么时候处理",
        )

        assert resolution.decision == TicketResolutionDecision.REUSE_ACTIVE_TICKET
        assert resolution.ticket_id == "ticket_123"


class TestTicketMergeHelpers:
    """测试归并服务内部帮助方法。"""

    @pytest.mark.anyio
    async def test_create_initial_ticket_uses_ticket_service_to_sync_snapshot(self):
        """测试创建首张 ticket 时会走 TicketService，避免漏掉会话快照。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        service.ticket_service.create_ticket = AsyncMock(side_effect=lambda ticket: ticket)

        ticket = await service.create_initial_ticket(
            conversation_id="conv_123",
            user_id="user_123",
            user_message="我的订单一直没发货",
        )

        assert ticket.status == ComplaintStatus.NEW.value
        assert ticket.is_primary_active is True
        created_ticket = service.ticket_service.create_ticket.await_args.args[0]
        assert created_ticket.conversation_id == "conv_123"
        assert created_ticket.user_id == "user_123"

    @pytest.mark.anyio
    async def test_attach_secondary_issue_updates_snapshot(self):
        """测试记录次级问题后会同步 ticket 快照，避免工作台状态滞后。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        service.ticket_service.update_snapshot = AsyncMock(side_effect=lambda ticket: ticket)
        ticket = build_ticket()

        result = await service.attach_secondary_issue(ticket, "另外我还想投诉客服回复太慢")

        assert result.secondary_issue_tags == ["secondary_issue"]
        assert result.secondary_issues[0]["raw_message"] == "另外我还想投诉客服回复太慢"

    def test_build_issue_fingerprint_normalizes_spaces(self):
        """测试同一问题在空白字符差异下会生成稳定指纹。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)

        first = service.build_issue_fingerprint("订单 一直  没发货")
        second = service.build_issue_fingerprint(" 订单 一直 没发货 ")

        assert first == second

    def test_should_merge_into_current_ticket_respects_closed_status(self):
        """测试已完结问题单不会再继续归并。"""
        mock_session = MagicMock()
        service = TicketMergeService(mock_session)
        ticket = build_ticket(status=ComplaintStatus.CLOSED.value)

        assert service.should_merge_into_current_ticket(ticket, "继续催单") is False
