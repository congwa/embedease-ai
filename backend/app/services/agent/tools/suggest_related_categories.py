"""推荐相关分类工具

## 功能描述
根据给定分类，推荐其他相关或相似的分类。

## 使用场景
- 用户询问："服饰鞋包还有什么相关的分类？"
- 用户想探索更多相关品类
- 需要展示分类之间的关联

## 输出格式
返回相关分类列表，每个分类包含：
- name: 分类名称
- reason: 推荐理由
- product_count: 该分类的商品数量
"""

from __future__ import annotations

import json
import uuid
from typing import Annotated

from langchain.tools import ToolRuntime, tool
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.product import Product
from app.schemas.events import StreamEventType

logger = get_logger("tool.suggest_related_categories")


class RelatedCategory(BaseModel):
    """相关分类模型"""

    name: str = Field(description="分类名称")
    reason: str = Field(description="推荐理由")
    product_count: int = Field(description="商品数量")


class SuggestRelatedCategoriesResponse(BaseModel):
    """推荐相关分类的返回结果"""

    source_category: str = Field(description="源分类名称")
    related_categories: list[RelatedCategory] = Field(description="相关分类列表")
    total_count: int = Field(description="相关分类数量")


# 分类关联映射（静态配置，可根据业务需求扩展）
CATEGORY_RELATIONS = {
    "服饰鞋包": {
        "配饰": "服饰鞋包的搭配单品",
        "运动户外": "运动风格的服饰鞋包",
        "箱包皮具": "与鞋包相关的箱包类商品",
    },
    "数码电器": {
        "智能设备": "智能化的数码产品",
        "办公用品": "办公场景的数码设备",
        "家用电器": "家庭使用的电器产品",
    },
    "美妆护肤": {
        "个人护理": "个人护理相关产品",
        "健康保健": "健康美容相关商品",
        "香水彩妆": "美妆类细分品类",
    },
    "食品饮料": {
        "生鲜食品": "新鲜食材类商品",
        "酒水饮品": "饮品类细分品类",
        "休闲零食": "零食小吃类商品",
    },
    "家居生活": {
        "家纺用品": "家居纺织品",
        "厨房用品": "厨房相关商品",
        "家装建材": "家装相关商品",
    },
    "运动户外": {
        "服饰鞋包": "运动服饰鞋包",
        "健身器材": "运动健身设备",
        "户外装备": "户外活动装备",
    },
    "母婴玩具": {
        "童装童鞋": "儿童服饰",
        "玩具乐器": "儿童玩具",
        "孕产用品": "孕产相关商品",
    },
    "图书音像": {
        "文化用品": "文化办公用品",
        "乐器": "音乐相关商品",
        "教育培训": "教育相关商品",
    },
}


@tool
async def suggest_related_categories(
    category_name: Annotated[str, Field(description="分类名称，如：服饰鞋包")],
    runtime: ToolRuntime,
    limit: Annotated[int | None, Field(default=5, description="返回的相关分类数量上限")] = 5,
) -> str:
    """推荐与指定分类相关的其他分类。

    根据分类之间的关联关系，推荐用户可能感兴趣的其他分类。
    适用于用户想探索更多相关品类时使用。

    Args:
        category_name: 分类名称，例如"服饰鞋包"、"数码电器"等
        limit: 返回的相关分类数量上限，默认为5

    Returns:
        相关分类列表的结构化字符串，包含分类名称、推荐理由和商品数量。

    Examples:
        >>> suggest_related_categories("服饰鞋包")
        '[{"name": "配饰", "reason": "服饰鞋包的搭配单品", ...}]'

        >>> suggest_related_categories("数码电器", limit=3)
        '[{"name": "智能设备", "reason": "智能化的数码产品", ...}]'
    """
    tool_call_id = uuid.uuid4().hex
    runtime.context.emitter.emit(
        StreamEventType.TOOL_START.value,
        {
            "tool_call_id": tool_call_id,
            "name": "suggest_related_categories",
            "input": {"category_name": category_name, "limit": limit},
        },
    )

    logger.info(
        "┌── 工具: suggest_related_categories 开始 ──┐",
        input_data={"category_name": category_name, "limit": limit},
    )

    try:
        # 查找预定义的相关分类
        related_map = CATEGORY_RELATIONS.get(category_name, {})

        if not related_map:
            logger.info(
                "│ [1] 未找到预定义的相关分类，返回所有其他分类",
                category_name=category_name,
            )
            # 如果没有预定义关系，返回所有其他分类
            async with get_db_context() as session:
                stmt = (
                    select(
                        Product.category,
                        func.count(Product.id).label("product_count"),
                    )
                    .where(Product.category.isnot(None))
                    .where(Product.category != category_name)
                    .group_by(Product.category)
                    .order_by(func.count(Product.id).desc())
                    .limit(limit)
                )

                result = await session.execute(stmt)
                categories_data = result.all()

                if not categories_data:
                    logger.warning("未找到其他分类", category_name=category_name)
                    runtime.context.emitter.emit(
                        StreamEventType.TOOL_END.value,
                        {
                            "tool_call_id": tool_call_id,
                            "name": "suggest_related_categories",
                            "status": "empty",
                            "count": 0,
                            "message": f"未找到与 {category_name} 相关的分类",
                        },
                    )
                    logger.info("└── 工具: suggest_related_categories 结束 (无结果) ──┘")
                    return json.dumps(
                        {
                            "error": f"未找到与 {category_name} 相关的分类",
                            "source_category": category_name,
                        },
                        ensure_ascii=False,
                    )

                related_categories = [
                    {
                        "name": cat_data.category,
                        "reason": "其他可选分类",
                        "product_count": cat_data.product_count,
                    }
                    for cat_data in categories_data
                ]
        else:
            logger.info(
                "│ [1] 找到预定义的相关分类",
                related_count=len(related_map),
            )

            # 查询相关分类的商品数量
            async with get_db_context() as session:
                related_categories = []
                for related_name, reason in list(related_map.items())[:limit]:
                    stmt = select(func.count(Product.id)).where(
                        Product.category == related_name
                    )
                    result = await session.execute(stmt)
                    product_count = result.scalar() or 0

                    related_categories.append(
                        {
                            "name": related_name,
                            "reason": reason,
                            "product_count": product_count,
                        }
                    )

                    logger.debug(
                        f"│     相关分类: {related_name}",
                        reason=reason,
                        product_count=product_count,
                    )

        if not related_categories:
            logger.warning("未找到相关分类", category_name=category_name)
            runtime.context.emitter.emit(
                StreamEventType.TOOL_END.value,
                {
                    "tool_call_id": tool_call_id,
                    "name": "suggest_related_categories",
                    "status": "empty",
                    "count": 0,
                    "message": f"未找到与 {category_name} 相关的分类",
                },
            )
            logger.info("└── 工具: suggest_related_categories 结束 (无结果) ──┘")
            return json.dumps(
                {
                    "error": f"未找到与 {category_name} 相关的分类",
                    "source_category": category_name,
                },
                ensure_ascii=False,
            )

        result_json = json.dumps(
            {
                "source_category": category_name,
                "related_categories": related_categories,
                "total_count": len(related_categories),
            },
            ensure_ascii=False,
            indent=2,
        )

        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "suggest_related_categories",
                "status": "success",
                "output_preview": related_categories[:3],
                "count": len(related_categories),
            },
        )
        logger.info(
            "└── 工具: suggest_related_categories 结束 ──┘",
            output_data={
                "source_category": category_name,
                "related_count": len(related_categories),
            },
        )
        return result_json

    except Exception as e:
        runtime.context.emitter.emit(
            StreamEventType.TOOL_END.value,
            {
                "tool_call_id": tool_call_id,
                "name": "suggest_related_categories",
                "status": "error",
                "count": 0,
                "error": str(e),
            },
        )
        logger.exception("推荐相关分类失败", category_name=category_name, error=str(e))
        return json.dumps({"error": f"推荐相关分类失败: {e}"}, ensure_ascii=False)
