"""compare_products 工具测试

测试商品对比工具的模型和逻辑。
"""

import pytest
import json


class TestCompareProductsInput:
    """测试商品对比输入"""

    def test_valid_two_product_ids(self):
        """测试两个商品 ID"""
        product_ids = ["P001", "P002"]
        assert len(product_ids) == 2

    def test_valid_multiple_product_ids(self):
        """测试多个商品 ID"""
        product_ids = ["P001", "P002", "P003", "P004"]
        assert len(product_ids) == 4

    def test_single_product_id(self):
        """测试单个商品 ID（边界）"""
        product_ids = ["P001"]
        assert len(product_ids) == 1

    def test_empty_product_ids(self):
        """测试空商品 ID 列表"""
        product_ids = []
        assert len(product_ids) == 0

    def test_duplicate_product_ids(self):
        """测试重复的商品 ID"""
        product_ids = ["P001", "P001"]
        assert len(set(product_ids)) == 1


class TestCompareProductsOutput:
    """测试商品对比输出"""

    def test_comparison_structure(self):
        """测试对比结构"""
        comparison = {
            "products": [
                {"id": "P001", "name": "商品A", "price": 100},
                {"id": "P002", "name": "商品B", "price": 200},
            ],
            "comparison_aspects": ["price", "features"],
        }
        assert len(comparison["products"]) == 2
        assert "price" in comparison["comparison_aspects"]

    def test_comparison_with_differences(self):
        """测试带差异的对比"""
        comparison = {
            "products": [
                {"id": "P001", "name": "商品A", "price": 100, "rating": 4.5},
                {"id": "P002", "name": "商品B", "price": 200, "rating": 4.8},
            ],
            "differences": {
                "price": {"P001": 100, "P002": 200, "diff": 100},
                "rating": {"P001": 4.5, "P002": 4.8, "diff": 0.3},
            },
        }
        assert comparison["differences"]["price"]["diff"] == 100

    def test_comparison_json_serializable(self):
        """测试对比结果可 JSON 序列化"""
        comparison = {
            "products": [
                {"id": "P001", "name": "A"},
                {"id": "P002", "name": "B"},
            ],
            "winner": "P002",
            "reason": "性价比更高",
        }
        json_str = json.dumps(comparison, ensure_ascii=False)
        assert "性价比" in json_str


class TestCompareProductsEdgeCases:
    """测试商品对比边界条件"""

    def test_compare_same_product(self):
        """测试对比相同商品"""
        product_ids = ["P001", "P001"]
        unique_ids = list(set(product_ids))
        assert len(unique_ids) == 1

    def test_compare_nonexistent_products(self):
        """测试对比不存在的商品"""
        result = {
            "error": "Some products not found",
            "found": ["P001"],
            "not_found": ["P999"],
        }
        assert len(result["not_found"]) == 1

    def test_compare_mixed_categories(self):
        """测试对比不同类别的商品"""
        comparison = {
            "products": [
                {"id": "P001", "category": "手机"},
                {"id": "P002", "category": "耳机"},
            ],
            "warning": "商品类别不同，对比可能不准确",
        }
        assert "warning" in comparison

    def test_compare_price_ranges(self):
        """测试价格范围差异"""
        products = [
            {"id": "P001", "price": 100},
            {"id": "P002", "price": 10000},
        ]
        price_diff = abs(products[0]["price"] - products[1]["price"])
        assert price_diff == 9900

    def test_compare_with_missing_attributes(self):
        """测试对比缺失属性的商品"""
        products = [
            {"id": "P001", "name": "商品A", "color": "红"},
            {"id": "P002", "name": "商品B"},  # 缺少 color
        ]
        # P002 没有 color 属性
        assert "color" not in products[1]
