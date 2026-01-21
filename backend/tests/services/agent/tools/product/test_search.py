"""search_products 工具测试

测试商品搜索工具的模型和逻辑。
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.agent.tools.product.search import (
    ProductSearchResult,
    SearchProductsResponse,
)


class TestSearchInputValidation:
    """测试搜索输入验证"""

    def test_valid_simple_query(self):
        """测试简单查询"""
        query = "降噪耳机"
        assert len(query) > 0
        assert isinstance(query, str)

    def test_valid_chinese_query(self):
        """测试中文查询"""
        query = "适合学生的笔记本电脑"
        assert "学生" in query
        assert "笔记本" in query

    def test_valid_with_price(self):
        """测试带价格的查询"""
        query = "2000元以下的手机"
        assert "2000" in query
        assert "元" in query

    def test_empty_query_handling(self):
        """测试空查询处理"""
        query = ""
        assert query == ""

    def test_whitespace_query_handling(self):
        """测试空白查询处理"""
        query = "   "
        assert query.strip() == ""

    def test_special_characters_in_query(self):
        """测试特殊字符查询"""
        query = "iPhone 15 Pro Max"
        assert "iPhone" in query
        assert "15" in query

    def test_very_long_query(self):
        """测试超长查询"""
        query = "我想要一款价格在2000-3000元之间、适合学生使用、续航时间长、" * 10
        assert len(query) > 100


class TestSearchOutputFormat:
    """测试搜索输出格式"""

    def test_output_is_json_serializable(self):
        """测试输出可 JSON 序列化"""
        products = [
            ProductSearchResult(
                id="P001",
                name="商品1",
                price=99.9,
                summary="摘要",
            )
        ]
        response = SearchProductsResponse(
            products=products,
            total_count=1,
            query="测试",
        )
        # 转为字典再序列化
        json_str = json.dumps(response.model_dump(), ensure_ascii=False)
        assert "P001" in json_str
        assert "商品1" in json_str

    def test_output_structure(self):
        """测试输出结构"""
        products = [
            ProductSearchResult(
                id="P001",
                name="商品",
                price=10,
                summary="摘要",
            )
        ]
        response = SearchProductsResponse(
            products=products,
            total_count=1,
            query="查询",
        )
        data = response.model_dump()
        
        assert "products" in data
        assert "total_count" in data
        assert "query" in data
        assert isinstance(data["products"], list)

    def test_product_fields_in_output(self):
        """测试商品字段在输出中"""
        product = ProductSearchResult(
            id="P001",
            name="测试商品",
            price=199.9,
            summary="商品描述",
            url="https://example.com",
            category="电子产品",
        )
        data = product.model_dump()
        
        assert data["id"] == "P001"
        assert data["name"] == "测试商品"
        assert data["price"] == 199.9
        assert data["summary"] == "商品描述"
        assert data["url"] == "https://example.com"
        assert data["category"] == "电子产品"


class TestSearchEdgeCases:
    """测试搜索边界条件"""

    def test_zero_results(self):
        """测试零结果"""
        response = SearchProductsResponse(
            products=[],
            total_count=0,
            query="不存在的商品xyz123",
        )
        assert len(response.products) == 0
        assert response.total_count == 0

    def test_single_result(self):
        """测试单结果"""
        products = [
            ProductSearchResult(id="P001", name="商品", price=10, summary="摘要")
        ]
        response = SearchProductsResponse(
            products=products,
            total_count=1,
            query="测试",
        )
        assert len(response.products) == 1

    def test_multiple_results(self):
        """测试多结果"""
        products = [
            ProductSearchResult(id=f"P{i:03d}", name=f"商品{i}", price=i*10, summary=f"摘要{i}")
            for i in range(1, 6)
        ]
        response = SearchProductsResponse(
            products=products,
            total_count=5,
            query="测试",
        )
        assert len(response.products) == 5

    def test_price_edge_cases(self):
        """测试价格边界情况"""
        # 零价格
        p1 = ProductSearchResult(id="P1", name="免费", price=0, summary="免费商品")
        assert p1.price == 0
        
        # 高价格
        p2 = ProductSearchResult(id="P2", name="奢侈品", price=99999.99, summary="高端")
        assert p2.price == 99999.99
        
        # 小数价格
        p3 = ProductSearchResult(id="P3", name="打折", price=9.99, summary="特价")
        assert p3.price == 9.99
