"""LLM 初始化模块"""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings

from app.core.chat_models import create_chat_model
from app.core.config import settings
from app.core.logging import get_logger
from app.core.models_dev import get_model_profile

logger = get_logger("llm")


@lru_cache
def get_chat_model(
    *,
    model: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """获取聊天模型

    Args:
        model: 可选，覆盖默认聊天模型 ID（例如爬虫/记忆模块使用独立模型）
        provider: 可选，覆盖默认提供商
        api_key: 可选，覆盖默认 API Key
        base_url: 可选，覆盖默认 Base URL
        temperature: 可选，模型温度（爬虫等场景建议使用 0 以获得稳定输出）

    支持的提供商：OpenAI、Anthropic、DeepSeek、SiliconFlow 等
    模型 profile 获取流程：
    1. 如果启用 models.dev（MODELS_DEV_ENABLED=true），从 api.json 拉取基础配置
    2. 用 .env 的 MODEL_PROFILES_JSON 覆盖（env 优先）
    3. 拉取失败时回退到纯 .env 配置（不影响启动）
    """
    model_name = model or settings.LLM_CHAT_MODEL
    provider_name = provider or settings.LLM_PROVIDER
    api_key_value = api_key or settings.LLM_API_KEY
    base_url_value = base_url or settings.LLM_BASE_URL

    logger.info(
        "初始化聊天模型",
        provider=provider_name,
        model=model_name,
    )

    # 获取最终 profile（models.dev + .env 合并）
    if settings.MODELS_DEV_ENABLED:
        custom_profile = get_model_profile(
            model_name=model_name,
            api_url=settings.MODELS_DEV_API_URL,
            provider_id=provider_name,
            timeout_seconds=settings.MODELS_DEV_TIMEOUT_SECONDS,
            cache_ttl_seconds=settings.MODELS_DEV_CACHE_TTL_SECONDS,
            env_profiles=settings.model_profiles,
        )
    else:
        # models.dev 禁用，仅使用 .env 配置
        model_key = model_name.strip().lower()
        custom_profile = settings.model_profiles.get(model_key, {})
        logger.info(
            "models.dev 已禁用，仅使用 .env 配置",
            provider=provider_name,
            model=model_name,
            profile=custom_profile,
        )

    # 如果 profile 为空，传 None 让 LangChain 使用默认行为
    profile_arg = custom_profile if custom_profile else None

    # 使用统一的模型创建接口
    # ModelRegistry 会自动根据模型特征选择合适的实现（完全无感知）
    # 从 profile 中提取参数（如果存在）
    model_kwargs = {}
    # 优先使用显式传入的 temperature，否则从 profile 中获取
    if temperature is not None:
        model_kwargs["temperature"] = temperature
    elif profile_arg and isinstance(profile_arg, dict) and "temperature" in profile_arg:
        model_kwargs["temperature"] = profile_arg["temperature"]

    if profile_arg and isinstance(profile_arg, dict):
        if "max_tokens" in profile_arg:
            model_kwargs["max_tokens"] = profile_arg["max_tokens"]
        if "max_completion_tokens" in profile_arg:
            model_kwargs["max_completion_tokens"] = profile_arg["max_completion_tokens"]

    # 使用统一的创建接口，根据 provider 和 profile 自动选择合适的实现
    model = create_chat_model(
        model=model_name,
        base_url=base_url_value,
        api_key=api_key_value,
        provider=provider_name,  # 传递提供商标识
        profile=custom_profile,  # 传递 profile 用于选择正确的实现
        **model_kwargs,
    )

    # 如果 profile 存在，尝试设置到模型上（某些实现可能需要）
    if profile_arg and hasattr(model, "profile"):
        try:
            model.profile = profile_arg
        except Exception:  # noqa: BLE001
            pass  # 某些实现可能不支持 profile 属性

    # 打印最终生效的 profile
    try:
        actual_profile = getattr(model, "profile", None)
        logger.info(
            "模型初始化完成",
            provider=provider_name,
            model=model_name,
            structured_output=(actual_profile or {}).get("structured_output")
            if isinstance(actual_profile, dict)
            else None,
            reasoning_output=(actual_profile or {}).get("reasoning_output")
            if isinstance(actual_profile, dict)
            else None,
            tool_calling=(actual_profile or {}).get("tool_calling")
            if isinstance(actual_profile, dict)
            else None,
            final_profile=actual_profile,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("读取模型 profile 失败", error=str(e))

    return model


@lru_cache
def get_memory_model() -> BaseChatModel:
    """获取 Memory 专用模型

    用于记忆系统的事实抽取、图谱抽取等任务。
    可以配置独立的模型（如更便宜的模型），不设置则复用聊天模型。
    """
    # 如果没有配置独立的 Memory 模型，直接返回聊天模型
    if not settings.MEMORY_MODEL:
        logger.debug(
            "Memory 使用主聊天模型",
            model=settings.LLM_CHAT_MODEL,
        )
        return get_chat_model()

    logger.info(
        "初始化 Memory 专用模型",
        provider=settings.effective_memory_provider,
        model=settings.effective_memory_model,
    )

    # 获取 profile（如果启用 models.dev）
    custom_profile = None
    if settings.MODELS_DEV_ENABLED:
        custom_profile = get_model_profile(
            model_name=settings.effective_memory_model,
            api_url=settings.MODELS_DEV_API_URL,
            provider_id=settings.effective_memory_provider,
            timeout_seconds=settings.MODELS_DEV_TIMEOUT_SECONDS,
            cache_ttl_seconds=settings.MODELS_DEV_CACHE_TTL_SECONDS,
            env_profiles=settings.model_profiles,
        )
    else:
        model_key = settings.effective_memory_model.strip().lower()
        custom_profile = settings.model_profiles.get(model_key, {})

    # 从 profile 中提取参数
    model_kwargs = {}
    if custom_profile and isinstance(custom_profile, dict):
        if "temperature" in custom_profile:
            model_kwargs["temperature"] = custom_profile["temperature"]
        if "max_tokens" in custom_profile:
            model_kwargs["max_tokens"] = custom_profile["max_tokens"]

    # 创建 Memory 专用模型
    model = create_chat_model(
        model=settings.effective_memory_model,
        base_url=settings.effective_memory_base_url,
        api_key=settings.effective_memory_api_key,
        provider=settings.effective_memory_provider,
        profile=custom_profile,
        **model_kwargs,
    )

    logger.info(
        "Memory 模型初始化完成",
        provider=settings.effective_memory_provider,
        model=settings.effective_memory_model,
    )

    return model


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """获取嵌入模型

    支持所有兼容 OpenAI API 格式的提供商
    """
    logger.info(
        "初始化嵌入模型",
        provider=settings.EMBEDDING_PROVIDER,
        model=settings.EMBEDDING_MODEL,
        dimension=settings.EMBEDDING_DIMENSION,
    )
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.effective_embedding_base_url,
        api_key=settings.effective_embedding_api_key,
    )
