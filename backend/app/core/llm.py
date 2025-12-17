"""LLM 初始化模块"""

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logging import get_logger
from app.core.models_dev import get_model_profile
from app.core.chat_models import create_chat_model

logger = get_logger("llm")


@lru_cache
def get_chat_model() -> BaseChatModel:
    """获取聊天模型

    支持的提供商：OpenAI、Anthropic、DeepSeek、SiliconFlow 等
    模型 profile 获取流程：
    1. 如果启用 models.dev（MODELS_DEV_ENABLED=true），从 api.json 拉取基础配置
    2. 用 .env 的 MODEL_PROFILES_JSON 覆盖（env 优先）
    3. 拉取失败时回退到纯 .env 配置（不影响启动）
    """
    logger.info(
        "初始化聊天模型",
        provider=settings.LLM_PROVIDER,
        model=settings.LLM_CHAT_MODEL,
    )

    # 获取最终 profile（models.dev + .env 合并）
    if settings.MODELS_DEV_ENABLED:
        custom_profile = get_model_profile(
            model_name=settings.LLM_CHAT_MODEL,
            api_url=settings.MODELS_DEV_API_URL,
            provider_id=settings.effective_models_dev_provider_id,
            timeout_seconds=settings.MODELS_DEV_TIMEOUT_SECONDS,
            cache_ttl_seconds=settings.MODELS_DEV_CACHE_TTL_SECONDS,
            env_profiles=settings.model_profiles,
        )
    else:
        # models.dev 禁用，仅使用 .env 配置
        model_key = settings.LLM_CHAT_MODEL.strip().lower()
        custom_profile = settings.model_profiles.get(model_key, {})
        logger.info(
            "models.dev 已禁用，仅使用 .env 配置",
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_CHAT_MODEL,
            profile=custom_profile,
        )

    # 如果 profile 为空，传 None 让 LangChain 使用默认行为
    profile_arg = custom_profile if custom_profile else None

    # 使用统一的模型创建接口
    # ModelRegistry 会自动根据模型特征选择合适的实现（完全无感知）
    # 从 profile 中提取参数（如果存在）
    model_kwargs = {}
    if profile_arg and isinstance(profile_arg, dict):
        if "temperature" in profile_arg:
            model_kwargs["temperature"] = profile_arg["temperature"]
        if "max_tokens" in profile_arg:
            model_kwargs["max_tokens"] = profile_arg["max_tokens"]
        if "max_completion_tokens" in profile_arg:
            model_kwargs["max_completion_tokens"] = profile_arg["max_completion_tokens"]

    # 使用统一的创建接口，根据 provider 和 profile 自动选择合适的实现
    model = create_chat_model(
        model=settings.LLM_CHAT_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        provider=settings.LLM_PROVIDER,  # 传递提供商标识
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
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_CHAT_MODEL,
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
