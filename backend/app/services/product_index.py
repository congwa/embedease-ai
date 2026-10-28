"""商品向量增量索引：先写完整新块，再仅回收同一商品的旧块。"""

import asyncio
import hashlib
import json
import uuid

from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.services.agent.retrieval.product import get_product_embeddings
from app.utils.text import split_text


def product_documents(product: dict) -> list[tuple[str, dict]]:
    """分块保留商品身份和规格；长文命中片段不丢掉所属商品信息。"""
    metadata = {
        "product_id": product["id"],
        "product_name": product["name"],
        **{
            k: product.get(k)
            for k in [
                "price",
                "category",
                "url",
                "brand",
                "tags",
                "image_urls",
                "source_site_id",
                "extra_metadata",
                "specs",
                "summary",
            ]
        },
        "embedding_input": "raw_text",
    }
    header = "\n".join(
        [
            f"商品ID: {product['id']}",
            f"商品名称: {product['name']}",
            f"品牌: {product.get('brand') or ''}",
            f"分类: {product.get('category') or ''}",
            f"价格: {product.get('price')}",
            f"核心卖点: {product.get('summary') or ''}",
            f"标签: {', '.join(product.get('tags') or [])}",
            f"规格: {json.dumps(product.get('specs') or {}, ensure_ascii=False)}",
        ]
    )
    description = product.get("description") or ""
    if len(description) <= settings.CHUNK_SIZE:
        return [(header + "\n" + description, {**metadata, "chunk_index": 0})]
    return [(header, {**metadata, "chunk_index": 0})] + [
        (header + "\n" + chunk, {**metadata, "chunk_index": i + 1})
        for i, chunk in enumerate(split_text(description))
    ]


async def index_products(products: list[dict]) -> None:
    """独立商品逐件发布；失败时保留旧块，重跑按稳定身份幂等清理。"""
    ids = [p["id"] for p in products]
    if len(ids) != len(set(ids)):
        raise ValueError("导入批次包含重复商品 ID")
    embeddings = await get_product_embeddings()
    client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=30)
    collection = settings.QDRANT_COLLECTION
    try:
        if not await asyncio.to_thread(client.collection_exists, collection):
            await asyncio.to_thread(
                client.create_collection,
                collection,
                vectors_config=models.VectorParams(
                    size=settings.EMBEDDING_DIMENSION, distance=models.Distance.COSINE
                ),
            )
        info = await asyncio.to_thread(client.get_collection, collection)
        if info.config.params.vectors.size != settings.EMBEDDING_DIMENSION:
            raise ValueError("集合维度与生效 Embedding 不一致，必须在新集合重建")
        existing, _ = await asyncio.to_thread(
            client.scroll, collection, limit=1, with_payload=True, with_vectors=False
        )
        model = getattr(embeddings, "model", settings.EMBEDDING_MODEL)
        if existing:
            profile = (existing[0].payload or {}).get("metadata", {})
            if (
                profile.get("embedding_input") != "raw_text"
                or profile.get("embedding_model") != model
            ):
                raise ValueError("旧索引编码或模型不一致，必须在新集合中完整重建后切换")
        for product in products:
            documents = product_documents(product)
            vectors = await embeddings.aembed_documents([text for text, _ in documents])
            if len(vectors) != len(documents) or any(
                len(v) != settings.EMBEDDING_DIMENSION for v in vectors
            ):
                raise ValueError("Embedding 返回数量或维度错误")
            # 内容批次进入点身份：新块全部写好之前，旧块仍可检索。
            revision = hashlib.sha256(
                json.dumps(product, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            points = [
                models.PointStruct(
                    id=str(
                        uuid.uuid5(uuid.NAMESPACE_URL, f"product:{product['id']}:{revision}:{i}")
                    ),
                    vector=vector,
                    payload={
                        "page_content": text,
                        "metadata": {**metadata, "embedding_model": model},
                    },
                )
                for i, ((text, metadata), vector) in enumerate(zip(documents, vectors))
            ]
            await asyncio.to_thread(client.upsert, collection, points=points, wait=True)
            stale = models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.product_id", match=models.MatchValue(value=product["id"])
                    )
                ],
                must_not=[models.HasIdCondition(has_id=[p.id for p in points])],
            )
            await asyncio.to_thread(
                client.delete,
                collection,
                points_selector=models.FilterSelector(filter=stale),
                wait=True,
            )
            if (
                await asyncio.to_thread(client.count, collection, count_filter=stale, exact=True)
            ).count:
                raise RuntimeError("商品旧向量清理未完成，请重试当前批次")
    finally:
        client.close()


async def remove_product_vectors(product_id: str) -> None:
    """只清理指定商品；SQL 删除后检索层会立即隐藏遗留向量。"""
    client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=30)
    try:
        selector = models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.product_id", match=models.MatchValue(value=product_id)
                    )
                ]
            )
        )
        await asyncio.to_thread(
            client.delete, settings.QDRANT_COLLECTION, points_selector=selector, wait=True
        )
    finally:
        client.close()
