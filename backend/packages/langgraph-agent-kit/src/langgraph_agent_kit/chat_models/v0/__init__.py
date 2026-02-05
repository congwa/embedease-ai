"""Chat Models v0 - 兼容层（已废弃）

⚠️ 本模块保留旧版实现，供紧急回退使用。
新代码请使用 v1 模块。

v0 使用自定义的 ReasoningChunk 结构和 additional_kwargs 机制，
通过 `model.extract_reasoning(message)` 提取推理内容。
"""

from langgraph_agent_kit.chat_models.v0.base import (
    ReasoningChunk,
    BaseReasoningChatModel,
    StandardChatModel,
)

__all__ = [
    "ReasoningChunk",
    "BaseReasoningChatModel",
    "StandardChatModel",
]
