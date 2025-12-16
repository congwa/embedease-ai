"""推荐结果的结构化输出模型"""

from pydantic import BaseModel, Field


class ProductRecommendation(BaseModel):
    """单个商品推荐"""

    product_id: str = Field(description="商品ID")
    product_name: str = Field(description="商品名称")
    price: float = Field(description="价格")
    reason: str = Field(description="推荐理由")
    pros: list[str] | None = Field(default=None, description="优点列表")
    cons: list[str] | None = Field(default=None, description="缺点列表")


class RecommendationResult(BaseModel):
    """商品推荐结果"""

    summary: str = Field(description="推荐总结")
    recommendations: list[ProductRecommendation] = Field(description="推荐的商品列表")
    alternative: ProductRecommendation | None = Field(
        default=None, description="备选商品（如果有）"
    )
    total_count: int = Field(description="推荐商品总数")


class ComparisonResult(BaseModel):
    """商品对比结果"""

    compared_products: list[dict] = Field(description="被对比的商品列表")
    winner: str | None = Field(default=None, description="最佳选择的商品ID")
    summary: str = Field(description="对比总结")
    key_differences: dict[str, list[str]] = Field(description="关键差异点")
