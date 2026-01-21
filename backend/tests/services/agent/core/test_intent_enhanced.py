"""IntentClassifier 增强测试

测试意图分类器的模糊意图处理、意图切换和上下文延续。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.agent.core.intent import IntentClassifier
from app.schemas.agent import RoutingPolicy, RoutingRule, SubAgentConfig, RoutingCondition


class TestIntentClassifierAmbiguityHandling:
    """测试模糊意图处理"""

    def test_short_message_continues_context(self):
        """测试短消息继续上下文"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        # 短消息应该继续使用当前 Agent
        result = classifier._should_continue("好的", "product_agent")
        assert result is True

    def test_long_message_may_switch(self):
        """测试长消息可能切换"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        # 长消息不一定继续
        long_msg = "我想问一下关于退款的问题，之前买的商品有质量问题"
        result = classifier._should_continue(long_msg, "product_agent")
        # 取决于是否有切换信号
        assert isinstance(result, bool)

    def test_switch_signal_detected(self):
        """测试检测到切换信号"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        # 包含切换信号的消息（需要超过 20 字符才会检查切换信号）
        # switch_signals = ["换一个", "换个", "其他", "另一个", "不是这个"]
        switch_messages = [
            "我想换一个助手来帮助我处理这个问题好吗请帮忙",  # 包含"换一个"，>20字符
            "我需要换个助手来处理这个比较复杂的问题吧",  # 包含"换个"，>20字符
            "我有其他问题需要问一下别的助手帮忙处理下",  # 包含"其他"，>20字符
            "另一个问题，我想请找别的人来帮忙处理一下",  # 包含"另一个"，>20字符
            "不是这个问题，我要换一下方向重新来开始做",  # 包含"不是这个"，>20字符
        ]
        for msg in switch_messages:
            assert len(msg) >= 20, f"消息'{msg}'长度不足20，实际{len(msg)}"
            result = classifier._should_continue(msg, "product_agent")
            assert result is False, f"'{msg}' 应该触发切换"


class TestIntentClassifierKeywordRouting:
    """测试关键词路由"""

    @pytest.mark.anyio
    async def test_keyword_match_priority(self):
        """测试关键词匹配优先级"""
        rules = [
            RoutingRule(
                condition=RoutingCondition(type="keyword", keywords=["退款", "退货"]),
                target="refund_agent",
                priority=10,
            ),
            RoutingRule(
                condition=RoutingCondition(type="keyword", keywords=["商品", "产品"]),
                target="product_agent",
                priority=5,
            ),
        ]
        policy = RoutingPolicy(type="keyword", rules=rules, default_agent="default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        # 退款关键词应该优先
        result = await classifier._keyword_routing("我想退款这个商品")
        assert result == "refund_agent"

    @pytest.mark.anyio
    async def test_no_keyword_match(self):
        """测试无关键词匹配"""
        rules = [
            RoutingRule(
                condition=RoutingCondition(type="keyword", keywords=["退款"]),
                target="refund_agent",
                priority=10,
            ),
        ]
        policy = RoutingPolicy(type="keyword", rules=rules, default_agent="default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        result = await classifier._keyword_routing("今天天气怎么样")
        assert result is None

    @pytest.mark.anyio
    async def test_routing_hints_match(self):
        """测试 routing_hints 匹配"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        sub_agents = [
            SubAgentConfig(
                agent_id="product_agent",
                name="商品助手",
                priority=10,
                routing_hints=["商品", "购买", "推荐"],
            ),
        ]
        classifier = IntentClassifier(policy, sub_agents)

        result = await classifier._keyword_routing("帮我推荐一个商品")
        assert result == "product_agent"


class TestIntentClassifierDefaultAgent:
    """测试默认 Agent 获取"""

    def test_get_default_agent_from_policy(self):
        """测试从策略获取默认 Agent"""
        policy = RoutingPolicy(type="keyword", default_agent="my_default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        result = classifier.get_default_agent()
        assert result == "my_default"

    def test_get_default_agent_from_sub_agents(self):
        """测试从子 Agent 获取默认（最高优先级）"""
        policy = RoutingPolicy(type="keyword", default_agent=None)
        sub_agents = [
            SubAgentConfig(agent_id="low_priority", name="低优先级", priority=1),
            SubAgentConfig(agent_id="high_priority", name="高优先级", priority=10),
            SubAgentConfig(agent_id="mid_priority", name="中优先级", priority=5),
        ]
        classifier = IntentClassifier(policy, sub_agents)

        result = classifier.get_default_agent()
        assert result == "high_priority"

    def test_get_default_agent_none(self):
        """测试无默认 Agent"""
        policy = RoutingPolicy(type="keyword", default_agent=None)
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        result = classifier.get_default_agent()
        assert result is None


class TestIntentClassifierClassify:
    """测试分类方法"""

    @pytest.mark.anyio
    async def test_classify_with_context_continuation(self):
        """测试带上下文延续的分类"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        # 短消息 + 当前 Agent = 继续使用
        result = await classifier.classify("好", context={"current_agent": "product_agent"})
        assert result == "product_agent"

    @pytest.mark.anyio
    async def test_classify_keyword_routing(self):
        """测试关键词路由分类"""
        rules = [
            RoutingRule(
                condition=RoutingCondition(type="keyword", keywords=["退款"]),
                target="refund_agent",
                priority=10,
            ),
        ]
        policy = RoutingPolicy(type="keyword", rules=rules, default_agent="default")
        sub_agents = []
        classifier = IntentClassifier(policy, sub_agents)

        result = await classifier.classify("我要退款")
        assert result == "refund_agent"


class TestIntentResponseParsing:
    """测试意图响应解析"""

    def test_parse_simple_intent(self):
        """测试解析简单意图"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._parse_intent_response("product_search")
        assert result == "product_search"

    def test_parse_intent_with_prefix(self):
        """测试解析带前缀的意图"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._parse_intent_response("- product_search")
        assert result == "product_search"

    def test_parse_intent_with_newlines(self):
        """测试解析带换行的意图"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._parse_intent_response("product_search\n其他内容")
        assert result == "product_search"

    def test_parse_unknown_intent(self):
        """测试解析 unknown 意图"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._parse_intent_response("unknown")
        assert result is None

    def test_parse_empty_response(self):
        """测试解析空响应"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._parse_intent_response("")
        assert result is None

    def test_parse_none_response(self):
        """测试解析 None 响应"""
        policy = RoutingPolicy(type="keyword", default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._parse_intent_response(None)
        assert result is None


class TestIntentToAgentMapping:
    """测试意图到 Agent 映射"""

    def test_match_intent_to_agent_by_rule(self):
        """测试通过规则匹配意图到 Agent"""
        rules = [
            RoutingRule(
                condition=RoutingCondition(type="intent", intents=["product_search", "browse"]),
                target="product_agent",
                priority=10,
            ),
        ]
        policy = RoutingPolicy(type="intent", rules=rules, default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._match_intent_to_agent("product_search")
        assert result == "product_agent"

    def test_match_intent_to_agent_by_name(self):
        """测试通过名称匹配意图到 Agent"""
        policy = RoutingPolicy(type="intent", default_agent="default")
        sub_agents = [
            SubAgentConfig(agent_id="product_agent", name="商品助手", priority=10),
        ]
        classifier = IntentClassifier(policy, sub_agents)

        result = classifier._match_intent_to_agent("商品助手")
        assert result == "product_agent"

    def test_match_intent_no_match(self):
        """测试无匹配"""
        policy = RoutingPolicy(type="intent", default_agent="default")
        classifier = IntentClassifier(policy, [])

        result = classifier._match_intent_to_agent("random_intent")
        assert result is None
