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
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.schemas.events import StreamEventType
from app.services.agent.retrieval.catalog import load_products

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
async def get_product_details(
    product_id: Annotated[str, Field(description="商品ID，如 P001")],
    runtime: ToolRuntime,
) -> str:
    """获取指定商品的详细信息。

    通过商品ID精确查询商品的完整信息，包括详细描述、规格参数等。
    适用于用户想深入了解某个具体商品时使用。

    Args:
        product_id: 商品ID，格式如 "P001"、"P002" 等。
                   可以从上一次检索结果或对话记录中获取。

    Returns:
        JSON 格式的商品详细信息字符串。
        如果商品不存在，返回错误提示。

    Examples:
        >>> get_product_details("P001")
        '{"id": "P001", "name": "索尼 WH-1000XM5", "price": 2999.0, ...}'

        >>> get_product_details("INVALID")
        '{"error": "未找到商品 INVALID"}'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "get_product_details",
            "input": {"product_id": product_id},
        },
    )

    logger.verbose(
        "┌── 工具: get_product_details 开始 ──┐",
        input_data={"product_id": product_id},
    )

    try:
        # ID 是精确身份，不能把“没有进入向量前十名”解释为商品不存在。
        product_detail = (await load_products([product_id])).get(product_id)
        if product_detail:
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "get_product_details",
                    "status": "success",
                    "output_preview": product_detail,
                    "count": 1,
                },
            )
            return json.dumps(product_detail, ensure_ascii=False)

        logger.warning("在结果中未找到匹配的商品", product_id=product_id)
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
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
                "tool_call_id": tool_call_id,
                "name": "get_product_details",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("获取商品详情失败", product_id=product_id, error=str(e))
        return json.dumps({"error": f"获取详情失败: {e}"}, ensure_ascii=False)
