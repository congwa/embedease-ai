"""面向访客的商品展示 Schema（不含管理字段）"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProductPublicDetail(BaseModel):
    """商品详情（公开）"""

    id: str
    name: str
    summary: str | None = None
    description: str | None = None
    price: float | None = None
    category: str | None = None
    brand: str | None = None
    url: str | None = None
    tags: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    specs: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
