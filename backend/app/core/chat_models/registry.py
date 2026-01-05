"""模型创建工厂（多态架构）

============================================================
核心职责
============================================================

- 提供 `create_chat_model` 函数：对外统一创建入口
- 根据 provider 和 profile 自动选择合适的模型实现

============================================================
选择逻辑
============================================================

1. 检查 profile.reasoning_output 判断是否为推理模型
2. 非推理模型 → StandardChatModel（直接使用 LangChain OpenAI）
3. 推理模型 → 根据 provider 选择对应的实现类

============================================================
扩展方式
============================================================

新增平台只需：
1. 在 `providers/` 下创建新的实现类
2. 在本文件的 `REASONING_MODEL_REGISTRY` 中注册
3. Agent 层无需任何修改
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models import BaseChatModel

from app.core.chat_models.base import StandardChatModel
from app.core.logging import get_logger

logger = get_logger("chat_models.registry")


# ============================================================
# 推理模型注册表
# ============================================================
# 新增平台只需在此添加映射，无需修改其他代码
# key: provider 名称（小写）
# value: 模型类的导入路径和类名

REASONING_MODEL_REGISTRY: dict[str, tuple[str, str]] = {
    "siliconflow": (
        "app.core.chat_models.providers.reasoning_content",
        "SiliconFlowReasoningChatModel",
    ),
    # 未来新增平台示例：
    # "moonshot": (
    #     "app.core.chat_models.providers.moonshot",
    #     "MoonshotReasoningChatModel",
    # ),
}


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
        provider: 提供商标识（如 siliconflow, openai）
        profile: 模型能力配置（可选，包含 reasoning_output 等信息）
        **kwargs: 其他参数（temperature, max_tokens 等）

    Returns:
        配置好的模型实例

    选择逻辑：
        1. reasoning_output=False → StandardChatModel
        2. reasoning_output=True + provider 在注册表中 → 对应的推理模型
        3. reasoning_output=True + provider 不在注册表中 → StandardChatModel（降级）
    """
    # 提取 profile 信息
    if profile is None:
        profile = kwargs.pop("profile", {})

    # 判断是否为推理模型
    is_reasoning_model = profile.get("reasoning_output", False) if profile else False
    provider_lower = provider.lower()

    if not is_reasoning_model:
        # 普通模型，使用标准实现
        logger.info(
            "创建标准模型",
            model=model,
            provider=provider,
        )
        return StandardChatModel(
            model=model,
            openai_api_base=base_url,
            openai_api_key=api_key,
            **kwargs,
        )

    # 推理模型：从注册表查找对应实现
    if provider_lower in REASONING_MODEL_REGISTRY:
        module_path, class_name = REASONING_MODEL_REGISTRY[provider_lower]

        # 动态导入模型类
        import importlib
        module = importlib.import_module(module_path)
        model_class = getattr(module, class_name)

        logger.info(
            "创建推理模型",
            model=model,
            provider=provider,
            model_class=class_name,
        )
        return model_class(
            model=model,
            openai_api_base=base_url,
            openai_api_key=api_key,
            **kwargs,
        )

    # provider 不在注册表中，降级为标准模型
    logger.warning(
        "未找到推理模型实现，降级为标准模型",
        model=model,
        provider=provider,
        registered_providers=list(REASONING_MODEL_REGISTRY.keys()),
    )
    return StandardChatModel(
        model=model,
        openai_api_base=base_url,
        openai_api_key=api_key,
        **kwargs,
    )
