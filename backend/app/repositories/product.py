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
    ) -> Product:
        """创建或更新商品"""
        product = await self.get_by_id(product_id)
        if product is None:
            return await self.create_product(
                product_id, name, summary, description, price, category, url
            )
        else:
            product.name = name
            product.summary = summary
            product.description = description
            product.price = price
            product.category = category
            product.url = url
            return await self.update(product)
