"""工具调用策略测试"""

import pytest

from app.services.agent.core.policy import (
    ToolPolicy,
    NATURAL_POLICY,
    FREE_POLICY,
    STRICT_POLICY,
    get_policy,
)


class TestToolPolicy:
    """测试 ToolPolicy 数据类"""

    def test_default_values(self):
        """测试默认值"""
        policy = ToolPolicy()
        assert policy.min_tool_calls == 0
        assert policy.fallback_tool is None
        assert policy.allow_direct_answer is True
        assert policy.clarification_tool is None
        assert policy.description == ""

    def test_custom_values(self):
        """测试自定义值"""
        policy = ToolPolicy(
            min_tool_calls=2,
            fallback_tool="search_products",
            allow_direct_answer=False,
            clarification_tool="guide_user",
            description="测试策略",
        )
        assert policy.min_tool_calls == 2
        assert policy.fallback_tool == "search_products"
        assert policy.allow_direct_answer is False
        assert policy.clarification_tool == "guide_user"
        assert policy.description == "测试策略"


class TestNaturalPolicy:
    """测试 NATURAL_POLICY 预定义策略"""

    def test_min_tool_calls(self):
        """测试不强制工具调用"""
        assert NATURAL_POLICY.min_tool_calls == 0

    def test_allow_direct_answer(self):
        """测试允许直接回答"""
        assert NATURAL_POLICY.allow_direct_answer is True

    def test_no_fallback_tool(self):
        """测试无回退工具"""
        assert NATURAL_POLICY.fallback_tool is None

    def test_description(self):
        """测试描述"""
        assert "自然模式" in NATURAL_POLICY.description


class TestFreePolicy:
    """测试 FREE_POLICY 预定义策略"""

    def test_min_tool_calls(self):
        """测试不强制工具调用"""
        assert FREE_POLICY.min_tool_calls == 0

    def test_allow_direct_answer(self):
        """测试允许直接回答"""
        assert FREE_POLICY.allow_direct_answer is True

    def test_no_fallback_tool(self):
        """测试无回退工具"""
        assert FREE_POLICY.fallback_tool is None

    def test_description(self):
        """测试描述"""
        assert "自由模式" in FREE_POLICY.description


class TestStrictPolicy:
    """测试 STRICT_POLICY 预定义策略"""

    def test_min_tool_calls(self):
        """测试必须调用工具"""
        assert STRICT_POLICY.min_tool_calls == 1

    def test_not_allow_direct_answer(self):
        """测试不允许直接回答"""
        assert STRICT_POLICY.allow_direct_answer is False

    def test_fallback_tool(self):
        """测试有回退工具"""
        assert STRICT_POLICY.fallback_tool == "guide_user"

    def test_clarification_tool(self):
        """测试有澄清工具"""
        assert STRICT_POLICY.clarification_tool == "guide_user"

    def test_description(self):
        """测试描述"""
        assert "严格模式" in STRICT_POLICY.description


class TestGetPolicy:
    """测试 get_policy 函数"""

    def test_get_natural_policy(self):
        """测试获取 natural 策略"""
        policy = get_policy("natural")
        assert policy is NATURAL_POLICY

    def test_get_free_policy(self):
        """测试获取 free 策略"""
        policy = get_policy("free")
        assert policy is FREE_POLICY

    def test_get_strict_policy(self):
        """测试获取 strict 策略"""
        policy = get_policy("strict")
        assert policy is STRICT_POLICY

    def test_unknown_mode_returns_natural(self):
        """测试未知模式返回 natural 策略"""
        policy = get_policy("unknown")
        assert policy is NATURAL_POLICY

    def test_empty_mode_returns_natural(self):
        """测试空模式返回 natural 策略"""
        policy = get_policy("")
        assert policy is NATURAL_POLICY
