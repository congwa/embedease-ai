"""列出所有分类工具

## 功能描述
列出商品库中的所有分类，包含每个分类的商品数量、价格区间等统计信息。

## 使用场景
- 用户询问："有哪些分类？"
- 用户想浏览所有商品类别
- 需要展示商品库的整体结构

## 输出格式
返回分类列表，每个分类包含：
- name: 分类名称
- product_count: 该分类下的商品数量
- price_range: 价格区间（最低价、最高价、平均价）
- sample_products: 代表商品列表（商品编号、名称）
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.product import Product
from app.schemas.events import StreamEventType

logger = get_logger("tool.list_all_categories")


class CategoryInfo(BaseModel):
    """分类信息模型"""

    name: str = Field(description="分类名称")
    product_count: int = Field(description="商品数量")
    price_range: dict = Field(description="价格区间信息")
    sample_products: list[dict] = Field(description="代表商品列表")


class ListAllCategoriesResponse(BaseModel):
    """列出所有分类的返回结果"""

    categories: list[CategoryInfo] = Field(description="分类列表")
    total_categories: int = Field(description="分类总数")


@tool
async def list_all_categories(
    runtime: ToolRuntime,
    limit: Annotated[int | None, Field(default=None, description="返回的分类数量上限")] = None,
) -> str:
    """列出商品库中的所有分类及其统计信息。

    返回所有商品分类的列表，包含每个分类的商品数量、价格区间和代表商品。
    适用于用户想了解商品库整体结构或浏览所有分类时使用。

    Args:
        limit: 返回的分类数量上限，不传则返回所有分类

    Returns:
        分类列表的结构化字符串，包含分类名称、商品数量、价格区间等信息。

    Examples:
        >>> list_all_categories()
        '[{"name": "服饰鞋包", "product_count": 20, ...}]'

        >>> list_all_categories(limit=5)
        '[{"name": "服饰鞋包", "product_count": 20, ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "list_all_categories",
            "input": {"limit": limit},
        },
    )

    logger.info(
        "┌── 工具: list_all_categories 开始 ──┐",
        input_data={"limit": limit},
    )

    try:
        async with get_db_context() as session:
            # 查询所有分类及其统计信息
            stmt = (
                select(
                    Product.category,
                    func.count(Product.id).label("product_count"),
                    func.min(Product.price).label("min_price"),
                    func.max(Product.price).label("max_price"),
                    func.avg(Product.price).label("avg_price"),
                )
                .where(Product.category.isnot(None))
                .group_by(Product.category)
                .order_by(func.count(Product.id).desc())
            )

            if limit:
                stmt = stmt.limit(limit)

            result = await session.execute(stmt)
            categories_data = result.all()

            logger.info(
                "│ [1] 查询到分类",
                category_count=len(categories_data),
            )

            if not categories_data:
                logger.warning("│ [1] 未找到任何分类")
                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "list_all_categories",
                        "status": "empty",
                        "count": 0,
                        "message": "商品库中暂无分类信息",
                    },
                )
                logger.info("└── 工具: list_all_categories 结束 (无结果) ──┘")
                return json.dumps({"error": "商品库中暂无分类信息"}, ensure_ascii=False)

            # 构建分类列表
            categories = []
            for cat_data in categories_data:
                category_name = cat_data.category
                product_count = cat_data.product_count

                # 获取该分类的代表商品（最多3个）
                sample_stmt = (
                    select(Product.id, Product.name, Product.price)
                    .where(Product.category == category_name)
                    .limit(3)
                )
                sample_result = await session.execute(sample_stmt)
                sample_products = [
                    {"id": p.id, "name": p.name, "price": p.price} for p in sample_result.all()
                ]

                category_info = {
                    "name": category_name,
                    "product_count": product_count,
                    "price_range": {
                        "min": float(cat_data.min_price) if cat_data.min_price else None,
                        "max": float(cat_data.max_price) if cat_data.max_price else None,
                        "avg": float(cat_data.avg_price) if cat_data.avg_price else None,
                    },
                    "sample_products": sample_products,
                }
                categories.append(category_info)

                logger.debug(
                    f"│     分类: {category_name}",
                    product_count=product_count,
                    price_range=category_info["price_range"],
                )

            result_json = json.dumps(
                {"categories": categories, "total_categories": len(categories)},
                ensure_ascii=False,
                indent=2,
            )

            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "list_all_categories",
                    "status": "success",
                    "output_preview": categories[:3],
                    "count": len(categories),
                },
            )
            logger.info(
                "└── 工具: list_all_categories 结束 ──┘",
                output_data={"category_count": len(categories)},
            )
            return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "list_all_categories",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("列出分类失败", error=str(e))
        return json.dumps({"error": f"列出分类失败: {e}"}, ensure_ascii=False)
