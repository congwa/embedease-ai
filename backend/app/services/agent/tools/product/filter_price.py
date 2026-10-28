"""按价格过滤商品工具

## 功能描述
根据价格区间过滤商品，帮助用户在预算内找到合适的商品。

## 使用场景
- 用户有明确预算："1000-2000元的耳机"
- 价格上限："3000元以下的笔记本"
- 价格下限："2000元以上的高端商品"
- 预算范围搜索："帮我找500-1000元的商品"

## 与其他能力的配合
1. **价格优先场景**：先用本工具过滤价格，再从结果中推荐
2. **需求+预算场景**：可以结合使用多个能力
   - 方案A：先进行商品搜索，再从结果中筛选价格
   - 方案B：先按价格过滤，再结合需求分析

## 价格过滤逻辑
- 只传 min_price：查找该价格以上的商品
- 只传 max_price：查找该价格以下的商品
- 同时传入：查找价格区间内的商品
- 都不传：返回所有商品（不推荐）

## 输出格式
返回 JSON 格式的商品列表：
- id: 商品ID
- name: 商品名称
- price: 价格（已过滤）
- summary: 商品摘要
- url: 商品链接
- category: 商品分类
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

logger = get_logger("tool.filter_by_price")


class PriceFilteredProduct(BaseModel):
    """价格过滤后的商品"""

    id: str = Field(description="商品ID")
    name: str = Field(description="商品名称")
    price: float = Field(description="价格（元），已在指定区间内")
    summary: str = Field(description="商品摘要")
    url: str | None = Field(default=None, description="商品链接")
    category: str | None = Field(default=None, description="商品分类")


class FilterByPriceResponse(BaseModel):
    """价格过滤结果"""

    products: list[PriceFilteredProduct] = Field(description="符合价格条件的商品列表")
    filter_criteria: dict = Field(description="过滤条件")
    total_count: int = Field(description="结果数量")


@tool
async def filter_by_price(
    runtime: ToolRuntime,
    min_price: Annotated[float | None, Field(default=None, description="最低价格（元）")] = None,
    max_price: Annotated[float | None, Field(default=None, description="最高价格（元）")] = None,
) -> str:
    """按价格区间过滤商品。

    根据用户的价格预算，过滤出符合价格条件的商品。
    可以指定最低价、最高价或同时指定价格区间。

    Args:
        min_price: 最低价格（元），例如 1000.0
                  不传或传 None 表示不限制最低价
        max_price: 最高价格（元），例如 3000.0
                  不传或传 None 表示不限制最高价

    Returns:
        JSON 格式的商品列表，所有商品价格都在指定区间内。
        如果没有符合条件的商品，返回空列表。

    Examples:
        # 查找 1000-2000 元的商品
        >>> filter_by_price(min_price=1000, max_price=2000)
        '[{"id": "P004", "name": "...", "price": 1299.0, ...}]'

        # 查找 3000 元以下的商品
        >>> filter_by_price(max_price=3000)
        '[{"id": "P001", "name": "...", "price": 2999.0, ...}]'

        # 查找 2000 元以上的高端商品
        >>> filter_by_price(min_price=2000)
        '[{"id": "P006", "name": "...", "price": 3999.0, ...}]'

    Note:
        - 建议结合用户的具体需求使用
        - 可以先价格过滤，再根据其他条件筛选
        - 默认最多返回 5 个商品
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "filter_by_price",
            "input": {"min_price": min_price, "max_price": max_price},
        },
    )

    logger.verbose(
        "┌── 工具: filter_by_price 开始 ──┐",
        input_data={"min_price": min_price, "max_price": max_price},
    )

    try:
        # 价格是结构化约束，必须检查全量 SQL 商品，不能只筛向量前二十名。
        statement = select(Product).where(Product.price.is_not(None))
        if min_price is not None:
            statement = statement.where(Product.price >= min_price)
        if max_price is not None:
            statement = statement.where(Product.price <= max_price)
        async with get_db_context() as session:
            rows = (
                await session.scalars(statement.order_by(Product.price, Product.id).limit(5))
            ).all()
            results = [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "summary": p.summary or "",
                    "url": p.url,
                    "category": p.category,
                }
                for p in rows
            ]

        if not results:
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "filter_by_price",
                    "status": "empty",
                    "output_preview": [],
                    "count": 0,
                },
            )
            logger.warning("未找到符合价格条件的商品")
            return json.dumps(
                {
                    "products": [],
                    "filter_criteria": {"min_price": min_price, "max_price": max_price},
                    "message": "未找到符合价格条件的商品",
                },
                ensure_ascii=False,
            )

        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "filter_by_price",
                "status": "success",
                "output_preview": results[:3],
                "count": len(results),
            },
        )
        result_json = json.dumps(results, ensure_ascii=False, indent=2)
        logger.verbose(
            "└── 工具: filter_by_price 结束 ──┘",
            result_count=len(results),
            price_range={
                "min": min(p["price"] for p in results),
                "max": max(p["price"] for p in results),
            },
        )
        return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "filter_by_price",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("价格过滤失败", error=str(e))
        return json.dumps({"error": f"价格过滤失败: {e}"}, ensure_ascii=False)
