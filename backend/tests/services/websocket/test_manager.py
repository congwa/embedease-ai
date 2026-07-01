"""WebSocket 连接管理器测试

本文件的业务职责，是验证客服工作台依赖的全局角色广播能力。
当某个会话的 handoff 队列发生变化时，系统需要把刷新信号推给所有在线客服连接，
而不是只推给目标会话本身。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.schemas.websocket import WSRole
from app.services.websocket.manager import ConnectionManager


class TestConnectionManagerGlobalBroadcast:
    """测试全局角色广播。"""

    @pytest.mark.anyio
    async def test_broadcast_to_role_global_only_targets_matching_role(self):
        """测试全局广播只发送给指定角色的连接。"""
        manager = ConnectionManager()
        manager._init_storage()

        agent_conn_a = SimpleNamespace(
            id="agent_conn_a",
            role=WSRole.AGENT,
            send=AsyncMock(return_value=True),
        )
        agent_conn_b = SimpleNamespace(
            id="agent_conn_b",
            role=WSRole.AGENT,
            send=AsyncMock(return_value=True),
        )
        user_conn = SimpleNamespace(
            id="user_conn",
            role=WSRole.USER,
            send=AsyncMock(return_value=True),
        )

        manager._connections_by_id = {
            "agent_conn_a": agent_conn_a,
            "agent_conn_b": agent_conn_b,
            "user_conn": user_conn,
        }

        sent_count = await manager.broadcast_to_role_global(
            WSRole.AGENT,
            {"action": "server.support_queue_changed", "payload": {"conversation_id": "conv_123"}},
        )

        assert sent_count == 2
        agent_conn_a.send.assert_awaited_once()
        agent_conn_b.send.assert_awaited_once()
        user_conn.send.assert_not_awaited()

