"""流响应处理器 - 解析 Agent 流输出，发射事件

使用方式：
    from app.services.agent.streams import StreamingResponseHandler

    handler = StreamingResponseHandler(emitter=context.emitter, model=model)
    async for msg in agent.astream(...):
        await handler.handle_message(msg)
    result = await handler.finalize()

职责：
    1. 解析 AIMessageChunk/AIMessage/ToolMessage
    2. 提取正文增量、推理增量、商品数据
    3. 发射对应的事件到 emitter
    4. 汇总最终结果
"""

import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("streams.handler")


def normalize_products_payload(payload: Any) -> list[dict[str, Any]] | None:
    """标准化商品数据格式

    Args:
        payload: 原始商品数据（可能是 dict 或 list）

    Returns:
        标准化后的商品列表，或 None
    """
    if payload is None:
        return None

    candidate: Any = payload
    if (
        isinstance(candidate, dict)
        and "products" in candidate
        and isinstance(candidate.get("products"), list)
    ):
        candidate = candidate.get("products")

    if not isinstance(candidate, list):
        return None

    normalized: list[dict[str, Any]] = []
    for item in candidate:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        if raw_id is None:
            continue
        normalized_item = dict(item)
        normalized_item["id"] = str(raw_id)
        normalized.append(normalized_item)

    return normalized or None


@dataclass
class StreamingResponseHandler:
    """流响应处理器（有状态）

    Attributes:
        emitter: 事件发射器（需要有 aemit 方法）
        model: LLM 模型实例（用于多态的推理提取）
        conversation_id: 会话 ID（用于日志）
    """

    emitter: Any
    model: Any = None
    conversation_id: str = ""

    # 内部状态
    full_content: str = field(default="", init=False)
    full_reasoning: str = field(default="", init=False)
    products_data: list[dict[str, Any]] | None = field(default=None, init=False)
    seen_tool_ids: set[str] = field(default_factory=set, init=False)

    # 统计
    content_events: int = field(default=0, init=False)
    reasoning_events: int = field(default=0, init=False)
    reasoning_chars: int = field(default=0, init=False)

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

        # 推理增量（通过多态接口提取，不依赖 additional_kwargs）
        if self.model and hasattr(self.model, "extract_reasoning"):
            reasoning_chunk = self.model.extract_reasoning(msg)
            if reasoning_chunk and reasoning_chunk.delta:
                self.full_reasoning += reasoning_chunk.delta
                self.reasoning_chars += len(reasoning_chunk.delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_chunk.delta},
                )

    async def _handle_ai_message(self, msg: AIMessage) -> None:
        """处理完整 AI 消息（兜底）"""
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

        # 兜底：从完整 AIMessage 提取推理（如果之前没有收到任何推理增量）
        if self.reasoning_events == 0 and self.model and hasattr(self.model, "extract_reasoning"):
            reasoning_chunk = self.model.extract_reasoning(msg)
            if reasoning_chunk and reasoning_chunk.delta:
                self.full_reasoning += reasoning_chunk.delta
                self.reasoning_chars += len(reasoning_chunk.delta)
                self.reasoning_events += 1
                await self.emitter.aemit(
                    StreamEventType.ASSISTANT_REASONING_DELTA.value,
                    {"delta": reasoning_chunk.delta},
                )

    async def _handle_tool_message(self, msg: ToolMessage) -> None:
        """处理工具消息，提取商品数据"""
        # 去重
        msg_id = getattr(msg, "id", None)
        if isinstance(msg_id, str) and msg_id in self.seen_tool_ids:
            return
        if isinstance(msg_id, str):
            self.seen_tool_ids.add(msg_id)

        content = msg.content
        try:
            parsed_data: Any
            if isinstance(content, str):
                parsed_data = json.loads(content)
            elif isinstance(content, (list, dict)):
                parsed_data = content
            else:
                return

            normalized_products = normalize_products_payload(parsed_data)
            if normalized_products is None:
                return

            self.products_data = normalized_products
            await self.emitter.aemit(
                StreamEventType.ASSISTANT_PRODUCTS.value,
                {"items": normalized_products},
            )
        except Exception:
            pass

    async def finalize(self) -> dict[str, Any]:
        """发送最终事件，返回汇总数据

        Returns:
            包含 content、reasoning、products 的字典
        """
        # 兜底：仅当"全程没有任何 content delta"时，才把 reasoning 兜底成 content（避免混流）
        if self.content_events == 0 and self.full_reasoning.strip():
            logger.warning(
                "检测到 content 全程为空，兜底将 reasoning 作为 content 输出",
                conversation_id=self.conversation_id,
                content_len=len(self.full_content),
                reasoning_len=len(self.full_reasoning),
            )
            self.full_content = self.full_reasoning
            self.full_reasoning = ""

        result = {
            "content": self.full_content,
            "reasoning": self.full_reasoning if self.full_reasoning else None,
            "products": self.products_data
            if isinstance(self.products_data, list) or self.products_data is None
            else [self.products_data],
        }

        await self.emitter.aemit(StreamEventType.ASSISTANT_FINAL.value, result)

        logger.info(
            "✅ 流处理完成",
            conversation_id=self.conversation_id,
            content_events=self.content_events,
            reasoning_events=self.reasoning_events,
            reasoning_chars=self.reasoning_chars,
        )

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
