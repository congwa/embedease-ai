"""严格模式中间件测试"""

import pytest
from langchain_core.messages import AIMessage

from app.services.agent.core.policy import ToolPolicy, STRICT_POLICY, NATURAL_POLICY
from app.services.agent.middleware.strict_mode import (
    StrictModeMiddleware,
    STRICT_MODE_FALLBACK_MESSAGE,
    _has_tool_calls,
    _get_mode_from_request,
)


class TestHasToolCalls:
    """测试 _has_tool_calls 函数"""

    def test_no_tool_calls(self):
        """测试无工具调用"""
        msg = AIMessage(content="普通回复")
        assert _has_tool_calls(msg) is False

    def test_has_tool_calls_attribute(self):
        """测试有 tool_calls 属性"""
        msg = AIMessage(
            content="",
            tool_calls=[{"id": "1", "name": "search", "args": {}}],
        )
        assert _has_tool_calls(msg) is True

    def test_empty_tool_calls(self):
        """测试空 tool_calls 列表"""
        msg = AIMessage(content="回复", tool_calls=[])
        assert _has_tool_calls(msg) is False

    def test_tool_calls_in_additional_kwargs(self):
        """测试 additional_kwargs 中的 tool_calls"""
        msg = AIMessage(
            content="",
            additional_kwargs={"tool_calls": [{"id": "1"}]},
        )
        assert _has_tool_calls(msg) is True


class TestStrictModeMiddlewareInit:
    """测试严格模式中间件初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        middleware = StrictModeMiddleware()
        assert middleware.policy is None
        assert middleware.fallback_message == STRICT_MODE_FALLBACK_MESSAGE

    def test_custom_policy(self):
        """测试自定义策略"""
        policy = ToolPolicy(min_tool_calls=2, allow_direct_answer=False)
        middleware = StrictModeMiddleware(policy=policy)
        assert middleware.policy is policy
        assert middleware.policy.min_tool_calls == 2

    def test_custom_fallback_message(self):
        """测试自定义回退消息"""
        custom_msg = "请提供更多信息"
        middleware = StrictModeMiddleware(custom_fallback_message=custom_msg)
        assert middleware.fallback_message == custom_msg


class TestFallbackMessage:
    """测试回退消息内容"""

    def test_fallback_message_content(self):
        """测试默认回退消息内容"""
        assert "严格模式" in STRICT_MODE_FALLBACK_MESSAGE
        assert "工具" in STRICT_MODE_FALLBACK_MESSAGE

    def test_fallback_message_suggestions(self):
        """测试回退消息包含建议"""
        assert "补充" in STRICT_MODE_FALLBACK_MESSAGE or "信息" in STRICT_MODE_FALLBACK_MESSAGE

    def test_fallback_message_not_empty(self):
        """测试回退消息不为空"""
        assert len(STRICT_MODE_FALLBACK_MESSAGE) > 50


class TestStrictPolicy:
    """测试 STRICT_POLICY 与中间件配合"""

    def test_strict_policy_requires_tool(self):
        """测试严格策略要求工具调用"""
        assert STRICT_POLICY.min_tool_calls >= 1
        assert STRICT_POLICY.allow_direct_answer is False

    def test_natural_policy_allows_direct(self):
        """测试自然策略允许直接回答"""
        assert NATURAL_POLICY.allow_direct_answer is True
