"""模型创建工厂 - 支持 v0/v1 切换

核心职责：
- 提供 `create_chat_model` 函数：对外统一创建入口
- 默认使用 v1 输出格式（output_version="v1"）
- 支持通过 `use_v0=True` 切换到兼容层

v1（默认）：
- 强制 output_version="v1"
- AIMessage.content 直接存储 content_blocks
- 使用 parse_content_blocks() 按类型分流

v0（兼容层）：
- 自定义 ReasoningChunk 结构
- 通过 model.extract_reasoning() 提取推理
- 需要显式传入 use_v0=True
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


# v0 推理模型注册表（兼容层使用）
V0_REASONING_MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    "siliconflow": (
        "langgraph_agent_kit.chat_models.v0.providers.siliconflow",
        "SiliconFlowReasoningChatModel",
    ),
}

# v1 推理模型注册表（需要特殊处理 reasoning_content 的提供商）
V1_REASONING_MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    "siliconflow": (
        "langgraph_agent_kit.chat_models.v1.providers.siliconflow",
        "SiliconFlowV1ChatModel",
    ),
}


def create_chat_model(
    model: str,
    base_url: str,
    api_key: str,
    provider: str,
    profile: dict[str, Any] | None = None,
    use_v0: bool = False,
    **kwargs: Any,
) -> BaseChatModel:
    """创建模型实例（统一入口）

    默认使用 v1 输出格式，可通过 use_v0=True 切换到兼容层。

    Args:
        model: 模型名称
        base_url: API 基础 URL
        api_key: API Key
        provider: 提供商标识（如 siliconflow, openai）
        profile: 模型能力配置（可选）
        use_v0: 是否使用 v0 兼容层（默认 False，使用 v1）
        **kwargs: 其他参数（temperature, max_tokens 等）

    Returns:
        配置好的模型实例
    """
    # 提取 profile 信息
    if profile is None:
        profile = kwargs.pop("profile", {})

    is_reasoning_model = profile.get("reasoning_output", False) if profile else False

    if use_v0:
        return _create_v0_model(model, base_url, api_key, provider, is_reasoning_model, **kwargs)
    else:
        return _create_v1_model(model, base_url, api_key, provider, is_reasoning_model, **kwargs)


def _create_v1_model(
    model: str,
    base_url: str,
    api_key: str,
    provider: str,
    is_reasoning_model: bool,
    **kwargs: Any,
) -> BaseChatModel:
    """创建 v1 模型（默认）
    
    对于需要特殊处理 reasoning_content 的提供商（如硅基流动），
    使用注册表中的专用模型类。
    """
    from langgraph_agent_kit.chat_models.v1.models import V1ChatModel

    provider_lower = provider.lower()

    # 推理模型：从注册表查找专用实现
    if is_reasoning_model and provider_lower in V1_REASONING_MODEL_REGISTRY:
        module_path, class_name = V1_REASONING_MODEL_REGISTRY[provider_lower]

        import importlib
        module = importlib.import_module(module_path)
        model_class = getattr(module, class_name)

        logger.info(
            f"创建 v1 推理模型: model={model}, provider={provider}, class={class_name}"
        )
        return model_class(
            model=model,
            openai_api_base=base_url,
            openai_api_key=api_key,
            **kwargs,
        )

    # 标准 v1 模型
    logger.info(
        f"创建 v1 标准模型: model={model}, provider={provider}, reasoning={is_reasoning_model}"
    )

    return V1ChatModel(
        model=model,
        openai_api_base=base_url,
        openai_api_key=api_key,
        **kwargs,
    )


def _create_v0_model(
    model: str,
    base_url: str,
    api_key: str,
    provider: str,
    is_reasoning_model: bool,
    **kwargs: Any,
) -> BaseChatModel:
    """创建 v0 模型（兼容层）"""
    from langgraph_agent_kit.chat_models.v0.base import StandardChatModel

    provider_lower = provider.lower()

    if not is_reasoning_model:
        logger.info(
            f"创建 v0 标准模型: model={model}, provider={provider}"
        )
        return StandardChatModel(
            model=model,
            openai_api_base=base_url,
            openai_api_key=api_key,
            **kwargs,
        )

    # 推理模型：从注册表查找对应实现
    if provider_lower in V0_REASONING_MODEL_REGISTRY:
        module_path, class_name = V0_REASONING_MODEL_REGISTRY[provider_lower]

        import importlib
        module = importlib.import_module(module_path)
        model_class = getattr(module, class_name)

        logger.info(
            f"创建 v0 推理模型: model={model}, provider={provider}, class={class_name}"
        )
        return model_class(
            model=model,
            openai_api_base=base_url,
            openai_api_key=api_key,
            **kwargs,
        )

    # provider 不在注册表中，降级为标准模型
    logger.warning(
        f"v0 未找到推理模型实现，降级为标准模型: model={model}, provider={provider}"
    )
    return StandardChatModel(
        model=model,
        openai_api_base=base_url,
        openai_api_key=api_key,
        **kwargs,
    )
