"""列出精选商品工具

## 功能描述
根据标签列出精选商品，如热门商品、新品、高性价比商品等。

## 使用场景
- 用户询问："有什么热门商品推荐？"
- 用户想看新品或特色商品
- 需要展示精选商品列表

## 输出格式
返回精选商品列表，每个商品包含：
- id: 商品编号
- name: 商品名称
- price: 价格
- summary: 商品摘要
- url: 商品链接
- category: 商品分类
- tags: 商品标签
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.product import Product
from app.schemas.events import StreamEventType

logger = get_logger("tool.list_featured_products")


class FeaturedProduct(BaseModel):
    """精选商品模型"""

    id: str = Field(description="商品编号")
    name: str = Field(description="商品名称")
    price: float | None = Field(description="价格")
    summary: str | None = Field(description="商品摘要")
    url: str | None = Field(description="商品链接")
    category: str | None = Field(description="商品分类")


class ListFeaturedProductsResponse(BaseModel):
    """列出精选商品的返回结果"""

    tag: str = Field(description="标签名称")
    products: list[FeaturedProduct] = Field(description="精选商品列表")
    total_count: int = Field(description="商品数量")


@tool
async def list_featured_products(
    runtime: ToolRuntime,
    tag: Annotated[
        str | None,
        Field(
            default="all",
            description="商品标签，可选值：hot（热门）、new（新品）、budget（高性价比）、all（全部）",
        ),
    ] = "all",
    limit: Annotated[int | None, Field(default=10, description="返回的商品数量上限")] = 10,
) -> str:
    """列出精选商品。

    根据标签返回精选商品列表，如热门商品、新品、高性价比商品等。
    适用于用户想看推荐商品或特色商品时使用。

    Args:
        tag: 商品标签，可选值：
             - "hot": 热门商品（按价格降序）
             - "new": 新品（按商品编号降序）
             - "budget": 高性价比商品（价格较低的商品）
             - "all": 全部商品（默认）
        limit: 返回的商品数量上限，默认为10

    Returns:
        精选商品列表的结构化字符串，包含商品信息。

    Examples:
        >>> list_featured_products(tag="hot")
        '[{"id": "P0001", "name": "...", "price": 999.0, ...}]'

        >>> list_featured_products(tag="budget", limit=5)
        '[{"id": "P0079", "name": "...", "price": 169.0, ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "list_featured_products",
            "input": {"tag": tag, "limit": limit},
        },
    )

    logger.info(
        "┌── 工具: list_featured_products 开始 ──┐",
        input_data={"tag": tag, "limit": limit},
    )

    try:
        async with get_db_context() as session:
            # 根据标签构建查询
            stmt = select(Product)

            if tag == "hot":
                # 热门商品：按价格降序（假设价格高的是热门商品）
                stmt = stmt.order_by(Product.price.desc())
            elif tag == "new":
                # 新品：按商品编号降序（假设编号越大越新）
                stmt = stmt.order_by(Product.id.desc())
            elif tag == "budget":
                # 高性价比：按价格升序
                stmt = stmt.where(Product.price.isnot(None)).order_by(Product.price.asc())
            else:
                # 全部商品：按商品编号排序
                stmt = stmt.order_by(Product.id)

            stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            products = result.scalars().all()

            logger.info(
                "│ [1] 查询到商品",
                product_count=len(products),
                tag=tag,
            )

            if not products:
                logger.warning("未找到精选商品", tag=tag)
                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "list_featured_products",
                        "status": "empty",
                        "count": 0,
                        "message": f"未找到标签为 {tag} 的精选商品",
                    },
                )
                logger.info("└── 工具: list_featured_products 结束 (无结果) ──┘")
                return json.dumps(
                    {"error": f"未找到标签为 {tag} 的精选商品", "tag": tag},
                    ensure_ascii=False,
                )

            # 构建商品列表
            product_list = []
            for product in products:
                product_info = {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "summary": product.summary[:200] if product.summary else None,
                    "url": product.url,
                    "category": product.category,
                }
                product_list.append(product_info)

                logger.debug(
                    f"│     商品: {product.name}",
                    product_id=product.id,
                    price=product.price,
                )

            result_json = json.dumps(
                {"tag": tag, "products": product_list, "total_count": len(product_list)},
                ensure_ascii=False,
                indent=2,
            )

            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "list_featured_products",
                    "status": "success",
                    "output_preview": product_list[:3],
                    "count": len(product_list),
                },
            )
            logger.info(
                "└── 工具: list_featured_products 结束 ──┘",
                output_data={"tag": tag, "product_count": len(product_list)},
            )
            return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "list_featured_products",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("列出精选商品失败", tag=tag, error=str(e))
        return json.dumps({"error": f"列出精选商品失败: {e}"}, ensure_ascii=False)
