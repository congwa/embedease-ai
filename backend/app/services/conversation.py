"""会话服务"""

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.user import UserRepository

logger = get_logger("conversation_service")


class ConversationService:
    """会话服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.user_repo = UserRepository(session)

    async def get_user_conversations(self, user_id: str) -> list[Conversation]:
        """获取用户的所有会话"""
        return await self.conversation_repo.get_by_user_id(user_id)

    async def get_conversation_with_messages(self, conversation_id: str) -> Conversation | None:
        """获取会话及其消息"""
        return await self.conversation_repo.get_with_messages(conversation_id)

    async def create_conversation(self, user_id: str) -> Conversation:
        """创建新会话"""
        # 确保用户存在
        await self.user_repo.get_or_create(user_id)

        conversation_id = str(uuid.uuid4())
        return await self.conversation_repo.create_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title="新对话",
        )

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话"""
        conversation = await self.conversation_repo.get_by_id(conversation_id)
        if conversation:
            await self.conversation_repo.delete(conversation)
            return True
        return False

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        products: str | None = None,
        *,
        message_id: str | None = None,
    ) -> Message:
        """添加消息到会话"""
        message_id = message_id or str(uuid.uuid4())
        message = await self.message_repo.create_message(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            products=products,
        )

        # 如果是用户的第一条消息，更新会话标题
        if role == "user":
            conversation = await self.conversation_repo.get_by_id(conversation_id)
            if conversation and conversation.title == "新对话":
                # 使用消息的前 50 个字符作为标题
                title = content[:50] + ("..." if len(content) > 50 else "")
                await self.conversation_repo.update_title(conversation_id, title)

        return message
