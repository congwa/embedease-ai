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
from app.core.chat_models.v1 import (
    V1ChatModel,
    parse_content_blocks,
    is_text_block,
    is_reasoning_block,
)

# 创建模型（自动强制 v1 输出）
model = V1ChatModel(
    model="...",
    openai_api_base="...",
    openai_api_key="...",
)

# 解析消息内容
parsed = parse_content_blocks(message)
print(parsed.text)       # 合并后的文本
print(parsed.reasoning)  # 合并后的推理
```
"""

from langgraph_agent_kit import (
    ContentBlock,
    TextContentBlock,
    ReasoningContentBlock,
    ToolCallBlock,
    is_text_block,
    is_reasoning_block,
    is_tool_call_block,
    ParsedContent,
    parse_content_blocks,
    parse_content_blocks_from_chunk,
    V1ChatModel,
    is_v1_model,
    SiliconFlowV1ChatModel,
)

__all__ = [
    # 类型
    "ContentBlock",
    "TextContentBlock",
    "ReasoningContentBlock",
    "ToolCallBlock",
    # 类型守卫
    "is_text_block",
    "is_reasoning_block",
    "is_tool_call_block",
    # 解析器
    "ParsedContent",
    "parse_content_blocks",
    "parse_content_blocks_from_chunk",
    # 模型
    "V1ChatModel",
    "SiliconFlowV1ChatModel",
    # 版本检测
    "is_v1_model",
]
