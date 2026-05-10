"""嵌入模型模块

提供统一的嵌入模型接口，供记忆系统和其他模块使用。
"""

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("embedding")


@lru_cache
def get_embedding_model() -> OpenAIEmbeddings:
    """获取嵌入模型

    支持所有兼容 OpenAI API 格式的提供商。
    这是 get_embeddings() 的别名，提供更语义化的命名。
    """
    logger.debug(
        "初始化嵌入模型",
        provider=settings.EMBEDDING_PROVIDER,
        model=settings.EMBEDDING_MODEL,
        dimension=settings.EMBEDDING_DIMENSION,
    )
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.effective_embedding_base_url,
        api_key=settings.effective_embedding_api_key,
        dimensions=settings.EMBEDDING_DIMENSION,
    )


# 别名，保持与 llm.py 的兼容性
get_embeddings = get_embedding_model
