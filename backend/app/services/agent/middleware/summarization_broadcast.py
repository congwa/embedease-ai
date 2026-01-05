"""Summarization 广播中间件

包装 LangChain 的 SummarizationMiddleware，在压缩发生时推送 SSE 事件给前端。
"""

from typing import Any

from langchain.agents.middleware.summarization import SummarizationMiddleware
from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import AnyMessage
from langgraph.runtime import Runtime

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("middleware.summarization_broadcast")


class SummarizationBroadcastMiddleware(AgentMiddleware):
    """Summarization 广播中间件

    包装 SummarizationMiddleware，在压缩发生时：
    1. 记录压缩前后的消息数量
    2. 通过 context.emitter 推送 context.summarized 事件给前端
    """

    def __init__(
        self,
        summarization_middleware: SummarizationMiddleware,
    ) -> None:
        """初始化

        Args:
            summarization_middleware: LangChain 的 SummarizationMiddleware 实例
        """
        super().__init__()
        self._inner = summarization_middleware

    def _count_messages(self, messages: list[AnyMessage]) -> int:
        """计算消息数量"""
        return len(messages) if messages else 0

    def _estimate_tokens(self, messages: list[AnyMessage]) -> int:
        """估算消息的 token 数量（使用内部的 token_counter）"""
        if not messages:
            return 0
        try:
            return self._inner.token_counter(messages)
        except Exception:
            return 0

    async def abefore_model(
        self,
        state: dict[str, Any],
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """模型调用前检测压缩并广播"""
        messages_before = state.get("messages", [])
        count_before = self._count_messages(messages_before)
        tokens_before = self._estimate_tokens(messages_before)

        # 调用内部的 SummarizationMiddleware
        result = await self._inner.abefore_model(state, runtime)

        # 如果没有返回结果，说明没有发生压缩
        if result is None:
            return None

        # 压缩发生了，计算压缩后的消息数量
        new_messages = result.get("messages", [])
        # 新消息列表可能包含 RemoveMessage 指令，需要过滤掉
        from langgraph.graph.message import RemoveMessage

        actual_messages = [m for m in new_messages if not isinstance(m, RemoveMessage)]
        count_after = self._count_messages(actual_messages)
        tokens_after = self._estimate_tokens(actual_messages)

        # 推送压缩事件
        try:
            context = getattr(runtime, "context", None)
            if context is not None:
                emitter = getattr(context, "emitter", None)
                if emitter is not None and hasattr(emitter, "aemit"):
                    payload = {
                        "messages_before": count_before,
                        "messages_after": count_after,
                    }
                    if tokens_before > 0:
                        payload["tokens_before"] = tokens_before
                    if tokens_after > 0:
                        payload["tokens_after"] = tokens_after

                    await emitter.aemit(
                        StreamEventType.CONTEXT_SUMMARIZED.value,
                        payload,
                    )

                    logger.info(
                        "上下文压缩完成",
                        messages_before=count_before,
                        messages_after=count_after,
                        tokens_before=tokens_before,
                        tokens_after=tokens_after,
                    )
        except Exception as e:
            # 广播失败不影响主流程
            logger.warning("压缩事件广播失败", error=str(e))

        return result

    def before_model(
        self,
        state: dict[str, Any],
        runtime: Runtime,
    ) -> dict[str, Any] | None:
        """同步版本（透传给内部中间件）"""
        messages_before = state.get("messages", [])
        count_before = self._count_messages(messages_before)
        tokens_before = self._estimate_tokens(messages_before)

        result = self._inner.before_model(state, runtime)

        if result is None:
            return None

        # 压缩发生了
        new_messages = result.get("messages", [])
        from langgraph.graph.message import RemoveMessage

        actual_messages = [m for m in new_messages if not isinstance(m, RemoveMessage)]
        count_after = self._count_messages(actual_messages)
        tokens_after = self._estimate_tokens(actual_messages)

        logger.info(
            "上下文压缩完成（同步）",
            messages_before=count_before,
            messages_after=count_after,
            tokens_before=tokens_before,
            tokens_after=tokens_after,
        )

        return result
