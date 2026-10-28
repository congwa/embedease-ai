"""商品身份与事实统一以 SQL 为准，向量仅提供候选和命中片段。"""

import json

from sqlalchemy import select

from app.core.database import get_db_context
from app.models.product import Product


def _decoded(value: str | None, default):
    """读取商品的 JSON 扩展字段，旧数据损坏时不编造规格。"""
    try:
        return json.loads(value) if value else default
    except (TypeError, ValueError):
        return default


async def load_products(product_ids: list[str]) -> dict[str, dict]:
    """按主键精确批量读取商品，不通过语义相似度判断商品是否存在。"""
    if not product_ids:
        return {}
    async with get_db_context() as session:
        rows = (await session.scalars(select(Product).where(Product.id.in_(product_ids)))).all()
        return {
            p.id: {
                "id": p.id,
                "name": p.name,
                "price": p.price,
                "category": p.category,
                "summary": p.summary or "",
                "description": p.description or p.summary or "",
                "url": p.url,
                "brand": p.brand,
                "source_site_id": p.source_site_id,
                "tags": _decoded(p.tags, []),
                "specs": _decoded(p.specs, {}),
                "image_urls": _decoded(p.image_urls, []),
                "extra_metadata": _decoded(p.extra_metadata, {}),
            }
            for p in rows
        }
