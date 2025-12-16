"""意图识别相关的数据模型"""

from pydantic import BaseModel, Field


class IntentAnalysis(BaseModel):
    """意图分析结果"""

    intent: str = Field(description="识别出的用户意图类型")
    confidence: float = Field(description="置信度（0-1之间）", ge=0, le=1)
    suggested_actions: list[str] = Field(description="建议采取的行动列表")
    reasoning: str = Field(description="意图识别的推理过程")


class ProductQuery(BaseModel):
    """商品查询意图"""

    intent_analysis: IntentAnalysis = Field(description="意图分析结果")
    search_query: str | None = Field(default=None, description="搜索查询字符串")
    product_ids: list[str] | None = Field(default=None, description="相关商品ID列表")
    filters: dict | None = Field(default=None, description="过滤条件")


# 意图类型常量
class IntentType:
    """意图类型枚举"""

    SEARCH = "search"  # 搜索商品
    COMPARE = "compare"  # 对比商品
    DETAIL = "detail"  # 查看详情
    FILTER_PRICE = "filter_price"  # 价格过滤
    RECOMMEND = "recommend"  # 推荐商品
    QUESTION = "question"  # 一般性问题
    GREETING = "greeting"  # 问候
    UNKNOWN = "unknown"  # 未知意图


# 意图到工具的映射
INTENT_TO_TOOLS = {
    IntentType.SEARCH: ["search_products"],
    IntentType.COMPARE: ["search_products", "compare_products"],
    IntentType.DETAIL: ["get_product_details"],
    IntentType.FILTER_PRICE: ["filter_by_price", "search_products"],
    IntentType.RECOMMEND: ["search_products", "filter_by_price"],
    IntentType.QUESTION: [],  # 不需要工具，直接回答
    IntentType.GREETING: [],  # 不需要工具
    IntentType.UNKNOWN: ["search_products"],  # 默认使用搜索
}
