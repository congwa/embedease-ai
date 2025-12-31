"""WebSocket 路由端点"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.schemas.websocket import WSAction, WSRole
from app.services.websocket.manager import ws_manager
from app.services.websocket.router import ws_router
from app.services.websocket.handlers.base import build_server_message
from app.services.support.handoff import HandoffService

# 确保 handlers 被注册
from app.services.websocket import handlers  # noqa: F401

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
    
    # 3. 注册连接
    conn = await ws_manager.connect(
        websocket=websocket,
        conversation_id=conversation_id,
        role=WSRole.USER,
        identity=user_id,
    )
    
    try:
        # 4. 获取当前 handoff 状态
        async with get_db_context() as session:
            handoff_service = HandoffService(session)
            handoff_state = await handoff_service.get_handoff_state(conversation_id) or "ai"
        
        # 5. 发送连接成功消息
        connected_msg = build_server_message(
            action=WSAction.SYSTEM_CONNECTED,
            payload={
                "connection_id": conn.id,
                "role": WSRole.USER.value,
                "conversation_id": conversation_id,
                "handoff_state": handoff_state,
            },
            conversation_id=conversation_id,
        )
        await conn.send(connected_msg)
        
        # 6. 通知客服端用户上线
        online_msg = build_server_message(
            action=WSAction.SERVER_USER_ONLINE,
            payload={"user_id": user_id, "conversation_id": conversation_id},
            conversation_id=conversation_id,
        )
        await ws_manager.send_to_role(conversation_id, WSRole.AGENT, online_msg)
        
        logger.info(
            "用户 WebSocket 已连接",
            conn_id=conn.id,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        
        # 7. 消息循环
        while True:
            try:
                data = await websocket.receive_json()
                await ws_router.route(conn, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.exception("处理用户消息失败", error=str(e))
                
    finally:
        # 8. 清理
        await ws_manager.disconnect(conn.id)
        
        # 通知客服端用户下线
        offline_msg = build_server_message(
            action=WSAction.SERVER_USER_OFFLINE,
            payload={"user_id": user_id, "conversation_id": conversation_id},
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
        # 4. 获取当前 handoff 状态
        async with get_db_context() as session:
            handoff_service = HandoffService(session)
            handoff_state = await handoff_service.get_handoff_state(conversation_id) or "ai"
        
        # 5. 发送连接成功消息
        connected_msg = build_server_message(
            action=WSAction.SYSTEM_CONNECTED,
            payload={
                "connection_id": conn.id,
                "role": WSRole.AGENT.value,
                "conversation_id": conversation_id,
                "handoff_state": handoff_state,
            },
            conversation_id=conversation_id,
        )
        await conn.send(connected_msg)
        
        # 6. 通知用户端客服上线
        online_msg = build_server_message(
            action=WSAction.SERVER_AGENT_ONLINE,
            payload={"operator": agent_id},
            conversation_id=conversation_id,
        )
        await ws_manager.send_to_role(conversation_id, WSRole.USER, online_msg)
        
        logger.info(
            "客服 WebSocket 已连接",
            conn_id=conn.id,
            agent_id=agent_id,
            conversation_id=conversation_id,
        )
        
        # 7. 消息循环
        while True:
            try:
                data = await websocket.receive_json()
                await ws_router.route(conn, data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.exception("处理客服消息失败", error=str(e))
                break
                
    finally:
        # 8. 清理
        await ws_manager.disconnect(conn.id)
        
        # 通知用户端客服下线
        offline_msg = build_server_message(
            action=WSAction.SERVER_AGENT_OFFLINE,
            payload={"operator": agent_id},
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
