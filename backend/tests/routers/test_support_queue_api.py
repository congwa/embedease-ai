"""客服队列 API 测试

本文件的业务职责，是验证客服工作台队列接口和 REST 备用发消息入口都能产出
队列页所需的数据与刷新信号，避免列表页出现预览或送达状态失真。
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.websocket import WSAction, WSRole


class TestSupportQueueEndpoints:
    """测试客服队列接口返回的列表合同。"""

    @pytest.mark.anyio
    async def test_list_conversations_returns_last_message_preview(self):
        """测试队列接口直接返回最后一条消息预览，供列表页直接渲染。"""
        from app.routers.support import list_conversations

        now = datetime(2026, 4, 2, 16, 50, 0)
        mock_db = MagicMock()

        with patch("app.routers.support.get_conversations_with_heat", new=AsyncMock(return_value=(
            [
                {
                    "id": "conv_123",
                    "user_id": "user_123",
                    "title": "退款投诉",
                    "conversation_mode": "human",
                    "handoff_state": "human",
                    "handoff_operator": "agent_a",
                    "handoff_reason": "已接管",
                    "user_online": True,
                    "updated_at": now,
                    "created_at": now,
                    "heat_score": 80,
                    "unread_count": 2,
                    "current_ticket_id": "ticket_123",
                    "ticket_status": "in_progress",
                    "primary_issue_tag": "refund_request",
                    "current_agent_tag": "resolution_execution_agent",
                    "risk_level": "high",
                    "review_status": "passed",
                    "review_score": 92,
                    "secondary_issue_detected": True,
                    "last_message": "请尽快处理，我还没有收到退款",
                    "last_message_at": now,
                    "last_message_role": "user",
                }
            ],
            1,
        ))) as mock_get_conversations:
            result = await list_conversations(db=mock_db)

            assert result.total == 1
            assert result.items[0].last_message == "请尽快处理，我还没有收到退款"
            assert result.items[0].last_message_role == "user"
            mock_get_conversations.assert_awaited_once()

    @pytest.mark.anyio
    async def test_send_human_message_keeps_offline_delivery_state_and_refreshes_queue(self):
        """测试 REST 备用发消息在用户离线时不会误标送达，并会刷新客服全局队列。"""
        from app.routers.support import send_human_message
        from app.schemas.support import HumanMessageRequest

        created_at = datetime(2026, 4, 2, 20, 0, 0)
        mock_db = MagicMock()
        mock_message_repo = MagicMock()
        mock_message_repo.mark_as_delivered = AsyncMock(return_value=0)

        with patch("app.routers.support.HandoffService") as MockHandoffService:
            with patch(
                "app.routers.support.MessageRepository",
                return_value=mock_message_repo,
            ):
                with patch(
                    "app.routers.support.ws_manager.send_to_role",
                    new=AsyncMock(side_effect=[0, 1]),
                ) as mock_send_to_role:
                    with patch(
                        "app.routers.support.ws_manager.broadcast_to_role_global",
                        new=AsyncMock(return_value=2),
                    ) as mock_broadcast_to_role_global:
                        mock_service = MockHandoffService.return_value
                        mock_service.add_human_message = AsyncMock(
                            return_value=MagicMock(
                                id="msg_123",
                                content="人工跟进中，请稍候",
                                created_at=created_at,
                            )
                        )

                        result = await send_human_message(
                            "conv_123",
                            HumanMessageRequest(
                                content="人工跟进中，请稍候",
                                operator="agent_a",
                            ),
                            db=mock_db,
                        )

        assert result.success is True
        assert result.message_id == "msg_123"
        assert mock_send_to_role.await_count == 2
        user_call = mock_send_to_role.await_args_list[0]
        agent_call = mock_send_to_role.await_args_list[1]
        assert user_call.args[0] == "conv_123"
        assert user_call.args[1] == WSRole.USER
        assert "is_delivered" not in user_call.args[2]["payload"]
        assert agent_call.args[0] == "conv_123"
        assert agent_call.args[1] == WSRole.AGENT
        assert agent_call.args[2]["payload"]["is_delivered"] is False
        assert agent_call.args[2]["payload"]["delivered_at"] is None
        mock_message_repo.mark_as_delivered.assert_not_awaited()
        mock_broadcast_to_role_global.assert_awaited_once()
        global_call = mock_broadcast_to_role_global.await_args
        assert global_call.args[0] == WSRole.AGENT
        assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert global_call.args[1]["payload"]["source"] == "support_rest_message"
