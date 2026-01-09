"""客服端消息处理器"""

from typing import Any

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.schemas.websocket import WSAction, WSRole
from app.services.support.handoff import HandoffService
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import WSConnection, ws_manager
from app.services.websocket.router import ws_router

logger = get_logger("websocket.handlers.agent")


@ws_router.handler(WSAction.CLIENT_AGENT_SEND_MESSAGE)
async def handle_agent_send_message(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服发送消息（支持图片）"""
    from datetime import datetime

    from app.repositories.message import MessageRepository
    from app.services.support.gateway import support_gateway

    content = payload.get("content", "")
    images = payload.get("images")  # 图片列表

    # 验证：必须有内容或图片
    if not content.strip() and not images:
        logger.warning(
            "客服消息发送失败：消息内容和图片不能同时为空",
            conn_id=conn.id,
            conversation_id=conn.conversation_id,
        )
        return

    async with get_db_context() as session:
        handoff_service = HandoffService(session)
        msg_repo = MessageRepository(session)

        # 添加人工消息（支持图片）
        message = await handoff_service.add_human_message(
            conversation_id=conn.conversation_id,
            content=content,
            operator=conn.identity,
            images=images,
        )

        if message:
            # 构建推送 payload
            push_payload: dict[str, Any] = {
                "message_id": message.id,
                "content": content,
                "operator": conn.identity,
                "created_at": message.created_at.isoformat(),
            }
            if images:
                push_payload["images"] = images

            # 通过 support_gateway 发送给用户（SSE 订阅者）
            sse_sent = await support_gateway.send_to_user(
                conn.conversation_id,
                {
                    "type": "support.human_message",
                    "payload": push_payload,
                },
            )

            # 同时通过 WebSocket 发送给用户（如果有 WebSocket 连接）
            ws_payload: dict[str, Any] = {
                "message_id": message.id,
                "role": "human_agent",
                "content": content,
                "created_at": message.created_at.isoformat(),
                "operator": conn.identity,
                "is_delivered": True,
                "delivered_at": datetime.now().isoformat(),
            }
            if images:
                ws_payload["images"] = images

            server_msg = build_server_message(
                action=WSAction.SERVER_MESSAGE,
                payload=ws_payload,
                conversation_id=conn.conversation_id,
            )
            ws_sent = await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, server_msg)

            # 如果任一渠道成功送达，更新消息状态
            if sse_sent > 0 or ws_sent > 0:
                await msg_repo.mark_as_delivered([message.id])
                logger.info(
                    "客服消息已送达用户",
                    conn_id=conn.id,
                    conversation_id=conn.conversation_id,
                    message_id=message.id,
                    sse_sent=sse_sent,
                    ws_sent=ws_sent,
                    has_images=bool(images),
                )
            else:
                # 消息未送达（用户离线），等用户上线时推送
                logger.info(
                    "客服消息已保存（用户离线，等待送达）",
                    conn_id=conn.id,
                    conversation_id=conn.conversation_id,
                    message_id=message.id,
                )
        else:
            logger.warning(
                "客服消息发送失败：会话不在人工模式",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
            )


@ws_router.handler(WSAction.CLIENT_AGENT_TYPING)
async def handle_agent_typing(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服输入状态"""
    server_msg = build_server_message(
        action=WSAction.SERVER_TYPING,
        payload={"role": "agent", "is_typing": payload["is_typing"]},
        conversation_id=conn.conversation_id,
    )
    await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, server_msg)


@ws_router.handler(WSAction.CLIENT_AGENT_READ)
async def handle_agent_read(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服已读回执"""
    from app.repositories.message import MessageRepository

    message_ids = payload["message_ids"]

    # 更新数据库已读状态
    async with get_db_context() as session:
        msg_repo = MessageRepository(session)
        count, read_at = await msg_repo.mark_as_read(message_ids, conn.identity)

    # 推送已读回执给用户端（包含已读时间）
    server_msg = build_server_message(
        action=WSAction.SERVER_READ_RECEIPT,
        payload={
            "role": "agent",
            "message_ids": message_ids,
            "read_at": read_at.isoformat(),
            "read_by": conn.identity,
        },
        conversation_id=conn.conversation_id,
    )
    await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, server_msg)

    logger.info(
        "客服已读回执",
        conn_id=conn.id,
        conversation_id=conn.conversation_id,
        message_count=count,
    )


@ws_router.handler(WSAction.CLIENT_AGENT_START_HANDOFF)
async def handle_agent_start_handoff(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服主动介入"""
    reason = payload.get("reason", "")

    async with get_db_context() as session:
        handoff_service = HandoffService(session)
        result = await handoff_service.start_handoff(
            conn.conversation_id,
            operator=conn.identity,
            reason=reason,
        )

        success = result.get("success")
        error = result.get("error")
        # 幂等处理：如果会话已处于人工模式，则视为成功
        if not success and error == "会话已在人工模式":
            success = True
            logger.info(
                "客服重复介入请求，忽略",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                operator=conn.identity,
            )
        if success:
            operator = conn.identity
            # 通知用户端
            server_msg = build_server_message(
                action=WSAction.SERVER_HANDOFF_STARTED,
                payload={"operator": operator, "reason": reason},
                conversation_id=conn.conversation_id,
            )
            await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, server_msg)

            # 通知其他客服端
            state_msg = build_server_message(
                action=WSAction.SERVER_CONVERSATION_STATE,
                payload={"handoff_state": "human", "operator": operator},
                conversation_id=conn.conversation_id,
            )
            await ws_manager.broadcast_to_conversation(
                conn.conversation_id,
                state_msg,
                exclude_conn_id=conn.id,
            )

            logger.info(
                "客服介入成功",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                operator=operator,
            )
        else:
            logger.warning(
                "客服介入失败",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                error=error,
            )


@ws_router.handler(WSAction.CLIENT_AGENT_END_HANDOFF)
async def handle_agent_end_handoff(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服结束介入"""
    summary = payload.get("summary", "")

    async with get_db_context() as session:
        handoff_service = HandoffService(session)
        result = await handoff_service.end_handoff(
            conn.conversation_id,
            operator=conn.identity,
            summary=summary,
        )

        success = result.get("success")
        error = result.get("error")
        # 幂等处理：如果会话已是 AI 模式，则视为成功
        if not success and error == "会话未在人工模式":
            success = True
            logger.info(
                "客服重复结束请求，忽略",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                operator=conn.identity,
            )
        if success:
            # 通知用户端
            server_msg = build_server_message(
                action=WSAction.SERVER_HANDOFF_ENDED,
                payload={"operator": conn.identity, "summary": summary},
                conversation_id=conn.conversation_id,
            )
            await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, server_msg)

            # 通知其他客服端
            state_msg = build_server_message(
                action=WSAction.SERVER_CONVERSATION_STATE,
                payload={"handoff_state": "ai", "operator": None},
                conversation_id=conn.conversation_id,
            )
            await ws_manager.broadcast_to_conversation(
                conn.conversation_id,
                state_msg,
                exclude_conn_id=conn.id,
            )

            logger.info(
                "客服介入结束",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                operator=conn.identity,
            )
        else:
            logger.warning(
                "结束介入失败",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                error=error,
            )


@ws_router.handler(WSAction.CLIENT_AGENT_TRANSFER)
async def handle_agent_transfer(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服转接"""
    target_agent_id = payload["target_agent_id"]
    reason = payload.get("reason", "")

    async with get_db_context() as session:
        handoff_service = HandoffService(session)

        # 更新介入客服
        result = await handoff_service.start_handoff(
            conn.conversation_id,
            operator=target_agent_id,
            reason=f"转接自 {conn.identity}: {reason}",
        )

        if result.get("success"):
            # 通知用户端
            server_msg = build_server_message(
                action=WSAction.SERVER_HANDOFF_STARTED,
                payload={
                    "operator": target_agent_id,
                    "reason": f"客服转接: {reason}",
                },
                conversation_id=conn.conversation_id,
            )
            await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, server_msg)

            logger.info(
                "客服转接成功",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                from_agent=conn.identity,
                to_agent=target_agent_id,
            )
