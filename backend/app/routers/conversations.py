"""会话 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    MessageResponse,
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
    db: AsyncSession = Depends(get_db_session),
):
    """获取会话详情（包含消息）"""
    service = ConversationService(db)
    conversation = await service.get_conversation_with_messages(conversation_id)

    if conversation is None:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 转换消息格式
    messages = [
        MessageResponse(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            products=msg.products,
            created_at=msg.created_at,
        )
        for msg in conversation.messages
    ]

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
