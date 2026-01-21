"""Agent 集成稳定性测试

测试多个组件协同工作时的稳定性。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.services.agent.middleware.noise_filter import NoiseFilterMiddleware
from app.services.agent.middleware.sliding_window import SlidingWindowMiddleware
from app.services.agent.middleware.strict_mode import StrictModeMiddleware
from app.services.agent.core.policy import ToolPolicy, NATURAL_POLICY, STRICT_POLICY
from app.services.agent.tools.registry import get_tools, get_tool_names


class TestMiddlewareChainStability:
    """中间件链稳定性测试"""

    def test_multiple_middleware_instances(self):
        """测试多个中间件实例共存"""
        noise_filter = NoiseFilterMiddleware(max_output_chars=500)
        sliding_window = SlidingWindowMiddleware(max_messages=10)
        strict_mode = StrictModeMiddleware(policy=NATURAL_POLICY)

        # 所有实例应该独立
        assert noise_filter is not sliding_window
        assert sliding_window is not strict_mode
        assert noise_filter is not strict_mode

    def test_middleware_config_independence(self):
        """测试中间件配置独立性"""
        mw1 = NoiseFilterMiddleware(max_output_chars=100)
        mw2 = NoiseFilterMiddleware(max_output_chars=200)

        # 修改一个不应影响另一个
        mw1.max_output_chars = 50
        assert mw2.max_output_chars == 200

    def test_message_flow_through_pipeline(self):
        """测试消息在管道中的流动"""
        messages = [
            SystemMessage(content="You are a helpful assistant"),
            HumanMessage(content="Hello"),
            AIMessage(content="Hi there!"),
            HumanMessage(content="How are you?"),
        ]

        # 滑动窗口处理
        sliding_window = SlidingWindowMiddleware(max_messages=3)
        trimmed = sliding_window._trim_messages(messages)

        # 结果应该有效
        assert len(trimmed) <= 4  # 包括系统消息
        assert all(
            isinstance(m, (SystemMessage, HumanMessage, AIMessage))
            for m in trimmed
        )


class TestPolicyAndToolIntegration:
    """策略和工具集成测试"""

    def test_natural_mode_tools(self):
        """测试自然模式工具"""
        policy = NATURAL_POLICY
        tools = get_tools(mode="natural")

        # 自然模式应该有工具
        assert len(tools) > 0
        assert policy.allow_direct_answer is True

    def test_strict_mode_policy(self):
        """测试严格模式策略"""
        policy = STRICT_POLICY
        tools = get_tools(mode="strict")

        # 严格模式策略应该正确配置
        assert policy.min_tool_calls >= 1
        assert policy.allow_direct_answer is False

    def test_tool_count_consistency(self):
        """测试工具数量一致性"""
        tools = get_tools(mode="natural")
        names = get_tool_names(mode="natural")

        # 工具数量应该等于名称数量
        assert len(tools) == len(names)


class TestMessageTypeHandling:
    """消息类型处理测试"""

    def test_mixed_message_types(self):
        """测试混合消息类型"""
        messages = [
            SystemMessage(content="System"),
            HumanMessage(content="Human"),
            AIMessage(content="AI"),
        ]

        sliding_window = SlidingWindowMiddleware(max_messages=10)
        count = sliding_window._count_messages(messages)
        assert count == 3

    def test_ai_message_with_tool_calls(self):
        """测试带工具调用的 AI 消息"""
        msg = AIMessage(
            content="Let me search for that",
            tool_calls=[
                {"id": "call_1", "name": "search_products", "args": {"query": "test"}}
            ],
        )

        from app.services.agent.middleware.strict_mode import _has_tool_calls
        assert _has_tool_calls(msg) is True

    def test_ai_message_without_tool_calls(self):
        """测试不带工具调用的 AI 消息"""
        msg = AIMessage(content="Just a regular response")

        from app.services.agent.middleware.strict_mode import _has_tool_calls
        assert _has_tool_calls(msg) is False


class TestConfigurationIntegration:
    """配置集成测试"""

    def test_default_configs_work_together(self):
        """测试默认配置协同工作"""
        from app.services.agent.core.config import (
            DEFAULT_PROMPTS,
            DEFAULT_TOOL_CATEGORIES,
            DEFAULT_TOOL_POLICIES,
        )

        # 所有 Agent 类型都应该有配置
        agent_types = ["product", "faq", "kb", "custom"]

        for agent_type in agent_types:
            assert agent_type in DEFAULT_PROMPTS
            assert agent_type in DEFAULT_TOOL_CATEGORIES
            assert agent_type in DEFAULT_TOOL_POLICIES

    def test_product_agent_full_config(self):
        """测试 product Agent 完整配置"""
        from app.services.agent.core.config import (
            DEFAULT_PROMPTS,
            DEFAULT_TOOL_CATEGORIES,
            DEFAULT_TOOL_POLICIES,
        )

        prompt = DEFAULT_PROMPTS["product"]
        categories = DEFAULT_TOOL_CATEGORIES["product"]
        policy = DEFAULT_TOOL_POLICIES["product"]

        # 配置应该有意义
        assert len(prompt) > 100
        assert len(categories) > 0
        assert "search" in categories
        assert policy["allow_direct_answer"] is True


class TestErrorRecovery:
    """错误恢复测试"""

    def test_noise_filter_recovers_from_invalid_json(self):
        """测试噪音过滤器从无效 JSON 恢复"""
        middleware = NoiseFilterMiddleware()

        invalid_jsons = [
            '{"incomplete":',
            '[1, 2, 3',
            'not json at all',
            '',
        ]

        for invalid in invalid_jsons:
            # 不应该抛出异常
            result = middleware._compress_json_output(invalid)
            assert result is not None

    def test_sliding_window_handles_edge_messages(self):
        """测试滑动窗口处理边界消息"""
        middleware = SlidingWindowMiddleware(max_messages=2)

        edge_cases = [
            [],  # 空列表
            [HumanMessage(content="")],  # 空内容
            [HumanMessage(content="a" * 10000)],  # 超长内容
        ]

        for messages in edge_cases:
            # 不应该抛出异常
            result = middleware._trim_messages(messages)
            assert isinstance(result, list)


class TestStateConsistency:
    """状态一致性测试"""

    def test_middleware_stateless(self):
        """测试中间件无状态"""
        middleware = NoiseFilterMiddleware(max_output_chars=100)

        # 多次调用应该产生一致结果
        input_str = "A" * 200
        result1 = middleware._truncate_string(input_str, 100)
        result2 = middleware._truncate_string(input_str, 100)

        assert result1 == result2

    def test_tool_registry_consistency(self):
        """测试工具注册表一致性"""
        # 多次调用应该返回相同结果
        tools1 = get_tools(mode="natural")
        tools2 = get_tools(mode="natural")

        assert len(tools1) == len(tools2)

        names1 = get_tool_names(mode="natural")
        names2 = get_tool_names(mode="natural")

        assert names1 == names2

    def test_policy_immutability(self):
        """测试策略不变性"""
        from app.services.agent.core.policy import NATURAL_POLICY

        # 获取原始值
        original_min_calls = NATURAL_POLICY.min_tool_calls
        original_allow_direct = NATURAL_POLICY.allow_direct_answer

        # 使用后值不变
        _ = NATURAL_POLICY.description
        assert NATURAL_POLICY.min_tool_calls == original_min_calls
        assert NATURAL_POLICY.allow_direct_answer == original_allow_direct
