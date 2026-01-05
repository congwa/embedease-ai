"""WebSocket 连接管理器

职责：
- 管理所有 WebSocket 连接的生命周期
- 按会话/角色组织连接
- 提供广播和定向发送能力
- 连接状态统计
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.core.logging import get_logger
from app.schemas.websocket import WSRole

logger = get_logger("websocket.manager")


@dataclass
class WSConnection:
    """WebSocket 连接实例"""

    id: str
    websocket: WebSocket
    conversation_id: str
    role: WSRole
    identity: str  # user_id 或 agent_id

    created_at: datetime = field(default_factory=datetime.now)
    last_ping_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: dict[str, Any] = field(default_factory=dict)
    is_alive: bool = True

    async def send(self, message: dict[str, Any]) -> bool:
        """发送消息到此连接"""
        if not self.is_alive:
            return False
        try:
            await self.websocket.send_json(message)
            return True
        except Exception as e:
            logger.warning("发送消息失败", conn_id=self.id, error=str(e))
            self.is_alive = False
            return False

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """关闭连接"""
        self.is_alive = False
        try:
            await self.websocket.close(code=code, reason=reason)
        except Exception:
            pass


class ConnectionManager:
    """WebSocket 连接管理器（单例）
    
    数据结构：
    - _connections_by_id: { conn_id -> WSConnection }
    - _connections_by_conversation: { conversation_id -> { conn_id -> WSConnection } }
    - _connections_by_identity: { identity -> { conn_id -> WSConnection } }
    """

    _instance: "ConnectionManager | None" = None

    def __new__(cls) -> "ConnectionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_storage()
        return cls._instance

    def _init_storage(self) -> None:
        self._lock = asyncio.Lock()
        self._connections_by_id: dict[str, WSConnection] = {}
        self._connections_by_conversation: dict[str, dict[str, WSConnection]] = defaultdict(dict)
        self._connections_by_identity: dict[str, dict[str, WSConnection]] = defaultdict(dict)

    async def connect(
        self,
        websocket: WebSocket,
        conversation_id: str,
        role: WSRole,
        identity: str,
        metadata: dict[str, Any] | None = None,
    ) -> WSConnection:
        """注册新连接"""
        conn_id = str(uuid4())

        conn = WSConnection(
            id=conn_id,
            websocket=websocket,
            conversation_id=conversation_id,
            role=role,
            identity=identity,
            metadata=metadata or {},
        )

        async with self._lock:
            self._connections_by_id[conn_id] = conn
            self._connections_by_conversation[conversation_id][conn_id] = conn
            self._connections_by_identity[identity][conn_id] = conn

        logger.info(
            "WebSocket 连接已注册",
            conn_id=conn_id,
            conversation_id=conversation_id,
            role=role,
            identity=identity,
        )

        return conn

    async def disconnect(self, conn_id: str) -> WSConnection | None:
        """注销连接"""
        async with self._lock:
            conn = self._connections_by_id.pop(conn_id, None)
            if conn:
                self._connections_by_conversation[conn.conversation_id].pop(conn_id, None)
                self._connections_by_identity[conn.identity].pop(conn_id, None)

                # 清理空字典
                if not self._connections_by_conversation[conn.conversation_id]:
                    del self._connections_by_conversation[conn.conversation_id]
                if not self._connections_by_identity[conn.identity]:
                    del self._connections_by_identity[conn.identity]

                logger.info("WebSocket 连接已注销", conn_id=conn_id)
        return conn

    def get_connection(self, conn_id: str) -> WSConnection | None:
        """获取连接"""
        return self._connections_by_id.get(conn_id)

    def get_connections_by_conversation(
        self,
        conversation_id: str,
        role: WSRole | None = None,
    ) -> list[WSConnection]:
        """获取会话的所有连接"""
        conns = list(self._connections_by_conversation.get(conversation_id, {}).values())
        if role:
            conns = [c for c in conns if c.role == role]
        return conns

    def get_connections_by_identity(self, identity: str) -> list[WSConnection]:
        """获取某身份的所有连接"""
        return list(self._connections_by_identity.get(identity, {}).values())

    async def send_to_connection(
        self,
        conn_id: str,
        message: dict[str, Any],
    ) -> bool:
        """发送消息到指定连接"""
        conn = self.get_connection(conn_id)
        if conn:
            return await conn.send(message)
        return False

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        message: dict[str, Any],
        *,
        exclude_role: WSRole | None = None,
        exclude_conn_id: str | None = None,
    ) -> int:
        """广播消息到会话的所有连接"""
        conns = self.get_connections_by_conversation(conversation_id)

        sent_count = 0
        for conn in conns:
            if exclude_role and conn.role == exclude_role:
                continue
            if exclude_conn_id and conn.id == exclude_conn_id:
                continue

            if await conn.send(message):
                sent_count += 1

        return sent_count

    async def send_to_role(
        self,
        conversation_id: str,
        role: WSRole,
        message: dict[str, Any],
    ) -> int:
        """发送消息到会话中指定角色的所有连接"""
        conns = self.get_connections_by_conversation(conversation_id, role=role)
        logger.info(
            "WS 广播准备发送",
            conversation_id=conversation_id,
            role=role.value if isinstance(role, WSRole) else role,
            target_count=len(conns),
            message_type=message.get("action"),
        )

        sent_count = 0
        for conn in conns:
            success = await conn.send(message)
            logger.info(
                "WS 广播发送结果",
                conversation_id=conversation_id,
                role=role.value if isinstance(role, WSRole) else role,
                conn_id=conn.id,
                success=success,
            )
            if success:
                sent_count += 1

        return sent_count

    def get_stats(self) -> dict[str, Any]:
        """获取连接统计"""
        total = len(self._connections_by_id)
        by_role: dict[str, int] = {"user": 0, "agent": 0}
        for conn in self._connections_by_id.values():
            role_key = conn.role.value if isinstance(conn.role, WSRole) else str(conn.role)
            by_role[role_key] = by_role.get(role_key, 0) + 1

        return {
            "total_connections": total,
            "by_role": by_role,
            "active_conversations": len(self._connections_by_conversation),
        }

    def get_all_connections(self) -> dict[str, WSConnection]:
        """获取所有连接（用于心跳检测）"""
        return self._connections_by_id.copy()


# 全局单例
ws_manager = ConnectionManager()
