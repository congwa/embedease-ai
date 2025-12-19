"""按价格过滤商品工具

## 功能描述
根据价格区间过滤商品，帮助用户在预算内找到合适的商品。

## 使用场景
- 用户有明确预算："1000-2000元的耳机"
- 价格上限："3000元以下的笔记本"
- 价格下限："2000元以上的高端商品"
- 预算范围搜索："帮我找500-1000元的商品"

## 与 search_products 的配合
1. **价格优先场景**：先用本工具过滤价格，再从结果中推荐
2. **需求+预算场景**：可以结合使用两个工具
   - 方案A：先 search_products 再从结果中筛选价格
   - 方案B：先 filter_by_price 再结合需求分析

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

from app.core.logging import get_logger
from app.services.agent.retriever import get_retriever
from app.services.streaming.context import ChatContext
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
def filter_by_price(
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

    logger.info(
        "┌── 工具: filter_by_price 开始 ──┐",
        input_data={"min_price": min_price, "max_price": max_price},
    )

    try:
        # 构建价格查询
        price_query = []
        if min_price is not None:
            price_query.append(f"价格 {min_price} 元以上")
        if max_price is not None:
            price_query.append(f"价格 {max_price} 元以下")

        query = " ".join(price_query) if price_query else "所有商品"

        logger.debug(f"│ 价格查询: {query}")

        # 检索商品（检索更多以供过滤）
        retriever = get_retriever(k=20)
        docs = retriever.invoke(query)

        logger.debug(f"│ 检索到 {len(docs)} 个文档")

        # 去重并按价格过滤
        seen_products = set()
        results = []

        for doc in docs:
            product_id = doc.metadata.get("product_id")
            if product_id in seen_products:
                continue

            price = doc.metadata.get("price")
            if price is None:
                logger.debug(f"│ 跳过无价格商品: {product_id}")
                continue

            # 价格过滤
            if min_price is not None and price < min_price:
                logger.debug(f"│ 价格过低({price}): {product_id}")
                continue
            if max_price is not None and price > max_price:
                logger.debug(f"│ 价格过高({price}): {product_id}")
                continue

            seen_products.add(product_id)

            product = {
                "id": product_id,
                "name": doc.metadata.get("product_name"),
                "price": price,
                "summary": doc.page_content[:200],
                "url": doc.metadata.get("url"),
                "category": doc.metadata.get("category"),
            }
            results.append(product)

            logger.debug(
                f"│ ✓ 符合条件 #{len(results)}",
                product_id=product_id,
                name=product["name"],
                price=price,
            )

            # 最多返回 5 个商品
            if len(results) >= 5:
                break

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
        logger.info(
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
