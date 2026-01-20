"""滑动窗口中间件

在模型调用前裁剪消息历史，保留最近的 N 条消息或 N 个 Token。
使用 langchain_core.messages.trim_messages 实现。
"""

from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState
from langchain_core.messages import AnyMessage, trim_messages
from langgraph.runtime import Runtime

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("middleware.sliding_window")


class SlidingWindowMiddleware(AgentMiddleware):
    """滑动窗口中间件

    在模型调用前裁剪消息历史，支持两种策略：
    1. 基于消息数量：保留最近的 N 条消息
    2. 基于 Token 数量：保留最近的 N 个 Token

    使用 langchain_core.messages.trim_messages 实现，确保：
    - 保留 SystemMessage（include_system=True）
    - 从 HumanMessage 开始（start_on="human"）
    - 使用 "last" 策略保留最新消息
    """

    def __init__(
        self,
        strategy: str = "messages",
        max_messages: int = 50,
        max_tokens: int = 8000,
        include_system: bool = True,
        start_on_human: bool = True,
        broadcast_trim: bool = True,
    ) -> None:
        """初始化滑动窗口中间件

        Args:
            strategy: 裁剪策略，"messages" 或 "tokens"
            max_messages: 最大消息数（strategy="messages" 时生效）
            max_tokens: 最大 Token 数（strategy="tokens" 时生效）
            include_system: 是否保留 SystemMessage
            start_on_human: 是否确保从 HumanMessage 开始
            broadcast_trim: 是否广播裁剪事件
        """
        super().__init__()
        self.strategy = strategy
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.include_system = include_system
        self.start_on_human = start_on_human
        self.broadcast_trim = broadcast_trim

        logger.debug(
            "SlidingWindowMiddleware 初始化",
            strategy=strategy,
            max_messages=max_messages,
            max_tokens=max_tokens,
        )

    def _count_messages(self, messages: list[AnyMessage]) -> int:
        """计算消息数量"""
        return len(messages) if messages else 0

    async def _broadcast_trim_event(
        self,
        runtime: Runtime,
        count_before: int,
        count_after: int,
    ) -> None:
        """广播裁剪事件"""
        if not self.broadcast_trim:
            return

        try:
            context = getattr(runtime, "context", None)
            if context is not None:
                emitter = getattr(context, "emitter", None)
                if emitter is not None and hasattr(emitter, "aemit"):
                    await emitter.aemit(
                        StreamEventType.CONTEXT_TRIMMED.value,
                        {
                            "messages_before": count_before,
                            "messages_after": count_after,
                            "strategy": self.strategy,
                        },
                    )
        except Exception as e:
            logger.warning("裁剪事件广播失败", error=str(e))

    def _trim_messages(self, messages: list[AnyMessage]) -> list[AnyMessage]:
        """执行消息裁剪"""
        if not messages:
            return messages

        if self.strategy == "messages":
            # 基于消息数量裁剪
            trimmed = trim_messages(
                messages,
                max_tokens=self.max_messages,
                token_counter=len,  # 按消息数量计数
                strategy="last",
                include_system=self.include_system,
                start_on="human" if self.start_on_human else None,
            )
        else:
            # 基于 Token 数量裁剪
            trimmed = trim_messages(
                messages,
                max_tokens=self.max_tokens,
                token_counter="approximate",  # 使用快速近似计数
                strategy="last",
                include_system=self.include_system,
                start_on="human" if self.start_on_human else None,
            )

        return list(trimmed)

    async def abefore_model(
        self,
        state: AgentState[Any],
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """模型调用前裁剪消息"""
        messages = state.get("messages", [])
        count_before = self._count_messages(messages)

        # 检查是否需要裁剪
        need_trim = False
        if self.strategy == "messages" and count_before > self.max_messages:
            need_trim = True
        elif self.strategy == "tokens":
            # Token 策略总是尝试裁剪，让 trim_messages 决定
            need_trim = True

        if not need_trim:
            return None

        # 执行裁剪
        trimmed = self._trim_messages(messages)
        count_after = self._count_messages(trimmed)

        # 如果没有变化，不更新状态
        if count_after >= count_before:
            return None

        logger.info(
            "滑动窗口裁剪",
            strategy=self.strategy,
            messages_before=count_before,
            messages_after=count_after,
        )

        # 广播裁剪事件
        await self._broadcast_trim_event(runtime, count_before, count_after)

        return {"messages": trimmed}

    def before_model(
        self,
        state: AgentState[Any],
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """同步版本"""
        messages = state.get("messages", [])
        count_before = self._count_messages(messages)

        need_trim = False
        if self.strategy == "messages" and count_before > self.max_messages:
            need_trim = True
        elif self.strategy == "tokens":
            need_trim = True

        if not need_trim:
            return None

        trimmed = self._trim_messages(messages)
        count_after = self._count_messages(trimmed)

        if count_after >= count_before:
            return None

        logger.info(
            "滑动窗口裁剪（同步）",
            strategy=self.strategy,
            messages_before=count_before,
            messages_after=count_after,
        )

        return {"messages": trimmed}
