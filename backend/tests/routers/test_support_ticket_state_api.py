"""客服问题单视角 API 测试

本文件的业务职责，是验证 support 路由已经提供 ticket 级取数与人工操作入口，
确保客服工作台不再只能围绕 conversation 维度工作。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.support import (
    ConversationTicketsResponse,
    RecentTaskSummarySchema,
    ReviewSummarySchema,
    SecondaryIssueSchema,
    TicketDetailSchema,
    TicketReopenRequest,
    TicketResolveRequest,
    TicketSummarySchema,
)
from app.schemas.websocket import WSAction, WSRole


def build_ticket_detail() -> TicketDetailSchema:
    """构造基础问题单详情，服务于 support ticket API 测试。"""
    return TicketDetailSchema(
        id="ticket_123",
        conversation_id="conv_123",
        user_id="user_123",
        status="handoff_pending",
        is_primary_active=True,
        primary_issue_tag="refund_request",
        secondary_issue_tags=["secondary_issue"],
        secondary_issues=[
            SecondaryIssueSchema(
                issue_tag="secondary_issue",
                reason="用户插入赔付诉求",
                raw_message="顺便我还要投诉赔付问题",
            )
        ],
        priority_level="urgent",
        risk_level="high",
        current_agent_tag="handoff_orchestrator_agent",
        current_task_id="task_123",
        current_node_key="handoff",
        unresolved_turns=3,
        rework_count=2,
        handoff_required=True,
        handoff_reason="连续驳回后升级人工",
        handoff_summary={"slot_data": {"order_id": "123456"}},
        slot_data={"order_id": "123456"},
        timeline=[{"event_type": "review.rejected", "summary": "高风险赔付"}],
        version=2,
        latest_review=ReviewSummarySchema(
            status="escalated",
            score=45,
            risk_level="high",
            reasons=["高风险赔付"],
            suggested_next_agent="human_support",
        ),
        recent_tasks=[
            RecentTaskSummarySchema(
                id="task_123",
                ticket_id="ticket_123",
                task_type="review",
                agent_tag="quality_reviewer_agent",
                status="done",
                goal="审查候选回复",
                success_criteria=["输出审查结论"],
                review_required=False,
                business_summary="审查 escalated：高风险赔付",
            )
        ],
    )


class TestSupportTicketRouter:
    """测试 support ticket 视角路由声明。"""

    def test_ticket_routes_exist(self):
        """测试当前 support router 已包含 ticket 视角接口。"""
        from app.routers.support import router

        routes = [route.path for route in router.routes]
        assert any(path.endswith("/active-ticket") for path in routes)
        assert any(path.endswith("/tickets") for path in routes)
        assert any("/tickets/{ticket_id}" in path for path in routes)
        assert any(path.endswith("/resolve") for path in routes)
        assert any(path.endswith("/reopen") for path in routes)


class TestSupportTicketEndpoints:
    """测试 support ticket 视角接口行为。"""

    @pytest.mark.anyio
    async def test_get_active_ticket_returns_detail(self):
        """测试 active-ticket 接口会返回当前主问题单完整详情。"""
        from app.routers.support import get_active_ticket

        detail = build_ticket_detail()
        mock_db = MagicMock()

        with patch("app.routers.support.SupportStateService") as MockStateService:
            mock_state_service = MockStateService.return_value
            mock_state_service.get_active_ticket_detail = AsyncMock(return_value=detail)

            result = await get_active_ticket("conv_123", db=mock_db)

            assert result.id == "ticket_123"
            assert result.latest_review is not None
            assert result.recent_tasks[0].task_type == "review"

    @pytest.mark.anyio
    async def test_list_conversation_tickets_returns_summaries(self):
        """测试会话 ticket 列表接口返回历史问题单摘要。"""
        from app.routers.support import list_conversation_tickets

        mock_db = MagicMock()
        ticket_summary = TicketSummarySchema(
            id="ticket_123",
            status="resolved",
            primary_issue_tag="refund_request",
            current_agent_tag="resolution_execution_agent",
            risk_level="medium",
        )

        with patch("app.routers.support.SupportStateService") as MockStateService:
            mock_state_service = MockStateService.return_value
            mock_state_service.list_ticket_summaries_by_conversation = AsyncMock(
                return_value=[ticket_summary]
            )

            result = await list_conversation_tickets("conv_123", db=mock_db)

            assert isinstance(result, ConversationTicketsResponse)
            assert result.total == 1
            assert result.items[0].id == "ticket_123"

    @pytest.mark.anyio
    async def test_get_ticket_detail_raises_404_when_missing(self):
        """测试 ticket 不存在时会返回 404，避免客服读取脏链接。"""
        from app.routers.support import get_ticket_detail

        mock_db = MagicMock()
        with patch("app.routers.support.SupportStateService") as MockStateService:
            mock_state_service = MockStateService.return_value
            mock_state_service.get_ticket_detail = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_ticket_detail("missing_ticket", db=mock_db)

            assert exc_info.value.status_code == 404

    @pytest.mark.anyio
    async def test_resolve_ticket_marks_resolved_and_returns_detail(self):
        """测试人工解决问题单接口会调用 ticket 服务并返回最新详情。"""
        from app.routers.support import resolve_ticket

        detail = build_ticket_detail()
        ticket = MagicMock()
        ticket.id = "ticket_123"
        mock_db = MagicMock()

        with patch("app.routers.support.ComplaintTicketRepository") as MockTicketRepo:
            with patch("app.routers.support.TicketService") as MockTicketService:
                with patch(
                    "app.routers.support._broadcast_ticket_state_update",
                    new=AsyncMock(return_value=detail),
                ) as mock_broadcast:
                    mock_ticket_repo = MockTicketRepo.return_value
                    mock_ticket_repo.get_by_id = AsyncMock(return_value=ticket)
                    mock_ticket_service = MockTicketService.return_value
                    mock_ticket_service.mark_resolved = AsyncMock(return_value=ticket)
                    mock_ticket_service.append_timeline_entry = AsyncMock(return_value=ticket)

                    result = await resolve_ticket(
                        "ticket_123",
                        TicketResolveRequest(operator="agent_a", summary="人工确认问题已解决"),
                        db=mock_db,
                    )

                    assert result.success is True
                    assert result.ticket is not None
                    assert result.ticket.id == "ticket_123"
                    mock_ticket_service.mark_resolved.assert_awaited_once_with(
                        ticket,
                        summary="人工确认问题已解决",
                    )
                    mock_broadcast.assert_awaited_once_with(db=mock_db, ticket_id="ticket_123")

    @pytest.mark.anyio
    async def test_reopen_ticket_calls_reopen_service(self):
        """测试人工重开问题单接口会把 ticket 交回 AI 主链路。"""
        from app.routers.support import reopen_ticket

        detail = build_ticket_detail()
        ticket = MagicMock()
        ticket.id = "ticket_123"
        mock_db = MagicMock()

        with patch("app.routers.support.ComplaintTicketRepository") as MockTicketRepo:
            with patch("app.routers.support.TicketService") as MockTicketService:
                with patch(
                    "app.routers.support._broadcast_ticket_state_update",
                    new=AsyncMock(return_value=detail),
                ) as mock_broadcast:
                    mock_ticket_repo = MockTicketRepo.return_value
                    mock_ticket_repo.get_by_id = AsyncMock(return_value=ticket)
                    mock_ticket_service = MockTicketService.return_value
                    mock_ticket_service.reopen_ticket = AsyncMock(return_value=ticket)

                    result = await reopen_ticket(
                        "ticket_123",
                        TicketReopenRequest(operator="agent_a", reason="用户继续投诉，问题未解决"),
                        db=mock_db,
                    )

                    assert result.success is True
                    assert result.ticket is not None
                    mock_ticket_service.reopen_ticket.assert_awaited_once_with(
                        ticket,
                        reason="用户继续投诉，问题未解决",
                        agent_tag="resolution_execution_agent",
                        node_key="resolution",
                    )
                    mock_broadcast.assert_awaited_once_with(db=mock_db, ticket_id="ticket_123")

    @pytest.mark.anyio
    async def test_broadcast_ticket_state_update_also_notifies_global_queue(self):
        """测试 resolve/reopen 后会额外通知客服全局队列刷新。"""
        from app.routers.support import _broadcast_ticket_state_update

        detail = build_ticket_detail()
        mock_db = MagicMock()
        ticket = MagicMock()
        ticket.id = "ticket_123"
        ticket.conversation_id = "conv_123"

        with patch("app.routers.support.SupportStateService") as MockStateService:
            with patch("app.routers.support.ComplaintTicketRepository") as MockTicketRepo:
                with patch("app.routers.support.TicketService") as MockTicketService:
                    with patch(
                        "app.routers.support.ws_manager.broadcast_to_conversation",
                        new=AsyncMock(return_value=2),
                    ) as mock_broadcast_to_conversation:
                        with patch(
                            "app.routers.support.ws_manager.broadcast_to_role_global",
                            new=AsyncMock(return_value=1),
                        ) as mock_broadcast_to_role_global:
                            mock_state_service = MockStateService.return_value
                            mock_state_service.build_ticket_detail = AsyncMock(return_value=detail)
                            mock_state_service.build_websocket_state_payload = AsyncMock(
                                return_value={"handoff_state": "human", "current_ticket": {"id": "ticket_123"}}
                            )
                            mock_ticket_repo = MockTicketRepo.return_value
                            mock_ticket_repo.get_by_id = AsyncMock(return_value=ticket)
                            mock_ticket_service = MockTicketService.return_value
                            mock_ticket_service.build_stream_summary.return_value.model_dump.return_value = {
                                "id": "ticket_123",
                                "status": "handoff_pending",
                            }

                            result = await _broadcast_ticket_state_update(
                                db=mock_db,
                                ticket_id="ticket_123",
                            )

        assert result.id == "ticket_123"
        assert mock_broadcast_to_conversation.await_count == 2
        mock_broadcast_to_role_global.assert_awaited_once()
        global_call = mock_broadcast_to_role_global.await_args
        assert global_call.args[0] == WSRole.AGENT
        assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert global_call.args[1]["payload"]["conversation_id"] == "conv_123"
        assert global_call.args[1]["payload"]["source"] == "support_ticket_state_update"
