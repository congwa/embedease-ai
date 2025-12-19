"""商品搜索工具

## 功能描述
根据用户的自然语言需求描述，搜索匹配的商品。支持增强检索策略（混合检索+重排序）。

## 使用场景
- 用户表达购物需求："我想买降噪耳机"
- 品类搜索："推荐跑步鞋"
- 特性搜索："适合学生的笔记本电脑"

## 检索策略
1. **向量相似度检索**：基于语义理解匹配商品
2. **关键词提取与过滤**：提取查询中的关键词，过滤更相关的结果
3. **相关性重排序**：综合多个因素（关键词匹配、价格、内容丰富度）重新排序

## 输出格式
返回 JSON 格式的商品列表，每个商品包含：
- id: 商品ID
- name: 商品名称
- price: 价格
- summary: 商品摘要（前200字符）
- url: 商品链接
- category: 商品分类
"""

import json
import uuid

from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.agent.retriever import get_retriever
from app.services.agent.enhanced_retriever import enhanced_search
from app.schemas.events import StreamEventType

logger = get_logger("tool.search_products")

# 是否使用增强检索（可通过环境变量配置）
USE_ENHANCED_RETRIEVAL = True


class ProductSearchResult(BaseModel):
    """商品搜索结果模型"""

    id: str = Field(description="商品ID")
    name: str = Field(description="商品名称")
    price: float = Field(description="价格（元）")
    summary: str = Field(description="商品摘要")
    url: str | None = Field(default=None, description="商品链接")
    category: str | None = Field(default=None, description="商品分类")


class SearchProductsResponse(BaseModel):
    """搜索商品工具的返回结果"""

    products: list[ProductSearchResult] = Field(description="搜索到的商品列表")
    total_count: int = Field(description="搜索结果总数")
    query: str = Field(description="原始查询")


@tool
async def search_products(
    query: Annotated[str, Field(description="用户的搜索需求描述")],
    runtime: ToolRuntime,
) -> str:
    """根据用户需求搜索匹配的商品。

    使用增强检索策略（向量相似度 + 关键词过滤 + 相关性重排序）来找到最匹配的商品。
    默认返回最多 5 个最相关的商品。

    Args:
        query: 用户的搜索需求描述，例如：
              - "降噪耳机"
              - "适合跑步的运动鞋"
              - "2000元左右的笔记本电脑"

    Returns:
        JSON 格式的商品列表字符串，包含商品的ID、名称、价格、摘要等信息。
        如果没有找到匹配商品，返回提示信息。

    Examples:
        >>> search_products("降噪耳机")
        '[{"id": "P001", "name": "索尼 WH-1000XM5", "price": 2999.0, ...}]'

        >>> search_products("1000元以下的耳机")
        '[{"id": "P002", "name": "小米耳机", "price": 899.0, ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "search_products",
            "input": {"query": query},
        },
    )

    logger.info(
        "┌── 工具: search_products 开始 ──┐",
        input_data={
            "query": query,
            "query_length": len(query),
        },
    )

    try:
        # 步骤 1 & 2: 使用增强检索或标准检索
        if USE_ENHANCED_RETRIEVAL:
            logger.debug("│ [1] 使用增强检索策略...")
            docs = await enhanced_search(query, k=5, enable_keyword_filter=True, enable_rerank=True)
        else:
            logger.debug("│ [1] 使用标准向量检索...")
            retriever = get_retriever(k=5)
            docs = retriever.invoke(query)

        logger.info(
            "│ [2] 检索完成",
            doc_count=len(docs),
            docs_preview=[
                {
                    "product_id": d.metadata.get("product_id"),
                    "product_name": d.metadata.get("product_name"),
                    "content_preview": d.page_content[:100] + "..."
                    if len(d.page_content) > 100
                    else d.page_content,
                }
                for d in docs[:3]  # 只显示前 3 个
            ]
            if docs
            else [],
        )

        if not docs:
            logger.warning(
                "│ [2] 未找到匹配商品",
                query=query,
            )
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "search_products",
                    "status": "empty",
                    "output_preview": [],
                    "count": 0,
                    "message": "未找到匹配的商品",
                },
            )
            logger.info("└── 工具: search_products 结束 (无结果) ──┘")
            return json.dumps({"error": "未找到匹配的商品", "query": query}, ensure_ascii=False)

        # 步骤 3: 去重和整理结果
        logger.debug("│ [3] 开始去重和整理结果...")
        seen_products = set()
        results = []

        for doc in docs:
            product_id = doc.metadata.get("product_id")
            if product_id in seen_products:
                logger.debug(f"│     跳过重复商品: {product_id}")
                continue
            seen_products.add(product_id)

            product = {
                "id": product_id,
                "name": doc.metadata.get("product_name"),
                "price": doc.metadata.get("price"),
                "summary": doc.page_content[:200],
                "url": doc.metadata.get("url"),
                "category": doc.metadata.get("category"),
            }
            results.append(product)

            logger.debug(
                f"│     添加商品 #{len(results)}",
                product_id=product_id,
                product_name=doc.metadata.get("product_name"),
                price=doc.metadata.get("price"),
            )

            # 最多返回 5 个不同的商品
            if len(results) >= 5:
                break

        # 步骤 4: 返回结果
        result_json = json.dumps(results, ensure_ascii=False, indent=2)

        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "search_products",
                "status": "success",
                "output_preview": results[:3],
                "count": len(results),
            },
        )
        logger.info(
            "└── 工具: search_products 结束 ──┘",
            output_data={
                "result_count": len(results),
                "products": [
                    {"id": p["id"], "name": p["name"], "price": p["price"]} for p in results
                ],
                "json_length": len(result_json),
            },
        )
        return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "search_products",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("搜索商品失败", query=query, error=str(e))
        return json.dumps({"error": f"搜索失败: {e}", "query": query}, ensure_ascii=False)
