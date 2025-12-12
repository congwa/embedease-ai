"""LLM 初始化模块"""

from functools import lru_cache

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logging import get_logger
from app.core.models_dev import get_model_profile

logger = get_logger("llm")


@lru_cache
def get_chat_model() -> BaseChatModel:
    """获取聊天模型（硅基流动）

    模型 profile 获取流程：
    1. 如果启用 models.dev（MODELS_DEV_ENABLED=true），从 api.json 拉取基础配置
    2. 用 .env 的 SILICONFLOW_MODEL_PROFILES_JSON 覆盖（env 优先）
    3. 拉取失败时回退到纯 .env 配置（不影响启动）
    """
    logger.info("初始化聊天模型", model=settings.SILICONFLOW_CHAT_MODEL)

    # 获取最终 profile（models.dev + .env 合并）
    if settings.MODELS_DEV_ENABLED:
        custom_profile = get_model_profile(
            model_name=settings.SILICONFLOW_CHAT_MODEL,
            api_url=settings.MODELS_DEV_API_URL,
            provider_id=settings.MODELS_DEV_PROVIDER_ID,
            timeout_seconds=settings.MODELS_DEV_TIMEOUT_SECONDS,
            cache_ttl_seconds=settings.MODELS_DEV_CACHE_TTL_SECONDS,
            env_profiles=settings.siliconflow_model_profiles,
        )
    else:
        # models.dev 禁用，仅使用 .env 配置
        model_key = settings.SILICONFLOW_CHAT_MODEL.strip().lower()
        custom_profile = settings.siliconflow_model_profiles.get(model_key, {})
        logger.info(
            "models.dev 已禁用，仅使用 .env 配置",
            model=settings.SILICONFLOW_CHAT_MODEL,
            profile=custom_profile,
        )

    # 如果 profile 为空，传 None 让 LangChain 使用默认行为
    profile_arg = custom_profile if custom_profile else None

    model = init_chat_model(
        f"openai:{settings.SILICONFLOW_CHAT_MODEL}",
        base_url=settings.SILICONFLOW_BASE_URL,
        api_key=settings.SILICONFLOW_API_KEY,
        profile=profile_arg,
    )

    # 打印最终生效的 profile
    try:
        actual_profile = getattr(model, "profile", None)
        logger.info(
            "模型初始化完成",
            model=settings.SILICONFLOW_CHAT_MODEL,
            structured_output=(actual_profile or {}).get("structured_output") if isinstance(actual_profile, dict) else None,
            reasoning_output=(actual_profile or {}).get("reasoning_output") if isinstance(actual_profile, dict) else None,
            tool_calling=(actual_profile or {}).get("tool_calling") if isinstance(actual_profile, dict) else None,
            final_profile=actual_profile,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("读取模型 profile 失败", error=str(e))

    return model


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """获取嵌入模型（硅基流动）"""
    logger.info(
        "初始化嵌入模型",
        model=settings.SILICONFLOW_EMBEDDING_MODEL,
        dimension=settings.SILICONFLOW_EMBEDDING_DIMENSION,
    )
    return OpenAIEmbeddings(
        model=settings.SILICONFLOW_EMBEDDING_MODEL,
        base_url=settings.SILICONFLOW_BASE_URL,
        api_key=settings.SILICONFLOW_API_KEY,
    )
