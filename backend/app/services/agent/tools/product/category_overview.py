"""获取分类概览工具

## 功能描述
获取指定分类的详细统计信息，包括商品数量、价格分布、热门关键词和代表商品。

## 使用场景
- 用户询问："服饰鞋包这个分类有什么特点？"
- 用户想深入了解某个具体分类
- 需要展示某分类的详细信息

## 输出格式
返回分类概览信息：
- category_name: 分类名称
- product_count: 商品数量
- price_distribution: 价格分布统计
- top_keywords: 热门关键词（从商品摘要中提取）
- representative_products: 代表商品列表
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.product import Product
from app.schemas.events import StreamEventType

logger = get_logger("tool.get_category_overview")


class CategoryOverview(BaseModel):
    """分类概览模型"""

    category_name: str = Field(description="分类名称")
    product_count: int = Field(description="商品数量")
    price_distribution: dict = Field(description="价格分布")
    top_keywords: list[str] = Field(description="热门关键词")
    representative_products: list[dict] = Field(description="代表商品")


@tool
async def get_category_overview(
    category_name: Annotated[str, Field(description="分类名称，必须是单一分类，如：服饰鞋包")],
    runtime: ToolRuntime,
) -> str:
    """获取指定分类的详细概览信息。

    返回某个分类的统计数据，包括商品数量、价格分布、热门关键词和代表商品。
    适用于用户想深入了解某个具体分类时使用。

    重要提示：每次调用只能查询一个分类。如需查询多个分类，请分多次调用本工具。

    Args:
        category_name: 分类名称，必须是单一分类，例如：
                      - "服饰鞋包"（正确）
                      - "数码电器"（正确）
                      - "玩具, 小猫玩具"（错误，包含多个分类）

    Returns:
        分类概览的结构化字符串，包含统计信息和代表商品。

    Examples:
        >>> get_category_overview("服饰鞋包")
        '{"category_name": "服饰鞋包", "product_count": 20, ...}'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "get_category_overview",
            "input": {"category_name": category_name},
        },
    )

    logger.info(
        "┌── 工具: get_category_overview 开始 ──┐",
        input_data={"category_name": category_name},
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
                    "name": "get_category_overview",
                    "status": "error",
                    "count": 0,
                    "message": error_msg,
                },
            )
            logger.info("└── 工具: get_category_overview 结束 (参数校验失败) ──┘")
            return json.dumps({"error": error_msg}, ensure_ascii=False)

        # 校验通过，继续执行
        async with get_db_context() as session:
            # 查询该分类的统计信息
            stats_stmt = select(
                func.count(Product.id).label("product_count"),
                func.min(Product.price).label("min_price"),
                func.max(Product.price).label("max_price"),
                func.avg(Product.price).label("avg_price"),
            ).where(Product.category == category_name)

            stats_result = await session.execute(stats_stmt)
            stats = stats_result.first()

            if not stats or stats.product_count == 0:
                logger.warning("未找到指定分类", category_name=category_name)
                runtime.context.emitter.emit(
                    StreamEventType.TOOL_END.value,
                    {
                        "tool_call_id": tool_call_id,
                        "name": "get_category_overview",
                        "status": "empty",
                        "count": 0,
                        "message": f"未找到分类：{category_name}",
                    },
                )
                logger.info("└── 工具: get_category_overview 结束 (无结果) ──┘")
                return json.dumps({"error": f"未找到分类：{category_name}"}, ensure_ascii=False)

            logger.info(
                "│ [1] 查询到分类统计",
                product_count=stats.product_count,
            )

            # 获取该分类的所有商品（用于提取关键词）
            products_stmt = select(Product.id, Product.name, Product.summary, Product.price).where(
                Product.category == category_name
            )

            products_result = await session.execute(products_stmt)
            products = products_result.all()

            # 提取热门关键词（从商品名称和摘要中）
            all_text = []
            for p in products:
                if p.name:
                    all_text.append(p.name)
                if p.summary:
                    all_text.append(p.summary)

            # 简单的关键词提取（分词并统计频率）
            keywords = []
            if all_text:
                text = " ".join(all_text)
                # 简单按空格和常见分隔符分词
                words = text.replace("、", " ").replace("，", " ").replace(",", " ").split()
                # 过滤短词和数字
                words = [w.strip() for w in words if len(w.strip()) > 1 and not w.isdigit()]
                # 统计词频
                word_counts = Counter(words)
                keywords = [word for word, _ in word_counts.most_common(10)]

            logger.debug(
                "│ [2] 提取关键词",
                keyword_count=len(keywords),
                keywords=keywords[:5],
            )

            # 获取代表商品（按价格排序，取中间价位的商品）
            representative_stmt = (
                select(Product.id, Product.name, Product.price, Product.summary)
                .where(Product.category == category_name)
                .order_by(Product.price)
                .limit(5)
            )
            rep_result = await session.execute(representative_stmt)
            representative_products = [
                {
                    "id": p.id,
                    "name": p.name,
                    "price": p.price,
                    "summary": p.summary[:100] if p.summary else None,
                }
                for p in rep_result.all()
            ]

            # 构建概览信息
            overview = {
                "category_name": category_name,
                "product_count": stats.product_count,
                "price_distribution": {
                    "min": float(stats.min_price) if stats.min_price else None,
                    "max": float(stats.max_price) if stats.max_price else None,
                    "avg": float(stats.avg_price) if stats.avg_price else None,
                },
                "top_keywords": keywords,
                "representative_products": representative_products,
            }

            result_json = json.dumps(overview, ensure_ascii=False, indent=2)

            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "get_category_overview",
                    "status": "success",
                    "output_preview": {
                        "category_name": category_name,
                        "product_count": stats.product_count,
                    },
                    "count": 1,
                },
            )
            logger.info(
                "└── 工具: get_category_overview 结束 ──┘",
                category_name=category_name,
                product_count=stats.product_count,
            )
            return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "get_category_overview",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("获取分类概览失败", category_name=category_name, error=str(e))
        return json.dumps({"error": f"获取分类概览失败: {e}"}, ensure_ascii=False)
