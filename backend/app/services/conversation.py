"""会话服务"""

import re
import uuid
from datetime import datetime
from string import Template
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.agent import Agent
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.tool_call import ToolCall
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.tool_call import ToolCallRepository
from app.repositories.user import UserRepository

logger = get_logger("conversation_service")


class ConversationService:
    """会话服务"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.conversation_repo = ConversationRepository(session)
        self.message_repo = MessageRepository(session)
        self.tool_call_repo = ToolCallRepository(session)
        self.user_repo = UserRepository(session)

    async def get_user_conversations(self, user_id: str) -> list[Conversation]:
        """获取用户的所有会话"""
        return await self.conversation_repo.get_by_user_id(user_id)

    async def get_conversation_with_messages(self, conversation_id: str) -> Conversation | None:
        """获取会话及其消息"""
        return await self.conversation_repo.get_with_messages(conversation_id)

    async def create_conversation(
        self,
        user_id: str,
        agent_id: str | None = None,
        channel: str = "web",
    ) -> Conversation:
        """创建新会话
        
        Args:
            user_id: 用户 ID
            agent_id: Agent ID（可选，用于获取开场白配置）
            channel: 渠道标识（web/support/api）
        """
        # 确保用户存在
        await self.user_repo.get_or_create(user_id)

        conversation_id = str(uuid.uuid4())
        conversation = await self.conversation_repo.create_conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            title="新对话",
            agent_id=agent_id,
        )

        # 处理开场白
        if agent_id:
            await self._handle_greeting(conversation, agent_id, channel)

        return conversation

    async def _handle_greeting(
        self,
        conversation: Conversation,
        agent_id: str,
        channel: str = "web",
    ) -> Message | None:
        """处理开场白消息
        
        Args:
            conversation: 会话实例
            agent_id: Agent ID
            channel: 渠道标识
            
        Returns:
            创建的开场白消息，如果不满足条件则返回 None
        """
        # 获取 Agent 配置
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.session.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent or not agent.greeting_config:
            return None

        config = agent.greeting_config
        if not config.get("enabled"):
            return None

        # 检查触发条件
        trigger = config.get("trigger", "first_visit")
        if trigger == "first_visit" and conversation.greeting_sent:
            return None

        # 获取渠道配置
        channels = config.get("channels", {})
        channel_config = channels.get(channel) or channels.get("default")
        if not channel_config:
            return None

        # 渲染模板
        body = channel_config.get("body", "")
        title = channel_config.get("title", "")
        subtitle = channel_config.get("subtitle", "")

        # 变量替换
        variables = {
            "agent_name": agent.name,
            "current_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        body = self._render_template(body, variables)
        title = self._render_template(title, variables)
        subtitle = self._render_template(subtitle, variables)

        # 组装内容
        content_parts = []
        if title:
            content_parts.append(f"**{title}**")
        if subtitle:
            content_parts.append(f"*{subtitle}*")
        if body:
            content_parts.append(body)
        content = "\n\n".join(content_parts)

        # 构建 extra_metadata
        cta = channel_config.get("cta") or config.get("cta")
        extra_metadata = {
            "channel": channel,
            "delay_ms": config.get("delay_ms", 1000),
            "greeting_config": {
                "title": title,
                "subtitle": subtitle,
                "body": body,
            },
        }
        if cta:
            extra_metadata["cta"] = cta

        # 创建开场白消息
        message = await self.add_message(
            conversation_id=conversation.id,
            role="system",
            content=content,
            message_type="greeting",
            extra_metadata=extra_metadata,
        )

        # 标记已发送
        if trigger == "first_visit":
            await self.conversation_repo.set_greeting_sent(conversation.id, True)

        logger.info(
            "发送开场白消息",
            conversation_id=conversation.id,
            agent_id=agent_id,
            channel=channel,
        )

        return message

    def _render_template(self, template: str, variables: dict[str, str]) -> str:
        """渲染模板变量
        
        支持 {{variable}} 格式的变量替换
        """
        if not template:
            return template

        # 将 {{var}} 转换为 $var 格式
        pattern = r"\{\{(\w+)\}\}"
        converted = re.sub(pattern, r"$\1", template)

        try:
            return Template(converted).safe_substitute(variables)
        except Exception:
            return template

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
        message_type: str = "text",
        extra_metadata: dict[str, Any] | None = None,
        token_count: int | None = None,
        tool_calls_data: list[dict[str, Any]] | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        """添加消息到会话
        
        Args:
            conversation_id: 会话 ID
            role: 角色 (user/assistant/system)
            content: 消息内容
            products: 推荐商品 JSON
            message_id: 消息 ID（可选，自动生成）
            message_type: 消息类型 (text/tool_call/tool_result)
            extra_metadata: 完整消息元数据（含 usage_metadata 等）
            token_count: Token 计数
            tool_calls_data: 工具调用数据列表
            latency_ms: 响应耗时（毫秒）
        """
        message_id = message_id or str(uuid.uuid4())
        message = await self.message_repo.create_message(
            message_id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            products=products,
            message_type=message_type,
            extra_metadata=extra_metadata,
            token_count=token_count,
            latency_ms=latency_ms,
        )

        # 保存工具调用记录
        if tool_calls_data:
            await self.tool_call_repo.batch_create_tool_calls(
                message_id=message_id,
                tool_calls_data=tool_calls_data,
            )
            logger.debug(
                "保存工具调用记录",
                message_id=message_id,
                tool_call_count=len(tool_calls_data),
            )

        # 如果是用户的第一条消息，更新会话标题
        if role == "user":
            conversation = await self.conversation_repo.get_by_id(conversation_id)
            if conversation and conversation.title == "新对话":
                title = content[:50] + ("..." if len(content) > 50 else "")
                await self.conversation_repo.update_title(conversation_id, title)

        return message

    async def add_tool_call(
        self,
        message_id: str,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        tool_call_id: str | None = None,
        status: str = "pending",
    ) -> ToolCall:
        """添加工具调用记录"""
        return await self.tool_call_repo.create_tool_call(
            message_id=message_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_call_id=tool_call_id,
            status=status,
        )

    async def update_tool_call_output(
        self,
        tool_call_id: str,
        tool_output: str,
        status: str = "success",
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> ToolCall | None:
        """更新工具调用结果"""
        return await self.tool_call_repo.update_tool_call_output(
            tool_call_id=tool_call_id,
            tool_output=tool_output,
            status=status,
            error_message=error_message,
            duration_ms=duration_ms,
        )

    async def get_messages_with_tool_calls(
        self,
        conversation_id: str,
    ) -> list[Message]:
        """获取会话消息（含工具调用）"""
        return await self.message_repo.get_by_conversation_id(
            conversation_id,
            include_tool_calls=True,
        )
