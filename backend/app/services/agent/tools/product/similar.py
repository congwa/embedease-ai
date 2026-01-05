"""查找相似商品工具

## 功能描述
根据给定商品编号，查找语义相似或可替代的商品。

## 使用场景
- 用户询问："有没有类似的商品？"
- 用户想看更多替代选项
- 需要推荐相似商品

## 输出格式
返回相似商品列表，每个商品包含：
- id: 商品编号
- name: 商品名称
- price: 价格
- summary: 商品摘要
- similarity_score: 相似度分数（0-1之间）
- url: 商品链接
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.schemas.events import StreamEventType
from app.services.agent.retrieval.product import get_retriever

logger = get_logger("tool.find_similar_products")


class SimilarProduct(BaseModel):
    """相似商品模型"""

    id: str = Field(description="商品编号")
    name: str = Field(description="商品名称")
    price: float | None = Field(description="价格")
    summary: str = Field(description="商品摘要")
    similarity_score: float | None = Field(description="相似度分数")
    url: str | None = Field(description="商品链接")
    category: str | None = Field(description="商品分类")


class FindSimilarProductsResponse(BaseModel):
    """查找相似商品的返回结果"""

    source_product_id: str = Field(description="源商品编号")
    similar_products: list[SimilarProduct] = Field(description="相似商品列表")
    total_count: int = Field(description="相似商品数量")


@tool
async def find_similar_products(
    product_id: Annotated[str, Field(description="商品编号，必须是单一商品编号，如：P0079")],
    runtime: ToolRuntime,
    top_k: Annotated[int | None, Field(default=5, description="返回的相似商品数量")] = 5,
) -> str:
    """查找与指定商品相似的其他商品。

    基于向量语义相似度，查找与给定商品相似或可替代的商品。
    适用于用户想看更多类似商品或寻找替代选项时使用。

    重要提示：每次调用只能查询一个商品编号。如需查询多个商品的相似商品，请分多次调用本工具。

    Args:
        product_id: 商品编号，必须是单一商品编号，例如：
                   - "P0079"（正确）
                   - "P0080"（正确）
                   - "P0079, P0080, P0081"（错误，包含多个编号）
        top_k: 返回的相似商品数量，默认为5

    Returns:
        相似商品列表的结构化字符串，包含商品信息和相似度分数。

    Examples:
        >>> find_similar_products("P0079")
        '[{"id": "P0080", "name": "...", "similarity_score": 0.95, ...}]'

        >>> find_similar_products("P0079", top_k=3)
        '[{"id": "P0080", "name": "...", "similarity_score": 0.95, ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "find_similar_products",
            "input": {"product_id": product_id, "top_k": top_k},
        },
    )

    logger.info(
        "┌── 工具: find_similar_products 开始 ──┐",
        input_data={"product_id": product_id, "top_k": top_k},
    )

    try:
        # 校验：检测是否包含多个商品编号（逗号、顿号等分隔符）
        separators = [",", "，", "、", "\n", ";", "；", " "]
        if any(sep in product_id for sep in separators):
            error_msg = "商品编号只能是单一编号，不能同时查询多个商品。如需查询多个商品的相似商品，请分多次调用本工具。"
            logger.warning(
                "│ [校验失败] 检测到多商品编号查询",
                product_id=product_id,
                detected_separators=[sep for sep in separators if sep in product_id],
            )
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "find_similar_products",
                    "status": "error",
                    "count": 0,
                    "message": error_msg,
                },
            )
            logger.info("└── 工具: find_similar_products 结束 (参数校验失败) ──┘")
            return json.dumps({"error": error_msg}, ensure_ascii=False)

        # 校验通过，继续执行
        # 首先获取源商品信息
        retriever = get_retriever(k=10)
        source_docs = retriever.invoke(f"商品编号: {product_id}")

        source_product = None
        for doc in source_docs:
            if doc.metadata.get("product_id") == product_id:
                source_product = doc
                break

        if not source_product:
            logger.warning("未找到源商品", product_id=product_id)
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "find_similar_products",
                    "status": "empty",
                    "count": 0,
                    "message": f"未找到商品 {product_id}",
                },
            )
            logger.info("└── 工具: find_similar_products 结束 (无结果) ──┘")
            return json.dumps({"error": f"未找到商品 {product_id}"}, ensure_ascii=False)

        logger.info(
            "│ [1] 找到源商品",
            product_name=source_product.metadata.get("product_name"),
        )

        # 使用源商品的内容进行相似度搜索
        query = source_product.page_content
        retriever_similar = get_retriever(k=top_k + 5)  # 多取一些，用于过滤源商品
        similar_docs = retriever_similar.invoke(query)

        logger.info(
            "│ [2] 检索到相似文档",
            doc_count=len(similar_docs),
        )

        # 过滤掉源商品本身，并去重
        seen_products = set()
        similar_products = []

        for doc in similar_docs:
            doc_product_id = doc.metadata.get("product_id")

            # 跳过源商品
            if doc_product_id == product_id:
                continue

            # 去重
            if doc_product_id in seen_products:
                continue

            seen_products.add(doc_product_id)

            # 构建相似商品信息
            similar_product = {
                "id": doc_product_id,
                "name": doc.metadata.get("product_name"),
                "price": doc.metadata.get("price"),
                "summary": doc.page_content[:200],
                "similarity_score": None,  # 向量库不直接返回分数，可以后续优化
                "url": doc.metadata.get("url"),
                "category": doc.metadata.get("category"),
            }
            similar_products.append(similar_product)

            logger.debug(
                f"│     相似商品 #{len(similar_products)}",
                product_id=doc_product_id,
                product_name=similar_product["name"],
            )

            # 达到数量上限
            if len(similar_products) >= top_k:
                break

        if not similar_products:
            logger.warning("未找到相似商品", product_id=product_id)
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "find_similar_products",
                    "status": "empty",
                    "count": 0,
                    "message": f"未找到与商品 {product_id} 相似的商品",
                },
            )
            logger.info("└── 工具: find_similar_products 结束 (无结果) ──┘")
            return json.dumps(
                {
                    "error": f"未找到与商品 {product_id} 相似的商品",
                    "source_product_id": product_id,
                },
                ensure_ascii=False,
            )

        result_json = json.dumps(
            {
                "source_product_id": product_id,
                "similar_products": similar_products,
                "total_count": len(similar_products),
            },
            ensure_ascii=False,
            indent=2,
        )

        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "find_similar_products",
                "status": "success",
                "output_preview": similar_products[:3],
                "count": len(similar_products),
            },
        )
        logger.info(
            "└── 工具: find_similar_products 结束 ──┘",
            output_data={
                "source_product_id": product_id,
                "similar_count": len(similar_products),
            },
        )
        return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "find_similar_products",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("查找相似商品失败", product_id=product_id, error=str(e))
        return json.dumps({"error": f"查找相似商品失败: {e}"}, ensure_ascii=False)
