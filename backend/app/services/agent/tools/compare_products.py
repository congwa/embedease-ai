"""商品对比工具

## 功能描述
对比多个商品的差异，帮助用户做出购买决策。

## 使用场景
- 用户想对比几款商品："对比一下这几款耳机"
- 用户犹豫不决："这两款哪个更好？"
- 多选一决策："帮我比较这3款笔记本"

## 对比维度
1. **价格对比**：最低价、最高价、价格区间
2. **分类信息**：商品所属类别
3. **描述对比**：各商品的特点和描述
4. **综合分析**：基于对比数据给出建议

## 使用建议
1. 先使用 `search_products` 搜索商品
2. 从搜索结果中提取商品ID
3. 使用本工具对比这些商品
4. 基于对比结果给用户建议

## 输出格式
返回 JSON 格式的对比结果：
- products: 商品详细信息列表
- comparison_points: 对比要点
  - price_range: 价格区间
  - categories: 涉及的分类
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.agent.retriever import get_retriever
from app.services.streaming.context import ChatContext
from app.schemas.events import StreamEventType

logger = get_logger("tool.compare_products")


class ProductComparisonItem(BaseModel):
    """对比商品信息"""

    id: str = Field(description="商品ID")
    name: str = Field(description="商品名称")
    price: float = Field(description="价格（元）")
    category: str | None = Field(default=None, description="商品分类")
    description: str = Field(description="商品描述摘要")
    url: str | None = Field(default=None, description="商品链接")


class PriceRange(BaseModel):
    """价格区间"""

    lowest: float = Field(description="最低价格")
    highest: float = Field(description="最高价格")
    average: float | None = Field(default=None, description="平均价格")


class ComparisonPoints(BaseModel):
    """对比要点"""

    price_range: PriceRange = Field(description="价格区间信息")
    categories: list[str] = Field(description="涉及的商品分类列表")
    product_count: int = Field(description="对比商品数量")


class CompareProductsResponse(BaseModel):
    """商品对比结果"""

    products: list[ProductComparisonItem] = Field(description="被对比的商品列表")
    comparison_points: ComparisonPoints = Field(description="对比要点")
    summary: str | None = Field(default=None, description="对比总结")


@tool
def compare_products(
    product_ids: Annotated[list[str], Field(description="要比较的商品ID列表（至少2个）")],
    runtime: ToolRuntime,
) -> str:
    """比较多个商品的差异。

    对比多个商品的价格、分类、特性等信息，帮助用户做出购买决策。
    至少需要提供2个商品ID才能进行对比。

    Args:
        product_ids: 要比较的商品ID列表，例如：
                    ["P001", "P002", "P003"]
                    至少需要2个商品ID

    Returns:
        JSON 格式的对比结果，包含：
        - 各商品的详细信息
        - 价格对比（最低、最高、平均）
        - 分类信息
        - 对比要点

    Examples:
        >>> compare_products(["P001", "P002"])
        '{"products": [...], "comparison_points": {...}}'

        >>> compare_products(["P001"])  # 错误：至少需要2个商品
        '{"error": "至少需要2个商品才能进行比较"}'

    Note:
        建议先使用 search_products 搜索商品，再从结果中提取ID进行对比。
    """
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "name": "compare_products",
            "input": {"product_ids": product_ids},
        },
    )

    logger.info(
        "┌── 工具: compare_products 开始 ──┐",
        input_data={"product_ids": product_ids, "count": len(product_ids)},
    )

    try:
        # 验证输入
        if len(product_ids) < 2:
            logger.warning("至少需要2个商品才能比较", provided=len(product_ids))
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "name": "compare_products",
                    "status": "error",
                    "count": 0,
                    "output_preview": [],
                    "error": "至少需要2个商品才能进行比较",
                },
            )
            return json.dumps(
                {"error": "至少需要2个商品才能进行比较", "provided_count": len(product_ids)},
                ensure_ascii=False,
            )

        # 获取所有商品的详细信息
        retriever = get_retriever(k=10)
        products: list[dict[str, Any]] = []

        for pid in product_ids:
            docs = retriever.invoke(f"商品ID: {pid}")

            for doc in docs:
                if doc.metadata.get("product_id") == pid:
                    product = {
                        "id": pid,
                        "name": doc.metadata.get("product_name"),
                        "price": doc.metadata.get("price"),
                        "category": doc.metadata.get("category"),
                        "description": doc.page_content[:300],
                        "url": doc.metadata.get("url"),
                    }
                    products.append(product)
                    logger.debug(f"│ 已找到商品: {product['name']}")
                    break

        if not products:
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "name": "compare_products",
                    "status": "empty",
                    "count": 0,
                    "output_preview": [],
                    "message": "未找到要比较的商品",
                },
            )
            logger.warning("未找到任何要比较的商品")
            return json.dumps({"error": "未找到要比较的商品"}, ensure_ascii=False)

        if len(products) < 2:
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "name": "compare_products",
                    "status": "error",
                    "count": 0,
                    "output_preview": products[:2],
                    "error": "找到的商品不足2个，无法进行对比",
                },
            )
            logger.warning("找到的商品不足2个", found=len(products))
            return json.dumps(
                {"error": "找到的商品不足2个，无法进行对比", "found_count": len(products)},
                ensure_ascii=False,
            )

        # 构建比较结果
        prices = [p["price"] for p in products if p["price"]]
        comparison = {
            "products": products,
            "comparison_points": {
                "price_range": {
                    "lowest": min(prices) if prices else 0,
                    "highest": max(prices) if prices else 0,
                    "average": sum(prices) / len(prices) if prices else 0,
                },
                "categories": list({p["category"] for p in products if p.get("category")}),
                "product_count": len(products),
            },
        }

        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "name": "compare_products",
                "status": "success",
                "output_preview": comparison["products"][:3],
                "count": len(products),
            },
        )
        result_json = json.dumps(comparison, ensure_ascii=False, indent=2)
        logger.info(
            "└── 工具: compare_products 结束 ──┘",
            product_count=len(products),
            price_range=comparison["comparison_points"]["price_range"],
        )
        return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "name": "compare_products",
                "status": "error",
                "count": 0,
                "output_preview": [],
                "error": str(e),
            },
        )
        logger.exception("比较商品失败", product_ids=product_ids, error=str(e))
        return json.dumps({"error": f"比较失败: {e}"}, ensure_ascii=False)
