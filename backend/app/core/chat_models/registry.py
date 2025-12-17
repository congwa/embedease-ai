"""模型创建工厂 - 基于 provider 和 profile 选择实现

本文件做什么：
- 提供 `ModelRegistry` 类：根据 provider 和 profile 创建合适的模型实例
- 提供 `create_chat_model` 函数：对外统一创建入口

选择逻辑：
1. 检查 profile.reasoning_output 判断是否为推理模型
2. 如果不是推理模型 → StandardChatModel
3. 如果是推理模型：
   - provider=siliconflow → ReasoningContentChatModel（使用 reasoning_content 字段）
   - 其他 → OpenAIReasoningChatModel（使用 reasoning 字段，OpenAI 标准）
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from app.core.chat_models.base import StandardChatModel
from app.core.logging import get_logger

logger = get_logger("chat_models.registry")


class ModelRegistry:
    """模型创建工厂
    
    根据 provider 和 profile 直接选择合适的实现，不需要复杂的匹配逻辑
    """

    @classmethod
    def create(
        cls,
        model: str,
        base_url: str,
        api_key: str,
        provider: str,
        profile: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseChatModel:
        """根据 provider 和 profile 创建合适的实例

        Args:
            model: 模型名称
            base_url: API 基础 URL
            api_key: API Key
            provider: 提供商标识（如 siliconflow, openai, anthropic）
            profile: 模型能力配置（包含 reasoning_output 等信息）
            **kwargs: 其他参数

        Returns:
            配置好的模型实例
        
        选择逻辑：
            1. 检查 profile.reasoning_output 判断是否为推理模型
            2. 非推理模型 → StandardChatModel
            3. 推理模型：
               - provider=siliconflow → ReasoningContentChatModel
               - 其他 → OpenAIReasoningChatModel（OpenAI 标准）
        """
        # 提取 profile 信息（从 kwargs 中移除，避免传递给模型构造函数）
        if profile is None:
            profile = kwargs.pop("profile", {})
        
        # 判断是否为推理模型
        is_reasoning_model = profile.get("reasoning_output", False) if profile else False
        
        if not is_reasoning_model:
            # 普通模型，使用标准实现
            logger.info(
                "创建标准模型",
                model=model,
                provider=provider,
                reasoning_output=False,
            )
            return StandardChatModel(
                model=model,
                openai_api_base=base_url,
                openai_api_key=api_key,
                **kwargs,
            )
        
        # 推理模型：根据 provider 选择实现
        provider_lower = provider.lower()
        
        if provider_lower == "siliconflow":
            # SiliconFlow 使用 reasoning_content 字段（OpenAI 兼容模式）
            logger.info(
                "创建 SiliconFlow 推理模型",
                model=model,
                provider=provider,
                reasoning_field="reasoning_content",
            )
            from app.core.chat_models.providers.reasoning_content import ReasoningContentChatModel
            return ReasoningContentChatModel(
                model=model,
                openai_api_base=base_url,
                openai_api_key=api_key,
                **kwargs,
            )
        else:
            # 其他提供商使用 OpenAI 标准 reasoning 字段
            logger.info(
                "创建 OpenAI 标准推理模型",
                model=model,
                provider=provider,
                reasoning_field="reasoning",
            )
            from app.core.chat_models.providers.openai import OpenAIReasoningChatModel
            return OpenAIReasoningChatModel(
                model=model,
                openai_api_base=base_url,
                openai_api_key=api_key,
                **kwargs,
            )


def create_chat_model(
    model: str,
    base_url: str,
    api_key: str,
    provider: str,
    profile: dict[str, Any] | None = None,
    **kwargs: Any,
) -> BaseChatModel:
    """创建聊天模型实例（统一入口）

    这是对外提供的统一接口，Agent 层只需调用此函数即可。
    内部根据 provider 和 profile 自动选择合适的实现。

    Args:
        model: 模型名称
        base_url: API 基础 URL
        api_key: API Key
        provider: 提供商标识（如 siliconflow, openai, anthropic）
        profile: 模型能力配置（可选，包含 reasoning_output 等信息）
        **kwargs: 其他参数（temperature, max_tokens 等）

    Returns:
        配置好的模型实例（统一返回 BaseChatModel 接口）

    Examples:
        >>> # 普通模型
        >>> model = create_chat_model(
        ...     model="moonshotai/Kimi-K2-Instruct",
        ...     base_url="https://api.siliconflow.cn/v1",
        ...     api_key="sk-...",
        ...     provider="siliconflow",
        ...     profile={"reasoning_output": False, "tool_calling": True}
        ... )
        >>> # reasoning_output=False -> StandardChatModel
        
        >>> # SiliconFlow 推理模型
        >>> model = create_chat_model(
        ...     model="moonshotai/Kimi-K2-Thinking",
        ...     base_url="https://api.siliconflow.cn/v1",
        ...     api_key="sk-...",
        ...     provider="siliconflow",
        ...     profile={"reasoning_output": True}
        ... )
        >>> # reasoning_output=True + provider=siliconflow -> ReasoningContentChatModel
    """
    return ModelRegistry.create(model, base_url, api_key, provider, profile=profile, **kwargs)
