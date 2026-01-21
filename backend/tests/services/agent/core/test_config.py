"""Agent 配置模块测试"""

import pytest

from app.services.agent.core.config import (
    DEFAULT_PROMPTS,
    DEFAULT_TOOL_CATEGORIES,
    DEFAULT_TOOL_POLICIES,
)


class TestDefaultPrompts:
    """测试默认 System Prompts"""

    def test_product_prompt_exists(self):
        """测试 product 类型提示存在"""
        assert "product" in DEFAULT_PROMPTS
        assert len(DEFAULT_PROMPTS["product"]) > 0

    def test_faq_prompt_exists(self):
        """测试 faq 类型提示存在"""
        assert "faq" in DEFAULT_PROMPTS
        assert len(DEFAULT_PROMPTS["faq"]) > 0

    def test_kb_prompt_exists(self):
        """测试 kb 类型提示存在"""
        assert "kb" in DEFAULT_PROMPTS
        assert len(DEFAULT_PROMPTS["kb"]) > 0

    def test_custom_prompt_exists(self):
        """测试 custom 类型提示存在"""
        assert "custom" in DEFAULT_PROMPTS
        assert len(DEFAULT_PROMPTS["custom"]) > 0

    def test_product_prompt_content(self):
        """测试 product 提示内容"""
        prompt = DEFAULT_PROMPTS["product"]
        assert "商品" in prompt or "推荐" in prompt

    def test_faq_prompt_content(self):
        """测试 faq 提示内容"""
        prompt = DEFAULT_PROMPTS["faq"]
        assert "FAQ" in prompt or "问答" in prompt

    def test_kb_prompt_content(self):
        """测试 kb 提示内容"""
        prompt = DEFAULT_PROMPTS["kb"]
        assert "知识库" in prompt or "知识" in prompt

    def test_all_prompts_are_strings(self):
        """测试所有提示都是字符串"""
        for key, prompt in DEFAULT_PROMPTS.items():
            assert isinstance(prompt, str)
            assert len(prompt) > 10


class TestDefaultToolCategories:
    """测试默认工具类别"""

    def test_product_categories(self):
        """测试 product 类型类别"""
        categories = DEFAULT_TOOL_CATEGORIES["product"]
        assert isinstance(categories, list)
        assert len(categories) > 0
        assert "search" in categories
        assert "query" in categories

    def test_faq_categories(self):
        """测试 faq 类型类别"""
        categories = DEFAULT_TOOL_CATEGORIES["faq"]
        assert isinstance(categories, list)
        assert "faq" in categories

    def test_kb_categories(self):
        """测试 kb 类型类别"""
        categories = DEFAULT_TOOL_CATEGORIES["kb"]
        assert isinstance(categories, list)
        assert "kb" in categories

    def test_custom_categories(self):
        """测试 custom 类型类别"""
        categories = DEFAULT_TOOL_CATEGORIES["custom"]
        assert isinstance(categories, list)
        # custom 类型默认空类别
        assert len(categories) == 0

    def test_product_has_core_categories(self):
        """测试 product 包含核心类别"""
        categories = DEFAULT_TOOL_CATEGORIES["product"]
        expected = ["search", "query", "compare", "filter", "category"]
        for cat in expected:
            assert cat in categories

    def test_all_types_have_categories(self):
        """测试所有类型都有类别配置"""
        expected_types = ["product", "faq", "kb", "custom"]
        for agent_type in expected_types:
            assert agent_type in DEFAULT_TOOL_CATEGORIES


class TestDefaultToolPolicies:
    """测试默认工具策略"""

    def test_product_policy(self):
        """测试 product 类型策略"""
        policy = DEFAULT_TOOL_POLICIES["product"]
        assert isinstance(policy, dict)
        assert "min_tool_calls" in policy
        assert "allow_direct_answer" in policy
        assert policy["min_tool_calls"] == 0
        assert policy["allow_direct_answer"] is True

    def test_faq_policy(self):
        """测试 faq 类型策略"""
        policy = DEFAULT_TOOL_POLICIES["faq"]
        assert isinstance(policy, dict)
        assert policy["allow_direct_answer"] is True

    def test_kb_policy(self):
        """测试 kb 类型策略"""
        policy = DEFAULT_TOOL_POLICIES["kb"]
        assert isinstance(policy, dict)
        # KB 必须基于检索结果
        assert policy["min_tool_calls"] == 1
        assert policy["allow_direct_answer"] is False

    def test_custom_policy(self):
        """测试 custom 类型策略"""
        policy = DEFAULT_TOOL_POLICIES["custom"]
        assert isinstance(policy, dict)
        assert policy["min_tool_calls"] == 0
        assert policy["allow_direct_answer"] is True

    def test_all_policies_have_required_fields(self):
        """测试所有策略都有必需字段"""
        required_fields = ["min_tool_calls", "allow_direct_answer"]
        for agent_type, policy in DEFAULT_TOOL_POLICIES.items():
            for field in required_fields:
                assert field in policy, f"{agent_type} 缺少 {field} 字段"

    def test_all_types_have_policies(self):
        """测试所有类型都有策略配置"""
        expected_types = ["product", "faq", "kb", "custom"]
        for agent_type in expected_types:
            assert agent_type in DEFAULT_TOOL_POLICIES
