"""聊天 API"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_context
from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.models.agent import SuggestedQuestion
from app.models.conversation import HandoffState
from app.schemas.chat import ChatRequest
from app.schemas.suggested_question import (
    SuggestedQuestionPublicItem,
    SuggestedQuestionsPublicResponse,
)
from app.services.chat_stream_adapter import (
    get_chat_stream_orchestrator,
    get_agent_service,
)
from app.services.conversation import ConversationService
from app.services.streaming.sse import encode_sse
from app.services.support.handoff import HandoffService

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = get_logger("chat")


@router.post("/chat")
async def chat(
    request_data: ChatRequest,
    request: Request,
):
    """流式聊天接口

    使用 SSE (Server-Sent Events) 返回流式响应。
    
    SQLite 防死锁优化：
    - 保存用户消息使用独立短事务，快速释放连接
    - 流式响应不持有长连接，工具内部自行创建短事务
    - 避免整个 SSE 流生命周期（可能数十秒）占用数据库连接

    支持客户端主动中断：
    - 客户端可以通过关闭连接来中断对话生成
    - 后端会检测断开并立即停止 Agent 执行

    事件类型:
    - meta.start: 开始 {"type": "meta.start", "payload": {"assistant_message_id": "...", "user_message_id": "..."}}
    - assistant.delta: 文本增量 {"type": "assistant.delta", "payload": {"delta": "..."}}
    - assistant.products: 商品数据 {"type": "assistant.products", "payload": {"items": [...]}}
    - assistant.final: 完成 {"type": "assistant.final", "payload": {"content": "...", "products": [...], "reasoning": "..."}}
    - support.handoff_started: 客服介入 {"type": "support.handoff_started", "payload": {...}}
    - support.human_message: 人工消息 {"type": "support.human_message", "payload": {...}}
    - error: 错误 {"type": "error", "payload": {"message": "..."}}
    """
    # 使用独立短事务保存用户消息和检查状态
    # 避免整个 SSE 流持有数据库连接
    async with get_db_context() as db:
        conversation_service = ConversationService(db)
        handoff_service = HandoffService(db)

        # 检查会话的 handoff 状态
        handoff_state = await handoff_service.get_handoff_state(request_data.conversation_id)
        is_human_mode = handoff_state == HandoffState.HUMAN.value

        # 准备图片元数据
        extra_metadata = None
        message_type = "text"
        if request_data.has_images:
            message_type = "text_with_images"
            extra_metadata = {
                "images": [img.model_dump() for img in request_data.images]  # type: ignore
            }

        # 保存用户消息
        user_message = await conversation_service.add_message(
            conversation_id=request_data.conversation_id,
            role="user",
            content=request_data.message,
            message_type=message_type,
            extra_metadata=extra_metadata,
        )
        # 提取需要的数据，在 session 关闭前获取
        user_message_id = user_message.id
        
    logger.info(
        "保存用户消息",
        message_id=user_message_id,
        conversation_id=request_data.conversation_id,
        is_human_mode=is_human_mode,
    )

    # 发送新消息通知（无论是否人工模式都发送，使用独立短事务）
    async def _notify_new_message():
        async with get_db_context() as notify_db:
            notify_handoff_service = HandoffService(notify_db)
            await notify_handoff_service.notify_new_message(
                conversation_id=request_data.conversation_id,
                user_id=request_data.user_id,
                message_preview=request_data.message[:200],
            )
    asyncio.create_task(_notify_new_message())

    # 如果是人工模式，转发消息给客服端，不走 RAG
    # 架构：发送消息立即返回，用户通过独立的 SSE 订阅接收客服消息
    if is_human_mode:
        # 通过 WebSocket 转发给客服（如果客服在线）
        from app.schemas.websocket import WSAction, WSRole
        from app.services.websocket.handlers.base import build_server_message
        from app.services.websocket.manager import ws_manager

        server_msg = build_server_message(
            action=WSAction.SERVER_MESSAGE,
            payload={
                "message_id": user_message_id,
                "role": "user",
                "content": request_data.message,
                "user_id": request_data.user_id,
            },
            conversation_id=request_data.conversation_id,
        )
        await ws_manager.send_to_role(request_data.conversation_id, WSRole.AGENT, server_msg)

        async def human_mode_response() -> AsyncGenerator[str, None]:
            """人工模式响应 - 立即返回确认，不保持连接"""
            yield encode_sse({
                "type": "meta.start",
                "payload": {
                    "user_message_id": user_message_id,
                    "assistant_message_id": None,
                    "mode": "human",
                },
            })
            yield encode_sse({
                "type": "support.human_mode",
                "payload": {
                    "message": "您的消息已发送给客服",
                },
            })
            # 立即结束流，用户通过独立订阅接收客服消息
            yield encode_sse({
                "type": "assistant.final",
                "payload": {
                    "content": "",
                    "mode": "human",
                },
            })

        return StreamingResponse(
            human_mode_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流，支持中断检测
        
        SQLite 防死锁优化：
        - 使用 NullPool，每个请求都是新连接，不会阻塞连接池
        - WAL 模式允许读写并发
        - 工具内部使用 get_db_context() 创建独立短事务
        - db=None 让工具不复用外层 session，避免嵌套事务
        """
        assistant_message_id = str(uuid.uuid4())
        
        # 为保存 assistant 消息创建独立 session
        # 注意：db=None 让工具自行创建短事务，避免嵌套
        async with get_db_context() as stream_db:
            stream_conversation_service = ConversationService(stream_db)
            # 获取适配后的服务
            agent_service = get_agent_service()
            OrchestratorClass = get_chat_stream_orchestrator()
            
            orchestrator = OrchestratorClass(
                conversation_service=stream_conversation_service,
                agent_service=agent_service,
                conversation_id=request_data.conversation_id,
                user_id=request_data.user_id,
                user_message=request_data.message,
                user_message_id=user_message_id,
                assistant_message_id=assistant_message_id,
                agent_id=request_data.agent_id,
                images=request_data.images,
                db=None,  # 不传递 session，让工具自行创建短事务
            )

            try:
                async for event in orchestrator.run():
                    # 检测客户端是否断开连接
                    if await request.is_disconnected():
                        logger.info(
                            "客户端断开连接，中止生成（不保存消息）",
                            conversation_id=request_data.conversation_id,
                            assistant_message_id=assistant_message_id,
                        )
                        break
                    yield encode_sse(event)
            except asyncio.CancelledError:
                logger.info(
                    "生成被取消（不保存消息）",
                    conversation_id=request_data.conversation_id,
                    assistant_message_id=assistant_message_id,
                )
                # 用户主动停止属于正常路径：不保存不完整的消息，直接返回
                return
            except Exception as e:
                logger.error("生成过程出错", error=str(e), exc_info=True)
                yield encode_sse({"type": "error", "payload": {"message": str(e)}})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ========== Suggested Questions (Public) ==========


@router.get("/agents/{agent_id}/suggested-questions", response_model=SuggestedQuestionsPublicResponse)
async def get_public_suggested_questions(
    agent_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取 Agent 的推荐问题（公开接口）

    返回按展示位置分组的问题列表，用于前端展示。
    自动过滤：
    - 未启用的问题
    - 不在生效时间范围内的问题
    """
    now = datetime.now(timezone.utc)

    # 查询启用的问题
    stmt = (
        select(SuggestedQuestion)
        .where(
            SuggestedQuestion.agent_id == agent_id,
            SuggestedQuestion.enabled == True,  # noqa: E712
        )
        .order_by(SuggestedQuestion.weight.desc(), SuggestedQuestion.click_count.desc())
    )

    result = await db.execute(stmt)
    questions = result.scalars().all()

    # 过滤时间范围
    valid_questions = []
    for q in questions:
        # 检查开始时间
        if q.start_time and q.start_time > now:
            continue
        # 检查结束时间
        if q.end_time and q.end_time < now:
            continue
        valid_questions.append(q)

    # 按展示位置分组
    welcome_questions: list[SuggestedQuestionPublicItem] = []
    input_questions: list[SuggestedQuestionPublicItem] = []

    for q in valid_questions:
        item = SuggestedQuestionPublicItem(id=q.id, question=q.question)
        if q.display_position in ("welcome", "both"):
            welcome_questions.append(item)
        if q.display_position in ("input", "both"):
            input_questions.append(item)

    return SuggestedQuestionsPublicResponse(
        welcome=welcome_questions[:6],  # 欢迎区最多6个
        input=input_questions[:4],  # 输入框上方最多4个
    )


@router.post("/suggested-questions/{question_id}/click", status_code=204)
async def record_question_click(
    question_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """记录推荐问题点击

    用于统计热门问题，优化推荐排序。
    """
    stmt = select(SuggestedQuestion).where(SuggestedQuestion.id == question_id)
    result = await db.execute(stmt)
    question = result.scalar_one_or_none()

    if not question:
        raise HTTPException(status_code=404, detail="推荐问题不存在")

    question.click_count += 1
    await db.flush()

    logger.debug("记录推荐问题点击", question_id=question_id, click_count=question.click_count)
