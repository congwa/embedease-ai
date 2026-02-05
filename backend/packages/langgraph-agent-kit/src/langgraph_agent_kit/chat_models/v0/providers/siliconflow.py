"""SiliconFlow（硅基流动）推理模型实现（v0 兼容层）

平台特性：
SiliconFlow 使用 OpenAI 兼容模式，但推理字段与 OpenAI 原生不同：
- OpenAI 原生：`choices[0].delta.reasoning`
- SiliconFlow：`choices[0].delta.reasoning_content`

本文件实现 SiliconFlow 专属的推理内容提取逻辑，将其转换为统一的 ReasoningChunk。
"""

from typing import Any

from langgraph_agent_kit.chat_models.v0.base import BaseReasoningChatModel, ReasoningChunk


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
        
        工作流程：
        1. 调用父类方法获取 generation_chunk
        2. 从 raw chunk 提取推理内容（SiliconFlow 使用 reasoning_content 字段）
        3. 将 ReasoningChunk 存储到 message._reasoning_chunk
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
        1. 如果提供了 raw_chunk，直接从 chunk 提取
        2. 否则从 message._reasoning_chunk 读取（正常流式场景）
        """
        if message is None:
            return None

        # 优先使用 raw_chunk（测试或特殊场景）
        if raw_chunk is not None:
            return self._normalize_reasoning_from_chunk(raw_chunk, message)

        # 正常场景：从 message 的 _reasoning_chunk 属性读取
        return getattr(message, "_reasoning_chunk", None)
