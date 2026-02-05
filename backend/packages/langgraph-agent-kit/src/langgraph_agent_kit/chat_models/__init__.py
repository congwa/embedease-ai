"""Chat Models - 统一的聊天模型基类

提供 v0 和 v1 两个版本的模型基类：
- v0: 使用自定义 ReasoningChunk 结构（已废弃，仅作兼容）
- v1: 使用 LangChain 标准 content_blocks（推荐）

============================================================
使用方式
============================================================

```python
from langgraph_agent_kit.chat_models import (
    # v1 推荐
    V1ChatModel,
    is_v1_model,
    # v0 兼容
    ReasoningChunk,
    BaseReasoningChatModel,
    StandardChatModel,
)
```
"""

from langgraph_agent_kit.chat_models.v0 import (
    ReasoningChunk,
    BaseReasoningChatModel,
    StandardChatModel,
)
from langgraph_agent_kit.chat_models.v0.providers import (
    SiliconFlowReasoningChatModel,
)
from langgraph_agent_kit.chat_models.v1 import (
    V1ChatModel,
    is_v1_model,
)
from langgraph_agent_kit.chat_models.v1.providers import (
    SiliconFlowV1ChatModel,
)
from langgraph_agent_kit.chat_models.registry import (
    create_chat_model,
    V0_REASONING_MODEL_REGISTRY,
    V1_REASONING_MODEL_REGISTRY,
)

__all__ = [
    # v0 兼容层
    "ReasoningChunk",
    "BaseReasoningChatModel",
    "StandardChatModel",
    "SiliconFlowReasoningChatModel",
    # v1 推荐
    "V1ChatModel",
    "is_v1_model",
    "SiliconFlowV1ChatModel",
    # 工厂
    "create_chat_model",
    "V0_REASONING_MODEL_REGISTRY",
    "V1_REASONING_MODEL_REGISTRY",
]
