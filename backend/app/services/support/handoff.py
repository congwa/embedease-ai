"""客服介入状态管理服务

负责：
- 管理会话的 handoff_state 状态机
- 提供介入、结束、查询 API
- 与通知服务联动
"""

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.conversation import Conversation, HandoffState
from app.models.message import Message
from app.services.support.notification.dispatcher import notification_dispatcher

logger = get_logger("support.handoff")


class HandoffService:
    """客服介入状态管理服务
    
    状态机：
        AI -> PENDING -> HUMAN -> AI
        AI -> HUMAN -> AI（运营直接介入）
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """获取会话"""
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_handoff_state(self, conversation_id: str) -> str | None:
        """获取会话的 handoff 状态"""
        conversation = await self.get_conversation(conversation_id)
        if conversation:
            return conversation.handoff_state
        return None

    async def is_human_mode(self, conversation_id: str) -> bool:
        """检查会话是否处于人工客服模式"""
        state = await self.get_handoff_state(conversation_id)
        return state == HandoffState.HUMAN.value

    async def start_handoff(
        self,
        conversation_id: str,
        *,
        operator: str,
        reason: str = "",
    ) -> dict[str, Any]:
        """开始人工介入
        
        Args:
            conversation_id: 会话 ID
            operator: 介入的客服标识（用户名/ID）
            reason: 介入原因
            
        Returns:
            操作结果
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return {"success": False, "error": "会话不存在"}

        if conversation.handoff_state == HandoffState.HUMAN.value:
            return {
                "success": False,
                "error": "会话已在人工模式",
                "current_operator": conversation.handoff_operator,
            }

        now = datetime.now()
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                handoff_state=HandoffState.HUMAN.value,
                handoff_operator=operator,
                handoff_reason=reason,
                handoff_at=now,
                updated_at=now,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(
            "客服介入成功",
            conversation_id=conversation_id,
            operator=operator,
            reason=reason,
        )

        return {
            "success": True,
            "conversation_id": conversation_id,
            "operator": operator,
            "handoff_at": now.isoformat(),
            "handoff_state": HandoffState.HUMAN.value,  # 保底：返回最新状态
        }

    async def end_handoff(
        self,
        conversation_id: str,
        *,
        operator: str,
        summary: str = "",
    ) -> dict[str, Any]:
        """结束人工介入，恢复 AI 模式
        
        Args:
            conversation_id: 会话 ID
            operator: 操作的客服标识
            summary: 客服总结（可选，会作为系统消息保存）
            
        Returns:
            操作结果
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return {"success": False, "error": "会话不存在"}

        if conversation.handoff_state != HandoffState.HUMAN.value:
            return {"success": False, "error": "会话未在人工模式"}

        now = datetime.now()

        if summary:
            import uuid
            summary_message = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role="system",
                content=f"[客服总结] {summary}",
                created_at=now,
            )
            self.session.add(summary_message)

        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(
                handoff_state=HandoffState.AI.value,
                handoff_operator=None,
                handoff_reason=None,
                handoff_at=None,
                updated_at=now,
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(
            "客服介入结束",
            conversation_id=conversation_id,
            operator=operator,
            has_summary=bool(summary),
        )

        return {
            "success": True,
            "conversation_id": conversation_id,
            "ended_by": operator,
            "handoff_state": HandoffState.AI.value,  # 保底：返回最新状态
        }

    async def update_notification_time(self, conversation_id: str) -> None:
        """更新最后通知时间"""
        now = datetime.now()
        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_notification_at=now)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def notify_new_message(
        self,
        conversation_id: str,
        user_id: str,
        message_preview: str,
        *,
        entry_page: str = "",
    ) -> None:
        """通知新消息（用户发话时调用）
        
        会更新 last_notification_at 并发送通知。
        """
        await self.update_notification_time(conversation_id)

        await notification_dispatcher.notify_new_message(
            conversation_id=conversation_id,
            user_id=user_id,
            message_preview=message_preview,
            entry_page=entry_page,
        )

    async def get_conversations_by_state(
        self,
        state: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """按状态获取会话列表"""
        stmt = (
            select(Conversation)
            .where(Conversation.handoff_state == state)
            .order_by(Conversation.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_human_conversations(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Conversation]:
        """获取当前所有人工客服会话"""
        return await self.get_conversations_by_state(
            HandoffState.HUMAN.value,
            limit=limit,
            offset=offset,
        )

    async def add_human_message(
        self,
        conversation_id: str,
        content: str,
        *,
        operator: str,
        images: list[dict[str, Any]] | None = None,
    ) -> Message | None:
        """添加人工客服消息
        
        Args:
            conversation_id: 会话 ID
            content: 消息内容
            operator: 客服标识
            images: 图片附件列表
            
        Returns:
            创建的消息，如果会话不在人工模式则返回 None
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            logger.warning("添加人工消息失败：会话不存在", conversation_id=conversation_id)
            return None

        if conversation.handoff_state != HandoffState.HUMAN.value:
            logger.warning(
                "添加人工消息失败：会话未在人工模式",
                conversation_id=conversation_id,
                current_state=conversation.handoff_state,
            )
            return None

        # 准备图片元数据
        message_type = "text_with_images" if images else "text"
        extra_metadata = {"images": images, "operator": operator} if images else {"operator": operator}

        import uuid
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role="human_agent",
            content=content,
            message_type=message_type,
            extra_metadata=extra_metadata,
            created_at=datetime.now(),
        )
        self.session.add(message)

        stmt = (
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(updated_at=datetime.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()

        logger.info(
            "人工客服消息已添加",
            conversation_id=conversation_id,
            message_id=message.id,
            operator=operator,
        )

        return message
