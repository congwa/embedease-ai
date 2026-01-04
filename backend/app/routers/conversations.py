"""会话 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    MessageResponse,
    ToolCallResponse,
)
from app.services.conversation import ConversationService

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def get_conversations(
    user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """获取用户的所有会话"""
    service = ConversationService(db)
    conversations = await service.get_user_conversations(user_id)
    return conversations


@router.post("", response_model=ConversationResponse)
async def create_conversation(
    request: ConversationCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """创建新会话"""
    service = ConversationService(db)
    conversation = await service.create_conversation(request.user_id)
    return conversation


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: str,
    include_tool_calls: bool = False,
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话详情（包含消息）
    
    Args:
        conversation_id: 会话 ID
        include_tool_calls: 是否包含工具调用详情
    """
    service = ConversationService(db)

    if include_tool_calls:
        # 获取带工具调用的消息
        conversation = await service.conversation_repo.get_by_id(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        msg_list = await service.get_messages_with_tool_calls(conversation_id)
    else:
        conversation = await service.get_conversation_with_messages(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        msg_list = conversation.messages

    # 转换消息格式
    messages = []
    for msg in msg_list:
        tool_calls_resp = []
        if include_tool_calls and hasattr(msg, "tool_calls") and msg.tool_calls:
            tool_calls_resp = [
                ToolCallResponse(
                    id=tc.id,
                    tool_call_id=tc.tool_call_id,
                    tool_name=tc.tool_name,
                    tool_input=tc.tool_input,
                    tool_output=tc.tool_output,
                    status=tc.status,
                    error_message=tc.error_message,
                    duration_ms=tc.duration_ms,
                    created_at=tc.created_at,
                )
                for tc in msg.tool_calls
            ]

        messages.append(
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                products=msg.products,
                message_type=getattr(msg, "message_type", "text"),
                extra_metadata=getattr(msg, "extra_metadata", None),
                token_count=getattr(msg, "token_count", None),
                tool_calls=tool_calls_resp,
                created_at=msg.created_at,
            )
        )

    return ConversationWithMessages(
        id=conversation.id,
        user_id=conversation.user_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """删除会话"""
    service = ConversationService(db)
    success = await service.delete_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")

    return {"success": True}
