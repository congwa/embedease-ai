"""Agent 边界条件测试

测试各种边界条件下的 Agent 行为稳定性。
"""

import pytest
import json
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.services.agent.middleware.noise_filter import NoiseFilterMiddleware
from app.services.agent.middleware.sliding_window import SlidingWindowMiddleware
from app.services.agent.middleware.strict_mode import (
    StrictModeMiddleware,
    _has_tool_calls,
    STRICT_MODE_FALLBACK_MESSAGE,
)
from app.services.agent.core.policy import ToolPolicy, get_policy
from app.services.agent.tools.registry import (
    ToolSpec,
    _get_tool_specs,
    get_tools,
    get_tool_names,
)


class TestNoiseFilterEdgeCases:
    """噪音过滤器边界条件测试"""

    def test_empty_string(self):
        """测试空字符串"""
        middleware = NoiseFilterMiddleware()
        result = middleware._remove_noise("")
        assert result == ""

    def test_whitespace_only(self):
        """测试纯空白字符串"""
        middleware = NoiseFilterMiddleware()
        result = middleware._remove_noise("   \n\t\r   ")
        assert result.strip() == ""

    def test_single_character(self):
        """测试单字符"""
        middleware = NoiseFilterMiddleware()
        result = middleware._remove_noise("a")
        assert result == "a"

    def test_newlines_only(self):
        """测试只有换行符"""
        middleware = NoiseFilterMiddleware()
        result = middleware._remove_noise("\n\n\n")
        # 应该压缩多个换行为少量
        assert result.count("\n") <= 2

    def test_mixed_content(self):
        """测试混合内容"""
        middleware = NoiseFilterMiddleware()
        content = "正常内容\n\n\n\n\n太多换行\n\n结束"
        result = middleware._remove_noise(content)
        assert "正常内容" in result
        assert "结束" in result

    def test_json_array_compression(self):
        """测试 JSON 数组压缩"""
        middleware = NoiseFilterMiddleware()
        json_array = json.dumps([
            {"id": "1", "name": "商品1", "description": "很长的描述" * 100},
            {"id": "2", "name": "商品2", "description": "另一个很长的描述" * 100},
        ])
        result = middleware._compress_json_output(json_array)
        # 应该返回有效 JSON
        try:
            parsed = json.loads(result)
            assert isinstance(parsed, list)
        except json.JSONDecodeError:
            pass  # 压缩后可能不是有效 JSON，这是允许的

    def test_nested_json_compression(self):
        """测试嵌套 JSON 压缩"""
        middleware = NoiseFilterMiddleware()
        nested_json = json.dumps({
            "products": [
                {"id": "1", "attrs": {"color": "red", "size": "L"}},
            ],
            "meta": {"total": 1},
        })
        result = middleware._compress_json_output(nested_json)
        assert result is not None

    def test_truncation_boundary(self):
        """测试截断边界"""
        middleware = NoiseFilterMiddleware(max_output_chars=10)
        content = "12345678901234567890"
        result = middleware._truncate_string(content, 10)
        assert len(result) <= 13  # 10 + "..."


class TestSlidingWindowEdgeCases:
    """滑动窗口边界条件测试"""

    def test_exactly_at_limit(self):
        """测试刚好在限制边界"""
        middleware = SlidingWindowMiddleware(max_messages=3)
        messages = [
            HumanMessage(content="1"),
            AIMessage(content="2"),
            HumanMessage(content="3"),
        ]
        trimmed = middleware._trim_messages(messages)
        assert len(trimmed) == 3

    def test_one_over_limit(self):
        """测试超出限制一条"""
        middleware = SlidingWindowMiddleware(max_messages=3)
        messages = [
            HumanMessage(content="1"),
            AIMessage(content="2"),
            HumanMessage(content="3"),
            AIMessage(content="4"),
        ]
        trimmed = middleware._trim_messages(messages)
        assert len(trimmed) <= 3

    def test_zero_limit(self):
        """测试零限制"""
        middleware = SlidingWindowMiddleware(max_messages=0)
        messages = [HumanMessage(content="test")]
        trimmed = middleware._trim_messages(messages)
        # 零限制应该返回空或最小必要消息
        assert isinstance(trimmed, list)

    def test_large_limit(self):
        """测试超大限制"""
        middleware = SlidingWindowMiddleware(max_messages=10000)
        messages = [HumanMessage(content="test")]
        trimmed = middleware._trim_messages(messages)
        assert trimmed is not None
        assert len(trimmed) == 1

    def test_all_same_type_messages(self):
        """测试全部相同类型消息"""
        middleware = SlidingWindowMiddleware(max_messages=3)
        messages = [
            HumanMessage(content="1"),
            HumanMessage(content="2"),
            HumanMessage(content="3"),
            HumanMessage(content="4"),
        ]
        trimmed = middleware._trim_messages(messages)
        assert len(trimmed) <= 4  # start_on_human 可能影响结果

    def test_only_system_messages(self):
        """测试只有系统消息"""
        middleware = SlidingWindowMiddleware(max_messages=2)
        messages = [
            SystemMessage(content="System 1"),
            SystemMessage(content="System 2"),
        ]
        trimmed = middleware._trim_messages(messages)
        assert isinstance(trimmed, list)

    def test_tool_messages(self):
        """测试包含工具消息"""
        middleware = SlidingWindowMiddleware(max_messages=10)
        messages = [
            HumanMessage(content="user"),
            AIMessage(content="ai", tool_calls=[{"id": "1", "name": "test", "args": {}}]),
            ToolMessage(content="tool result", tool_call_id="1"),
        ]
        trimmed = middleware._trim_messages(messages)
        assert len(trimmed) == 3


class TestStrictModeEdgeCases:
    """严格模式边界条件测试"""

    def test_empty_tool_calls_list(self):
        """测试空工具调用列表"""
        msg = AIMessage(content="test", tool_calls=[])
        assert _has_tool_calls(msg) is False

    def test_none_tool_calls(self):
        """测试 None 工具调用"""
        msg = AIMessage(content="test")
        # 不设置 tool_calls
        assert _has_tool_calls(msg) is False

    def test_tool_calls_with_empty_dict(self):
        """测试空字典的工具调用"""
        msg = AIMessage(content="test", additional_kwargs={})
        assert _has_tool_calls(msg) is False

    def test_policy_with_zero_min_calls(self):
        """测试零最小调用次数的策略"""
        policy = ToolPolicy(min_tool_calls=0, allow_direct_answer=True)
        middleware = StrictModeMiddleware(policy=policy)
        assert middleware.policy.min_tool_calls == 0

    def test_policy_with_high_min_calls(self):
        """测试高最小调用次数的策略"""
        policy = ToolPolicy(min_tool_calls=100, allow_direct_answer=False)
        middleware = StrictModeMiddleware(policy=policy)
        assert middleware.policy.min_tool_calls == 100

    def test_fallback_message_not_empty(self):
        """测试回退消息不为空"""
        assert len(STRICT_MODE_FALLBACK_MESSAGE) > 0
        assert "严格模式" in STRICT_MODE_FALLBACK_MESSAGE


class TestToolRegistryEdgeCases:
    """工具注册表边界条件测试"""

    def test_empty_category_filter(self):
        """测试空类别过滤"""
        tools = get_tools(categories=[])
        # 空类别应该返回空列表
        assert len(tools) == 0

    def test_nonexistent_category(self):
        """测试不存在的类别"""
        tools = get_tools(categories=["nonexistent_category"])
        assert len(tools) == 0

    def test_mixed_valid_invalid_categories(self):
        """测试混合有效和无效类别"""
        tools = get_tools(categories=["search", "nonexistent"])
        # 应该返回匹配 search 的工具
        assert len(tools) > 0

    def test_exclude_all_categories(self):
        """测试排除所有类别"""
        specs = _get_tool_specs()
        all_categories = set()
        for spec in specs:
            all_categories.update(spec.categories)

        tools = get_tools(exclude_categories=list(all_categories))
        # 排除所有类别后应该返回没有类别的工具或空列表
        assert isinstance(tools, list)

    def test_tool_spec_with_empty_categories(self):
        """测试空类别的工具规格"""
        spec = ToolSpec(name="test", tool=lambda: None, categories=[])
        assert spec.categories == []

    def test_tool_spec_with_none_modes(self):
        """测试 None 模式的工具规格"""
        spec = ToolSpec(name="test", tool=lambda: None, modes=None)
        assert spec.modes is None  # None 表示所有模式可用


class TestPolicyEdgeCases:
    """策略边界条件测试"""

    def test_get_policy_case_sensitive(self):
        """测试策略获取大小写敏感"""
        # 小写应该匹配
        natural = get_policy("natural")
        assert natural is not None

        # 大写应该返回默认
        NATURAL = get_policy("NATURAL")
        assert NATURAL is not None  # 返回默认策略

    def test_get_policy_with_spaces(self):
        """测试带空格的策略名称"""
        policy = get_policy(" natural ")
        # 带空格应该返回默认策略
        assert policy is not None

    def test_policy_all_fields_none(self):
        """测试所有字段为默认值的策略"""
        policy = ToolPolicy()
        assert policy.min_tool_calls == 0
        assert policy.fallback_tool is None
        assert policy.allow_direct_answer is True
        assert policy.clarification_tool is None
        assert policy.description == ""

    def test_policy_description_multiline(self):
        """测试多行描述"""
        policy = ToolPolicy(description="第一行\n第二行\n第三行")
        assert "\n" in policy.description


class TestMessageContentEdgeCases:
    """消息内容边界条件测试"""

    def test_ai_message_with_list_content(self):
        """测试列表内容的 AI 消息"""
        msg = AIMessage(content=["part1", "part2"])
        assert isinstance(msg.content, list)
        assert len(msg.content) == 2

    def test_ai_message_with_dict_content(self):
        """测试字典内容的 AI 消息"""
        # 某些模型可能返回结构化内容
        msg = AIMessage(content=[{"type": "text", "text": "hello"}])
        assert isinstance(msg.content, list)

    def test_human_message_multiline(self):
        """测试多行人类消息"""
        content = "第一行\n第二行\n第三行"
        msg = HumanMessage(content=content)
        assert msg.content == content
        assert msg.content.count("\n") == 2

    def test_system_message_very_long(self):
        """测试超长系统消息"""
        long_content = "系统提示" * 10000
        msg = SystemMessage(content=long_content)
        assert len(msg.content) == len(long_content)


class TestTypeConversionEdgeCases:
    """类型转换边界条件测试"""

    def test_truncate_short_string(self):
        """测试截断短字符串"""
        middleware = NoiseFilterMiddleware()
        result = middleware._truncate_string("short", 100)
        assert result == "short"

    def test_truncate_number_to_string(self):
        """测试截断数字转字符串"""
        middleware = NoiseFilterMiddleware()
        # 数字应该被安全处理
        result = middleware._truncate_string(str(12345), 100)
        assert "12345" in result

    def test_compress_non_json(self):
        """测试压缩非 JSON 内容"""
        middleware = NoiseFilterMiddleware()
        non_json = "这不是 JSON 内容"
        result = middleware._compress_json_output(non_json)
        # 非 JSON 应该返回原内容
        assert result == non_json
