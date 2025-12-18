"""聊天 API"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.core.logging import get_logger
from app.schemas.chat import ChatRequest
from app.services.chat_stream import ChatStreamOrchestrator
from app.services.agent.agent import agent_service
from app.services.conversation import ConversationService
from app.services.streaming.sse import encode_sse

router = APIRouter(prefix="/api/v1", tags=["chat"])
logger = get_logger("chat")


@router.post("/chat")
async def chat(
    request_data: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
):
    """流式聊天接口

    使用 SSE (Server-Sent Events) 返回流式响应。

    支持客户端主动中断：
    - 客户端可以通过关闭连接来中断对话生成
    - 后端会检测断开并立即停止 Agent 执行

    事件类型:
    - meta.start: 开始 {"type": "meta.start", "payload": {"assistant_message_id": "...", "user_message_id": "..."}}
    - assistant.delta: 文本增量 {"type": "assistant.delta", "payload": {"delta": "..."}}
    - assistant.products: 商品数据 {"type": "assistant.products", "payload": {"items": [...]}}
    - assistant.final: 完成 {"type": "assistant.final", "payload": {"content": "...", "products": [...], "reasoning": "..."}}
    - error: 错误 {"type": "error", "payload": {"message": "..."}}
    """
    conversation_service = ConversationService(db)

    # 保存用户消息
    user_message = await conversation_service.add_message(
        conversation_id=request_data.conversation_id,
        role="user",
        content=request_data.message,
    )
    logger.info(
        "保存用户消息",
        message_id=user_message.id,
        conversation_id=request_data.conversation_id,
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        """生成 SSE 事件流，支持中断检测"""
        assistant_message_id = str(uuid.uuid4())
        orchestrator = ChatStreamOrchestrator(
            conversation_service=conversation_service,
            agent_service=agent_service,
            conversation_id=request_data.conversation_id,
            user_id=request_data.user_id,
            user_message=request_data.message,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message_id,
            mode=request_data.effective_mode,
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
                # logger.debug(
                #     "发送SSE事件",
                #     event=event,
                # )
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
