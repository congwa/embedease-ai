"""客服端消息处理器

本文件的业务职责，是承接客服工作台的实时操作，并把“人工消息、已读、接入、结束接入、
转接、撤回、编辑”等动作翻译成用户端和客服端都能消费的 WebSocket 事件。
"""

from datetime import datetime
from typing import Any

from app.core.dependencies import get_services
from app.core.logging import get_logger
from app.schemas.websocket import WSAction, WSRole
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import WSConnection, ws_manager
from app.services.websocket.router import ws_router

logger = get_logger("websocket.handlers.agent")


async def _notify_user_handoff_event(
    *,
    conversation_id: str,
    action: WSAction,
    payload: dict[str, Any],
) -> None:
    """向用户端发送 handoff 事件提示。

    这个内部方法只负责发送“客服已接入/已结束”的事件提示，不重复发送会话状态。
    当前主 ticket 和会话状态的实时广播统一由 complaint handoff 服务负责，避免同一动作
    被 WebSocket handler 和服务层各推一次 `server.conversation_state`。
    """
    server_msg = build_server_message(
        action=action,
        payload=payload,
        conversation_id=conversation_id,
    )
    await ws_manager.send_to_role(conversation_id, WSRole.USER, server_msg)


async def _broadcast_support_queue_change(
    *,
    conversation_id: str,
    handoff_state: str,
    reason: str,
    source: str,
    changed_at: str | None = None,
) -> None:
    """广播客服全局队列变更信号。

    这个内部方法服务于客服列表页跨会话刷新。人工回复、人工已读等动作虽然发生在单会话内，
    但也会改变最后消息、未读数和排序优先级，需要同步提示所有在线客服页面静默刷新。
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


@ws_router.handler(WSAction.CLIENT_AGENT_SEND_MESSAGE)
async def handle_agent_send_message(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服发送消息（支持图片）。

    这个 handler 除了完成实时发消息，还要触发客服列表页的全局队列刷新，
    让未监控会话的最后消息和排序也能及时更新。
    """

    content = payload.get("content", "")
    images = payload.get("images")  # 图片列表
    client_message_id = payload.get("message_id")

    # 验证：必须有内容或图片
    if not content.strip() and not images:
        logger.warning(
            "客服消息发送失败：消息内容和图片不能同时为空",
            conn_id=conn.id,
            conversation_id=conn.conversation_id,
        )
        return

    async with get_services() as services:
        # 添加人工消息（支持图片）
        message = await services.handoff.add_human_message(
            conversation_id=conn.conversation_id,
            content=content,
            operator=conn.identity,
            images=images,
            message_id=client_message_id,
        )

        if message:
            delivered_at = None
            is_delivered = False

            # 先尝试通过 WebSocket 发送给用户，决定这条人工消息是否已真正送达。
            user_payload: dict[str, Any] = {
                "message_id": message.id,
                "role": "human_agent",
                "content": content,
                "created_at": message.created_at.isoformat(),
                "operator": conn.identity,
            }
            if images:
                user_payload["images"] = images

            user_msg = build_server_message(
                action=WSAction.SERVER_MESSAGE,
                payload=user_payload,
                conversation_id=conn.conversation_id,
            )
            ws_sent = await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, user_msg)

            # 如果成功送达，更新消息状态
            if ws_sent > 0:
                await services.message_repo.mark_as_delivered([message.id])
                delivered_at = datetime.now().isoformat()
                is_delivered = True
                logger.info(
                    "客服消息已送达用户",
                    conn_id=conn.id,
                    conversation_id=conn.conversation_id,
                    message_id=message.id,
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

            # 再广播给所有客服端，让当前标签页能把乐观消息合并成真实状态，
            # 其他客服标签页也能立即看到这条人工回复。
            ws_payload: dict[str, Any] = {
                "message_id": message.id,
                "role": "human_agent",
                "content": content,
                "created_at": message.created_at.isoformat(),
                "operator": conn.identity,
                "is_delivered": is_delivered,
                "delivered_at": delivered_at,
            }
            if images:
                ws_payload["images"] = images

            agent_msg = build_server_message(
                action=WSAction.SERVER_MESSAGE,
                payload=ws_payload,
                conversation_id=conn.conversation_id,
            )
            await ws_manager.send_to_role(conn.conversation_id, WSRole.AGENT, agent_msg)
            await _broadcast_support_queue_change(
                conversation_id=conn.conversation_id,
                handoff_state="human",
                reason="agent_message",
                source="agent_message",
                changed_at=message.created_at.isoformat(),
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
    """处理客服已读回执。

    这个 handler 既要同步当前会话未读数，也要提醒客服列表页刷新全局队列，
    让未监控会话的未读红点能够及时归零。
    """
    message_ids = payload["message_ids"]

    # 更新数据库已读状态
    async with get_services() as services:
        count, read_at = await services.message_repo.mark_as_read(message_ids, conn.identity)
        unread_count = await services.message_repo.get_unread_count(conn.conversation_id, "agent")
        state_payload = await services.support_state.build_websocket_state_payload(
            conn.conversation_id,
            unread_count=unread_count,
        )

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

    # 推送最新会话状态给客服端，确保列表页和其他客服标签页的未读数立即同步归零。
    state_msg = build_server_message(
        action=WSAction.SERVER_CONVERSATION_STATE,
        payload=state_payload,
        conversation_id=conn.conversation_id,
    )
    await ws_manager.send_to_role(conn.conversation_id, WSRole.AGENT, state_msg)
    await _broadcast_support_queue_change(
        conversation_id=conn.conversation_id,
        handoff_state=state_payload["handoff_state"],
        reason="agent_read",
        source="agent_read",
        changed_at=read_at.isoformat(),
    )

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

    async with get_services() as services:
        result = await services.complaint_handoff.accept_handoff(
            conversation_id=conn.conversation_id,
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
            # 这里只补 handoff 提示事件；完整状态广播由 complaint handoff 服务统一发送。
            await _notify_user_handoff_event(
                conversation_id=conn.conversation_id,
                action=WSAction.SERVER_HANDOFF_STARTED,
                payload={"operator": operator, "reason": reason},
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

    async with get_services() as services:
        result = await services.complaint_handoff.finish_handoff(
            conversation_id=conn.conversation_id,
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
            # 这里只补 handoff 提示事件；完整状态广播由 complaint handoff 服务统一发送。
            await _notify_user_handoff_event(
                conversation_id=conn.conversation_id,
                action=WSAction.SERVER_HANDOFF_ENDED,
                payload={"operator": conn.identity, "summary": summary},
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
    """处理客服转接。

    这个 handler 服务于人工客服把当前会话移交给其他客服的场景。
    它只触发转接事件提示和新的会话状态同步，不应复用“开始接入”逻辑。
    """
    target_agent_id = payload["target_agent_id"]
    reason = payload.get("reason", "")

    async with get_services() as services:
        # 转接当前人工会话给新的客服，不再走 start_handoff 状态机。
        result = await services.complaint_handoff.transfer_handoff(
            conversation_id=conn.conversation_id,
            operator=target_agent_id,
            reason=f"转接自 {conn.identity}: {reason}",
        )

        if result.get("success"):
            await _notify_user_handoff_event(
                conversation_id=conn.conversation_id,
                action=WSAction.SERVER_HANDOFF_STARTED,
                payload={
                    "operator": target_agent_id,
                    "reason": f"客服转接: {reason}",
                },
            )

            logger.info(
                "客服转接成功",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                from_agent=conn.identity,
                to_agent=target_agent_id,
            )
        else:
            logger.warning(
                "客服转接失败",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                from_agent=conn.identity,
                to_agent=target_agent_id,
                error=result.get("error"),
            )


@ws_router.handler(WSAction.CLIENT_AGENT_WITHDRAW_MESSAGE)
async def handle_agent_withdraw_message(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服撤回消息。

    这个 handler 不只负责把消息标记为撤回，还要推动客服全局队列刷新。
    如果最后一条人工消息被撤回，列表页的最新消息预览和排序都需要立即重算。
    """
    from datetime import datetime, timedelta

    message_id = payload.get("message_id")
    reason = payload.get("reason", "")

    if not message_id:
        logger.warning(
            "撤回消息失败：缺少 message_id",
            conn_id=conn.id,
            conversation_id=conn.conversation_id,
        )
        return

    async with get_services() as services:
        # 获取消息
        message = await services.message_repo.get_by_id(message_id)
        if not message:
            logger.warning(
                "撤回消息失败：消息不存在",
                conn_id=conn.id,
                message_id=message_id,
            )
            return

        # 验证消息属于当前会话
        if message.conversation_id != conn.conversation_id:
            logger.warning(
                "撤回消息失败：消息不属于当前会话",
                conn_id=conn.id,
                message_id=message_id,
            )
            return

        # 检查是否已撤回
        if message.is_withdrawn:
            logger.info(
                "消息已被撤回，忽略重复请求",
                conn_id=conn.id,
                message_id=message_id,
            )
            return

        # 检查时间限制（默认 5 分钟）
        time_limit_minutes = 5
        if datetime.now() - message.created_at > timedelta(minutes=time_limit_minutes):
            logger.warning(
                "撤回消息失败：已超过时间限制",
                conn_id=conn.id,
                message_id=message_id,
                time_limit_minutes=time_limit_minutes,
            )
            # 可以通过 WebSocket 返回错误给客服端
            return

        # 执行撤回
        updated_message = await services.message_repo.withdraw_message(
            message_id=message_id,
            operator=conn.identity,
        )

        if updated_message:
            withdrawn_at = updated_message.withdrawn_at or datetime.now()
            withdrawn_payload = {
                "message_id": message_id,
                "withdrawn_by": conn.identity,
                "withdrawn_at": withdrawn_at.isoformat(),
                "reason": reason,
            }

            # 通知用户端
            user_msg = build_server_message(
                action=WSAction.SERVER_MESSAGE_WITHDRAWN,
                payload=withdrawn_payload,
                conversation_id=conn.conversation_id,
            )
            ws_sent = await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, user_msg)

            # 通知其他客服端
            await ws_manager.broadcast_to_conversation(
                conn.conversation_id,
                user_msg,
                exclude_conn_id=conn.id,
            )
            await _broadcast_support_queue_change(
                conversation_id=conn.conversation_id,
                handoff_state="human",
                reason="agent_message_withdrawn",
                source="agent_message_withdrawn",
                changed_at=withdrawn_at.isoformat(),
            )

            logger.info(
                "消息撤回成功",
                conn_id=conn.id,
                conversation_id=conn.conversation_id,
                message_id=message_id,
                operator=conn.identity,
                ws_sent=ws_sent,
            )


@ws_router.handler(WSAction.CLIENT_AGENT_EDIT_MESSAGE)
async def handle_agent_edit_message(
    conn: WSConnection,
    action: str,
    payload: dict[str, Any],
) -> None:
    """处理客服编辑消息。

    这个 handler 不只负责改写消息内容，还要让客服列表页感知最后消息预览的变化。
    否则跨会话队列会继续显示旧文案，导致人工判断优先级时看到过期信息。
    """
    from datetime import datetime, timedelta

    message_id = payload.get("message_id")
    new_content = payload.get("new_content", "").strip()
    regenerate = payload.get("regenerate", True)

    if not message_id or not new_content:
        logger.warning(
            "编辑消息失败：缺少 message_id 或 new_content",
            conn_id=conn.id,
            conversation_id=conn.conversation_id,
        )
        return

    async with get_services() as services:
        # 获取消息
        message = await services.message_repo.get_by_id(message_id)
        if not message:
            logger.warning(
                "编辑消息失败：消息不存在",
                conn_id=conn.id,
                message_id=message_id,
            )
            return

        # 验证消息属于当前会话
        if message.conversation_id != conn.conversation_id:
            logger.warning(
                "编辑消息失败：消息不属于当前会话",
                conn_id=conn.id,
                message_id=message_id,
            )
            return

        # 检查是否已撤回
        if message.is_withdrawn:
            logger.warning(
                "编辑消息失败：消息已被撤回",
                conn_id=conn.id,
                message_id=message_id,
            )
            return

        # 检查时间限制（默认 5 分钟）
        time_limit_minutes = 5
        if datetime.now() - message.created_at > timedelta(minutes=time_limit_minutes):
            logger.warning(
                "编辑消息失败：已超过时间限制",
                conn_id=conn.id,
                message_id=message_id,
                time_limit_minutes=time_limit_minutes,
            )
            return

        old_content = message.content

        # 执行编辑
        updated_message = await services.message_repo.edit_message(
            message_id=message_id,
            new_content=new_content,
            operator=conn.identity,
        )

        if not updated_message:
            logger.warning(
                "编辑消息失败：更新失败",
                conn_id=conn.id,
                message_id=message_id,
            )
            return

        # 如果需要重新生成，删除后续的 AI 回复
        deleted_message_ids: list[str] = []
        if regenerate and message.role == "user":
            subsequent_messages = await services.message_repo.get_messages_after(
                conversation_id=conn.conversation_id,
                after_message_id=message_id,
            )
            # 只删除紧随其后的 assistant 消息
            for msg in subsequent_messages:
                if msg.role == "assistant":
                    deleted_message_ids.append(msg.id)
                else:
                    break  # 遇到非 assistant 消息就停止

            if deleted_message_ids:
                await services.message_repo.delete_messages(deleted_message_ids)

        edited_at = updated_message.edited_at or datetime.now()
        edited_payload = {
            "message_id": message_id,
            "old_content": old_content,
            "new_content": new_content,
            "edited_by": conn.identity,
            "edited_at": edited_at.isoformat(),
            "deleted_message_ids": deleted_message_ids,
            "regenerate_triggered": regenerate and len(deleted_message_ids) > 0,
        }

        # 通知用户端
        user_msg = build_server_message(
            action=WSAction.SERVER_MESSAGE_EDITED,
            payload=edited_payload,
            conversation_id=conn.conversation_id,
        )
        ws_sent = await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, user_msg)

        # 如果有删除的消息，额外通知
        if deleted_message_ids:
            deleted_msg = build_server_message(
                action=WSAction.SERVER_MESSAGES_DELETED,
                payload={
                    "message_ids": deleted_message_ids,
                    "reason": "edit_regenerate",
                },
                conversation_id=conn.conversation_id,
            )
            await ws_manager.send_to_role(conn.conversation_id, WSRole.USER, deleted_msg)

        # 通知其他客服端
        await ws_manager.broadcast_to_conversation(
            conn.conversation_id,
            user_msg,
            exclude_conn_id=conn.id,
        )
        await _broadcast_support_queue_change(
            conversation_id=conn.conversation_id,
            handoff_state="human",
            reason="agent_message_edited",
            source="agent_message_edited",
            changed_at=edited_at.isoformat(),
        )

        logger.info(
            "消息编辑成功",
            conn_id=conn.id,
            conversation_id=conn.conversation_id,
            message_id=message_id,
            operator=conn.identity,
            deleted_count=len(deleted_message_ids),
            regenerate=regenerate,
            ws_sent=ws_sent,
        )
