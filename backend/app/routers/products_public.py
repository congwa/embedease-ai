"""公开商品 API（无需管理权限，供商城式落地页使用）"""

import json
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session
from app.models.product import Product
from app.schemas.product_public import ProductPublicDetail

router = APIRouter(prefix="/api/v1/products", tags=["products-public"])

_SLUG_SAFE = re.compile(r"^[a-zA-Z0-9][-a-zA-Z0-9_.]{0,127}$")


def _parse_json_list(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data if x is not None]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def _parse_json_dict(raw: str | None) -> dict[str, str]:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items() if v is not None}
    except (json.JSONDecodeError, TypeError):
        pass
    return {}


def _product_to_public(p: Product) -> ProductPublicDetail:
    return ProductPublicDetail(
        id=p.id,
        name=p.name,
        summary=p.summary,
        description=p.description,
        price=p.price,
        category=p.category,
        brand=p.brand,
        url=p.url,
        tags=_parse_json_list(p.tags),
        image_urls=_parse_json_list(p.image_urls),
        specs=_parse_json_dict(p.specs),
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


@router.get("/by-slug/{slug}", response_model=ProductPublicDetail)
async def get_product_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db_session),
):
    """按 URL 路径 slug 解析商品（与 fixture 中 /products/<slug> 一致）"""
    if not _SLUG_SAFE.match(slug):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 slug")

    like_suffix = f"%/products/{slug}"
    like_exact = f"%/products/{slug}/%"

    stmt = (
        select(Product)
        .where(
            or_(
                Product.id == slug,
                Product.url.like(like_suffix),
                Product.url.like(like_exact),
            )
        )
        .order_by(Product.updated_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    return _product_to_public(row)


@router.get("/{product_id}", response_model=ProductPublicDetail)
async def get_product_by_id(
    product_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    """按商品 ID（如 P0001）获取详情"""
    if len(product_id) > 80 or not product_id.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的商品 ID")

    row = await db.get(Product, product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="商品不存在")
    return _product_to_public(row)
