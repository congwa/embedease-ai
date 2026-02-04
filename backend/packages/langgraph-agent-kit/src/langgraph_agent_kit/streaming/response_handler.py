"""流式响应处理器 - 处理 LangGraph 的流式输出"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from langgraph_agent_kit.core.events import StreamEventType

if TYPE_CHECKING:
    from langgraph_agent_kit.core.emitter import QueueDomainEmitter


class StreamingResponseHandler:
    """流式响应处理器
    
    处理 LangGraph 的流式输出，将模型响应转换为 domain events。
    
    职责：
    - 处理 assistant.delta / assistant.reasoning.delta
    - 发射 llm.call.start / llm.call.end
    - 聚合最终内容
    """

    def __init__(
        self,
        *,
        emitter: "QueueDomainEmitter",
        model: Any = None,
        conversation_id: str | None = None,
    ):
        self._emitter = emitter
        self._model = model
        self._conversation_id = conversation_id
        self._full_content = ""
        self._reasoning = ""
        self._in_llm_call = False
        self._llm_call_start_time: float | None = None

    async def handle_message(self, message: Any) -> None:
        """处理单条消息"""
        from langchain_core.messages import AIMessageChunk

        if isinstance(message, AIMessageChunk):
            await self._handle_ai_chunk(message)

    async def _handle_ai_chunk(self, chunk: Any) -> None:
        """处理 AI 消息块"""
        import time

        if not self._in_llm_call:
            self._in_llm_call = True
            self._llm_call_start_time = time.time()
            await self._emitter.aemit(
                StreamEventType.LLM_CALL_START.value,
                {"message_count": 0},
            )

        content = getattr(chunk, "content", "")
        if content:
            self._full_content += content
            await self._emitter.aemit(
                StreamEventType.ASSISTANT_DELTA.value,
                {"delta": content},
            )

        additional_kwargs = getattr(chunk, "additional_kwargs", {})
        reasoning = additional_kwargs.get("reasoning_content", "")
        if reasoning:
            self._reasoning += reasoning
            await self._emitter.aemit(
                StreamEventType.ASSISTANT_REASONING_DELTA.value,
                {"delta": reasoning},
            )

    async def finalize(self) -> None:
        """结束处理，发射最终事件"""
        import time

        if self._in_llm_call:
            elapsed_ms = 0
            if self._llm_call_start_time:
                elapsed_ms = int((time.time() - self._llm_call_start_time) * 1000)
            
            await self._emitter.aemit(
                StreamEventType.LLM_CALL_END.value,
                {"elapsed_ms": elapsed_ms},
            )
            self._in_llm_call = False

        await self._emitter.aemit(
            StreamEventType.ASSISTANT_FINAL.value,
            {
                "content": self._full_content,
                "reasoning": self._reasoning if self._reasoning else None,
            },
        )

    @property
    def full_content(self) -> str:
        return self._full_content

    @property
    def reasoning(self) -> str:
        return self._reasoning
