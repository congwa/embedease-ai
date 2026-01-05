"""按属性列出商品工具

## 功能描述
根据商品属性关键词（如"简约"、"舒适"、"轻便"等）筛选商品。

## 使用场景
- 用户询问："有哪些简约风格的商品？"
- 用户想按特定属性筛选商品
- 需要根据描述特征查找商品

## 输出格式
返回匹配的商品列表，每个商品包含：
- id: 商品编号
- name: 商品名称
- price: 价格
- summary: 商品摘要
- url: 商品链接
- category: 商品分类
- matched_keywords: 匹配到的关键词
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field
from sqlalchemy import or_, select

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.product import Product
from app.schemas.events import StreamEventType

logger = get_logger("tool.list_products_by_attribute")


class ProductByAttribute(BaseModel):
    """按属性筛选的商品模型"""

    id: str = Field(description="商品编号")
    name: str = Field(description="商品名称")
    price: float | None = Field(description="价格")
    summary: str | None = Field(description="商品摘要")
    url: str | None = Field(description="商品链接")
    category: str | None = Field(description="商品分类")
    matched_keywords: list[str] = Field(description="匹配到的关键词")


class ListProductsByAttributeResponse(BaseModel):
    """按属性列出商品的返回结果"""

    keywords: list[str] = Field(description="搜索关键词")
    products: list[ProductByAttribute] = Field(description="匹配的商品列表")
    total_count: int = Field(description="商品数量")


@tool
async def list_products_by_attribute(
    keyword: Annotated[str, Field(description="属性关键词，必须是单一关键词，如：简约")],
    runtime: ToolRuntime,
    limit: Annotated[int | None, Field(default=10, description="返回的商品数量上限")] = 10,
) -> str:
    """根据属性关键词列出商品。

    在商品名称、摘要和描述中搜索包含指定关键词的商品。
    适用于用户想按特定属性或特征筛选商品时使用。

    重要提示：每次调用只能使用一个关键词。如需多个属性筛选，请分多次调用本工具。

    Args:
        keyword: 属性关键词，必须是单一关键词，例如：
                - "简约"（正确）
                - "舒适"（正确）
                - "简约,舒适,轻便"（错误，包含多个关键词）
        limit: 返回的商品数量上限，默认为10

    Returns:
        匹配的商品列表的结构化字符串，包含商品信息和匹配的关键词。

    Examples:
        >>> list_products_by_attribute("简约")
        '[{"id": "P0079", "name": "...", "matched_keywords": ["简约"], ...}]'

        >>> list_products_by_attribute("舒适", limit=5)
        '[{"id": "P0080", "name": "...", "matched_keywords": ["舒适"], ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "list_products_by_attribute",
            "input": {"keyword": keyword, "limit": limit},
        },
    )

    logger.info(
        "┌── 工具: list_products_by_attribute 开始 ──┐",
        input_data={"keyword": keyword, "limit": limit},
    )

    try:
        # 校验：检测是否包含多个关键词（逗号、顿号等分隔符）
        separators = [",", "，", "、", "\n", ";", "；"]
        if any(sep in keyword for sep in separators):
            error_msg = "属性关键词只能是单一关键词，不能同时使用多个关键词。如需多属性筛选，请分多次调用本工具。"
            logger.warning(
                "│ [校验失败] 检测到多关键词查询",
                keyword=keyword,
                detected_separators=[sep for sep in separators if sep in keyword],
            )
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "list_products_by_attribute",
                    "status": "error",
                    "count": 0,
                    "error": error_msg,
                },
            )
            logger.info("└── 工具: list_products_by_attribute 结束 (参数校验失败) ──┘")
            return json.dumps({"error": error_msg}, ensure_ascii=False)

        # 校验关键词不为空
        keyword = keyword.strip()
        if not keyword:
            error_msg = "未提供有效关键词"
            logger.warning("│ [校验失败] 关键词为空")
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "list_products_by_attribute",
                    "status": "error",
                    "count": 0,
                    "error": error_msg,
                },
            )
            logger.info("└── 工具: list_products_by_attribute 结束 (无关键词) ──┘")
            return json.dumps({"error": error_msg}, ensure_ascii=False)

        # 校验通过，继续执行
        keyword_list = [keyword]
        logger.info(
            "│ [1] 使用关键词",
            keyword=keyword,
        )

        async with get_db_context() as session:
            # 构建查询条件：在名称、摘要、描述中搜索关键词
            conditions = []
            for keyword in keyword_list:
                keyword_pattern = f"%{keyword}%"
                conditions.append(
                    or_(
                        Product.name.like(keyword_pattern),
                        Product.summary.like(keyword_pattern),
                        Product.description.like(keyword_pattern),
                    )
                )

            # 组合所有条件（任意一个关键词匹配即可）
            stmt = select(Product).where(or_(*conditions)).limit(limit * 2)  # 多取一些用于后续过滤

            result = await session.execute(stmt)
            products = result.scalars().all()

            logger.info(
                "│ [2] 查询到商品",
                product_count=len(products),
            )

            if not products:
                logger.warning("未找到匹配的商品", keyword=keyword)
                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "list_products_by_attribute",
                        "status": "empty",
                        "count": 0,
                        "message": f"未找到包含关键词 {keyword} 的商品",
                    },
                )
                logger.info("└── 工具: list_products_by_attribute 结束 (无结果) ──┘")
                return json.dumps(
                    {
                        "error": f"未找到包含关键词 {keyword} 的商品",
                        "keyword": keyword,
                    },
                    ensure_ascii=False,
                )

            # 构建商品列表，并标注匹配的关键词
            product_list = []
            for product in products:
                # 检查哪些关键词匹配
                matched_keywords = []
                product_text = (
                    f"{product.name or ''} {product.summary or ''} {product.description or ''}"
                )

                for keyword in keyword_list:
                    if keyword in product_text:
                        matched_keywords.append(keyword)

                if not matched_keywords:
                    continue

                product_info = {
                    "id": product.id,
                    "name": product.name,
                    "price": product.price,
                    "summary": product.summary[:200] if product.summary else None,
                    "url": product.url,
                    "category": product.category,
                    "matched_keywords": matched_keywords,
                }
                product_list.append(product_info)

                logger.debug(
                    f"│     商品: {product.name}",
                    product_id=product.id,
                    matched_keywords=matched_keywords,
                )

                # 达到数量上限
                if len(product_list) >= limit:
                    break

            if not product_list:
                logger.warning("过滤后未找到匹配的商品", keyword=keyword)
                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "list_products_by_attribute",
                        "status": "empty",
                        "count": 0,
                        "message": f"未找到包含关键词 {keyword} 的商品",
                    },
                )
                logger.info("└── 工具: list_products_by_attribute 结束 (无结果) ──┘")
                return json.dumps(
                    {
                        "error": f"未找到包含关键词 {keyword} 的商品",
                        "keyword": keyword,
                    },
                    ensure_ascii=False,
                )

            result_json = json.dumps(
                {
                    "keyword": keyword,
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
                    "name": "list_products_by_attribute",
                    "status": "success",
                    "output_preview": product_list[:3],
                    "count": len(product_list),
                },
            )
            logger.info(
                "└── 工具: list_products_by_attribute 结束 ──┘",
                output_data={
                    "keyword": keyword,
                    "product_count": len(product_list),
                },
            )
            return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "list_products_by_attribute",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("按属性列出商品失败", keyword=keyword, error=str(e))
        return json.dumps({"error": f"按属性列出商品失败: {e}"}, ensure_ascii=False)
