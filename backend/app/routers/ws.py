"""WebSocket 路由端点"""

from datetime import datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.dependencies import get_services
from app.core.logging import get_logger
from app.models.message import Message
from app.schemas.websocket import WSAction, WSRole

# 确保 handlers 被注册
from app.services.websocket import handlers  # noqa: F401
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import ws_manager
from app.services.websocket.router import ws_router

logger = get_logger("router.ws")

router = APIRouter(prefix="/ws", tags=["websocket"])
SUPPORT_QUEUE_CHANNEL_ID = "__support_queue__"


def _build_connected_payload(
    *,
    connection_id: str,
    role: WSRole,
    conversation_id: str,
    handoff_state: str,
    peer_online: bool,
    peer_last_online_at: datetime | None,
    unread_count: int,
    conversation_state_payload: dict,
) -> dict:
    """构建 system.connected 的完整 payload。

    这个方法服务于用户端和客服端初始建连时的状态恢复，确保 `system.connected`
    与后续 `server.conversation_state` 使用同一套状态字段，避免重连后少字段。
    """
    return {
        "connection_id": connection_id,
        "role": role.value,
        "conversation_id": conversation_id,
        "handoff_state": handoff_state,
        "peer_online": peer_online,
        "peer_last_online_at": peer_last_online_at.isoformat() if peer_last_online_at else None,
        "unread_count": unread_count,
        "conversation_mode": conversation_state_payload["conversation_mode"],
        "current_ticket": conversation_state_payload["current_ticket"],
        "review_summary": conversation_state_payload["review_summary"],
        "recent_tasks": conversation_state_payload["recent_tasks"],
        "secondary_issues": conversation_state_payload["secondary_issues"],
        "handoff_summary": conversation_state_payload["handoff_summary"],
    }


def _build_support_queue_connected_payload(
    *,
    connection_id: str,
) -> dict:
    """构建客服全局队列频道的 connected payload。

    这个方法服务于客服列表页的独立全局连接。该连接不绑定真实会话，
    只负责接收 `server.support_queue_changed` 这类跨会话队列信号。
    """
    return {
        "connection_id": connection_id,
        "role": WSRole.AGENT.value,
        "conversation_id": SUPPORT_QUEUE_CHANNEL_ID,
        "conversation_mode": "ai",
        "handoff_state": "ai",
        "peer_online": False,
        "peer_last_online_at": None,
        "unread_count": 0,
        "current_ticket": None,
        "review_summary": None,
        "recent_tasks": [],
        "secondary_issues": [],
        "handoff_summary": None,
    }


async def _broadcast_support_queue_change(
    *,
    conversation_id: str,
    handoff_state: str,
    reason: str,
    source: str,
    changed_at: str | None = None,
) -> None:
    """广播客服全局队列变更信号。

    这个方法服务于 `/ws/user/*` 和 `/ws/agent/*` 这类连接生命周期事件。
    当用户在线状态变化时，即使客服列表页没有订阅该会话，也要刷新在线徽标和排序优先级。
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


def _build_server_message_payload(
    message: Message,
    *,
    delivered_at: datetime | None = None,
) -> dict:
    """把数据库消息转换成 WebSocket `server.message` payload。

    这个方法服务于重连后的未送达消息补发，确保图片、operator 和送达/已读状态
    与正常实时推送保持同一份协议，不会因为走补发链路而丢字段。
    """
    extra_metadata = message.extra_metadata or {}
    payload = {
        "message_id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "is_delivered": True,
        "delivered_at": (delivered_at or message.delivered_at or datetime.now()).isoformat(),
        "read_at": message.read_at.isoformat() if message.read_at else None,
        "read_by": message.read_by,
        "is_withdrawn": message.is_withdrawn,
        "withdrawn_at": message.withdrawn_at.isoformat() if message.withdrawn_at else None,
        "withdrawn_by": message.withdrawn_by,
        "is_edited": message.is_edited,
        "edited_at": message.edited_at.isoformat() if message.edited_at else None,
        "edited_by": message.edited_by,
    }
    if extra_metadata.get("operator"):
        payload["operator"] = extra_metadata["operator"]
    if extra_metadata.get("images"):
        payload["images"] = extra_metadata["images"]
    return payload


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
    handoff_state = "ai"

    try:
        async with get_services() as services:
            # 4. 获取当前 handoff 状态和在线状态
            handoff_state = await services.handoff.get_handoff_state(conversation_id) or "ai"
            online_status = await services.conversation_repo.get_online_status(conversation_id)

            # 5. 更新用户在线状态到数据库
            await services.conversation_repo.set_user_online(conversation_id, True)

            # 6. 获取未读消息数
            unread_count = await services.message_repo.get_unread_count(conversation_id, "user")

            # 7. 获取未送达消息并推送
            undelivered = await services.message_repo.get_undelivered_messages(conversation_id, "user")

        # 8. 发送连接成功消息
        peer_last_online = online_status.get("agent_last_online_at")
        async with get_services() as services:
            conversation_state_payload = await services.support_state.build_websocket_state_payload(
                conversation_id,
                unread_count=unread_count,
                peer_last_online_at=peer_last_online,
            )
        connected_msg = build_server_message(
            action=WSAction.SYSTEM_CONNECTED,
            payload=_build_connected_payload(
                connection_id=conn.id,
                role=WSRole.USER,
                conversation_id=conversation_id,
                handoff_state=handoff_state,
                peer_online=online_status.get("agent_online", False),
                peer_last_online_at=peer_last_online,
                unread_count=unread_count,
                conversation_state_payload=conversation_state_payload,
            ),
            conversation_id=conversation_id,
        )
        await conn.send(connected_msg)

        # 9. 推送未送达消息
        if undelivered:
            delivered_ids = []
            delivered_messages_for_agents: list[tuple[Message, datetime]] = []
            for msg in undelivered:
                delivered_at = datetime.now()
                server_msg = build_server_message(
                    action=WSAction.SERVER_MESSAGE,
                    payload=_build_server_message_payload(msg, delivered_at=delivered_at),
                    conversation_id=conversation_id,
                )
                await conn.send(server_msg)
                delivered_ids.append(msg.id)
                delivered_messages_for_agents.append((msg, delivered_at))

            # 标记为已送达
            if delivered_ids:
                async with get_services() as svc:
                    await svc.message_repo.mark_as_delivered(delivered_ids)

                # 把离线补发后的送达状态同步给客服端，更新“待送达/已送达”展示。
                for msg, delivered_at in delivered_messages_for_agents:
                    agent_sync_msg = build_server_message(
                        action=WSAction.SERVER_MESSAGE,
                        payload=_build_server_message_payload(msg, delivered_at=delivered_at),
                        conversation_id=conversation_id,
                    )
                    await ws_manager.send_to_role(conversation_id, WSRole.AGENT, agent_sync_msg)

        # 10. 通知客服端用户上线
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
        await _broadcast_support_queue_change(
            conversation_id=conversation_id,
            handoff_state=handoff_state,
            reason="user_online",
            source="user_online",
            changed_at=now.isoformat(),
        )

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
        async with get_services() as svc:
            await svc.conversation_repo.set_user_online(conversation_id, False)

        await ws_manager.disconnect(conn.id)

        # 通知客服端用户下线
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
        await _broadcast_support_queue_change(
            conversation_id=conversation_id,
            handoff_state=handoff_state,
            reason="user_offline",
            source="user_offline",
            changed_at=now.isoformat(),
        )

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
        async with get_services() as services:
            # 4. 获取当前 handoff 状态和在线状态
            handoff_state = await services.handoff.get_handoff_state(conversation_id) or "ai"
            online_status = await services.conversation_repo.get_online_status(conversation_id)

            # 5. 更新客服在线状态到数据库
            await services.conversation_repo.set_agent_online(conversation_id, True, agent_id)

            # 6. 获取未读消息数（发给客服的消息）
            unread_count = await services.message_repo.get_unread_count(conversation_id, "agent")

            # 7. 获取未送达消息并推送
            undelivered = await services.message_repo.get_undelivered_messages(conversation_id, "agent")

        # 8. 发送连接成功消息
        peer_last_online = online_status.get("user_last_online_at")
        async with get_services() as services:
            conversation_state_payload = await services.support_state.build_websocket_state_payload(
                conversation_id,
                unread_count=unread_count,
                peer_last_online_at=peer_last_online,
            )
        connected_msg = build_server_message(
            action=WSAction.SYSTEM_CONNECTED,
            payload=_build_connected_payload(
                connection_id=conn.id,
                role=WSRole.AGENT,
                conversation_id=conversation_id,
                handoff_state=handoff_state,
                peer_online=online_status.get("user_online", False),
                peer_last_online_at=peer_last_online,
                unread_count=unread_count,
                conversation_state_payload=conversation_state_payload,
            ),
            conversation_id=conversation_id,
        )
        await conn.send(connected_msg)

        # 9. 推送未送达消息
        if undelivered:
            delivered_ids = []
            for msg in undelivered:
                delivered_at = datetime.now()
                server_msg = build_server_message(
                    action=WSAction.SERVER_MESSAGE,
                    payload=_build_server_message_payload(msg, delivered_at=delivered_at),
                    conversation_id=conversation_id,
                )
                await conn.send(server_msg)
                delivered_ids.append(msg.id)

            # 标记为已送达
            if delivered_ids:
                async with get_services() as svc:
                    await svc.message_repo.mark_as_delivered(delivered_ids)

        # 10. 通知用户端客服上线
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
        async with get_services() as svc:
            await svc.conversation_repo.set_agent_online(conversation_id, False, None)

        await ws_manager.disconnect(conn.id)

        # 通知用户端客服下线
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


@router.websocket("/agent-queue")
async def ws_agent_queue_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="客服认证 token"),
):
    """客服工作台全局队列 WebSocket 连接。

    这个端点服务于客服列表页的跨会话刷新能力。它不承载具体会话消息，
    只负责把 `server.support_queue_changed` 这类全局队列事件推给在线客服页面。
    """
    success, agent_id, error = await _authenticate_agent(token)
    if not success:
        await websocket.close(code=4001, reason=error)
        return

    await websocket.accept()
    conn = await ws_manager.connect(
        websocket=websocket,
        conversation_id=SUPPORT_QUEUE_CHANNEL_ID,
        role=WSRole.AGENT,
        identity=agent_id,
    )

    try:
        connected_msg = build_server_message(
            action=WSAction.SYSTEM_CONNECTED,
            payload=_build_support_queue_connected_payload(connection_id=conn.id),
            conversation_id=SUPPORT_QUEUE_CHANNEL_ID,
        )
        await conn.send(connected_msg)

        logger.info(
            "客服全局队列 WebSocket 已连接",
            conn_id=conn.id,
            agent_id=agent_id,
        )

        while True:
            try:
                if not conn.is_alive:
                    break
                data = await websocket.receive_json()
                await ws_router.route(conn, data)
            except WebSocketDisconnect:
                break
            except RuntimeError as e:
                if "not connected" in str(e).lower():
                    logger.debug("客服全局队列 WebSocket 已关闭", conn_id=conn.id)
                else:
                    logger.exception("处理客服全局队列消息失败", error=str(e))
                break
            except Exception as e:
                logger.exception("处理客服全局队列消息失败", error=str(e))
                break
    finally:
        await ws_manager.disconnect(conn.id)
        logger.info("客服全局队列 WebSocket 断开", conn_id=conn.id, agent_id=agent_id)


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
