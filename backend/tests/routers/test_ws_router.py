"""WebSocket 路由测试

本文件的业务职责，是验证用户端、客服端和客服全局队列频道的建连 payload 与实时链路一致，
避免工作台重连后丢字段，或全局队列频道无法正常接收心跳与跨会话刷新信号。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import WebSocketDisconnect

from app.schemas.websocket import WSAction, WSRole


class _FakeQueueWebSocket:
    """测试用客服全局队列 WebSocket。

    这个测试替身服务于直接驱动 `/ws/agent-queue` 端点，
    用最小代价验证建连成功消息和后续心跳收发是否按协议工作。
    """

    def __init__(self, incoming_messages: list[dict]):
        """预装待接收消息，模拟客服页面建连后的入站事件序列。"""
        self._incoming_messages = list(incoming_messages)
        self.accept = AsyncMock()
        self.close = AsyncMock()
        self.client = ("127.0.0.1", 9527)
        self.headers = {}

    async def receive_json(self) -> dict:
        """按顺序吐出测试消息，并在耗尽后模拟断连。"""
        if self._incoming_messages:
            return self._incoming_messages.pop(0)
        raise WebSocketDisconnect()


class _FakeServicesContext:
    """测试用 WebSocket 路由服务容器上下文。"""

    def __init__(self, services: SimpleNamespace):
        """持有当前端点测试所需的假服务集合。"""
        self.services = services

    async def __aenter__(self) -> SimpleNamespace:
        """进入上下文时返回假服务容器，模拟真实依赖注入。"""
        return self.services

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        """退出上下文时不吞异常，保证端点回归测试能暴露真实失败。"""
        return False


class TestWebSocketRouterHelpers:
    """测试 WebSocket 路由中的 payload 组装辅助方法。"""

    def test_build_support_queue_connected_payload_uses_virtual_channel(self):
        """测试客服全局队列频道会返回虚拟会话 connected payload。"""
        from app.routers.ws import (
            SUPPORT_QUEUE_CHANNEL_ID,
            _build_support_queue_connected_payload,
        )

        payload = _build_support_queue_connected_payload(connection_id="conn_queue_123")

        assert payload["connection_id"] == "conn_queue_123"
        assert payload["conversation_id"] == SUPPORT_QUEUE_CHANNEL_ID
        assert payload["role"] == "agent"
        assert payload["recent_tasks"] == []
        assert payload["secondary_issues"] == []

    def test_build_connected_payload_keeps_full_support_state_fields(self):
        """测试 connected payload 会完整带上 support state 的上下文字段。"""
        from app.routers.ws import _build_connected_payload

        payload = _build_connected_payload(
            connection_id="conn_123",
            role=WSRole.AGENT,
            conversation_id="conv_123",
            handoff_state="human",
            peer_online=True,
            peer_last_online_at=datetime(2026, 4, 2, 18, 0, 0),
            unread_count=3,
            conversation_state_payload={
                "conversation_mode": "human",
                "current_ticket": {"id": "ticket_123", "status": "in_progress"},
                "review_summary": {"status": "passed", "score": 92},
                "recent_tasks": [{"id": "task_123", "task_type": "review"}],
                "secondary_issues": [{"issue_tag": "compensation"}],
                "handoff_summary": {"source": "user_websocket_request"},
            },
        )

        assert payload["role"] == "agent"
        assert payload["conversation_mode"] == "human"
        assert payload["current_ticket"]["id"] == "ticket_123"
        assert payload["recent_tasks"][0]["task_type"] == "review"
        assert payload["secondary_issues"][0]["issue_tag"] == "compensation"
        assert payload["handoff_summary"]["source"] == "user_websocket_request"

    def test_build_server_message_payload_keeps_full_message_status(self):
        """测试未送达消息补发时会保留图片、operator、撤回和编辑状态。"""
        from types import SimpleNamespace

        from app.routers.ws import _build_server_message_payload

        payload = _build_server_message_payload(
            SimpleNamespace(
                id="msg_123",
                role="human_agent",
                content="请看截图说明",
                created_at=datetime(2026, 4, 2, 18, 5, 0),
                delivered_at=None,
                read_at=None,
                read_by=None,
                is_withdrawn=True,
                withdrawn_at=datetime(2026, 4, 2, 18, 7, 0),
                withdrawn_by="agent_a",
                is_edited=True,
                edited_at=datetime(2026, 4, 2, 18, 8, 0),
                edited_by="agent_b",
                extra_metadata={
                    "operator": "agent_a",
                    "images": [
                        {
                            "id": "img_1",
                            "url": "https://example.com/a.png",
                            "thumbnail_url": "https://example.com/a-thumb.png",
                        }
                    ],
                },
            ),
            delivered_at=datetime(2026, 4, 2, 18, 6, 0),
        )

        assert payload["message_id"] == "msg_123"
        assert payload["operator"] == "agent_a"
        assert payload["images"][0]["id"] == "img_1"
        assert payload["is_delivered"] is True
        assert payload["delivered_at"] == "2026-04-02T18:06:00"
        assert payload["is_withdrawn"] is True
        assert payload["withdrawn_at"] == "2026-04-02T18:07:00"
        assert payload["withdrawn_by"] == "agent_a"
        assert payload["is_edited"] is True
        assert payload["edited_at"] == "2026-04-02T18:08:00"
        assert payload["edited_by"] == "agent_b"


class TestAgentQueueEndpoint:
    """测试客服全局队列频道端点。"""

    @pytest.mark.anyio
    async def test_ws_agent_queue_endpoint_sends_connected_and_handles_ping(self):
        """测试客服全局队列频道建连后能返回 connected，并继续处理系统心跳。"""
        from app.routers.ws import SUPPORT_QUEUE_CHANNEL_ID, ws_agent_queue_endpoint

        websocket = _FakeQueueWebSocket(
            incoming_messages=[
                {
                    "id": "ping_123",
                    "action": WSAction.SYSTEM_PING,
                    "payload": {},
                }
            ]
        )
        conn = SimpleNamespace(
            id="conn_queue_123",
            is_alive=True,
            send=AsyncMock(return_value=True),
        )

        with patch(
            "app.routers.ws._authenticate_agent",
            new=AsyncMock(return_value=(True, "agent_123", "")),
        ):
            with patch(
                "app.routers.ws.ws_manager.connect",
                new=AsyncMock(return_value=conn),
            ) as mock_connect:
                with patch(
                    "app.routers.ws.ws_manager.disconnect",
                    new=AsyncMock(return_value=conn),
                ) as mock_disconnect:
                    await ws_agent_queue_endpoint(websocket, token="agent_123")

        websocket.accept.assert_awaited_once()
        mock_connect.assert_awaited_once()
        mock_disconnect.assert_awaited_once_with("conn_queue_123")
        assert conn.send.await_count == 2

        connected_call = conn.send.await_args_list[0]
        pong_call = conn.send.await_args_list[1]
        assert connected_call.args[0]["action"] == WSAction.SYSTEM_CONNECTED
        assert connected_call.args[0]["conversation_id"] == SUPPORT_QUEUE_CHANNEL_ID
        assert connected_call.args[0]["payload"]["conversation_id"] == SUPPORT_QUEUE_CHANNEL_ID
        assert pong_call.args[0]["action"] == WSAction.SYSTEM_PONG


class TestUserEndpointQueueRefresh:
    """测试用户端建连生命周期对客服全局队列的刷新。"""

    @pytest.mark.anyio
    async def test_ws_user_endpoint_broadcasts_queue_change_on_connect_and_disconnect(self):
        """测试用户上线和下线都会通知客服列表页刷新在线状态。"""
        from app.routers.ws import ws_user_endpoint

        websocket = _FakeQueueWebSocket(incoming_messages=[])
        conn = SimpleNamespace(
            id="conn_user_123",
            is_alive=True,
            send=AsyncMock(return_value=True),
        )
        services = SimpleNamespace(
            handoff=SimpleNamespace(
                get_handoff_state=AsyncMock(return_value="pending"),
            ),
            conversation_repo=SimpleNamespace(
                get_online_status=AsyncMock(
                    return_value={
                        "agent_online": False,
                        "agent_last_online_at": None,
                    }
                ),
                set_user_online=AsyncMock(return_value=None),
            ),
            message_repo=SimpleNamespace(
                get_unread_count=AsyncMock(return_value=0),
                get_undelivered_messages=AsyncMock(return_value=[]),
            ),
            support_state=SimpleNamespace(
                build_websocket_state_payload=AsyncMock(
                    return_value={
                        "conversation_mode": "ai",
                        "current_ticket": None,
                        "review_summary": None,
                        "recent_tasks": [],
                        "secondary_issues": [],
                        "handoff_summary": None,
                    }
                )
            ),
        )

        with patch(
            "app.routers.ws._authenticate_user",
            new=AsyncMock(return_value=(True, "user_123", "")),
        ):
            with patch(
                "app.routers.ws.get_services",
                return_value=_FakeServicesContext(services),
            ):
                with patch(
                    "app.routers.ws.ws_manager.connect",
                    new=AsyncMock(return_value=conn),
                ):
                    with patch(
                        "app.routers.ws.ws_manager.disconnect",
                        new=AsyncMock(return_value=conn),
                    ) as mock_disconnect:
                        with patch(
                            "app.routers.ws.ws_manager.send_to_role",
                            new=AsyncMock(return_value=1),
                        ) as mock_send_to_role:
                            with patch(
                                "app.routers.ws.ws_manager.broadcast_to_role_global",
                                new=AsyncMock(return_value=2),
                            ) as mock_broadcast_to_role_global:
                                await ws_user_endpoint(
                                    websocket,
                                    conversation_id="conv_123",
                                    token="user_token",
                                )

        websocket.accept.assert_awaited_once()
        mock_disconnect.assert_awaited_once_with("conn_user_123")
        assert conn.send.await_count == 1
        assert conn.send.await_args_list[0].args[0]["action"] == WSAction.SYSTEM_CONNECTED
        assert mock_send_to_role.await_count == 2
        assert services.conversation_repo.set_user_online.await_count == 2
        assert mock_broadcast_to_role_global.await_count == 2

        online_call = mock_broadcast_to_role_global.await_args_list[0]
        offline_call = mock_broadcast_to_role_global.await_args_list[1]
        assert online_call.args[0] == WSRole.AGENT
        assert online_call.args[1]["action"] == WSAction.SERVER_SUPPORT_QUEUE_CHANGED
        assert online_call.args[1]["payload"]["source"] == "user_online"
        assert online_call.args[1]["payload"]["handoff_state"] == "pending"
        assert offline_call.args[1]["payload"]["source"] == "user_offline"
        assert offline_call.args[1]["payload"]["handoff_state"] == "pending"
