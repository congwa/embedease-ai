"""ComplaintConversationOrchestrator 实时广播测试

本文件的业务职责，是验证客诉主链路在广播会话状态时，
会同时发出客服全局队列刷新信号，确保非监控会话也能被实时抬进工作台优先队列。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.websocket import WSAction, WSRole
from app.services.complaint.orchestrator import ComplaintConversationOrchestrator


class TestComplaintConversationOrchestratorRealtime:
    """测试客诉主链路的实时广播辅助方法。"""

    @pytest.mark.anyio
    async def test_broadcast_conversation_state_also_notifies_global_queue(self):
        """测试会话状态广播时会同步通知客服全局队列刷新。"""
        orchestrator = ComplaintConversationOrchestrator(MagicMock())
        orchestrator.support_state_service.build_websocket_state_payload = AsyncMock(
            return_value={
                "handoff_state": "pending",
                "current_ticket": {"id": "ticket_123", "status": "handoff_pending"},
                "review_summary": {"status": "escalated"},
            }
        )

        with patch(
            "app.services.complaint.orchestrator.ws_manager.broadcast_to_conversation",
            new=AsyncMock(return_value=2),
        ) as mock_broadcast_to_conversation:
            with patch(
                "app.services.complaint.orchestrator.ws_manager.broadcast_to_role_global",
                new=AsyncMock(return_value=1),
            ) as mock_broadcast_to_role_global:
                await orchestrator._broadcast_conversation_state("conv_123")

        mock_broadcast_to_conversation.assert_awaited_once()
        mock_broadcast_to_role_global.assert_awaited_once()
        global_call = mock_broadcast_to_role_global.await_args
        assert global_call.args[0] == WSRole.AGENT
        assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert global_call.args[1]["payload"]["conversation_id"] == "conv_123"
        assert global_call.args[1]["payload"]["handoff_state"] == "pending"
        assert global_call.args[1]["payload"]["reason"] == "handoff_pending"
        assert global_call.args[1]["payload"]["source"] == "complaint_orchestrator_state"

