"""用户端消息处理器

本文件的业务职责，是承接用户侧实时动作，并把“发消息、输入中、已读、请求人工”
翻译成客服工作台和用户聊天页都能消费的 WebSocket 事件。
"""

from datetime import datetime
from typing import Any

from app.core.dependencies import get_services
from app.core.logging import get_logger
from app.models.conversation import HandoffState
from app.schemas.websocket import WSAction, WSRole
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import WSConnection, ws_manager
from app.services.websocket.router import ws_router

logger = get_logger("websocket.handlers.user")


async def _broadcast_support_queue_change(
    *,
    conversation_id: str,
    handoff_state: str,
    reason: str,
    source: str,
    changed_at: str | None = None,
) -> None:
    """广播客服全局队列变更信号。

    这个内部方法服务于客服列表页的跨会话刷新。当用户有新消息时，即使该会话当前没有被
    列表页实时订阅，也要让在线客服页面及时刷新队列排序、最后消息和未读数。
    """
    queue_msg = build_server_message(
        action=WSAction.SERVER_SUPPORT_QUEUE_CHANGED,
        payload={
            "conversation_id": conversation_id,
            "handoff_state": handoff_state,
            "reason": reason,
            "source": source,
            "changed_at": changed_at or datetime.now().isoformat(),
        },
        conversation_id=conversation_id,
    )
    await ws_manager.broadcast_to_role_global(WSRole.AGENT, queue_msg)


@ws_router.handler(WSAction.CLIENT_USER_SEND_MESSAGE)
async def handle_user_send_message(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理用户发送消息。

    这个 handler 既负责把消息写入会话，也负责在用户新消息到来时提醒客服工作台刷新全局队列，
    让未监控会话也能因为新未读或最新动态被及时抬高优先级。
    """

    content = payload["content"]
    client_message_id = payload.get("message_id")

    async with get_services() as services:
        # 检查 handoff 状态和客服在线状态
        handoff_state = await services.handoff.get_handoff_state(conn.conversation_id)
        online_status = await services.conversation_repo.get_online_status(conn.conversation_id)
        agent_online = online_status.get("agent_online", False)

        if handoff_state == HandoffState.HUMAN.value:
            # 人工模式：保存消息并转发给客服
            message = await services.conversation.add_message(
                conversation_id=conn.conversation_id,
                role="user",
                content=content,
                message_id=client_message_id,
            )

            # 检查客服是否在线，尝试推送
            sent_count = 0
            if agent_online:
                server_msg = build_server_message(
                    action=WSAction.SERVER_MESSAGE,
                    payload={
                        "message_id": message.id,
                        "role": "user",
                        "content": content,
                        "created_at": message.created_at.isoformat(),
                        "is_delivered": True,
                        "delivered_at": datetime.now().isoformat(),
                    },
                    conversation_id=conn.conversation_id,
                )
                sent_count = await ws_manager.send_to_role(conn.conversation_id, WSRole.AGENT, server_msg)

            # 如果成功送达，更新消息状态
            if sent_count > 0:
                await services.message_repo.mark_as_delivered([message.id])
                logger.info(
                    "用户消息已送达客服",
                    conn_id=conn.id,
                    conversation_id=conn.conversation_id,
                    message_id=message.id,
                )
            else:
                # 消息未送达（客服离线），等客服上线时推送
                logger.info(
                    "用户消息已保存（客服离线，等待送达）",
                    conn_id=conn.id,
                    conversation_id=conn.conversation_id,
                    message_id=message.id,
                )

            await _broadcast_support_queue_change(
                conversation_id=conn.conversation_id,
                handoff_state=handoff_state,
                reason="user_message",
                source="user_message_human",
                changed_at=message.created_at.isoformat(),
            )

        else:
            # AI 模式：保存消息，触发通知
            message = await services.conversation.add_message(
                conversation_id=conn.conversation_id,
                role="user",
                content=content,
                message_id=client_message_id,
            )

            # 触发通知（异步，不阻塞）
            try:
                await services.handoff.notify_new_message(
                    conversation_id=conn.conversation_id,
                    user_id=conn.identity,
                    message_preview=content[:200],
                )
            except Exception as e:
                logger.warning("通知发送失败", error=str(e))

            logger.info(
                "用户消息已保存（AI模式）",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                message_id=message.id,
            )

            await _broadcast_support_queue_change(
                conversation_id=conn.conversation_id,
                handoff_state=handoff_state or HandoffState.AI.value,
                reason="user_message",
                source="user_message_ai",
                changed_at=message.created_at.isoformat(),
            )


@ws_router.handler(WSAction.CLIENT_USER_TYPING)
async def handle_user_typing(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理用户输入状态"""
    server_msg = build_server_message(
        action=WSAction.SERVER_TYPING,
        payload={"role": "user", "is_typing": payload["is_typing"]},
        conversation_id=conn.conversation_id,
    )
    await ws_manager.send_to_role(conn.conversation_id, WSRole.AGENT, server_msg)


@ws_router.handler(WSAction.CLIENT_USER_READ)
async def handle_user_read(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理用户已读回执"""
    message_ids = payload["message_ids"]

    # 更新数据库已读状态
    async with get_services() as services:
        count, read_at = await services.message_repo.mark_as_read(message_ids, conn.identity)

    # 推送已读回执给客服端（包含已读时间）
    server_msg = build_server_message(
        action=WSAction.SERVER_READ_RECEIPT,
        payload={
            "role": "user",
            "message_ids": message_ids,
            "read_at": read_at.isoformat(),
            "read_by": conn.identity,
        },
        conversation_id=conn.conversation_id,
    )
    await ws_manager.send_to_role(conn.conversation_id, WSRole.AGENT, server_msg)

    logger.info(
        "用户已读回执",
        conn_id=conn.id,
        conversation_id=conn.conversation_id,
        message_count=count,
    )


@ws_router.handler(WSAction.CLIENT_USER_REQUEST_HANDOFF)
async def handle_user_request_handoff(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理用户请求人工客服"""
    reason = payload.get("reason", "用户主动请求")

    async with get_services() as services:
        await services.complaint_handoff.request_handoff_for_conversation(
            conversation_id=conn.conversation_id,
            handoff_reason=reason,
            requested_by=conn.identity,
            handoff_summary={"source": "user_websocket_request"},
        )

    # 发送通知给客服
    try:
        from app.services.support.notification.dispatcher import notification_dispatcher
        await notification_dispatcher.notify_handoff_request(
            conversation_id=conn.conversation_id,
            user_id=conn.identity,
            reason=reason,
        )
    except Exception as e:
        logger.warning("人工客服请求通知发送失败", error=str(e))

    logger.info(
        "用户请求人工客服",
        conn_id=conn.id,
        conversation_id=conn.conversation_id,
        reason=reason,
    )
