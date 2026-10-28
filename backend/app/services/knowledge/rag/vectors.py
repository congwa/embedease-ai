"""Qdrant 适配器：只处理托管集合，所有检索强制注入知识源过滤。"""

import math
from contextlib import asynccontextmanager

from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

from app.core.config import settings
from app.services.knowledge.rag.settings import RagError


@asynccontextmanager
async def qdrant():
    """为一次操作创建客户端，当前 SDK 不实现异步上下文管理，显式关闭。"""
    client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=30)
    try:
        yield client
    finally:
        await client.close()


def validate_vectors(vectors: list, expected: int, dimension: int) -> None:
    """拒绝缺项、错误维度、零向量及非有限数，禁止发布不完整索引。"""
    if len(vectors) != expected:
        raise RagError("Embedding 返回数量不匹配")
    for vector in vectors:
        if len(vector) != dimension or not all(math.isfinite(v) for v in vector):
            raise RagError("Embedding 向量维度或数值无效")
        if not any(v != 0 for v in vector):
            raise RagError("Embedding 返回零向量")


async def ensure_collection(client: AsyncQdrantClient, name: str, dimension: int) -> None:
    """幂等创建并检查维度；同名但不兼容的集合不能复用。"""
    if not name.startswith("kb_managed_v1_"):
        raise RagError("禁止写入非托管 collection")
    if not await client.collection_exists(name):
        try:
            await client.create_collection(
                name,
                vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
            )
        except UnexpectedResponse as exc:
            if exc.status_code != 409:
                raise
    info = await client.get_collection(name)
    vectors = info.config.params.vectors
    if not isinstance(vectors, models.VectorParams) or vectors.size != dimension:
        raise RagError("已有 collection 的向量配置不兼容", 409)
    for key in ("config_id", "document_id", "revision_id"):
        await client.create_payload_index(name, key, models.PayloadSchemaType.KEYWORD, wait=True)


def scope_filter(config_id: str, **values: str) -> models.Filter:
    """将资源归属放在数据库查询之外的第二道检索边界。"""
    return models.Filter(
        must=[
            models.FieldCondition(key=k, match=models.MatchValue(value=v))
            for k, v in {"config_id": config_id, **values}.items()
        ]
    )


async def remove_revision(collection: str, config_id: str, revision_id: str) -> None:
    """按版本删除向量；集合不存在视作已清理。"""
    async with qdrant() as client:
        if await client.collection_exists(collection):
            await client.delete(
                collection,
                models.FilterSelector(filter=scope_filter(config_id, revision_id=revision_id)),
                wait=True,
            )
            # wait=True 确认操作完成后，再核对数量；未确认清理不能报告入库成功。
            remaining = await client.count(
                collection,
                count_filter=scope_filter(config_id, revision_id=revision_id),
                exact=True,
            )
            if remaining.count:
                raise ConnectionError("旧版本向量清理尚未完成")
