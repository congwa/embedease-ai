"""获取商品详情工具

## 功能描述
根据商品ID获取指定商品的详细信息，包括完整描述、规格参数等。

## 使用场景
- 用户想了解某个具体商品的详细信息
- Agent 需要获取商品的完整描述以进行对比
- 用户询问商品的具体参数和特性

## 与 search_products 的区别
- `search_products`: 根据需求描述搜索商品（模糊搜索）
- `get_product_details`: 根据商品ID获取详情（精确查询）

## 输出格式
返回 JSON 格式的商品详细信息：
- id: 商品ID
- name: 商品名称
- price: 价格
- category: 分类
- description: 完整描述
- url: 商品链接
"""

from __future__ import annotations

import json

from typing import Annotated, Any

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.agent.retriever import get_retriever
from app.schemas.events import StreamEventType

logger = get_logger("tool.get_product_details")


class ProductDetail(BaseModel):
    """商品详情模型"""

    id: str = Field(description="商品ID")
    name: str = Field(description="商品名称")
    price: float = Field(description="价格（元）")
    category: str | None = Field(default=None, description="商品分类")
    description: str = Field(description="完整描述")
    url: str | None = Field(default=None, description="商品链接")


@tool
def get_product_details(
    product_id: Annotated[str, Field(description="商品ID，如 P001")],
    runtime: ToolRuntime,
) -> str:
    """获取指定商品的详细信息。

    通过商品ID精确查询商品的完整信息，包括详细描述、规格参数等。
    适用于用户想深入了解某个具体商品时使用。

    Args:
        product_id: 商品ID，格式如 "P001"、"P002" 等。
                   可以从 search_products 的结果中获取。

    Returns:
        JSON 格式的商品详细信息字符串。
        如果商品不存在，返回错误提示。

    Examples:
        >>> get_product_details("P001")
        '{"id": "P001", "name": "索尼 WH-1000XM5", "price": 2999.0, ...}'

        >>> get_product_details("INVALID")
        '{"error": "未找到商品 INVALID"}'
    """
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "name": "get_product_details",
            "input": {"product_id": product_id},
        },
    )

    logger.info(
        "┌── 工具: get_product_details 开始 ──┐",
        input_data={"product_id": product_id},
    )

    try:
        # 使用 product_id 作为查询
        retriever = get_retriever(k=10)
        docs = retriever.invoke(f"商品ID: {product_id}")

        if not docs:
            logger.warning("未找到指定商品", product_id=product_id)
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "name": "get_product_details",
                    "status": "empty",
                    "count": 0,
                    "output_preview": {},
                    "message": f"未找到商品 {product_id}",
                },
            )
            return json.dumps({"error": f"未找到商品 {product_id}"}, ensure_ascii=False)

        # 查找匹配的商品
        for doc in docs:
            if doc.metadata.get("product_id") == product_id:
                product_detail = {
                    "id": product_id,
                    "name": doc.metadata.get("product_name"),
                    "price": doc.metadata.get("price"),
                    "category": doc.metadata.get("category"),
                    "description": doc.page_content,
                    "url": doc.metadata.get("url"),
                }

                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "name": "get_product_details",
                        "status": "success",
                        "output_preview": product_detail,
                        "count": 1,
                    },
                )
                result_json = json.dumps(product_detail, ensure_ascii=False, indent=2)
                logger.info(
                    "└── 工具: get_product_details 结束 ──┘",
                    product_name=product_detail["name"],
                )
                return result_json

        logger.warning("在结果中未找到匹配的商品", product_id=product_id)
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "name": "get_product_details",
                "status": "empty",
                "count": 0,
                "output_preview": {},
                "message": f"未找到商品 {product_id}",
            },
        )
        return json.dumps({"error": f"未找到商品 {product_id}"}, ensure_ascii=False)

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "name": "get_product_details",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("获取商品详情失败", product_id=product_id, error=str(e))
        return json.dumps({"error": f"获取详情失败: {e}"}, ensure_ascii=False)
