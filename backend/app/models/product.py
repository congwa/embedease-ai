"""商品模型"""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Product(Base):
    """商品表

    扩展字段说明：
    - tags: 商品标签，JSON 数组格式，如 ["热销", "新品"]
    - brand: 品牌名称
    - image_urls: 商品图片 URL 列表，JSON 数组格式
    - specs: 商品规格，JSON 对象格式，如 {"颜色": "红色", "尺寸": "XL"}
    - extra_metadata: 其他扩展信息，JSON 对象格式
    - source_site_id: 来源站点 ID（关联爬取模块）
    """

    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 扩展字段
    tags: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="商品标签（JSON 数组）"
    )
    brand: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="品牌名称"
    )
    image_urls: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="商品图片 URL（JSON 数组）"
    )
    specs: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="商品规格（JSON 对象）"
    )
    extra_metadata: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="其他扩展信息（JSON 对象）"
    )

    # 来源追溯
    source_site_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="来源站点 ID"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
