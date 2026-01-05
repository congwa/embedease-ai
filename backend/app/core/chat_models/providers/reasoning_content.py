"""SiliconFlow（硅基流动）推理模型实现

============================================================
平台特性
============================================================

SiliconFlow 使用 OpenAI 兼容模式，但推理字段与 OpenAI 原生不同：
- OpenAI 原生：`choices[0].delta.reasoning`
- SiliconFlow：`choices[0].delta.reasoning_content`

本文件实现 SiliconFlow 专属的推理内容提取逻辑，将其转换为统一的 ReasoningChunk。

============================================================
工作流程
============================================================

1. LangChain 调用 `_convert_chunk_to_generation_chunk` 处理原始 chunk
2. 本类覆盖该方法，从 chunk 中提取推理内容
3. 提取的 ReasoningChunk 存储在 message 的 `_reasoning_chunk` 属性上
4. Agent 层调用 `extract_reasoning(message)` 获取统一结构

============================================================
扩展说明
============================================================

如果未来有其他平台也使用 `reasoning_content` 字段，可以：
1. 直接复用本类
2. 或继承本类并覆盖 `provider_name` 属性
"""

from typing import Any

from app.core.chat_models.base import BaseReasoningChatModel, ReasoningChunk
from app.core.logging import get_logger

logger = get_logger("chat_models.siliconflow")


class SiliconFlowReasoningChatModel(BaseReasoningChatModel):
    """SiliconFlow 推理模型实现
    
    从 `choices[0].delta.reasoning_content` 提取推理内容，
    转换为统一的 ReasoningChunk 结构，存储在 message 上。
    
    Agent 层只需调用 `extract_reasoning(message)` 即可获取推理内容，
    无需关心 SiliconFlow 的具体字段名。
    """

    @property
    def provider_name(self) -> str:
        """平台标识"""
        return "siliconflow"

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> Any:
        """路径 A 注入点：从 raw chunk 提取推理内容并存储到 message 上
        
        这是多态的关键：每个平台在这里实现自己的推理提取逻辑，
        Agent 层无需关心具体实现。
        
        工作流程：
        1. 调用父类方法获取 generation_chunk
        2. 从 raw chunk 提取推理内容（SiliconFlow 使用 reasoning_content 字段）
        3. 将 ReasoningChunk 存储到 message._reasoning_chunk
        
        Args:
            chunk: 原始 dict chunk
            default_chunk_class: 默认的 chunk 类
            base_generation_info: 基础生成信息
        
        Returns:
            ChatGenerationChunk 对象
        """
        # 调用父类（ChatOpenAI）的方法获取基础转换
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )

        if generation_chunk is None:
            return None

        # 从 raw chunk 提取推理内容
        reasoning = self._normalize_reasoning_from_chunk(chunk, generation_chunk.message)
        if reasoning:
            # 存储到 message 的自定义属性（不使用 additional_kwargs）
            generation_chunk.message._reasoning_chunk = reasoning

        return generation_chunk

    def _normalize_reasoning_from_chunk(
        self,
        chunk: dict | None,
        message: Any,
    ) -> ReasoningChunk | None:
        """从 SiliconFlow 的 chunk 中提取推理内容
        
        SiliconFlow 使用 Chat Completions streaming（路径 A），
        推理内容位于 `choices[0].delta.reasoning_content`。
        
        Args:
            chunk: 原始 dict chunk
            message: AIMessageChunk 对象（本实现中未使用，但保持接口一致）
        
        Returns:
            ReasoningChunk 或 None
        """
        if not isinstance(chunk, dict):
            return None

        # 从 choices[0].delta.reasoning_content 提取
        choices = chunk.get("choices", [])
        if not choices:
            return None

        choice = choices[0]
        if not isinstance(choice, dict):
            return None

        delta = choice.get("delta", {})
        if not isinstance(delta, dict):
            return None

        reasoning_content = delta.get("reasoning_content")
        if not isinstance(reasoning_content, str) or not reasoning_content:
            return None

        return ReasoningChunk(
            delta=reasoning_content,
            provider=self.provider_name,
            source="chunk.delta.reasoning_content",
        )

    def extract_reasoning(
        self, message: Any, *, raw_chunk: dict | None = None
    ) -> ReasoningChunk | None:
        """从 message 中提取推理内容（Agent 层调用此方法）
        
        优先级：
        1. 如果提供了 raw_chunk，直接从 chunk 提取（用于测试或特殊场景）
        2. 否则从 message._reasoning_chunk 读取（正常流式场景）
        
        Args:
            message: LangChain 的 AIMessageChunk 或 AIMessage 对象
            raw_chunk: 原始 dict chunk（可选，通常不需要传）
        
        Returns:
            ReasoningChunk 或 None
        """
        if message is None:
            return None

        # 优先使用 raw_chunk（测试或特殊场景）
        if raw_chunk is not None:
            return self._normalize_reasoning_from_chunk(raw_chunk, message)

        # 正常场景：从 message 的 _reasoning_chunk 属性读取
        return getattr(message, "_reasoning_chunk", None)
