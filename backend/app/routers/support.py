"""客服支持 API

提供：
- 客服介入/结束 API
- 人工消息发送 API
- 会话状态查询 API
- 客服端 SSE 连接
"""

import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.repositories.agent_score_snapshot import AgentScoreSnapshotRepository
from app.repositories.complaint_ticket import ComplaintTicketRepository
from app.repositories.message import MessageRepository
from app.schemas.support import (
    AgentScoreSnapshotListResponse,
    AgentScoreSnapshotSchema,
    ConversationListItem,
    ConversationListResponse,
    ConversationStateResponse,
    ConversationTicketsResponse,
    HandoffEndRequest,
    HandoffResponse,
    HandoffStartRequest,
    HumanMessageRequest,
    HumanMessageResponse,
    SupportStatsResponse,
    TicketActionResponse,
    TicketDetailSchema,
    TicketReopenRequest,
    TicketResolveRequest,
)
from app.schemas.websocket import WSAction, WSRole
from app.services.complaint.handoff_service import ComplaintHandoffService
from app.services.complaint.ticket_service import TicketService
from app.services.support.handoff import HandoffService
from app.services.support.heat_score import get_conversations_with_heat, get_support_stats
from app.services.support.state_service import SupportStateService
from app.services.websocket.handlers.base import build_server_message
from app.services.websocket.manager import ws_manager

router = APIRouter(prefix="/api/v1/support", tags=["support"])
logger = get_logger("router.support")


async def _broadcast_ticket_state_update(
    *,
    db: AsyncSession,
    ticket_id: str,
) -> TicketDetailSchema:
    """广播问题单与会话状态更新。

    这个内部方法服务于 support 侧的 resolve / reopen 操作，确保人工操作后
    工作台和用户侧立即收到新的 ticket 快照。
    """
    support_state_service = SupportStateService(db)
    ticket_repo = ComplaintTicketRepository(db)
    ticket_service = TicketService(db)

    ticket = await ticket_repo.get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="问题单不存在")

    detail = await support_state_service.build_ticket_detail(ticket)
    ticket_message = build_server_message(
        action=WSAction.SERVER_TICKET_UPDATED,
        payload={"ticket": ticket_service.build_stream_summary(ticket).model_dump(mode="json")},
        conversation_id=ticket.conversation_id,
    )
    await ws_manager.broadcast_to_conversation(ticket.conversation_id, ticket_message)

    state_payload = await support_state_service.build_websocket_state_payload(ticket.conversation_id)
    state_message = build_server_message(
        action=WSAction.SERVER_CONVERSATION_STATE,
        payload=state_payload,
        conversation_id=ticket.conversation_id,
    )
    await ws_manager.broadcast_to_conversation(ticket.conversation_id, state_message)

    queue_changed_message = build_server_message(
        action=WSAction.SERVER_SUPPORT_QUEUE_CHANGED,
        payload={
            "conversation_id": ticket.conversation_id,
            "handoff_state": state_payload["handoff_state"],
            "reason": detail.status,
            "source": "support_ticket_state_update",
        },
        conversation_id=ticket.conversation_id,
    )
    await ws_manager.broadcast_to_role_global(WSRole.AGENT, queue_changed_message)
    return detail


@router.post("/handoff/{conversation_id}", response_model=HandoffResponse)
async def start_handoff(
    conversation_id: str,
    request: HandoffStartRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """开始客服介入
    
    将会话切换到人工客服模式，后续用户消息将不再触发 RAG。
    """
    result = await ComplaintHandoffService(db).accept_handoff(
        conversation_id=conversation_id,
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

        logger.info(
            "客服介入通知已发送",
            conversation_id=conversation_id,
            operator=request.operator,
            ws_sent=ws_sent,
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
    result = await ComplaintHandoffService(db).finish_handoff(
        conversation_id=conversation_id,
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

        logger.info(
            "客服结束通知已发送",
            conversation_id=conversation_id,
            operator=request.operator,
            ws_sent=ws_sent,
        )

    return HandoffResponse(**result)


@router.get("/handoff/{conversation_id}", response_model=ConversationStateResponse)
async def get_handoff_state(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取客服详情页所需的完整会话状态。

    这个接口不再只返回 handoff_state，还会返回当前主问题单和最近 review 摘要。
    """
    support_state_service = SupportStateService(db)
    service = HandoffService(db)
    conversation = await service.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    unread_count = await MessageRepository(db).get_unread_count(conversation_id, "agent")
    state = await support_state_service.build_conversation_state(
        conversation,
        unread_count=unread_count,
        peer_last_online_at=conversation.user_last_online_at,
    )
    return state


@router.get(
    "/conversations/{conversation_id}/active-ticket",
    response_model=TicketDetailSchema,
)
async def get_active_ticket(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话当前主问题单详情。

    这个接口服务于客服工作台从会话视角切到问题单视角时，直接读取当前主活动 ticket。
    """
    detail = await SupportStateService(db).get_active_ticket_detail(conversation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="当前会话没有主问题单")
    return detail


@router.get(
    "/conversations/{conversation_id}/tickets",
    response_model=ConversationTicketsResponse,
)
async def list_conversation_tickets(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话下全部问题单摘要。

    这个接口服务于客服查看当前会话历史 ticket，判断是否需要回溯旧问题单。
    """
    support_state_service = SupportStateService(db)
    tickets = await support_state_service.list_ticket_summaries_by_conversation(conversation_id)
    return ConversationTicketsResponse(
        conversation_id=conversation_id,
        items=tickets,
        total=len(tickets),
    )


@router.get("/tickets/{ticket_id}", response_model=TicketDetailSchema)
async def get_ticket_detail(
    ticket_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取单张问题单详情。

    这个接口服务于客服在工作台单独打开历史或当前 ticket 时查看完整业务上下文。
    """
    detail = await SupportStateService(db).get_ticket_detail(ticket_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="问题单不存在")
    return detail


@router.post("/tickets/{ticket_id}/resolve", response_model=TicketActionResponse)
async def resolve_ticket(
    ticket_id: str,
    request: TicketResolveRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """手动解决问题单。

    这个接口服务于人工客服确认问题已经处理完成，并把 ticket 明确标记为 resolved。
    """
    ticket_repo = ComplaintTicketRepository(db)
    ticket_service = TicketService(db)
    ticket = await ticket_repo.get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="问题单不存在")

    summary = request.summary or f"客服 {request.operator or 'unknown'} 手动标记问题已解决"
    ticket = await ticket_service.mark_resolved(ticket, summary=summary)
    ticket = await ticket_service.append_timeline_entry(
        ticket,
        event_type="support.ticket.resolved",
        summary=summary,
        extra={"operator": request.operator},
    )
    detail = await _broadcast_ticket_state_update(db=db, ticket_id=ticket.id)
    return TicketActionResponse(success=True, ticket=detail)


@router.post("/tickets/{ticket_id}/reopen", response_model=TicketActionResponse)
async def reopen_ticket(
    ticket_id: str,
    request: TicketReopenRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """手动重开问题单。

    这个接口服务于人工客服发现问题并未真正解决时，把 ticket 重新交回 AI 主链路继续推进。
    """
    ticket_repo = ComplaintTicketRepository(db)
    ticket_service = TicketService(db)
    ticket = await ticket_repo.get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="问题单不存在")

    reopen_reason = request.reason or f"客服 {request.operator or 'unknown'} 手动重开问题单"
    ticket = await ticket_service.reopen_ticket(
        ticket,
        reason=reopen_reason,
        agent_tag="resolution_execution_agent",
        node_key="resolution",
    )
    detail = await _broadcast_ticket_state_update(db=db, ticket_id=ticket.id)
    return TicketActionResponse(success=True, ticket=detail)


@router.post("/message/{conversation_id}", response_model=HumanMessageResponse)
async def send_human_message(
    conversation_id: str,
    request: HumanMessageRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """客服发送消息。

    这个 REST 入口是客服工作台的备用发消息链路。它必须与 WebSocket 入口保持同一套
    送达语义和队列刷新行为，避免前端切换发送通道后出现“用户离线却显示已送达”的错账。
    """
    # 验证：必须有内容或图片
    if not request.content.strip() and not request.has_images:
        return HumanMessageResponse(
            success=False,
            error="发送失败：消息内容和图片不能同时为空",
        )

    service = HandoffService(db)
    
    # 准备图片数据
    images_data = None
    if request.has_images:
        images_data = [img.model_dump() for img in request.images]  # type: ignore
    
    message = await service.add_human_message(
        conversation_id,
        content=request.content,
        operator=request.operator,
        images=images_data,
    )

    if not message:
        return HumanMessageResponse(
            success=False,
            error="发送失败：会话不存在或未在人工模式",
        )

    # 通过 WebSocket 发送给用户，并以真实送达结果作为消息状态来源。
    from datetime import datetime
    delivered_at = None
    is_delivered = False
    ws_payload = {
        "message_id": message.id,
        "role": "human_agent",
        "content": message.content,
        "created_at": message.created_at.isoformat(),
        "operator": request.operator,
    }
    if images_data:
        ws_payload["images"] = images_data

    user_ws_msg = build_server_message(
        action=WSAction.SERVER_MESSAGE,
        payload=ws_payload,
        conversation_id=conversation_id,
    )
    ws_sent = await ws_manager.send_to_role(conversation_id, WSRole.USER, user_ws_msg)
    if ws_sent > 0:
        await MessageRepository(db).mark_as_delivered([message.id])
        delivered_at = datetime.now().isoformat()
        is_delivered = True

    agent_ws_payload = {
        **ws_payload,
        "is_delivered": is_delivered,
        "delivered_at": delivered_at,
    }
    agent_ws_msg = build_server_message(
        action=WSAction.SERVER_MESSAGE,
        payload=agent_ws_payload,
        conversation_id=conversation_id,
    )
    await ws_manager.send_to_role(conversation_id, WSRole.AGENT, agent_ws_msg)

    queue_changed_message = build_server_message(
        action=WSAction.SERVER_SUPPORT_QUEUE_CHANGED,
        payload={
            "conversation_id": conversation_id,
            "handoff_state": "human",
            "reason": "agent_message",
            "source": "support_rest_message",
            "changed_at": message.created_at.isoformat(),
        },
        conversation_id=conversation_id,
    )
    await ws_manager.broadcast_to_role_global(WSRole.AGENT, queue_changed_message)

    return HumanMessageResponse(
        success=True,
        message_id=message.id,
        conversation_id=conversation_id,
        created_at=message.created_at.isoformat(),
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(
    state: str | None = None,
    sort_by: str = "heat",  # heat | time
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话列表（支持热度排序）
    
    Args:
        state: 筛选状态（ai/pending/human），留空返回全部
        sort_by: 排序方式 - heat(热度优先) 或 time(时间优先)
        limit: 分页大小
        offset: 分页偏移
    """
    start = time.perf_counter()
    logger.debug(f"API /conversations: 开始 state={state}, sort_by={sort_by}, limit={limit}, offset={offset}")
    
    items_data, total = await get_conversations_with_heat(
        db,
        state=state,
        sort_by=sort_by,
        limit=limit,
        offset=offset,
    )
    logger.debug(f"API /conversations: get_conversations_with_heat 完成，耗时 {(time.perf_counter() - start) * 1000:.2f}ms")

    items = [
        ConversationListItem(
            id=c["id"],
            user_id=c["user_id"],
            title=c["title"],
            conversation_mode=c["conversation_mode"],
            handoff_state=c["handoff_state"],
            handoff_operator=c["handoff_operator"],
            handoff_reason=c["handoff_reason"],
            user_online=c["user_online"],
            updated_at=c["updated_at"],
            created_at=c["created_at"],
            heat_score=c["heat_score"],
            unread_count=c["unread_count"],
            current_ticket_id=c["current_ticket_id"],
            ticket_status=c["ticket_status"],
            primary_issue_tag=c["primary_issue_tag"],
            current_agent_tag=c["current_agent_tag"],
            risk_level=c["risk_level"],
            review_status=c["review_status"],
            review_score=c["review_score"],
            secondary_issue_detected=c["secondary_issue_detected"],
            last_message=c["last_message"],
            last_message_at=c["last_message_at"],
            last_message_role=c["last_message_role"],
        )
        for c in items_data
    ]

    response = ConversationListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )
    logger.debug(f"API /conversations: 全部完成，总耗时 {(time.perf_counter() - start) * 1000:.2f}ms")
    return response


@router.get("/stats", response_model=SupportStatsResponse)
async def get_stats(
    db: AsyncSession = Depends(get_db_session),
):
    """获取客服统计数据（用于红点提醒）
    
    Returns:
        pending_count: 等待接入数
        human_count: 人工服务中数
        total_unread: 总未读消息数
        high_heat_count: 高热会话数
    """
    start = time.perf_counter()
    logger.debug("API /stats: 开始")
    
    stats = await get_support_stats(db)
    
    logger.debug(f"API /stats: 全部完成，总耗时 {(time.perf_counter() - start) * 1000:.2f}ms")
    return SupportStatsResponse(**stats)


@router.get("/agent-score-snapshots", response_model=AgentScoreSnapshotListResponse)
async def list_agent_score_snapshots(
    window_type: str = "daily",
    limit: int = 20,
    db: AsyncSession = Depends(get_db_session),
):
    """获取最近一批 Agent 绩效快照。

    这个接口服务于后续运营后台和管理视图，让前端直接读取 scheduler 统计产出的快照结果，
    不需要在请求时临时全量扫描 task/review 表。
    """
    snapshot_repo = AgentScoreSnapshotRepository(db)
    snapshots = await snapshot_repo.list_by_window_type(window_type, limit=limit)
    return AgentScoreSnapshotListResponse(
        items=[
            AgentScoreSnapshotSchema.model_validate(snapshot, from_attributes=True)
            for snapshot in snapshots
        ],
        total=len(snapshots),
        window_type=window_type,
    )


@router.get("/connections/{conversation_id}")
async def get_connections(conversation_id: str):
    """获取会话的 WebSocket 连接数统计"""
    conns = ws_manager.get_connections_by_conversation(conversation_id)
    user_count = sum(1 for c in conns if c.role.value == "user")
    agent_count = sum(1 for c in conns if c.role.value == "agent")
    return {"user": user_count, "agent": agent_count, "total": len(conns)}
