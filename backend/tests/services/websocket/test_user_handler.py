"""用户 WebSocket Handler 测试

本文件的业务职责，是验证用户端主动请求人工客服时，
系统会把请求交给 complaint handoff 编排服务并继续触发客服通知链路。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.websocket import WSAction, WSRole


class _FakeServicesContext:
    """测试用服务容器上下文。"""

    def __init__(self, services: SimpleNamespace):
        self.services = services

    async def __aenter__(self) -> SimpleNamespace:
        return self.services

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class TestUserHandoffHandler:
    """测试用户请求人工处理器。"""

    @pytest.mark.anyio
    async def test_handle_user_request_handoff_dispatches_complaint_service_and_notification(self):
        """测试用户请求人工会进入客诉编排并继续通知客服侧。"""
        from app.services.websocket.handlers.user import handle_user_request_handoff

        conn = SimpleNamespace(
            id="user_conn_123",
            identity="user_123",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            complaint_handoff=SimpleNamespace(
                request_handoff_for_conversation=AsyncMock()
            )
        )

        with patch(
            "app.services.websocket.handlers.user.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.support.notification.dispatcher.notification_dispatcher.notify_handoff_request",
                new=AsyncMock(return_value=None),
            ) as mock_notify:
                await handle_user_request_handoff(
                    conn,
                    WSAction.CLIENT_USER_REQUEST_HANDOFF,
                    {"reason": "我需要人工专员处理赔付"},
                )

        services.complaint_handoff.request_handoff_for_conversation.assert_awaited_once_with(
            conversation_id="conv_123",
            handoff_reason="我需要人工专员处理赔付",
            requested_by="user_123",
            handoff_summary={"source": "user_websocket_request"},
        )
        mock_notify.assert_awaited_once_with(
            conversation_id="conv_123",
            user_id="user_123",
            reason="我需要人工专员处理赔付",
        )


class TestUserSendMessageHandler:
    """测试用户发消息处理器。"""

    @pytest.mark.anyio
    async def test_handle_user_send_message_in_human_mode_broadcasts_global_queue_change(self):
        """测试人工模式下用户新消息会触发客服全局队列刷新。"""
        from app.services.websocket.handlers.user import handle_user_send_message

        created_at = datetime(2026, 4, 2, 19, 0, 0)
        conn = SimpleNamespace(
            id="user_conn_human",
            identity="user_123",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            handoff=SimpleNamespace(
                get_handoff_state=AsyncMock(return_value="human"),
            ),
            conversation_repo=SimpleNamespace(
                get_online_status=AsyncMock(return_value={"agent_online": True}),
            ),
            conversation=SimpleNamespace(
                add_message=AsyncMock(
                    return_value=SimpleNamespace(id="msg_123", created_at=created_at)
                )
            ),
            message_repo=SimpleNamespace(
                mark_as_delivered=AsyncMock(return_value=1),
            ),
        )

        with patch(
            "app.services.websocket.handlers.user.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.user.ws_manager.send_to_role",
                new=AsyncMock(return_value=1),
            ) as mock_send_to_role:
                with patch(
                    "app.services.websocket.handlers.user.ws_manager.broadcast_to_role_global",
                    new=AsyncMock(return_value=2),
                ) as mock_broadcast_to_role_global:
                    await handle_user_send_message(
                        conn,
                        WSAction.CLIENT_USER_SEND_MESSAGE,
                        {"content": "你们这赔付到底什么时候处理", "message_id": "client_msg_123"},
                    )

        services.message_repo.mark_as_delivered.assert_awaited_once_with(["msg_123"])
        mock_send_to_role.assert_awaited_once()
        mock_broadcast_to_role_global.assert_awaited_once()
        global_call = mock_broadcast_to_role_global.await_args
        assert global_call.args[0] == WSRole.AGENT
        assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert global_call.args[1]["payload"]["conversation_id"] == "conv_123"
        assert global_call.args[1]["payload"]["source"] == "user_message_human"

    @pytest.mark.anyio
    async def test_handle_user_send_message_in_ai_mode_broadcasts_global_queue_change(self):
        """测试 AI 模式下用户新消息也会触发客服全局队列刷新。"""
        from app.services.websocket.handlers.user import handle_user_send_message

        created_at = datetime(2026, 4, 2, 19, 5, 0)
        conn = SimpleNamespace(
            id="user_conn_ai",
            identity="user_123",
            conversation_id="conv_123",
        )
        services = SimpleNamespace(
            handoff=SimpleNamespace(
                get_handoff_state=AsyncMock(return_value="ai"),
                notify_new_message=AsyncMock(return_value=None),
            ),
            conversation_repo=SimpleNamespace(
                get_online_status=AsyncMock(return_value={"agent_online": False}),
            ),
            conversation=SimpleNamespace(
                add_message=AsyncMock(
                    return_value=SimpleNamespace(id="msg_ai_123", created_at=created_at)
                )
            ),
        )

        with patch(
            "app.services.websocket.handlers.user.get_services",
            return_value=_FakeServicesContext(services),
        ):
            with patch(
                "app.services.websocket.handlers.user.ws_manager.broadcast_to_role_global",
                new=AsyncMock(return_value=2),
            ) as mock_broadcast_to_role_global:
                await handle_user_send_message(
                    conn,
                    WSAction.CLIENT_USER_SEND_MESSAGE,
                    {"content": "我还是不满意，你们必须继续处理"},
                )

        services.handoff.notify_new_message.assert_awaited_once_with(
            conversation_id="conv_123",
            user_id="user_123",
            message_preview="我还是不满意，你们必须继续处理",
        )
        mock_broadcast_to_role_global.assert_awaited_once()
        global_call = mock_broadcast_to_role_global.await_args
        assert global_call.args[0] == WSRole.AGENT
        assert global_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert global_call.args[1]["payload"]["conversation_id"] == "conv_123"
        assert global_call.args[1]["payload"]["source"] == "user_message_ai"
