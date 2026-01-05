"""Chat Models 统一入口（多态架构）

============================================================
核心设计
============================================================

本模块采用**多态架构**，让不同平台在各自的子类中完成推理内容的提取与归一化，
Agent 层只消费统一的 `ReasoningChunk` 结构。

**关键约束**：
- 不再使用 `additional_kwargs["reasoning_content"]`
- Agent 层通过 `model.extract_reasoning(message)` 获取推理内容
- 新增平台只需继承 `BaseReasoningChatModel` 并在 registry 注册

============================================================
目录结构
============================================================

- `base.py`：定义 ReasoningChunk 结构和 BaseReasoningChatModel 抽象基类
- `registry.py`：模型创建工厂，根据 provider 选择实现
- `providers/`：各平台具体实现
  - `reasoning_content.py`：SiliconFlow 实现

============================================================
使用方式
============================================================

```python
from app.core.chat_models import create_chat_model

# 创建模型（自动选择实现）
model = create_chat_model(
    model="...",
    base_url="...",
    api_key="...",
    provider="siliconflow",
    profile={"reasoning_output": True},
)

# Agent 层获取推理内容
reasoning = model.extract_reasoning(message, raw_chunk=chunk)
if reasoning:
    print(reasoning.delta)  # 推理增量文本
```
"""

from __future__ import annotations

# 基类和统一结构（供扩展使用）
from app.core.chat_models.base import (
    BaseReasoningChatModel,
    ReasoningChunk,
    StandardChatModel,
)

# SiliconFlow 实现（供调试使用）
from app.core.chat_models.providers.reasoning_content import SiliconFlowReasoningChatModel

# 统一入口（外部只需使用这个）
from app.core.chat_models.registry import create_chat_model

__all__ = [
    # 统一入口
    "create_chat_model",
    # 统一结构
    "ReasoningChunk",
    # 基类
    "BaseReasoningChatModel",
    "StandardChatModel",
    # 实现类
    "SiliconFlowReasoningChatModel",
]
