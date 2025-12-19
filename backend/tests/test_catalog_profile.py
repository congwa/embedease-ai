"""商品库画像服务测试"""

import pytest

from app.services.catalog_profile import CatalogProfileService


class TestBuildProfile:
    """测试画像统计生成"""

    def test_empty_products(self):
        """空商品列表"""
        service = CatalogProfileService(session=None)  # build_profile 不需要 session
        profile = service.build_profile_from_products([], top_n=3)
        
        assert profile["total_products"] == 0
        assert profile["top_categories"] == []
        assert profile["category_count"] == 0
        assert profile["priced_count"] == 0
        assert profile["min_price"] is None
        assert profile["max_price"] is None

    def test_category_counting(self):
        """类目统计与排序"""
        products = [
            {"id": "1", "name": "手机1", "category": "手机", "price": 1000},
            {"id": "2", "name": "手机2", "category": "手机", "price": 2000},
            {"id": "3", "name": "耳机1", "category": "耳机", "price": 100},
            {"id": "4", "name": "路由器1", "category": "路由器", "price": 200},
            {"id": "5", "name": "无类目", "category": None, "price": 50},
            {"id": "6", "name": "空类目", "category": "  ", "price": 60},
        ]
        service = CatalogProfileService(session=None)
        profile = service.build_profile_from_products(products, top_n=3)
        
        assert profile["total_products"] == 6
        assert profile["category_count"] == 3  # 手机、耳机、路由器
        
        # Top 类目按数量排序
        top_cats = profile["top_categories"]
        assert len(top_cats) == 3
        assert top_cats[0]["name"] == "手机"
        assert top_cats[0]["count"] == 2
        assert top_cats[1]["name"] in ["耳机", "路由器"]

    def test_price_statistics(self):
        """价格统计"""
        products = [
            {"id": "1", "name": "商品1", "category": "A", "price": 100},
            {"id": "2", "name": "商品2", "category": "A", "price": 500},
            {"id": "3", "name": "商品3", "category": "B", "price": 1000},
            {"id": "4", "name": "无价格", "category": "B", "price": None},
        ]
        service = CatalogProfileService(session=None)
        profile = service.build_profile_from_products(products, top_n=3)
        
        assert profile["priced_count"] == 3
        assert profile["unpriced_count"] == 1
        assert profile["min_price"] == 100
        assert profile["max_price"] == 1000

    def test_all_prices_none(self):
        """所有商品无价格"""
        products = [
            {"id": "1", "name": "商品1", "category": "A", "price": None},
            {"id": "2", "name": "商品2", "category": "B", "price": None},
        ]
        service = CatalogProfileService(session=None)
        profile = service.build_profile_from_products(products, top_n=3)
        
        assert profile["priced_count"] == 0
        assert profile["min_price"] is None
        assert profile["max_price"] is None


class TestRenderPrompt:
    """测试短提示词渲染"""

    def test_normal_prompt(self):
        """正常渲染"""
        profile = {
            "top_categories": [
                {"name": "手机", "count": 10},
                {"name": "耳机", "count": 5},
            ],
            "priced_count": 15,
            "min_price": 100,
            "max_price": 5000,
        }
        service = CatalogProfileService(session=None)
        prompt = service.render_prompt(profile)
        
        assert len(prompt) <= 100
        assert "手机" in prompt
        assert "耳机" in prompt
        assert "100" in prompt
        assert "5000" in prompt
        assert "仅基于检索结果推荐" in prompt

    def test_no_categories(self):
        """无类目"""
        profile = {
            "top_categories": [],
            "priced_count": 5,
            "min_price": 50,
            "max_price": 200,
        }
        service = CatalogProfileService(session=None)
        prompt = service.render_prompt(profile)
        
        assert len(prompt) <= 100
        assert "未知" in prompt

    def test_no_price(self):
        """无价格"""
        profile = {
            "top_categories": [{"name": "手机", "count": 3}],
            "priced_count": 0,
            "min_price": None,
            "max_price": None,
        }
        service = CatalogProfileService(session=None)
        prompt = service.render_prompt(profile)
        
        assert len(prompt) <= 100
        assert "价位未知" in prompt

    def test_length_limit_with_long_categories(self):
        """超长类目名时自动截断"""
        profile = {
            "top_categories": [
                {"name": "超级长的类目名称一二三四五", "count": 10},
                {"name": "另一个超级长的类目名称", "count": 8},
                {"name": "第三个很长的类目名", "count": 5},
            ],
            "priced_count": 20,
            "min_price": 99.9,
            "max_price": 9999.9,
        }
        service = CatalogProfileService(session=None)
        prompt = service.render_prompt(profile)
        
        # 必须保证不超过 100 字
        assert len(prompt) <= 100
        # 必须包含行为约束
        assert "仅基于检索结果推荐" in prompt


class TestFingerprint:
    """测试指纹计算"""

    def test_same_data_same_fingerprint(self):
        """相同数据产生相同指纹"""
        profile1 = {
            "total_products": 10,
            "top_categories": [{"name": "A", "count": 5}],
            "priced_count": 8,
            "min_price": 100,
            "max_price": 1000,
            "generated_at": "2025-01-01T00:00:00Z",
        }
        profile2 = {
            "total_products": 10,
            "top_categories": [{"name": "A", "count": 5}],
            "priced_count": 8,
            "min_price": 100,
            "max_price": 1000,
            "generated_at": "2025-12-31T23:59:59Z",  # 不同时间
        }
        service = CatalogProfileService(session=None)
        
        fp1 = service.compute_fingerprint(profile1)
        fp2 = service.compute_fingerprint(profile2)
        
        # 时间戳不影响指纹
        assert fp1 == fp2

    def test_different_data_different_fingerprint(self):
        """不同数据产生不同指纹"""
        profile1 = {
            "total_products": 10,
            "top_categories": [{"name": "A", "count": 5}],
            "priced_count": 8,
        }
        profile2 = {
            "total_products": 20,  # 不同
            "top_categories": [{"name": "A", "count": 5}],
            "priced_count": 8,
        }
        service = CatalogProfileService(session=None)
        
        fp1 = service.compute_fingerprint(profile1)
        fp2 = service.compute_fingerprint(profile2)
        
        assert fp1 != fp2
