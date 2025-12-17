"""Chat Models 统一入口 - 基于 provider 和 profile 自动选择实现

核心设计：
- **简单直接**：根据 provider 和 profile.reasoning_output 直接选择实现
- **无需注册**：不需要复杂的 matcher 和注册机制
- **易于扩展**：新增提供商只需在 ModelRegistry.create 中添加判断

选择逻辑：
1. 检查 profile.reasoning_output 判断是否为推理模型
2. 非推理模型 → StandardChatModel
3. 推理模型：
   - provider=siliconflow → ReasoningContentChatModel
   - 其他 → OpenAIReasoningChatModel（OpenAI 标准）

目录结构：
- `base.py`：抽象基类和标准实现
- `registry.py`：模型创建工厂和统一入口
- `providers/`：各提供商特定实现
  - `reasoning_content.py`：SiliconFlow 等使用 reasoning_content 字段
  - `openai.py`：OpenAI 标准使用 reasoning 字段
"""

from __future__ import annotations

# 统一入口（最重要，外部只需使用这个）
from app.core.chat_models.registry import create_chat_model

# 基类（供扩展使用）
from app.core.chat_models.base import (
    BaseReasoningChatModel,
    StandardChatModel,
)

# 工厂类（供扩展使用）
from app.core.chat_models.registry import ModelRegistry

# 具体实现（供调试使用）
from app.core.chat_models.providers.reasoning_content import ReasoningContentChatModel
from app.core.chat_models.providers.openai import OpenAIReasoningChatModel

__all__ = [
    # 统一入口（外部使用）
    "create_chat_model",
    # 工厂类
    "ModelRegistry",
    # 基类
    "BaseReasoningChatModel",
    "StandardChatModel",
    # 实现类（调试用）
    "ReasoningContentChatModel",
    "OpenAIReasoningChatModel",
]
