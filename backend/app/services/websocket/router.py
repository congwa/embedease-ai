"""WebSocket 消息路由器

职责：
- 解析入站消息
- 根据 action 分发到对应 handler
- 统一错误处理
- 消息确认
"""

import time
from typing import Any, Awaitable, Callable
from uuid import uuid4

from pydantic import ValidationError

from app.core.logging import get_logger
from app.schemas.websocket import (
    ACTION_PAYLOAD_MAP,
    WS_PROTOCOL_VERSION,
    WSAction,
    WSErrorCode,
)
from app.services.websocket.manager import WSConnection

logger = get_logger("websocket.router")


# Handler 类型定义
HandlerFunc = Callable[[WSConnection, str, dict[str, Any]], Awaitable[None]]


class MessageRouter:
    """消息路由器（单例）
    
    使用方式：
        router = MessageRouter()
        
        @router.handler(WSAction.CLIENT_USER_SEND_MESSAGE)
        async def handle_user_message(conn, action, payload):
            ...
        
        # 在 WebSocket 端点中
        await router.route(conn, raw_message)
    """

    _instance: "MessageRouter | None" = None
    _handlers: dict[str, HandlerFunc]

    def __new__(cls) -> "MessageRouter":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
        return cls._instance

    def handler(self, action: str | WSAction) -> Callable[[HandlerFunc], HandlerFunc]:
        """注册 handler 装饰器"""
        def decorator(func: HandlerFunc) -> HandlerFunc:
            action_str = action.value if isinstance(action, WSAction) else action
            self._handlers[action_str] = func
            logger.debug(f"注册 WebSocket handler: {action_str}")
            return func
        return decorator

    def register(self, action: str | WSAction, handler: HandlerFunc) -> None:
        """手动注册 handler"""
        action_str = action.value if isinstance(action, WSAction) else action
        self._handlers[action_str] = handler

    async def route(self, conn: WSConnection, raw_message: dict[str, Any]) -> None:
        """路由消息到对应 handler"""
        message_id = raw_message.get("id", str(uuid4()))
        action = raw_message.get("action")

        # 1. 验证 action
        if not action:
            await self._send_error(conn, message_id, WSErrorCode.INVALID_ACTION, "缺少 action 字段")
            return

        # 2. 查找 handler
        handler = self._handlers.get(action)
        if not handler:
            await self._send_error(conn, message_id, WSErrorCode.INVALID_ACTION, f"未知 action: {action}")
            return

        # 3. 验证 payload（如果有定义）
        payload = raw_message.get("payload", {})
        payload_cls = ACTION_PAYLOAD_MAP.get(action)
        if payload_cls:
            try:
                validated_payload = payload_cls(**payload)
                payload = validated_payload.model_dump()
            except ValidationError as e:
                await self._send_error(
                    conn, message_id, WSErrorCode.INVALID_PAYLOAD,
                    f"Payload 验证失败: {e.errors()}"
                )
                return

        # 4. 执行 handler
        try:
            await handler(conn, action, payload)

            # 发送确认（非系统消息）
            if not action.startswith("system."):
                await self._send_ack(conn, message_id, "ok")

        except Exception as e:
            logger.exception("Handler 执行失败", action=action, error=str(e))
            await self._send_error(conn, message_id, WSErrorCode.INTERNAL_ERROR, str(e))

    async def _send_ack(self, conn: WSConnection, message_id: str, status: str) -> None:
        """发送确认"""
        await conn.send(self._build_message(
            action=WSAction.SYSTEM_ACK,
            payload={"received_id": message_id, "status": status},
            reply_to=message_id,
        ))

    async def _send_error(
        self,
        conn: WSConnection,
        message_id: str,
        code: WSErrorCode,
        message: str,
        detail: Any = None,
    ) -> None:
        """发送错误"""
        await conn.send(self._build_message(
            action=WSAction.SYSTEM_ERROR,
            payload={"code": code.value, "message": message, "detail": detail},
            reply_to=message_id,
            error={"code": code.value, "message": message, "detail": detail},
        ))

    def _build_message(
        self,
        action: str | WSAction,
        payload: dict[str, Any],
        conversation_id: str | None = None,
        reply_to: str | None = None,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """构建消息"""
        return {
            "v": WS_PROTOCOL_VERSION,
            "id": str(uuid4()),
            "ts": int(time.time() * 1000),
            "action": action.value if isinstance(action, WSAction) else action,
            "payload": payload,
            "conversation_id": conversation_id,
            "reply_to": reply_to,
            "error": error,
        }


# 全局单例
ws_router = MessageRouter()
