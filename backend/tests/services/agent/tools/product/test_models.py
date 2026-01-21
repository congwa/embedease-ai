"""商品工具 Pydantic 模型测试

测试商品工具中定义的所有 Pydantic 模型的验证逻辑。
"""

import pytest
from pydantic import ValidationError

from app.services.agent.tools.product.search import (
    ProductSearchResult,
    SearchProductsResponse,
)


class TestProductSearchResult:
    """测试 ProductSearchResult 模型"""

    def test_valid_minimal(self):
        """测试最小有效数据"""
        result = ProductSearchResult(
            id="P001",
            name="测试商品",
            price=99.99,
            summary="商品摘要",
        )
        assert result.id == "P001"
        assert result.name == "测试商品"
        assert result.price == 99.99
        assert result.summary == "商品摘要"
        assert result.url is None
        assert result.category is None

    def test_valid_full(self):
        """测试完整有效数据"""
        result = ProductSearchResult(
            id="P001",
            name="测试商品",
            price=99.99,
            summary="商品摘要",
            url="https://example.com/product/P001",
            category="电子产品",
        )
        assert result.url == "https://example.com/product/P001"
        assert result.category == "电子产品"

    def test_price_zero(self):
        """测试价格为零"""
        result = ProductSearchResult(
            id="P001",
            name="免费商品",
            price=0,
            summary="免费",
        )
        assert result.price == 0

    def test_price_float(self):
        """测试浮点价格"""
        result = ProductSearchResult(
            id="P001",
            name="商品",
            price=123.456,
            summary="摘要",
        )
        assert result.price == 123.456

    def test_empty_summary(self):
        """测试空摘要"""
        result = ProductSearchResult(
            id="P001",
            name="商品",
            price=10,
            summary="",
        )
        assert result.summary == ""

    def test_chinese_content(self):
        """测试中文内容"""
        result = ProductSearchResult(
            id="商品001",
            name="中文商品名称",
            price=199.9,
            summary="这是一个中文摘要，包含特殊字符！@#",
            category="数码产品/手机",
        )
        assert "中文" in result.name
        assert "特殊字符" in result.summary

    def test_missing_required_field_id(self):
        """测试缺少必需字段 id"""
        with pytest.raises(ValidationError):
            ProductSearchResult(
                name="商品",
                price=10,
                summary="摘要",
            )

    def test_missing_required_field_name(self):
        """测试缺少必需字段 name"""
        with pytest.raises(ValidationError):
            ProductSearchResult(
                id="P001",
                price=10,
                summary="摘要",
            )

    def test_missing_required_field_price(self):
        """测试缺少必需字段 price"""
        with pytest.raises(ValidationError):
            ProductSearchResult(
                id="P001",
                name="商品",
                summary="摘要",
            )

    def test_missing_required_field_summary(self):
        """测试缺少必需字段 summary"""
        with pytest.raises(ValidationError):
            ProductSearchResult(
                id="P001",
                name="商品",
                price=10,
            )


class TestSearchProductsResponse:
    """测试 SearchProductsResponse 模型"""

    def test_valid_empty_products(self):
        """测试空商品列表"""
        response = SearchProductsResponse(
            products=[],
            total_count=0,
            query="搜索词",
        )
        assert response.products == []
        assert response.total_count == 0
        assert response.query == "搜索词"

    def test_valid_with_products(self):
        """测试带商品的响应"""
        products = [
            ProductSearchResult(id="P001", name="商品1", price=10, summary="摘要1"),
            ProductSearchResult(id="P002", name="商品2", price=20, summary="摘要2"),
        ]
        response = SearchProductsResponse(
            products=products,
            total_count=2,
            query="测试",
        )
        assert len(response.products) == 2
        assert response.total_count == 2

    def test_product_access(self):
        """测试商品访问"""
        products = [
            ProductSearchResult(id="P001", name="商品1", price=10, summary="摘要1"),
        ]
        response = SearchProductsResponse(
            products=products,
            total_count=1,
            query="测试",
        )
        assert response.products[0].id == "P001"
        assert response.products[0].name == "商品1"

    def test_missing_products(self):
        """测试缺少 products 字段"""
        with pytest.raises(ValidationError):
            SearchProductsResponse(
                total_count=0,
                query="测试",
            )

    def test_missing_total_count(self):
        """测试缺少 total_count 字段"""
        with pytest.raises(ValidationError):
            SearchProductsResponse(
                products=[],
                query="测试",
            )

    def test_missing_query(self):
        """测试缺少 query 字段"""
        with pytest.raises(ValidationError):
            SearchProductsResponse(
                products=[],
                total_count=0,
            )
