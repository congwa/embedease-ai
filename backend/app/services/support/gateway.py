"""人工客服消息网关

负责：
- 管理客服端和用户端的实时连接
- 消息的双向分发（SSE）
- 连接生命周期管理
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger

logger = get_logger("support.gateway")


@dataclass
class Connection:
    """连接信息"""

    id: str
    conversation_id: str
    role: str  # "user" | "agent"
    queue: asyncio.Queue[dict[str, Any]]
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class SupportGateway:
    """人工客服消息网关
    
    单例模式，管理所有客服/用户连接和消息分发。
    
    使用方式：
        gateway = SupportGateway()
        
        # 用户端连接
        async for event in gateway.subscribe_user(conversation_id, user_id):
            yield event
            
        # 客服端连接
        async for event in gateway.subscribe_agent(conversation_id, agent_id):
            yield event
            
        # 发送消息
        await gateway.broadcast_to_conversation(conversation_id, event)
    """

    _instance: "SupportGateway | None" = None
    _connections: dict[str, dict[str, Connection]]
    _lock: asyncio.Lock

    def __new__(cls) -> "SupportGateway":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connections = defaultdict(dict)
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def _add_connection(
        self,
        conversation_id: str,
        role: str,
        metadata: dict[str, Any] | None = None,
    ) -> Connection:
        """添加连接"""
        conn_id = str(uuid4())
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        conn = Connection(
            id=conn_id,
            conversation_id=conversation_id,
            role=role,
            queue=queue,
            metadata=metadata or {},
        )

        async with self._lock:
            self._connections[conversation_id][conn_id] = conn

        logger.info(
            "新连接加入",
            conn_id=conn_id,
            conversation_id=conversation_id,
            role=role,
        )

        return conn

    async def _remove_connection(self, conversation_id: str, conn_id: str) -> None:
        """移除连接"""
        async with self._lock:
            if conversation_id in self._connections:
                self._connections[conversation_id].pop(conn_id, None)
                if not self._connections[conversation_id]:
                    del self._connections[conversation_id]

        logger.info("连接已移除", conn_id=conn_id, conversation_id=conversation_id)

    async def broadcast_to_conversation(
        self,
        conversation_id: str,
        event: dict[str, Any],
        *,
        exclude_role: str | None = None,
        exclude_conn_id: str | None = None,
    ) -> int:
        """广播消息到会话的所有连接
        
        Args:
            conversation_id: 会话 ID
            event: 事件数据
            exclude_role: 排除的角色
            exclude_conn_id: 排除的连接 ID
            
        Returns:
            发送成功的连接数
        """
        async with self._lock:
            conns = list(self._connections.get(conversation_id, {}).values())

        sent_count = 0
        for conn in conns:
            if exclude_role and conn.role == exclude_role:
                continue
            if exclude_conn_id and conn.id == exclude_conn_id:
                continue

            try:
                await conn.queue.put(event)
                sent_count += 1
            except Exception as e:
                logger.warning(
                    "广播消息失败",
                    conn_id=conn.id,
                    error=str(e),
                )

        return sent_count

    async def send_to_user(
        self,
        conversation_id: str,
        event: dict[str, Any],
    ) -> int:
        """发送消息到用户端"""
        sent = await self.broadcast_to_conversation(
            conversation_id,
            event,
            exclude_role="agent",
        )
        logger.info(
            "客服事件推送给用户",
            conversation_id=conversation_id,
            event_type=event.get("type"),
            sent_count=sent,
        )
        return sent

    async def send_to_agents(
        self,
        conversation_id: str,
        event: dict[str, Any],
    ) -> int:
        """发送消息到客服端"""
        sent = await self.broadcast_to_conversation(
            conversation_id,
            event,
            exclude_role="user",
        )
        logger.info(
            "客服事件推送给客服端",
            conversation_id=conversation_id,
            event_type=event.get("type"),
            sent_count=sent,
        )
        return sent

    async def subscribe_user(
        self,
        conversation_id: str,
        user_id: str,
    ):
        """用户端订阅会话消息
        
        Yields:
            SSE 事件数据
        """
        conn = await self._add_connection(
            conversation_id,
            role="user",
            metadata={"user_id": user_id},
        )

        try:
            yield {
                "type": "support.connected",
                "payload": {"connection_id": conn.id},
            }

            while True:
                try:
                    event = await asyncio.wait_for(conn.queue.get(), timeout=30)
                    yield event
                except asyncio.TimeoutError:
                    yield {"type": "support.ping", "payload": {}}
                except asyncio.CancelledError:
                    break

        finally:
            await self._remove_connection(conversation_id, conn.id)

    async def subscribe_agent(
        self,
        conversation_id: str,
        agent_id: str,
    ):
        """客服端订阅会话消息
        
        Yields:
            SSE 事件数据
        """
        conn = await self._add_connection(
            conversation_id,
            role="agent",
            metadata={"agent_id": agent_id},
        )

        try:
            yield {
                "type": "support.connected",
                "payload": {"connection_id": conn.id},
            }

            while True:
                try:
                    event = await asyncio.wait_for(conn.queue.get(), timeout=30)
                    yield event
                except asyncio.TimeoutError:
                    yield {"type": "support.ping", "payload": {}}
                except asyncio.CancelledError:
                    break

        finally:
            await self._remove_connection(conversation_id, conn.id)

    def get_connection_count(self, conversation_id: str) -> dict[str, int]:
        """获取会话的连接数统计"""
        conns = self._connections.get(conversation_id, {})
        user_count = sum(1 for c in conns.values() if c.role == "user")
        agent_count = sum(1 for c in conns.values() if c.role == "agent")
        return {"user": user_count, "agent": agent_count, "total": len(conns)}

    def get_all_active_conversations(self) -> list[str]:
        """获取所有有活跃连接的会话 ID"""
        return list(self._connections.keys())


support_gateway = SupportGateway()
