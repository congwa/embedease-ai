"""滑动窗口中间件测试"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.services.agent.middleware.sliding_window import SlidingWindowMiddleware


class TestSlidingWindowInit:
    """测试中间件初始化"""

    def test_default_init(self):
        """测试默认初始化"""
        middleware = SlidingWindowMiddleware()
        assert middleware.strategy == "messages"
        assert middleware.max_messages == 50
        assert middleware.max_tokens == 8000
        assert middleware.include_system is True
        assert middleware.start_on_human is True
        assert middleware.broadcast_trim is True

    def test_custom_init(self):
        """测试自定义初始化"""
        middleware = SlidingWindowMiddleware(
            strategy="tokens",
            max_messages=100,
            max_tokens=16000,
            include_system=False,
            start_on_human=False,
            broadcast_trim=False,
        )
        assert middleware.strategy == "tokens"
        assert middleware.max_messages == 100
        assert middleware.max_tokens == 16000
        assert middleware.include_system is False


class TestCountMessages:
    """测试消息计数"""

    def test_count_empty(self):
        """测试空列表"""
        middleware = SlidingWindowMiddleware()
        assert middleware._count_messages([]) == 0

    def test_count_none(self):
        """测试 None"""
        middleware = SlidingWindowMiddleware()
        assert middleware._count_messages(None) == 0

    def test_count_messages(self):
        """测试正常计数"""
        middleware = SlidingWindowMiddleware()
        messages = [
            HumanMessage(content="问题1"),
            AIMessage(content="回答1"),
            HumanMessage(content="问题2"),
        ]
        assert middleware._count_messages(messages) == 3


class TestTrimMessages:
    """测试消息裁剪"""

    def test_no_trim_needed(self):
        """测试不需要裁剪"""
        middleware = SlidingWindowMiddleware(max_messages=10)
        messages = [
            SystemMessage(content="系统提示"),
            HumanMessage(content="问题"),
            AIMessage(content="回答"),
        ]
        result = middleware._trim_messages(messages)
        assert len(result) == 3

    def test_trim_by_messages(self):
        """测试按消息数量裁剪"""
        middleware = SlidingWindowMiddleware(
            strategy="messages",
            max_messages=3,
        )
        messages = [
            SystemMessage(content="系统提示"),
            HumanMessage(content="问题1"),
            AIMessage(content="回答1"),
            HumanMessage(content="问题2"),
            AIMessage(content="回答2"),
            HumanMessage(content="问题3"),
            AIMessage(content="回答3"),
        ]
        result = middleware._trim_messages(messages)
        # 应该保留 system + 最近的消息
        assert len(result) <= 4  # system + 最多 3 条

    def test_preserve_system_message(self):
        """测试保留 SystemMessage"""
        middleware = SlidingWindowMiddleware(
            strategy="messages",
            max_messages=2,
            include_system=True,
        )
        messages = [
            SystemMessage(content="系统提示"),
            HumanMessage(content="问题1"),
            AIMessage(content="回答1"),
            HumanMessage(content="问题2"),
            AIMessage(content="回答2"),
        ]
        result = middleware._trim_messages(messages)
        # SystemMessage 应该被保留
        system_msgs = [m for m in result if isinstance(m, SystemMessage)]
        assert len(system_msgs) >= 1

    def test_start_on_human(self):
        """测试从 HumanMessage 开始"""
        middleware = SlidingWindowMiddleware(
            strategy="messages",
            max_messages=3,
            start_on_human=True,
        )
        messages = [
            SystemMessage(content="系统"),
            HumanMessage(content="问题1"),
            AIMessage(content="回答1"),
            HumanMessage(content="问题2"),
            AIMessage(content="回答2"),
        ]
        result = middleware._trim_messages(messages)
        # 去掉 SystemMessage 后，第一条应该是 HumanMessage
        non_system = [m for m in result if not isinstance(m, SystemMessage)]
        if non_system:
            assert isinstance(non_system[0], HumanMessage)

    def test_empty_messages(self):
        """测试空消息列表"""
        middleware = SlidingWindowMiddleware()
        assert middleware._trim_messages([]) == []


class TestBeforeModel:
    """测试 before_model 方法"""

    def test_no_trim_below_threshold(self):
        """测试低于阈值不裁剪"""
        middleware = SlidingWindowMiddleware(
            strategy="messages",
            max_messages=10,
        )
        state = {
            "messages": [
                HumanMessage(content="问题"),
                AIMessage(content="回答"),
            ]
        }

        class MockRuntime:
            pass

        result = middleware.before_model(state, MockRuntime())
        assert result is None  # 不需要裁剪

    def test_trim_above_threshold(self):
        """测试超过阈值裁剪"""
        middleware = SlidingWindowMiddleware(
            strategy="messages",
            max_messages=3,
        )
        messages = [
            SystemMessage(content="系统"),
            HumanMessage(content="问题1"),
            AIMessage(content="回答1"),
            HumanMessage(content="问题2"),
            AIMessage(content="回答2"),
            HumanMessage(content="问题3"),
            AIMessage(content="回答3"),
        ]
        state = {"messages": messages}

        class MockRuntime:
            pass

        result = middleware.before_model(state, MockRuntime())
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) < len(messages)

    def test_empty_state(self):
        """测试空状态"""
        middleware = SlidingWindowMiddleware()
        state = {}

        class MockRuntime:
            pass

        result = middleware.before_model(state, MockRuntime())
        assert result is None


class TestTokenStrategy:
    """测试 Token 策略"""

    def test_token_strategy_init(self):
        """测试 Token 策略初始化"""
        middleware = SlidingWindowMiddleware(
            strategy="tokens",
            max_tokens=1000,
        )
        assert middleware.strategy == "tokens"
        assert middleware.max_tokens == 1000

    def test_messages_strategy_trim_with_long_content(self):
        """测试消息策略裁剪较长内容"""
        middleware = SlidingWindowMiddleware(
            strategy="messages",
            max_messages=2,
        )
        # 创建包含较长内容的消息
        messages = [
            SystemMessage(content="系统提示" * 10),
            HumanMessage(content="这是一个很长的问题" * 20),
            AIMessage(content="这是一个很长的回答" * 20),
            HumanMessage(content="另一个很长的问题" * 20),
        ]
        result = middleware._trim_messages(messages)
        # 消息策略会裁剪到指定数量
        assert len(result) <= 3  # system + 最多 2 条
