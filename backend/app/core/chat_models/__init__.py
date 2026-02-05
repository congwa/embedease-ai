"""Chat Models 统一入口 - v1 版本

============================================================
核心设计
============================================================

本模块强制使用 LangChain v1 输出格式，基于 content_blocks 标准化消息内容。

**关键特性**：
- 强制 `output_version="v1"`，不可配置
- 使用 LangChain 标准 `content_blocks` 而非自定义结构
- 按块类型（text/reasoning/tool_call）分流处理

============================================================
目录结构
============================================================

- `v1/`：v1 标准实现（当前使用）
  - `types.py`：类型定义和类型守卫
  - `parser.py`：内容块解析器
  - `models.py`：模型基类
- `v0/`：兼容层（已废弃，供紧急回退）
- `registry.py`：模型创建工厂

============================================================
使用方式
============================================================

```python
from app.core.chat_models import create_chat_model, parse_content_blocks

# 创建模型（强制 v1 输出）
model = create_chat_model(
    model="...",
    base_url="...",
    api_key="...",
    provider="siliconflow",
)

# 解析消息内容（v1 方式）
parsed = parse_content_blocks(message)
print(parsed.text)       # 合并后的文本
print(parsed.reasoning)  # 合并后的推理
```
"""

from __future__ import annotations

from langgraph_agent_kit import (
    V1ChatModel,
    ParsedContent,
    parse_content_blocks,
    parse_content_blocks_from_chunk,
    is_text_block,
    is_reasoning_block,
    is_tool_call_block,
    is_v1_model,
    ContentBlock,
    TextContentBlock,
    ReasoningContentBlock,
    ToolCallBlock,
    create_chat_model,
)

__all__ = [
    # 统一入口
    "create_chat_model",
    # v1 模型
    "V1ChatModel",
    # v1 解析器
    "ParsedContent",
    "parse_content_blocks",
    "parse_content_blocks_from_chunk",
    # v1 类型守卫
    "is_text_block",
    "is_reasoning_block",
    "is_tool_call_block",
    # 版本检测
    "is_v1_model",
    # v1 类型
    "ContentBlock",
    "TextContentBlock",
    "ReasoningContentBlock",
    "ToolCallBlock",
]
