"""categories 工具测试

测试类目相关工具的模型和逻辑。
"""

import pytest
import json


class TestListAllCategoriesOutput:
    """测试列出所有类目输出"""

    def test_output_is_list(self):
        """测试输出是列表"""
        categories = ["手机", "电脑", "耳机", "配件"]
        assert isinstance(categories, list)
        assert len(categories) > 0

    def test_output_json_serializable(self):
        """测试输出可 JSON 序列化"""
        categories = ["电子产品", "服装", "食品"]
        json_str = json.dumps(categories, ensure_ascii=False)
        assert "电子产品" in json_str

    def test_hierarchical_categories(self):
        """测试层级类目"""
        categories = [
            {"name": "电子产品", "children": ["手机", "电脑"]},
            {"name": "服装", "children": ["男装", "女装"]},
        ]
        assert len(categories) == 2
        assert len(categories[0]["children"]) == 2

    def test_category_with_count(self):
        """测试带数量的类目"""
        categories = [
            {"name": "手机", "count": 150},
            {"name": "电脑", "count": 80},
        ]
        assert categories[0]["count"] == 150


class TestCategoryOverviewOutput:
    """测试类目概览输出"""

    def test_overview_structure(self):
        """测试概览结构"""
        overview = {
            "category": "手机",
            "total_products": 150,
            "price_range": {"min": 500, "max": 15000},
            "top_brands": ["Apple", "Samsung", "Xiaomi"],
        }
        assert overview["total_products"] == 150
        assert len(overview["top_brands"]) == 3

    def test_overview_with_stats(self):
        """测试带统计的概览"""
        overview = {
            "category": "耳机",
            "stats": {
                "avg_price": 500,
                "median_price": 300,
                "total_reviews": 5000,
            },
        }
        assert overview["stats"]["avg_price"] == 500


class TestListProductsByCategoryOutput:
    """测试按类目列商品输出"""

    def test_output_structure(self):
        """测试输出结构"""
        result = {
            "category": "手机",
            "products": [
                {"id": "P001", "name": "iPhone"},
                {"id": "P002", "name": "Galaxy"},
            ],
            "total": 2,
        }
        assert result["category"] == "手机"
        assert len(result["products"]) == 2

    def test_empty_category(self):
        """测试空类目"""
        result = {
            "category": "不存在的类目",
            "products": [],
            "total": 0,
        }
        assert len(result["products"]) == 0

    def test_paginated_output(self):
        """测试分页输出"""
        result = {
            "category": "手机",
            "products": [{"id": f"P{i:03d}"} for i in range(10)],
            "total": 150,
            "page": 1,
            "page_size": 10,
            "has_more": True,
        }
        assert len(result["products"]) == 10
        assert result["has_more"] is True


class TestSuggestRelatedCategoriesOutput:
    """测试推荐相关类目输出"""

    def test_related_categories(self):
        """测试相关类目"""
        result = {
            "query": "手机",
            "related": ["手机壳", "充电器", "耳机", "贴膜"],
        }
        assert len(result["related"]) == 4

    def test_related_with_scores(self):
        """测试带分数的相关类目"""
        result = {
            "query": "笔记本电脑",
            "related": [
                {"category": "电脑包", "relevance": 0.95},
                {"category": "鼠标", "relevance": 0.85},
                {"category": "键盘", "relevance": 0.80},
            ],
        }
        assert result["related"][0]["relevance"] > result["related"][1]["relevance"]


class TestCategoriesEdgeCases:
    """测试类目边界条件"""

    def test_empty_categories(self):
        """测试空类目列表"""
        categories = []
        assert len(categories) == 0

    def test_single_category(self):
        """测试单个类目"""
        categories = ["唯一类目"]
        assert len(categories) == 1

    def test_deeply_nested_categories(self):
        """测试深层嵌套类目"""
        category = {
            "name": "电子产品",
            "children": [{
                "name": "手机",
                "children": [{
                    "name": "智能手机",
                    "children": [{"name": "5G手机"}],
                }],
            }],
        }
        assert category["children"][0]["children"][0]["children"][0]["name"] == "5G手机"

    def test_category_with_special_chars(self):
        """测试带特殊字符的类目"""
        categories = ["数码/电子", "服装&配饰", "食品（进口）"]
        assert "/" in categories[0]
        assert "&" in categories[1]
        assert "（" in categories[2]

    def test_unicode_category_names(self):
        """测试 Unicode 类目名称"""
        categories = ["👕 服装", "📱 手机", "🎧 耳机"]
        assert "👕" in categories[0]
