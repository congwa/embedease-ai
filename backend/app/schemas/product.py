"""商品相关 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """创建商品请求

    扩展字段（向后兼容，均为可选）：
    - tags: 商品标签列表
    - brand: 品牌名称
    - image_urls: 商品图片 URL 列表
    - specs: 商品规格字典
    - extra_metadata: 其他扩展信息字典
    - source_site_id: 来源站点 ID
    """

    id: str = Field(..., description="商品 ID")
    name: str = Field(..., description="商品名称")
    summary: str | None = Field(None, description="核心卖点（100字以内）")
    description: str | None = Field(None, description="详细描述")
    price: float | None = Field(None, description="价格")
    category: str | None = Field(None, description="分类")
    url: str | None = Field(None, description="商品链接")

    # 扩展字段
    tags: list[str] | None = Field(None, description="商品标签列表")
    brand: str | None = Field(None, description="品牌名称")
    image_urls: list[str] | None = Field(None, description="商品图片 URL 列表")
    specs: dict[str, str] | None = Field(None, description="商品规格")
    extra_metadata: dict | None = Field(None, description="其他扩展信息")
    source_site_id: str | None = Field(None, description="来源站点 ID")


class ProductResponse(BaseModel):
    """商品响应"""

    id: str
    name: str
    summary: str | None
    price: float | None
    category: str | None
    url: str | None
    tags: list[str] | None = None
    brand: str | None = None
    image_urls: list[str] | None = None
    specs: dict[str, str] | None = None
    extra_metadata: dict | None = None
    source_site_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductSearchResult(BaseModel):
    """商品搜索结果"""

    id: str
    name: str
    summary: str | None
    price: float | None
    url: str | None
    brand: str | None = None
    image_urls: list[str] | None = None
