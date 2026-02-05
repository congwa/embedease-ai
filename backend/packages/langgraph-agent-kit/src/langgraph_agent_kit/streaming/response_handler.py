"""流式响应处理器 - 处理 LangGraph 的流式输出

支持 v0/v1 双模式：
- v1 模式（默认）：使用 content_blocks 解析
- v0 模式：使用 model.extract_reasoning() 解析

功能：
- AIMessageChunk 增量处理
- AIMessage 兜底处理
- ToolMessage 框架（可由子类扩展）
- 文本/推理增量聚合
- LLM_CALL_START/END 边界事件
- ASSISTANT_FINAL 最终事件
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.streaming.content_parser import parse_content_blocks

if TYPE_CHECKING:
    from langgraph_agent_kit.core.emitter import QueueDomainEmitter

__all__ = ["StreamingResponseHandler"]


@dataclass
class StreamingResponseHandler:
    """流式响应处理器（支持 v0/v1 双模式）
    
    处理 LangGraph 的流式输出，将模型响应转换为 domain events。
    
    Attributes:
        emitter: 事件发射器（需要有 aemit 方法）
        conversation_id: 会话 ID（用于日志）
        model: LLM 模型实例（v0 模式需要，用于 extract_reasoning）
        mode: 解析模式，"v1"（默认）或 "v0" 或 "auto"（自动检测）
    """

    emitter: Any
    conversation_id: str = ""
    model: Any = None
    mode: Literal["v0", "v1", "auto"] = "v1"

    # 内部状态
    full_content: str = field(default="", init=False)
    full_reasoning: str = field(default="", init=False)
    seen_tool_ids: set[str] = field(default_factory=set, init=False)

    # LLM 调用状态
    _in_llm_call: bool = field(default=False, init=False)
    _llm_call_start_time: float | None = field(default=None, init=False)

    # 统计
    content_events: int = field(default=0, init=False)
    reasoning_events: int = field(default=0, init=False)
    reasoning_chars: int = field(default=0, init=False)

    def _is_v1_mode(self) -> bool:
        """判断是否使用 v1 模式"""
        if self.mode == "v1":
            return True
        if self.mode == "v0":
            return False
        # auto 模式：检测 model 的版本
        if self.model is None:
            return True  # 无 model 默认 v1
        version = getattr(self.model, "_chat_model_version", None)
        return version == "v1" or version is None

    async def handle_message(self, msg: Any) -> None:
        """处理单条消息（核心分发逻辑）
        
        Args:
            msg: LangChain 消息对象
        """
        if isinstance(msg, AIMessageChunk):
            await self._handle_ai_chunk(msg)
        elif isinstance(msg, AIMessage):
            await self._handle_ai_message(msg)
        elif isinstance(msg, ToolMessage):
            await self._handle_tool_message(msg)

    async def _handle_ai_chunk(self, msg: AIMessageChunk) -> None:
        """处理 AI 增量消息"""
        # 开始 LLM 调用
        if not self._in_llm_call:
            self._in_llm_call = True
            self._llm_call_start_time = time.time()
            await self.emitter.aemit(
                StreamEventType.LLM_CALL_START.value,
                {"message_count": 0},
            )

        if self._is_v1_mode():
            await self._handle_ai_chunk_v1(msg)
        else:
            await self._handle_ai_chunk_v0(msg)

    async def _handle_ai_chunk_v1(self, msg: AIMessageChunk) -> None:
        """v1：使用 content_blocks 解析"""
        parsed = parse_content_blocks(msg)

        # 文本增量
        text_delta = parsed.text
        if text_delta:
            self.full_content += text_delta
            self.content_events += 1
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_DELTA.value,
                {"delta": text_delta},
            )

        # 推理增量
        reasoning_delta = parsed.reasoning
        if reasoning_delta:
            self.full_reasoning += reasoning_delta
            self.reasoning_chars += len(reasoning_delta)
            self.reasoning_events += 1
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_REASONING_DELTA.value,
                {"delta": reasoning_delta},
            )

    async def _handle_ai_chunk_v0(self, msg: AIMessageChunk) -> None:
        """v0：使用 model.extract_reasoning() 解析"""
        # 正文增量
        delta = msg.content or ""
        if isinstance(delta, list):
            delta = "".join(str(x) for x in delta)
        if isinstance(delta, str) and delta:
            self.full_content += delta
            self.content_events += 1
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_DELTA.value,
                {"delta": delta},
            )

        # 推理增量（通过多态接口提取）
        if self.model and hasattr(self.model, "extract_reasoning"):
            reasoning_chunk = self.model.extract_reasoning(msg)
            if reasoning_chunk and getattr(reasoning_chunk, "delta", None):
                reasoning_delta = reasoning_chunk.delta
                self.full_reasoning += reasoning_delta
                self.reasoning_chars += len(reasoning_delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_delta},
                )

    async def _handle_ai_message(self, msg: AIMessage) -> None:
        """处理完整 AI 消息（兜底场景）"""
        if self._is_v1_mode():
            await self._handle_ai_message_v1(msg)
        else:
            await self._handle_ai_message_v0(msg)

    async def _handle_ai_message_v1(self, msg: AIMessage) -> None:
        """v1：使用 content_blocks 解析（兜底）"""
        parsed = parse_content_blocks(msg)

        # 兜底：如果之前没有收到任何 content chunk
        if self.content_events == 0:
            text_delta = parsed.text
            if text_delta:
                self.full_content += text_delta
                self.content_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_DELTA.value,
                    {"delta": text_delta},
                )

        # 兜底：从完整 AIMessage 提取推理
        if self.reasoning_events == 0:
            reasoning_delta = parsed.reasoning
            if reasoning_delta:
                self.full_reasoning += reasoning_delta
                self.reasoning_chars += len(reasoning_delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_delta},
                )

    async def _handle_ai_message_v0(self, msg: AIMessage) -> None:
        """v0：使用 model.extract_reasoning() 解析（兜底）"""
        # 兜底：如果之前没有收到任何 content chunk
        if self.content_events == 0:
            delta = msg.content or ""
            if isinstance(delta, list):
                delta = "".join(str(x) for x in delta)
            if isinstance(delta, str) and delta:
                self.full_content += delta
                self.content_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_DELTA.value,
                    {"delta": delta},
                )

        # 兜底：从完整 AIMessage 提取推理
        if self.reasoning_events == 0 and self.model and hasattr(self.model, "extract_reasoning"):
            reasoning_chunk = self.model.extract_reasoning(msg)
            if reasoning_chunk and getattr(reasoning_chunk, "delta", None):
                reasoning_delta = reasoning_chunk.delta
                self.full_reasoning += reasoning_delta
                self.reasoning_chars += len(reasoning_delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_delta},
                )

    async def _handle_tool_message(self, msg: ToolMessage) -> None:
        """处理工具消息（可由子类扩展）
        
        默认实现只做去重，不处理内容。
        子类可覆盖此方法处理业务特定逻辑（如商品数据提取）。
        """
        msg_id = getattr(msg, "id", None)
        if isinstance(msg_id, str) and msg_id in self.seen_tool_ids:
            return
        if isinstance(msg_id, str):
            self.seen_tool_ids.add(msg_id)

    async def finalize(self) -> dict[str, Any]:
        """发送最终事件，返回汇总数据
        
        Returns:
            包含 content、reasoning 的字典
        """
        # 结束 LLM 调用
        if self._in_llm_call:
            elapsed_ms = 0
            if self._llm_call_start_time:
                elapsed_ms = int((time.time() - self._llm_call_start_time) * 1000)
            
            await self.emitter.aemit(
                StreamEventType.LLM_CALL_END.value,
                {"elapsed_ms": elapsed_ms},
            )
            self._in_llm_call = False

        # 兜底：仅当"全程没有任何 content delta"时，把 reasoning 兜底成 content
        if self.content_events == 0 and self.full_reasoning.strip():
            self.full_content = self.full_reasoning
            self.full_reasoning = ""

        result = {
            "content": self.full_content,
            "reasoning": self.full_reasoning if self.full_reasoning else None,
        }

        await self.emitter.aemit(StreamEventType.ASSISTANT_FINAL.value, result)

        return result

    def get_stats(self) -> dict[str, int]:
        """获取统计信息
        
        Returns:
            统计字典
        """
        return {
            "content_events": self.content_events,
            "reasoning_events": self.reasoning_events,
            "reasoning_chars": self.reasoning_chars,
        }
