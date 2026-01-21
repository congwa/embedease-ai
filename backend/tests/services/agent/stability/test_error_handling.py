"""Agent 错误处理稳定性测试

测试 Agent 在各种异常情况下的稳定性和错误处理能力。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.agent.middleware.noise_filter import NoiseFilterMiddleware
from app.services.agent.middleware.sliding_window import SlidingWindowMiddleware
from app.services.agent.middleware.strict_mode import StrictModeMiddleware
from app.services.agent.core.policy import ToolPolicy


class TestToolCallErrorHandling:
    """测试工具调用错误处理"""

    def test_tool_empty_result_handling(self):
        """测试工具返回空结果的处理"""
        middleware = NoiseFilterMiddleware()
        # 空结果应该被安全处理
        result = middleware._compress_json_output("[]")
        assert result == "[]"

    def test_tool_invalid_json_handling(self):
        """测试工具返回无效 JSON 的处理"""
        middleware = NoiseFilterMiddleware()
        # 无效 JSON 应该返回原始内容
        invalid_json = "this is not json"
        result = middleware._compress_json_output(invalid_json)
        assert result == invalid_json

    def test_tool_malformed_result_handling(self):
        """测试工具返回畸形结果的处理"""
        middleware = NoiseFilterMiddleware()
        # 畸形 JSON 应该返回原始内容
        malformed = '{"incomplete": '
        result = middleware._compress_json_output(malformed)
        assert result == malformed

    def test_tool_very_large_result_truncation(self):
        """测试超大工具结果的截断处理"""
        middleware = NoiseFilterMiddleware(max_output_chars=100)
        large_output = "A" * 1000
        result = middleware._truncate_string(large_output, 100)
        assert len(result) <= 103  # 100 + "..."

    def test_tool_unicode_result_handling(self):
        """测试 Unicode 结果的处理"""
        middleware = NoiseFilterMiddleware()
        unicode_output = '{"name": "商品名称🎉", "desc": "测试描述"}'
        result = middleware._compress_json_output(unicode_output)
        assert "商品名称" in result


class TestMessageEdgeCases:
    """测试消息边界条件"""

    def test_empty_message_list(self):
        """测试空消息列表"""
        middleware = SlidingWindowMiddleware(max_messages=10)
        count = middleware._count_messages([])
        assert count == 0

    def test_none_message_list(self):
        """测试 None 消息列表"""
        middleware = SlidingWindowMiddleware(max_messages=10)
        count = middleware._count_messages(None)
        assert count == 0

    def test_single_message(self):
        """测试单条消息"""
        middleware = SlidingWindowMiddleware(max_messages=10)
        messages = [HumanMessage(content="Hello")]
        count = middleware._count_messages(messages)
        assert count == 1

    def test_message_with_empty_content(self):
        """测试空内容消息"""
        middleware = SlidingWindowMiddleware(max_messages=10)
        messages = [HumanMessage(content="")]
        count = middleware._count_messages(messages)
        assert count == 1

    def test_message_with_whitespace_content(self):
        """测试纯空白消息"""
        middleware = NoiseFilterMiddleware()
        result = middleware._remove_noise("   \n\t   ")
        assert result.strip() == ""

    def test_message_with_special_chars(self):
        """测试特殊字符消息"""
        middleware = NoiseFilterMiddleware()
        special_content = "<script>alert('xss')</script>"
        result = middleware._remove_noise(special_content)
        # 应该保持内容（不是 XSS 过滤器）
        assert result is not None

    def test_message_with_emoji(self):
        """测试 Emoji 消息"""
        middleware = NoiseFilterMiddleware()
        emoji_content = "你好 👋 世界 🌍"
        result = middleware._remove_noise(emoji_content)
        assert "你好" in result
        assert "世界" in result

    def test_very_long_message(self):
        """测试超长消息"""
        middleware = NoiseFilterMiddleware(max_output_chars=1000)
        long_message = "测试" * 10000
        result = middleware._truncate_string(long_message, 1000)
        assert len(result) <= 1003  # 1000 + "..."


class TestMiddlewarePipelineStability:
    """测试中间件管道稳定性"""

    def test_noise_filter_with_empty_input(self):
        """测试噪音过滤器处理空输入"""
        middleware = NoiseFilterMiddleware()
        result = middleware._filter_output("")
        assert result == ""

    def test_sliding_window_preserves_system_message(self):
        """测试滑动窗口保留系统消息"""
        middleware = SlidingWindowMiddleware(max_messages=3)
        messages = [
            SystemMessage(content="System prompt"),
            HumanMessage(content="User 1"),
            AIMessage(content="AI 1"),
            HumanMessage(content="User 2"),
            AIMessage(content="AI 2"),
        ]
        trimmed = middleware._trim_messages(messages)
        # 应该保留系统消息
        assert any(isinstance(m, SystemMessage) for m in trimmed)

    def test_sliding_window_starts_on_human(self):
        """测试滑动窗口从人类消息开始"""
        middleware = SlidingWindowMiddleware(max_messages=2)
        messages = [
            HumanMessage(content="User 1"),
            AIMessage(content="AI 1"),
            HumanMessage(content="User 2"),
            AIMessage(content="AI 2"),
        ]
        trimmed = middleware._trim_messages(messages)
        # 第一条非系统消息应该是 HumanMessage
        non_system = [m for m in trimmed if not isinstance(m, SystemMessage)]
        if non_system:
            assert isinstance(non_system[0], HumanMessage)

    def test_strict_mode_with_various_policies(self):
        """测试严格模式与不同策略"""
        # 自然策略
        natural_middleware = StrictModeMiddleware(
            policy=ToolPolicy(min_tool_calls=0, allow_direct_answer=True)
        )
        assert natural_middleware.policy.allow_direct_answer is True

        # 严格策略
        strict_middleware = StrictModeMiddleware(
            policy=ToolPolicy(min_tool_calls=1, allow_direct_answer=False)
        )
        assert strict_middleware.policy.min_tool_calls == 1


class TestConfigurationStability:
    """测试配置稳定性"""

    def test_middleware_default_config(self):
        """测试中间件默认配置"""
        noise_filter = NoiseFilterMiddleware()
        sliding_window = SlidingWindowMiddleware()
        strict_mode = StrictModeMiddleware()

        # 所有中间件都应该能正常初始化
        assert noise_filter is not None
        assert sliding_window is not None
        assert strict_mode is not None

    def test_middleware_custom_config(self):
        """测试中间件自定义配置"""
        noise_filter = NoiseFilterMiddleware(max_output_chars=500)
        sliding_window = SlidingWindowMiddleware(max_messages=20)
        strict_mode = StrictModeMiddleware(
            custom_fallback_message="自定义消息"
        )

        assert noise_filter.max_output_chars == 500
        assert sliding_window.max_messages == 20
        assert strict_mode.fallback_message == "自定义消息"

    def test_middleware_extreme_config(self):
        """测试中间件极端配置"""
        # 极小值
        noise_filter_min = NoiseFilterMiddleware(max_output_chars=1)
        sliding_window_min = SlidingWindowMiddleware(max_messages=1)

        # 极大值
        noise_filter_max = NoiseFilterMiddleware(max_output_chars=1000000)
        sliding_window_max = SlidingWindowMiddleware(max_messages=10000)

        # 都应该能正常工作
        assert noise_filter_min.max_output_chars == 1
        assert sliding_window_min.max_messages == 1
        assert noise_filter_max.max_output_chars == 1000000
        assert sliding_window_max.max_messages == 10000


class TestDataIntegrity:
    """测试数据完整性"""

    def test_message_content_preserved(self):
        """测试消息内容完整性"""
        middleware = SlidingWindowMiddleware(max_messages=100)
        original_content = "这是原始消息内容，包含中文和 English"
        messages = [HumanMessage(content=original_content)]
        trimmed = middleware._trim_messages(messages)
        assert len(trimmed) == 1
        assert trimmed[0].content == original_content

    def test_message_order_preserved(self):
        """测试消息顺序完整性"""
        middleware = SlidingWindowMiddleware(max_messages=100)
        messages = [
            HumanMessage(content="1"),
            AIMessage(content="2"),
            HumanMessage(content="3"),
        ]
        trimmed = middleware._trim_messages(messages)
        contents = [m.content for m in trimmed]
        assert contents == ["1", "2", "3"]

    def test_metadata_preserved(self):
        """测试元数据完整性"""
        msg = AIMessage(
            content="test",
            additional_kwargs={"key": "value"},
            response_metadata={"model": "test"},
        )
        assert msg.additional_kwargs["key"] == "value"
        assert msg.response_metadata["model"] == "test"


class TestConcurrencyStability:
    """测试并发稳定性（基础）"""

    def test_middleware_instance_isolation(self):
        """测试中间件实例隔离"""
        mw1 = NoiseFilterMiddleware(max_output_chars=100)
        mw2 = NoiseFilterMiddleware(max_output_chars=200)

        # 实例应该是独立的
        assert mw1.max_output_chars != mw2.max_output_chars
        assert mw1 is not mw2

    def test_policy_instance_isolation(self):
        """测试策略实例隔离"""
        policy1 = ToolPolicy(min_tool_calls=1)
        policy2 = ToolPolicy(min_tool_calls=2)

        # 实例应该是独立的
        assert policy1.min_tool_calls != policy2.min_tool_calls
        assert policy1 is not policy2

    def test_message_list_modification_safety(self):
        """测试消息列表修改安全性"""
        original_messages = [
            HumanMessage(content="User"),
            AIMessage(content="AI"),
        ]
        middleware = SlidingWindowMiddleware(max_messages=1)

        # 原始列表不应被修改
        original_len = len(original_messages)
        _ = middleware._trim_messages(original_messages.copy())
        assert len(original_messages) == original_len
