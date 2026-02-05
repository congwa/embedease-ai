"""Chat Models v1 - 基于 LangChain content_blocks 的标准化实现

============================================================
核心设计
============================================================

本模块强制使用 LangChain v1 输出格式，基于 content_blocks 标准化消息内容。

**关键特性**：
- 强制 `output_version="v1"`，不可配置
- 使用 LangChain 标准 `content_blocks` 而非自定义结构
- 按块类型（text/reasoning/tool_call）分流处理

============================================================
使用方式
============================================================

```python
from langgraph_agent_kit.chat_models.v1 import (
    V1ChatModel,
    is_v1_model,
)

# 创建模型（自动强制 v1 输出）
model = V1ChatModel(
    model="...",
    openai_api_base="...",
    openai_api_key="...",
)
```
"""

from langgraph_agent_kit.chat_models.v1.models import (
    V1ChatModel,
    is_v1_model,
)

__all__ = [
    "V1ChatModel",
    "is_v1_model",
]
