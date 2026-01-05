"""客服支持 API

提供：
- 客服介入/结束 API
- 人工消息发送 API
- 会话状态查询 API
- 客服端 SSE 连接
"""

import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.schemas.support import (
    ConversationListItem,
    ConversationListResponse,
    ConversationStateResponse,
    HandoffEndRequest,
    HandoffResponse,
    HandoffStartRequest,
    HumanMessageRequest,
    HumanMessageResponse,
)
from app.schemas.websocket import WSAction, WSRole
from app.services.support.gateway import support_gateway
from app.services.support.handoff import HandoffService
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import ws_manager

router = APIRouter(prefix="/api/v1/support", tags=["support"])
logger = get_logger("router.support")


@router.post("/handoff/{conversation_id}", response_model=HandoffResponse)
async def start_handoff(
    conversation_id: str,
    request: HandoffStartRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """开始客服介入
    
    将会话切换到人工客服模式，后续用户消息将不再触发 RAG。
    """
    service = HandoffService(db)
    result = await service.start_handoff(
        conversation_id,
        operator=request.operator,
        reason=request.reason,
    )

    if result.get("success"):
        # 通过 WebSocket 推送给用户
        ws_msg = build_server_message(
            action=WSAction.SERVER_HANDOFF_STARTED,
            payload={
                "operator": request.operator,
                "reason": request.reason,
                "message": "客服已上线，正在为您服务",
            },
            conversation_id=conversation_id,
        )
        ws_sent = await ws_manager.send_to_role(conversation_id, WSRole.USER, ws_msg)

        # 同时尝试 SSE 推送（兼容旧客户端）
        sse_sent = await support_gateway.send_to_user(
            conversation_id,
            {
                "type": "support.handoff_started",
                "payload": {
                    "operator": request.operator,
                    "message": "客服已上线，正在为您服务",
                },
            },
        )

        logger.info(
            "客服介入通知已发送",
            conversation_id=conversation_id,
            operator=request.operator,
            ws_sent=ws_sent,
            sse_sent=sse_sent,
        )

    return HandoffResponse(**result)


@router.post("/handoff/{conversation_id}/close", response_model=HandoffResponse)
async def end_handoff(
    conversation_id: str,
    request: HandoffEndRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """结束客服介入
    
    将会话切换回 AI 模式。
    """
    service = HandoffService(db)
    result = await service.end_handoff(
        conversation_id,
        operator=request.operator,
        summary=request.summary,
    )

    if result.get("success"):
        # 通过 WebSocket 推送给用户
        ws_msg = build_server_message(
            action=WSAction.SERVER_HANDOFF_ENDED,
            payload={
                "operator": request.operator,
                "summary": request.summary,
                "message": "人工客服已结束服务，您可以继续与智能助手对话",
            },
            conversation_id=conversation_id,
        )
        ws_sent = await ws_manager.send_to_role(conversation_id, WSRole.USER, ws_msg)

        # 同时尝试 SSE 推送（兼容旧客户端）
        sse_sent = await support_gateway.send_to_user(
            conversation_id,
            {
                "type": "support.handoff_ended",
                "payload": {
                    "message": "人工客服已结束服务，您可以继续与智能助手对话",
                },
            },
        )

        logger.info(
            "客服结束通知已发送",
            conversation_id=conversation_id,
            operator=request.operator,
            ws_sent=ws_sent,
            sse_sent=sse_sent,
        )

    return HandoffResponse(**result)


@router.get("/handoff/{conversation_id}", response_model=ConversationStateResponse)
async def get_handoff_state(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话的客服介入状态"""
    service = HandoffService(db)
    conversation = await service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    return ConversationStateResponse(
        conversation_id=conversation.id,
        handoff_state=conversation.handoff_state,
        handoff_operator=conversation.handoff_operator,
        handoff_reason=conversation.handoff_reason,
        handoff_at=conversation.handoff_at.isoformat() if conversation.handoff_at else None,
        last_notification_at=(
            conversation.last_notification_at.isoformat()
            if conversation.last_notification_at
            else None
        ),
    )


@router.post("/message/{conversation_id}", response_model=HumanMessageResponse)
async def send_human_message(
    conversation_id: str,
    request: HumanMessageRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """客服发送消息
    
    仅当会话处于人工模式时有效。
    """
    service = HandoffService(db)
    message = await service.add_human_message(
        conversation_id,
        content=request.content,
        operator=request.operator,
    )

    if not message:
        return HumanMessageResponse(
            success=False,
            error="发送失败：会话不存在或未在人工模式",
        )

    await support_gateway.send_to_user(
        conversation_id,
        {
            "type": "support.human_message",
            "payload": {
                "message_id": message.id,
                "content": message.content,
                "operator": request.operator,
                "created_at": message.created_at.isoformat(),
            },
        },
    )

    return HumanMessageResponse(
        success=True,
        message_id=message.id,
        conversation_id=conversation_id,
        created_at=message.created_at.isoformat(),
    )


@router.get("/conversations")
async def list_conversations(
    state: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话列表
    
    Args:
        state: 筛选状态（ai/pending/human），留空返回全部
        limit: 分页大小
        offset: 分页偏移
    """
    service = HandoffService(db)

    if state:
        conversations = await service.get_conversations_by_state(
            state,
            limit=limit,
            offset=offset,
        )
    else:
        from sqlalchemy import select

        from app.models.conversation import Conversation

        stmt = (
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await db.execute(stmt)
        conversations = list(result.scalars().all())

    items = [
        ConversationListItem(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            handoff_state=c.handoff_state,
            handoff_operator=c.handoff_operator,
            updated_at=c.updated_at,
            created_at=c.created_at,
        )
        for c in conversations
    ]

    return ConversationListResponse(
        items=items,
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.get("/stream/{conversation_id}")
async def agent_stream(
    conversation_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """客服端 SSE 连接
    
    客服订阅会话消息流，接收用户消息和系统事件。
    """
    service = HandoffService(db)
    conversation = await service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in support_gateway.subscribe_agent(conversation_id, agent_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/connections/{conversation_id}")
async def get_connections(conversation_id: str):
    """获取会话的连接数统计"""
    return support_gateway.get_connection_count(conversation_id)


@router.get("/user-stream/{conversation_id}")
async def user_stream(
    conversation_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """用户端 SSE 连接 - 接收客服消息
    
    用户订阅会话消息流，接收客服消息和系统事件。
    此连接应在进入人工模式时建立，独立于发送消息的请求。
    """
    service = HandoffService(db)
    conversation = await service.get_conversation(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    async def event_generator() -> AsyncGenerator[str, None]:
        async for event in support_gateway.subscribe_user(conversation_id, user_id):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
