"""WebSocket 路由端点"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.schemas.websocket import WSAction, WSRole
from app.services.support.handoff import HandoffService

# 确保 handlers 被注册
from app.services.websocket import handlers  # noqa: F401
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import ws_manager
from app.services.websocket.router import ws_router

logger = get_logger("router.ws")

router = APIRouter(prefix="/ws", tags=["websocket"])


async def _authenticate_user(token: str | None, conversation_id: str) -> tuple[bool, str, str]:
    """验证用户身份
    
    Returns:
        (success, user_id, error_message)
    """
    if not token:
        return False, "", "缺少认证 token"

    # TODO: 实现真实的 token 验证（JWT 等）
    # 这里简化处理，支持 "user_{user_id}" 格式或直接使用 token 作为 user_id
    if token.startswith("user_"):
        return True, token[5:], ""

    return True, token, ""


async def _authenticate_agent(token: str | None) -> tuple[bool, str, str]:
    """验证客服身份
    
    Returns:
        (success, agent_id, error_message)
    """
    if not token:
        return False, "", "缺少认证 token"

    # TODO: 实现真实的 token 验证（企业微信 OAuth 等）
    if token.startswith("agent_"):
        return True, token[6:], ""

    return True, token, ""


@router.websocket("/user/{conversation_id}")
async def ws_user_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(..., description="用户认证 token"),
):
    """用户端 WebSocket 连接
    
    URL: ws://host/ws/user/{conversation_id}?token=xxx
    
    连接成功后会收到 system.connected 消息，包含：
    - connection_id: 连接 ID
    - role: "user"
    - conversation_id: 会话 ID
    - handoff_state: 当前客服介入状态
    - peer_online: 客服是否在线
    - peer_last_online_at: 客服最后在线时间
    - unread_count: 未读消息数
    
    支持的 Action：
    - client.user.send_message: 发送消息
    - client.user.typing: 输入状态
    - client.user.read: 已读回执
    - client.user.request_handoff: 请求人工客服
    - system.ping: 心跳
    """
    # 1. 验证身份
    success, user_id, error = await _authenticate_user(token, conversation_id)
    if not success:
        await websocket.close(code=4001, reason=error)
        return

    # 2. 接受连接
    await websocket.accept()
    logger.info(
        "用户 WebSocket 握手成功，等待注册",
        conversation_id=conversation_id,
        user_id=user_id,
        client=str(websocket.client),
        headers=dict(websocket.headers),
    )

    # 3. 注册连接
    conn = await ws_manager.connect(
        websocket=websocket,
        conversation_id=conversation_id,
        role=WSRole.USER,
        identity=user_id,
    )

    try:
        async with get_db_context() as session:
            from app.repositories.conversation import ConversationRepository
            from app.repositories.message import MessageRepository

            handoff_service = HandoffService(session)
            conv_repo = ConversationRepository(session)
            msg_repo = MessageRepository(session)

            # 4. 获取当前 handoff 状态和在线状态
            handoff_state = await handoff_service.get_handoff_state(conversation_id) or "ai"
            online_status = await conv_repo.get_online_status(conversation_id)

            # 5. 更新用户在线状态到数据库
            await conv_repo.set_user_online(conversation_id, True)

            # 6. 获取未读消息数
            unread_count = await msg_repo.get_unread_count(conversation_id, "user")

            # 7. 获取未送达消息并推送
            undelivered = await msg_repo.get_undelivered_messages(conversation_id, "user")

        # 8. 发送连接成功消息
        peer_last_online = online_status.get("agent_last_online_at")
        connected_msg = build_server_message(
            action=WSAction.SYSTEM_CONNECTED,
            payload={
                "connection_id": conn.id,
                "role": WSRole.USER.value,
                "conversation_id": conversation_id,
                "handoff_state": handoff_state,
                "peer_online": online_status.get("agent_online", False),
                "peer_last_online_at": peer_last_online.isoformat() if peer_last_online else None,
                "unread_count": unread_count,
            },
            conversation_id=conversation_id,
        )
        await conn.send(connected_msg)

        # 9. 推送未送达消息
        if undelivered:
            delivered_ids = []
            for msg in undelivered:
                server_msg = build_server_message(
                    action=WSAction.SERVER_MESSAGE,
                    payload={
                        "message_id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "is_delivered": True,
                        "delivered_at": msg.created_at.isoformat(),
                        "read_at": msg.read_at.isoformat() if msg.read_at else None,
                        "read_by": msg.read_by,
                    },
                    conversation_id=conversation_id,
                )
                await conn.send(server_msg)
                delivered_ids.append(msg.id)

            # 标记为已送达
            if delivered_ids:
                async with get_db_context() as session:
                    msg_repo = MessageRepository(session)
                    await msg_repo.mark_as_delivered(delivered_ids)

        # 10. 通知客服端用户上线
        from datetime import datetime
        now = datetime.now()
        online_msg = build_server_message(
            action=WSAction.SERVER_USER_ONLINE,
            payload={
                "user_id": user_id,
                "conversation_id": conversation_id,
                "online": True,
                "last_online_at": now.isoformat(),
            },
            conversation_id=conversation_id,
        )
        await ws_manager.send_to_role(conversation_id, WSRole.AGENT, online_msg)

        logger.info(
            "用户 WebSocket 已连接",
            conn_id=conn.id,
            user_id=user_id,
            conversation_id=conversation_id,
            undelivered_count=len(undelivered) if undelivered else 0,
        )

        # 11. 消息循环
        while True:
            try:
                # 检查连接是否仍然有效
                if not conn.is_alive:
                    break
                data = await websocket.receive_json()
                await ws_router.route(conn, data)
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                # 处理 "WebSocket is not connected" 错误
                if "not connected" in str(e).lower():
                    logger.debug("WebSocket 连接已关闭", conn_id=conn.id)
                else:
                    logger.exception("处理用户消息失败", error=str(e))
                break
            except Exception as e:
                logger.exception("处理用户消息失败", error=str(e))
                break

    finally:
        # 12. 清理 - 更新数据库在线状态
        async with get_db_context() as session:
            conv_repo = ConversationRepository(session)
            await conv_repo.set_user_online(conversation_id, False)

        await ws_manager.disconnect(conn.id)

        # 通知客服端用户下线
        from datetime import datetime
        now = datetime.now()
        offline_msg = build_server_message(
            action=WSAction.SERVER_USER_OFFLINE,
            payload={
                "user_id": user_id,
                "conversation_id": conversation_id,
                "online": False,
                "last_online_at": now.isoformat(),
            },
            conversation_id=conversation_id,
        )
        await ws_manager.send_to_role(conversation_id, WSRole.AGENT, offline_msg)

        logger.info("用户 WebSocket 断开", conn_id=conn.id, user_id=user_id)


@router.websocket("/agent/{conversation_id}")
async def ws_agent_endpoint(
    websocket: WebSocket,
    conversation_id: str,
    token: str = Query(..., description="客服认证 token"),
):
    """客服端 WebSocket 连接
    
    URL: ws://host/ws/agent/{conversation_id}?token=xxx
    
    连接成功后会收到 system.connected 消息，包含：
    - connection_id: 连接 ID
    - role: "agent"
    - conversation_id: 会话 ID
    - handoff_state: 当前客服介入状态
    - peer_online: 用户是否在线
    - peer_last_online_at: 用户最后在线时间
    - unread_count: 未读消息数
    
    支持的 Action：
    - client.agent.send_message: 发送消息
    - client.agent.typing: 输入状态
    - client.agent.read: 已读回执
    - client.agent.start_handoff: 开始介入
    - client.agent.end_handoff: 结束介入
    - client.agent.transfer: 转接客服
    - system.ping: 心跳
    """
    # 1. 验证身份
    success, agent_id, error = await _authenticate_agent(token)
    if not success:
        await websocket.close(code=4001, reason=error)
        return

    # 2. 接受连接
    await websocket.accept()

    # 3. 注册连接
    conn = await ws_manager.connect(
        websocket=websocket,
        conversation_id=conversation_id,
        role=WSRole.AGENT,
        identity=agent_id,
    )

    try:
        async with get_db_context() as session:
            from app.repositories.conversation import ConversationRepository
            from app.repositories.message import MessageRepository

            handoff_service = HandoffService(session)
            conv_repo = ConversationRepository(session)
            msg_repo = MessageRepository(session)

            # 4. 获取当前 handoff 状态和在线状态
            handoff_state = await handoff_service.get_handoff_state(conversation_id) or "ai"
            online_status = await conv_repo.get_online_status(conversation_id)

            # 5. 更新客服在线状态到数据库
            await conv_repo.set_agent_online(conversation_id, True, agent_id)

            # 6. 获取未读消息数（发给客服的消息）
            unread_count = await msg_repo.get_unread_count(conversation_id, "agent")

            # 7. 获取未送达消息并推送
            undelivered = await msg_repo.get_undelivered_messages(conversation_id, "agent")

        # 8. 发送连接成功消息
        peer_last_online = online_status.get("user_last_online_at")
        connected_msg = build_server_message(
            action=WSAction.SYSTEM_CONNECTED,
            payload={
                "connection_id": conn.id,
                "role": WSRole.AGENT.value,
                "conversation_id": conversation_id,
                "handoff_state": handoff_state,
                "peer_online": online_status.get("user_online", False),
                "peer_last_online_at": peer_last_online.isoformat() if peer_last_online else None,
                "unread_count": unread_count,
            },
            conversation_id=conversation_id,
        )
        await conn.send(connected_msg)

        # 9. 推送未送达消息
        if undelivered:
            delivered_ids = []
            for msg in undelivered:
                server_msg = build_server_message(
                    action=WSAction.SERVER_MESSAGE,
                    payload={
                        "message_id": msg.id,
                        "role": msg.role,
                        "content": msg.content,
                        "created_at": msg.created_at.isoformat(),
                        "is_delivered": True,
                        "delivered_at": msg.created_at.isoformat(),
                        "read_at": msg.read_at.isoformat() if msg.read_at else None,
                        "read_by": msg.read_by,
                    },
                    conversation_id=conversation_id,
                )
                await conn.send(server_msg)
                delivered_ids.append(msg.id)

            # 标记为已送达
            if delivered_ids:
                async with get_db_context() as session:
                    msg_repo = MessageRepository(session)
                    await msg_repo.mark_as_delivered(delivered_ids)

        # 10. 通知用户端客服上线
        from datetime import datetime
        now = datetime.now()
        online_msg = build_server_message(
            action=WSAction.SERVER_AGENT_ONLINE,
            payload={
                "operator": agent_id,
                "online": True,
                "last_online_at": now.isoformat(),
            },
            conversation_id=conversation_id,
        )
        await ws_manager.send_to_role(conversation_id, WSRole.USER, online_msg)

        logger.info(
            "客服 WebSocket 已连接",
            conn_id=conn.id,
            agent_id=agent_id,
            conversation_id=conversation_id,
            undelivered_count=len(undelivered) if undelivered else 0,
        )

        # 11. 消息循环
        while True:
            try:
                # 检查连接是否仍然有效
                if not conn.is_alive:
                    break
                data = await websocket.receive_json()
                await ws_router.route(conn, data)
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                # 处理 "WebSocket is not connected" 错误
                if "not connected" in str(e).lower():
                    logger.debug("WebSocket 连接已关闭", conn_id=conn.id)
                else:
                    logger.exception("处理客服消息失败", error=str(e))
                break
            except Exception as e:
                logger.exception("处理客服消息失败", error=str(e))
                break

    finally:
        # 12. 清理 - 更新数据库在线状态
        async with get_db_context() as session:
            conv_repo = ConversationRepository(session)
            await conv_repo.set_agent_online(conversation_id, False, None)

        await ws_manager.disconnect(conn.id)

        # 通知用户端客服下线
        from datetime import datetime
        now = datetime.now()
        offline_msg = build_server_message(
            action=WSAction.SERVER_AGENT_OFFLINE,
            payload={
                "operator": agent_id,
                "online": False,
                "last_online_at": now.isoformat(),
            },
            conversation_id=conversation_id,
        )
        await ws_manager.send_to_role(conversation_id, WSRole.USER, offline_msg)

        logger.info("客服 WebSocket 断开", conn_id=conn.id, agent_id=agent_id)


@router.get("/stats")
async def get_ws_stats():
    """获取 WebSocket 连接统计
    
    Returns:
        - total_connections: 总连接数
        - by_role: 按角色统计 {"user": n, "agent": m}
        - active_conversations: 有活跃连接的会话数
    """
    return ws_manager.get_stats()


@router.get("/connections/{conversation_id}")
async def get_conversation_connections(conversation_id: str):
    """获取指定会话的连接信息"""
    conns = ws_manager.get_connections_by_conversation(conversation_id)
    return {
        "conversation_id": conversation_id,
        "connections": [
            {
                "id": c.id,
                "role": c.role.value if hasattr(c.role, 'value') else c.role,
                "identity": c.identity,
                "created_at": c.created_at.isoformat(),
                "is_alive": c.is_alive,
            }
            for c in conns
        ],
        "user_count": sum(1 for c in conns if c.role == WSRole.USER),
        "agent_count": sum(1 for c in conns if c.role == WSRole.AGENT),
    }
