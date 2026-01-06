"""记忆向量存储模块

提供独立的 Qdrant 集合用于事实记忆的向量存储与检索。
与商品向量存储（QDRANT_COLLECTION）隔离，避免相互干扰。
"""

from functools import lru_cache

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings
from app.core.health import DependencyStatus, dependency_registry
from app.core.llm import get_embeddings
from app.core.logging import get_logger

logger = get_logger("memory.vector_store")


@lru_cache
def get_memory_qdrant_client() -> QdrantClient | None:
    """获取记忆专用 Qdrant 客户端（复用连接配置）
    
    Returns:
        QdrantClient 实例，连接失败时返回 None
    """
    try:
        logger.debug(
            "连接 Qdrant（记忆集合）",
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
        )
        client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            timeout=5.0,  # 设置 5 秒超时，避免长时间阻塞
        )
        # 测试连接
        client.get_collections()
        # 更新健康状态
        dependency_registry.set_status("qdrant", DependencyStatus.HEALTHY)
        return client
    except Exception as e:
        logger.error(
            "Qdrant 连接失败（记忆服务）",
            error=str(e),
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            dependency="qdrant",
            report_type="dependency_unavailable",
        )
        # 更新健康状态
        dependency_registry.set_status("qdrant", DependencyStatus.UNHEALTHY, error=str(e))
        return None


def ensure_memory_collection() -> bool:
    """确保记忆集合存在，不存在则创建
    
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        client = get_memory_qdrant_client()
        if client is None:
            return False
            
        collection_name = settings.MEMORY_FACT_COLLECTION

        collections = client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            logger.debug("记忆集合已存在", collection=collection_name)
            return True

        logger.info(
            "创建记忆集合",
            collection=collection_name,
            dimension=settings.EMBEDDING_DIMENSION,
        )
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            ),
        )
        return True
    except Exception as e:
        logger.error(
            "记忆集合初始化失败",
            error=str(e),
            collection=settings.MEMORY_FACT_COLLECTION,
            dependency="qdrant",
        )
        return False


@lru_cache
def get_memory_vector_store() -> QdrantVectorStore | None:
    """获取记忆向量存储（独立集合）

    与商品向量存储隔离，使用 MEMORY_FACT_COLLECTION 集合。
    
    Returns:
        QdrantVectorStore 实例，初始化失败时返回 None
    """
    try:
        if not ensure_memory_collection():
            return None

        client = get_memory_qdrant_client()
        if client is None:
            return None
            
        embeddings = get_embeddings()

        logger.info(
            "初始化记忆向量存储",
            collection=settings.MEMORY_FACT_COLLECTION,
            embedding_model=settings.EMBEDDING_MODEL,
            embedding_dimension=settings.EMBEDDING_DIMENSION,
        )
        return QdrantVectorStore(
            client=client,
            collection_name=settings.MEMORY_FACT_COLLECTION,
            embedding=embeddings,
        )
    except Exception as e:
        logger.error(
            "记忆向量存储初始化失败",
            error=str(e),
            collection=settings.MEMORY_FACT_COLLECTION,
            dependency="qdrant",
        )
        return None
