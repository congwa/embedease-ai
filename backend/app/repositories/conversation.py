"""会话 Repository"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """会话数据访问"""

    model = Conversation

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_user_id(self, user_id: str) -> list[Conversation]:
        """获取用户的所有会话"""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_with_messages(self, conversation_id: str) -> Conversation | None:
        """获取会话及其消息"""
        result = await self.session.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        return result.scalar_one_or_none()

    async def create_conversation(
        self,
        conversation_id: str,
        user_id: str,
        title: str = "新对话",
        agent_id: str | None = None,
    ) -> Conversation:
        """创建会话"""
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title=title,
            agent_id=agent_id,
        )
        return await self.create(conversation)

    async def set_greeting_sent(
        self,
        conversation_id: str,
        sent: bool = True,
    ) -> Conversation | None:
        """设置开场白已发送标记"""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.greeting_sent = sent
            await self.update(conversation)
        return conversation

    async def update_title(self, conversation_id: str, title: str) -> Conversation | None:
        """更新会话标题"""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.title = title[:200]  # 截断标题
            await self.update(conversation)
        return conversation

    async def set_user_online(
        self,
        conversation_id: str,
        online: bool,
    ) -> Conversation | None:
        """设置用户在线状态"""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.user_online = online
            if online:
                conversation.user_last_online_at = datetime.now()
            else:
                conversation.user_last_online_at = datetime.now()
            await self.update(conversation)
        return conversation

    async def set_agent_online(
        self,
        conversation_id: str,
        online: bool,
        agent_id: str | None = None,
    ) -> Conversation | None:
        """设置客服在线状态"""
        conversation = await self.get_by_id(conversation_id)
        if conversation:
            conversation.agent_online = online
            if online:
                conversation.agent_last_online_at = datetime.now()
                conversation.current_agent_id = agent_id
            else:
                conversation.agent_last_online_at = datetime.now()
                conversation.current_agent_id = None
            await self.update(conversation)
        return conversation

    async def get_online_status(
        self,
        conversation_id: str,
    ) -> dict:
        """获取会话的在线状态"""
        conversation = await self.get_by_id(conversation_id)
        if not conversation:
            return {
                "user_online": False,
                "user_last_online_at": None,
                "agent_online": False,
                "agent_last_online_at": None,
                "current_agent_id": None,
            }
        return {
            "user_online": conversation.user_online,
            "user_last_online_at": conversation.user_last_online_at,
            "agent_online": conversation.agent_online,
            "agent_last_online_at": conversation.agent_last_online_at,
            "current_agent_id": conversation.current_agent_id,
        }
