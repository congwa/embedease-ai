"""向量检索服务"""

from functools import lru_cache

from langchain_core.vectorstores import VectorStoreRetriever
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.core.config import settings
from app.core.llm import get_embeddings
from app.core.logging import get_logger

logger = get_logger("retriever")


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """获取 Qdrant 客户端"""
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
    )
    logger.debug("│ Qdrant 客户端已创建")
    return client


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    """获取向量存储"""
    client = get_qdrant_client()
    embeddings = get_embeddings()

    logger.info(
        "│ 初始化向量存储",
        vector_store={
            "collection": settings.QDRANT_COLLECTION,
            "embedding_model": settings.SILICONFLOW_EMBEDDING_MODEL,
            "embedding_dimension": settings.SILICONFLOW_EMBEDDING_DIMENSION,
        },
    )
    store = QdrantVectorStore(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
        embedding=embeddings,
    )
    logger.debug("│ 向量存储已初始化")
    return store


def get_retriever(k: int = 5) -> VectorStoreRetriever:
    """获取检索器"""
    vector_store = get_vector_store()
    logger.debug(
        "│ 创建检索器",
        retriever_config={"k": k, "search_type": "similarity"},
    )
    return vector_store.as_retriever(search_kwargs={"k": k})
