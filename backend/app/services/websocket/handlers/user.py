"""用户端消息处理器"""

from typing import Any

from app.core.dependencies import get_services
from app.core.logging import get_logger
from app.models.conversation import HandoffState
from app.schemas.websocket import WSAction, WSRole
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import WSConnection, ws_manager
from app.services.websocket.router import ws_router

logger = get_logger("websocket.handlers.user")


@ws_router.handler(WSAction.CLIENT_USER_SEND_MESSAGE)
async def handle_user_send_message(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理用户发送消息"""
    from datetime import datetime

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
