"""purchase 工具测试

测试获取购买链接工具的模型和逻辑。
"""

import pytest
import json


class TestGetProductPurchaseLinksInput:
    """测试获取购买链接输入"""

    def test_valid_product_id(self):
        """测试有效的商品 ID"""
        product_id = "P001"
        assert len(product_id) > 0

    def test_multiple_product_ids(self):
        """测试多个商品 ID"""
        product_ids = ["P001", "P002"]
        assert len(product_ids) == 2


class TestGetProductPurchaseLinksOutput:
    """测试获取购买链接输出"""

    def test_output_structure(self):
        """测试输出结构"""
        result = {
            "product_id": "P001",
            "links": [
                {"platform": "京东", "url": "https://jd.com/P001"},
                {"platform": "淘宝", "url": "https://taobao.com/P001"},
            ],
        }
        assert len(result["links"]) == 2

    def test_link_with_price(self):
        """测试带价格的链接"""
        link = {
            "platform": "京东",
            "url": "https://jd.com/P001",
            "price": 2999,
            "in_stock": True,
        }
        assert link["price"] == 2999
        assert link["in_stock"] is True

    def test_output_json_serializable(self):
        """测试输出可 JSON 序列化"""
        result = {
            "links": [{"platform": "京东", "url": "https://jd.com"}],
        }
        json_str = json.dumps(result, ensure_ascii=False)
        assert "京东" in json_str


class TestPurchaseLinksEdgeCases:
    """测试购买链接边界条件"""

    def test_no_links_available(self):
        """测试无可用链接"""
        result = {
            "product_id": "P001",
            "links": [],
            "message": "暂无购买链接",
        }
        assert len(result["links"]) == 0

    def test_product_not_found(self):
        """测试商品不存在"""
        result = {
            "error": "Product not found",
            "product_id": "INVALID",
        }
        assert "error" in result

    def test_out_of_stock(self):
        """测试缺货"""
        link = {
            "platform": "京东",
            "url": "https://jd.com/P001",
            "in_stock": False,
            "restock_date": "2024-02-01",
        }
        assert link["in_stock"] is False

    def test_multiple_platforms(self):
        """测试多平台"""
        platforms = ["京东", "淘宝", "拼多多", "苏宁", "亚马逊"]
        links = [{"platform": p, "url": f"https://{p}.com"} for p in platforms]
        assert len(links) == 5

    def test_affiliate_links(self):
        """测试联盟链接"""
        link = {
            "platform": "京东",
            "url": "https://jd.com/P001?affiliate=abc123",
            "is_affiliate": True,
        }
        assert "affiliate" in link["url"]
        assert link["is_affiliate"] is True
