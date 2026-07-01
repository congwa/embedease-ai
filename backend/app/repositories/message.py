"""消息 Repository"""

from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """消息数据访问"""

    model = Message

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_conversation_id(
        self,
        conversation_id: str,
        include_tool_calls: bool = False,
    ) -> list[Message]:
        """获取会话的所有消息
        
        Args:
            conversation_id: 会话 ID
            include_tool_calls: 是否预加载工具调用记录
        """
        query = select(Message).where(Message.conversation_id == conversation_id)
        if include_tool_calls:
            query = query.options(selectinload(Message.tool_calls))
        query = query.order_by(Message.created_at)
        result = await self.session.execute(query)
        return list(result.scalars().unique().all())

    async def get_paginated(
        self,
        conversation_id: str,
        limit: int = 50,
        cursor: str | None = None,
        include_tool_calls: bool = False,
    ) -> tuple[list[Message], str | None, bool]:
        """分页获取会话消息（基于游标，按时间倒序）
        
        Args:
            conversation_id: 会话 ID
            limit: 每页数量
            cursor: 游标（上一页最后一条消息的 ID）
            include_tool_calls: 是否预加载工具调用记录
            
        Returns:
            (消息列表, 下一页游标, 是否还有更多)
        """
        query = select(Message).where(Message.conversation_id == conversation_id)

        # 如果有游标，获取游标消息的创建时间作为分页基准
        if cursor:
            cursor_msg = await self.get_by_id(cursor)
            if cursor_msg:
                query = query.where(Message.created_at < cursor_msg.created_at)

        if include_tool_calls:
            query = query.options(selectinload(Message.tool_calls))

        # 按时间倒序（最新消息在前），多取一条判断是否还有更多
        query = query.order_by(Message.created_at.desc()).limit(limit + 1)
        result = await self.session.execute(query)
        messages = list(result.scalars().unique().all())

        # 判断是否还有更多
        has_more = len(messages) > limit
        if has_more:
            messages = messages[:limit]

        # 返回时反转为正序（旧消息在前）
        messages.reverse()

        # 下一页游标为当前页最早一条消息的 ID
        next_cursor = messages[0].id if messages and has_more else None

        return messages, next_cursor, has_more

    async def create_message(
        self,
        message_id: str,
        conversation_id: str,
        role: str,
        content: str,
        products: str | None = None,
        is_delivered: bool = False,
        message_type: str = "text",
        extra_metadata: dict[str, Any] | None = None,
        token_count: int | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        """创建消息
        
        Args:
            message_id: 消息 ID
            conversation_id: 会话 ID
            role: 角色
            content: 内容
            products: 推荐商品 JSON
            is_delivered: 是否已送达
            message_type: 消息类型 (text/tool_call/tool_result/multimodal_image)
            extra_metadata: 完整消息元数据（含 tool_calls、usage_metadata 等）
            token_count: Token 计数
        """
        message = Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            products=products,
            is_delivered=is_delivered,
            delivered_at=datetime.now() if is_delivered else None,
            message_type=message_type,
            extra_metadata=extra_metadata,
            token_count=token_count,
            latency_ms=latency_ms,
        )
        return await self.create(message)

    async def get_undelivered_messages(
        self,
        conversation_id: str,
        target_role: str,
    ) -> list[Message]:
        """获取未送达给目标角色的消息
        
        Args:
            conversation_id: 会话 ID
            target_role: 目标角色 ("user" 获取发给用户的未送达消息, "agent" 获取发给客服的未送达消息)
        """
        # 发给用户的消息: role in (assistant, human_agent, system)
        # 发给客服的消息: role = user
        if target_role == "user":
            role_filter = Message.role.in_(["assistant", "human_agent", "system"])
        else:
            role_filter = Message.role == "user"

        result = await self.session.execute(
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.is_delivered.is_(False),
                    role_filter,
                )
            )
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())

    async def mark_as_delivered(
        self,
        message_ids: list[str],
    ) -> int:
        """标记消息为已送达"""
        now = datetime.now()
        count = 0
        for msg_id in message_ids:
            message = await self.get_by_id(msg_id)
            if message and not message.is_delivered:
                message.is_delivered = True
                message.delivered_at = now
                await self.update(message)
                count += 1
        return count

    async def mark_as_read(
        self,
        message_ids: list[str],
        read_by: str,
    ) -> tuple[int, datetime]:
        """标记消息为已读
        
        Returns:
            (更新数量, 已读时间)
        """
        now = datetime.now()
        count = 0
        for msg_id in message_ids:
            message = await self.get_by_id(msg_id)
            if message and message.read_at is None:
                message.read_at = now
                message.read_by = read_by
                await self.update(message)
                count += 1
        return count, now

    async def get_unread_count(
        self,
        conversation_id: str,
        target_role: str,
    ) -> int:
        """获取未读消息数量
        
        Args:
            target_role: 目标角色，统计发给该角色的未读消息数
        """
        if target_role == "user":
            role_filter = Message.role.in_(["assistant", "human_agent", "system"])
        else:
            role_filter = Message.role == "user"

        # 这里必须用 SQL 的 IS NULL，而不是 Python 的 `is None`，
        # 否则客服工作台会把未读数统计成错误结果。
        result = await self.session.execute(
            select(func.count())
            .select_from(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.read_at.is_(None),
                    role_filter,
                )
            )
        )
        return result.scalar() or 0

    # ========== 撤回/编辑相关方法 ==========

    async def withdraw_message(
        self,
        message_id: str,
        operator: str,
    ) -> Message | None:
        """撤回消息
        
        Args:
            message_id: 消息 ID
            operator: 操作人（客服 ID）
            
        Returns:
            更新后的消息，如果消息不存在或已撤回则返回 None
        """
        message = await self.get_by_id(message_id)
        if not message or message.is_withdrawn:
            return None
        
        now = datetime.now()
        message.is_withdrawn = True
        message.withdrawn_at = now
        message.withdrawn_by = operator
        await self.update(message)
        return message

    async def edit_message(
        self,
        message_id: str,
        new_content: str,
        operator: str,
    ) -> Message | None:
        """编辑消息内容
        
        Args:
            message_id: 消息 ID
            new_content: 新内容
            operator: 操作人（客服 ID）
            
        Returns:
            更新后的消息，如果消息不存在或已撤回则返回 None
        """
        message = await self.get_by_id(message_id)
        if not message or message.is_withdrawn:
            return None
        
        now = datetime.now()
        # 首次编辑时保存原始内容
        if not message.is_edited:
            message.original_content = message.content
        
        message.content = new_content
        message.is_edited = True
        message.edited_at = now
        message.edited_by = operator
        await self.update(message)
        return message

    async def get_messages_after(
        self,
        conversation_id: str,
        after_message_id: str,
    ) -> list[Message]:
        """获取指定消息之后的所有消息
        
        Args:
            conversation_id: 会话 ID
            after_message_id: 起始消息 ID（不包含）
            
        Returns:
            后续消息列表
        """
        # 先获取参考消息的创建时间
        ref_message = await self.get_by_id(after_message_id)
        if not ref_message:
            return []
        
        result = await self.session.execute(
            select(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.created_at > ref_message.created_at,
                )
            )
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())

    async def delete_messages(
        self,
        message_ids: list[str],
    ) -> int:
        """删除消息
        
        Args:
            message_ids: 要删除的消息 ID 列表
            
        Returns:
            删除的消息数量
        """
        count = 0
        for msg_id in message_ids:
            message = await self.get_by_id(msg_id)
            if message:
                await self.session.delete(message)
                count += 1
        await self.session.flush()
        return count
