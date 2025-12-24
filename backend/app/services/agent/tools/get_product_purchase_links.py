"""获取商品购买链接工具

## 功能描述
获取指定商品的购买链接，支持批量查询。

## 使用场景
- 用户询问："这些商品的购买链接是什么？"
- 用户想直接购买商品
- 需要提供商品的对外链接

## 输出格式
返回商品链接列表，每个商品包含：
- id: 商品编号
- name: 商品名称
- url: 购买链接
- url_status: 链接状态（可用/不可用/未知）
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

logger = get_logger("tool.get_product_purchase_links")


class ProductPurchaseLink(BaseModel):
    """商品购买链接模型"""

    id: str = Field(description="商品编号")
    name: str = Field(description="商品名称")
    url: str | None = Field(description="购买链接")
    url_status: str = Field(description="链接状态")


class GetProductPurchaseLinksResponse(BaseModel):
    """获取商品购买链接的返回结果"""

    product_ids: list[str] = Field(description="查询的商品编号列表")
    links: list[ProductPurchaseLink] = Field(description="商品链接列表")
    total_count: int = Field(description="商品数量")


@tool
async def get_product_purchase_links(
    product_ids: Annotated[
        str, Field(description="商品编号列表，多个编号用逗号分隔，如：P0079,P0080,P0081")
    ],
    runtime: ToolRuntime,
) -> str:
    """获取指定商品的购买链接。

    返回一个或多个商品的购买链接，方便用户直接访问商品页面。
    适用于用户想获取商品购买链接时使用。

    Args:
        product_ids: 商品编号列表，多个编号用逗号分隔，例如：
                    - "P0079"
                    - "P0079,P0080,P0081"

    Returns:
        商品链接列表的结构化字符串，包含商品编号、名称和购买链接。

    Examples:
        >>> get_product_purchase_links("P0079")
        '[{"id": "P0079", "name": "...", "url": "https://...", ...}]'

        >>> get_product_purchase_links("P0079,P0080")
        '[{"id": "P0079", "name": "...", "url": "https://...", ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "get_product_purchase_links",
            "input": {"product_ids": product_ids},
        },
    )

    logger.info(
        "┌── 工具: get_product_purchase_links 开始 ──┐",
        input_data={"product_ids": product_ids},
    )

    try:
        # 解析商品编号列表
        product_id_list = [pid.strip() for pid in product_ids.split(",") if pid.strip()]

        if not product_id_list:
            logger.warning("未提供有效的商品编号")
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "get_product_purchase_links",
                    "status": "error",
                    "count": 0,
                    "message": "未提供有效的商品编号",
                },
            )
            logger.info("└── 工具: get_product_purchase_links 结束 (无编号) ──┘")
            return json.dumps({"error": "未提供有效的商品编号"}, ensure_ascii=False)

        logger.info(
            "│ [1] 解析商品编号",
            product_id_count=len(product_id_list),
            product_ids=product_id_list,
        )

        async with get_db_context() as session:
            # 查询商品信息
            stmt = select(Product).where(Product.id.in_(product_id_list))
            result = await session.execute(stmt)
            products = result.scalars().all()

            logger.info(
                "│ [2] 查询到商品",
                product_count=len(products),
            )

            if not products:
                logger.warning("未找到指定的商品", product_ids=product_id_list)
                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "get_product_purchase_links",
                        "status": "empty",
                        "count": 0,
                        "message": f"未找到商品：{', '.join(product_id_list)}",
                    },
                )
                logger.info("└── 工具: get_product_purchase_links 结束 (无结果) ──┘")
                return json.dumps(
                    {
                        "error": f"未找到商品：{', '.join(product_id_list)}",
                        "product_ids": product_id_list,
                    },
                    ensure_ascii=False,
                )

            # 构建链接列表
            links = []
            for product in products:
                # 判断链接状态
                url_status = "未知"
                if product.url:
                    url_status = "可用"
                else:
                    url_status = "不可用"

                link_info = {
                    "id": product.id,
                    "name": product.name,
                    "url": product.url,
                    "url_status": url_status,
                }
                links.append(link_info)

                logger.debug(
                    f"│     商品链接: {product.name}",
                    product_id=product.id,
                    url_status=url_status,
                    url=product.url[:50] if product.url else None,
                )

            result_json = json.dumps(
                {
                    "product_ids": product_id_list,
                    "links": links,
                    "total_count": len(links),
                },
                ensure_ascii=False,
                indent=2,
            )

            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "get_product_purchase_links",
                    "status": "success",
                    "output_preview": links[:3],
                    "count": len(links),
                },
            )
            logger.info(
                "└── 工具: get_product_purchase_links 结束 ──┘",
                output_data={
                    "product_ids": product_id_list,
                    "link_count": len(links),
                },
            )
            return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "get_product_purchase_links",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("获取商品购买链接失败", product_ids=product_ids, error=str(e))
        return json.dumps({"error": f"获取商品购买链接失败: {e}"}, ensure_ascii=False)
