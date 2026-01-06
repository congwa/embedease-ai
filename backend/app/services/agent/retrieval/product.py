"""向量检索服务"""

from functools import lru_cache
from typing import TYPE_CHECKING

from langchain_core.vectorstores import VectorStoreRetriever
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

if TYPE_CHECKING:
    pass

from app.core.config import settings
from app.core.health import DependencyStatus, dependency_registry
from app.core.llm import get_embeddings
from app.core.logging import get_logger

logger = get_logger("retriever")


@lru_cache
def get_qdrant_client() -> QdrantClient | None:
    """获取 Qdrant 客户端
    
    Returns:
        QdrantClient 实例，连接失败时返回 None
    """
    try:
        logger.info(
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
def get_vector_store() -> QdrantVectorStore | None:
    """获取向量存储
    
    Returns:
        QdrantVectorStore 实例，初始化失败时返回 None
    """
    try:
        client = get_qdrant_client()
        if client is None:
            return None
            
        embeddings = get_embeddings()

        logger.info(
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
    """获取检索器
    
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
