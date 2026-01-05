"""按分类列出商品工具

## 功能描述
列出指定分类下的所有商品，支持分页和排序。

## 使用场景
- 用户询问："服饰鞋包分类下有哪些商品？"
- 用户想浏览某个分类的商品列表
- 需要展示某分类的商品清单

## 输出格式
返回商品列表，每个商品包含：
- id: 商品编号
- name: 商品名称
- price: 价格
- summary: 商品摘要
- url: 商品链接
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

logger = get_logger("tool.list_products_by_category")


class ProductInCategory(BaseModel):
    """分类中的商品模型"""

    id: str = Field(description="商品编号")
    name: str = Field(description="商品名称")
    price: float | None = Field(description="价格")
    summary: str | None = Field(description="商品摘要")
    url: str | None = Field(description="商品链接")


class ListProductsByCategoryResponse(BaseModel):
    """按分类列出商品的返回结果"""

    category_name: str = Field(description="分类名称")
    products: list[ProductInCategory] = Field(description="商品列表")
    total_count: int = Field(description="商品总数")


@tool
async def list_products_by_category(
    category_name: Annotated[str, Field(description="分类名称，必须是单一分类，如：服饰鞋包")],
    runtime: ToolRuntime,
    limit: Annotated[int | None, Field(default=10, description="返回的商品数量上限")] = 10,
    offset: Annotated[int | None, Field(default=0, description="跳过的商品数量，用于分页")] = 0,
) -> str:
    """列出指定分类下的商品。

    返回某个分类下的商品列表，支持分页查询。
    适用于用户想浏览某个分类的商品时使用。

    重要提示：每次调用只能查询一个分类。如需查询多个分类，请分多次调用本工具。

    Args:
        category_name: 分类名称，必须是单一分类，例如：
                      - "服饰鞋包"（正确）
                      - "数码电器"（正确）
                      - "玩具, 小猫玩具, 小狗玩具"（错误，包含多个分类）
        limit: 返回的商品数量上限，默认为10
        offset: 跳过的商品数量，用于分页，默认为0

    Returns:
        商品列表的结构化字符串，包含商品编号、名称、价格等信息。

    Examples:
        >>> list_products_by_category("服饰鞋包")
        '[{"id": "P0079", "name": "服饰鞋包-商品09", ...}]'

        >>> list_products_by_category("服饰鞋包", limit=5, offset=10)
        '[{"id": "P0089", "name": "服饰鞋包-商品19", ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "list_products_by_category",
            "input": {
                "category_name": category_name,
                "limit": limit,
                "offset": offset,
            },
        },
    )

    logger.info(
        "┌── 工具: list_products_by_category 开始 ──┐",
        input_data={
            "category_name": category_name,
            "limit": limit,
            "offset": offset,
        },
    )

    try:
        # 校验：检测是否包含多个分类（逗号、顿号等分隔符）
        separators = [",", "，", "、", "\n", ";", "；"]
        if any(sep in category_name for sep in separators):
            error_msg = "分类名称只能是单一分类，不能同时查询多个分类。如需查询多个分类，请分多次调用本工具。"
            logger.warning(
                "│ [校验失败] 检测到多分类查询",
                category_name=category_name,
                detected_separators=[sep for sep in separators if sep in category_name],
            )
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "list_products_by_category",
                    "status": "error",
                    "count": 0,
                    "error": error_msg,
                },
            )
            logger.info("└── 工具: list_products_by_category 结束 (参数校验失败) ──┘")
            return json.dumps(
                {"error": error_msg, "category_name": category_name},
                ensure_ascii=False,
            )

        # 校验通过，继续执行
        async with get_db_context() as session:
            # 查询该分类下的商品
            stmt = (
                select(Product)
                .where(Product.category == category_name)
                .order_by(Product.id)
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)
            products = result.scalars().all()

            logger.info(
                "│ [1] 查询到商品",
                product_count=len(products),
            )

            if not products:
                logger.warning("未找到该分类下的商品", category_name=category_name)
                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "list_products_by_category",
                        "status": "empty",
                        "count": 0,
                        "message": f"分类 {category_name} 下暂无商品",
                    },
                )
                logger.info("└── 工具: list_products_by_category 结束 (无结果) ──┘")
                return json.dumps(
                    {
                        "error": f"分类 {category_name} 下暂无商品",
                        "category_name": category_name,
                    },
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
                }
                product_list.append(product_info)

                logger.debug(
                    f"│     商品: {product.name}",
                    product_id=product.id,
                    price=product.price,
                )

            result_json = json.dumps(
                {
                    "category_name": category_name,
                    "products": product_list,
                    "total_count": len(product_list),
                },
                ensure_ascii=False,
                indent=2,
            )

            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "list_products_by_category",
                    "status": "success",
                    "output_preview": product_list[:3],
                    "count": len(product_list),
                },
            )
            logger.info(
                "└── 工具: list_products_by_category 结束 ──┘",
                output_data={
                    "category_name": category_name,
                    "product_count": len(product_list),
                },
            )
            return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "list_products_by_category",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("列出分类商品失败", category_name=category_name, error=str(e))
        return json.dumps({"error": f"列出分类商品失败: {e}"}, ensure_ascii=False)
