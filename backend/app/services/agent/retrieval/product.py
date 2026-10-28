"""向量检索服务"""

import asyncio
from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_core.vectorstores import VectorStoreRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

if TYPE_CHECKING:
    pass

from app.core.config import settings
from app.core.health import DependencyStatus, dependency_registry
from app.core.logging import get_logger

logger = get_logger("retriever")


@lru_cache
def get_qdrant_client() -> QdrantClient | None:
    """获取 Qdrant 客户端

    Returns:
        QdrantClient 实例，连接失败时返回 None
    """
    try:
        logger.verbose(
            "│ 连接 Qdrant",
            connection={
                "host": settings.QDRANT_HOST,
                "port": settings.QDRANT_PORT,
            },
        )
        client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=5.0,  # 设置 5 秒超时
        )
        # 测试连接
        client.get_collections()
        logger.debug("│ Qdrant 客户端已创建")
        # 更新健康状态
        dependency_registry.set_status("qdrant", DependencyStatus.HEALTHY)
        return client
    except Exception as e:
        logger.error(
            "Qdrant 连接失败（商品检索）",
            error=str(e),
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            dependency="qdrant",
            report_type="dependency_unavailable",
        )
        # 更新健康状态
        dependency_registry.set_status("qdrant", DependencyStatus.UNHEALTHY, error=str(e))
        return None


@lru_cache
def get_default_product_embeddings() -> OpenAIEmbeddings:
    """商品专用原文编码，保留其他已建索引使用的共享工厂行为。"""
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        base_url=settings.effective_embedding_base_url,
        api_key=settings.effective_embedding_api_key,
        check_embedding_ctx_length=False,
    )


async def get_product_embeddings():
    """商品入库和检索使用同一生效配置，第三方接口统一发送原文。"""
    # 优先从数据库获取 Embedding 配置
    embeddings = None
    try:
        from app.core.database import get_db_context
        from app.services.system_config import get_effective_embedding_config

        async with get_db_context() as session:
            embed_config = await get_effective_embedding_config(session)
            if embed_config.api_key:
                embeddings = OpenAIEmbeddings(
                    model=embed_config.model,
                    base_url=embed_config.base_url,
                    api_key=embed_config.api_key,
                    check_embedding_ctx_length=False,
                )
                logger.verbose(
                    "│ 使用数据库 Embedding 配置",
                    model=embed_config.model,
                    base_url=embed_config.base_url,
                )
    except Exception as e:
        logger.warning("获取数据库 Embedding 配置失败，使用默认配置", error=str(e))

    # 回退到默认配置
    if embeddings is None:
        embeddings = get_default_product_embeddings()

    return embeddings


async def get_vector_store_async() -> QdrantVectorStore | None:
    """获取向量存储（异步版本，优先使用数据库配置）

    Returns:
        QdrantVectorStore 实例，初始化失败时返回 None
    """
    try:
        client = await asyncio.to_thread(get_qdrant_client)
        if client is None:
            return None

        embeddings = await get_product_embeddings()

        logger.verbose(
            "│ 初始化向量存储",
            vector_store={
                "collection": settings.QDRANT_COLLECTION,
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
            },
        )
        info = await asyncio.to_thread(client.get_collection, settings.QDRANT_COLLECTION)
        if info.config.params.vectors.size != settings.EMBEDDING_DIMENSION:
            raise ValueError("商品集合维度与配置不一致")
        # 已核对维度，禁用每次初始化都会发起的 dummy Embedding 请求。
        store = await asyncio.to_thread(
            QdrantVectorStore,
            client=client,
            collection_name=settings.QDRANT_COLLECTION,
            embedding=embeddings,
            validate_collection_config=False,
        )
        logger.debug("│ 向量存储已初始化")
        return store
    except Exception as e:
        logger.error(
            "向量存储初始化失败",
            error=str(e),
            collection=settings.QDRANT_COLLECTION,
            dependency="qdrant",
        )
        return None


@lru_cache
def get_vector_store() -> QdrantVectorStore | None:
    """获取向量存储（同步版本，使用环境变量配置）

    注意：此函数使用 lru_cache，首次调用后会缓存结果。
    如需使用数据库配置，请使用 get_vector_store_async。

    Returns:
        QdrantVectorStore 实例，初始化失败时返回 None
    """
    try:
        client = get_qdrant_client()
        if client is None:
            return None

        embeddings = get_default_product_embeddings()

        logger.verbose(
            "│ 初始化向量存储",
            vector_store={
                "collection": settings.QDRANT_COLLECTION,
                "embedding_model": settings.EMBEDDING_MODEL,
                "embedding_dimension": settings.EMBEDDING_DIMENSION,
            },
        )
        store = QdrantVectorStore(
            client=client,
            collection_name=settings.QDRANT_COLLECTION,
            embedding=embeddings,
        )
        logger.debug("│ 向量存储已初始化")
        return store
    except Exception as e:
        logger.error(
            "向量存储初始化失败",
            error=str(e),
            collection=settings.QDRANT_COLLECTION,
            dependency="qdrant",
        )
        return None


def get_retriever(k: int = 5) -> VectorStoreRetriever | None:
    """获取检索器（同步版本）

    Returns:
        VectorStoreRetriever 实例，初始化失败时返回 None
    """
    vector_store = get_vector_store()
    if vector_store is None:
        logger.warning("向量存储不可用，无法创建检索器")
        return None

    logger.debug(
        "│ 创建检索器",
        retriever_config={"k": k, "search_type": "similarity"},
    )
    return vector_store.as_retriever(search_kwargs={"k": k})


async def get_retriever_async(k: int = 5) -> VectorStoreRetriever | None:
    """获取检索器（异步版本，优先使用数据库配置）

    Returns:
        VectorStoreRetriever 实例，初始化失败时返回 None
    """
    vector_store = await get_vector_store_async()
    if vector_store is None:
        logger.warning("向量存储不可用，无法创建检索器")
        return None

    logger.debug(
        "│ 创建检索器（异步）",
        retriever_config={"k": k, "search_type": "similarity"},
    )
    return vector_store.as_retriever(search_kwargs={"k": k})
