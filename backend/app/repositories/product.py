"""商品 Repository"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.repositories.base import BaseRepository


class ProductRepository(BaseRepository[Product]):
    """商品数据访问"""

    model = Product

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_category(self, category: str) -> list[Product]:
        """根据分类获取商品"""
        result = await self.session.execute(select(Product).where(Product.category == category))
        return list(result.scalars().all())

    async def create_product(
        self,
        product_id: str,
        name: str,
        summary: str | None = None,
        description: str | None = None,
        price: float | None = None,
        category: str | None = None,
        url: str | None = None,
    ) -> Product:
        """创建商品"""
        product = Product(
            id=product_id,
            name=name,
            summary=summary,
            description=description,
            price=price,
            category=category,
            url=url,
        )
        return await self.create(product)

    async def upsert_product(
        self,
        product_id: str,
        name: str,
        summary: str | None = None,
        description: str | None = None,
        price: float | None = None,
        category: str | None = None,
        url: str | None = None,
        tags: str | None = None,
        brand: str | None = None,
        image_urls: str | None = None,
        specs: str | None = None,
        extra_metadata: str | None = None,
        source_site_id: str | None = None,
    ) -> Product:
        """创建或更新商品

        Args:
            product_id: 商品 ID
            name: 商品名称
            summary: 核心卖点
            description: 详细描述
            price: 价格
            category: 分类
            url: 商品链接
            tags: 标签（JSON 字符串）
            brand: 品牌
            image_urls: 图片 URL（JSON 字符串）
            specs: 规格（JSON 字符串）
            extra_metadata: 扩展信息（JSON 字符串）
            source_site_id: 来源站点 ID
        """
        product = await self.get_by_id(product_id)
        if product is None:
            product = Product(
                id=product_id,
                name=name,
                summary=summary,
                description=description,
                price=price,
                category=category,
                url=url,
                tags=tags,
                brand=brand,
                image_urls=image_urls,
                specs=specs,
                extra_metadata=extra_metadata,
                source_site_id=source_site_id,
            )
            return await self.create(product)
        else:
            product.name = name
            product.summary = summary
            product.description = description
            product.price = price
            product.category = category
            product.url = url
            # 扩展字段：仅在有值时更新
            if tags is not None:
                product.tags = tags
            if brand is not None:
                product.brand = brand
            if image_urls is not None:
                product.image_urls = image_urls
            if specs is not None:
                product.specs = specs
            if extra_metadata is not None:
                product.extra_metadata = extra_metadata
            if source_site_id is not None:
                product.source_site_id = source_site_id
            return await self.update(product)
