"""Chat Models v0 - 兼容层（已废弃）

============================================================
⚠️ 废弃警告
============================================================

本模块保留旧版实现，供紧急回退使用。
新代码请使用 `app.core.chat_models.v1`。

============================================================
历史背景
============================================================

v0 使用自定义的 ReasoningChunk 结构和 additional_kwargs 机制，
通过 `model.extract_reasoning(message)` 提取推理内容。

v1 改用 LangChain 标准 content_blocks，直接从 message.content_blocks 
按块类型分流处理。
"""

from langgraph_agent_kit import (
    ReasoningChunk,
    BaseReasoningChatModel,
    StandardChatModel,
    SiliconFlowReasoningChatModel,
)

__all__ = [
    "ReasoningChunk",
    "BaseReasoningChatModel",
    "StandardChatModel",
    "SiliconFlowReasoningChatModel",
]
