"""意图分类器测试"""

import pytest

from app.schemas.agent import (
    RoutingPolicy,
    RoutingRule,
    RoutingCondition,
    SubAgentConfig,
)
from app.services.agent.core.intent import IntentClassifier


class TestIntentClassifierInit:
    """测试意图分类器初始化"""

    def test_basic_init(self):
        """测试基本初始化"""
        policy = RoutingPolicy()
        sub_agents = [
            SubAgentConfig(agent_id="agent_1", name="Agent 1"),
        ]
        classifier = IntentClassifier(
            routing_policy=policy,
            sub_agents=sub_agents,
        )
        assert classifier.policy is policy
        assert len(classifier.sub_agents) == 1

    def test_agent_map_creation(self):
        """测试 Agent 映射创建"""
        policy = RoutingPolicy()
        sub_agents = [
            SubAgentConfig(agent_id="product_agent", name="商品助手"),
            SubAgentConfig(agent_id="faq_agent", name="FAQ助手"),
        ]
        classifier = IntentClassifier(
            routing_policy=policy,
            sub_agents=sub_agents,
        )
        assert "product_agent" in classifier._agent_map
        assert "faq_agent" in classifier._agent_map

    def test_empty_sub_agents(self):
        """测试空子 Agent 列表"""
        policy = RoutingPolicy()
        classifier = IntentClassifier(
            routing_policy=policy,
            sub_agents=[],
        )
        assert len(classifier.sub_agents) == 0
        assert len(classifier._agent_map) == 0


class TestRoutingPolicy:
    """测试路由策略"""

    def test_keyword_policy_type(self):
        """测试关键词策略类型"""
        policy = RoutingPolicy(type="keyword")
        assert policy.type == "keyword"

    def test_intent_policy_type(self):
        """测试意图策略类型"""
        policy = RoutingPolicy(type="intent")
        assert policy.type == "intent"

    def test_hybrid_policy_type(self):
        """测试混合策略类型"""
        policy = RoutingPolicy(type="hybrid")
        assert policy.type == "hybrid"

    def test_default_policy_type(self):
        """测试默认策略类型"""
        policy = RoutingPolicy()
        assert policy.type == "hybrid"


class TestRoutingRule:
    """测试路由规则"""

    def test_keyword_rule(self):
        """测试关键词规则"""
        rule = RoutingRule(
            condition=RoutingCondition(
                type="keyword",
                keywords=["推荐", "商品"],
            ),
            target="product_agent",
            priority=10,
        )
        assert rule.target == "product_agent"
        assert rule.priority == 10
        assert "推荐" in rule.condition.keywords

    def test_intent_rule(self):
        """测试意图规则"""
        rule = RoutingRule(
            condition=RoutingCondition(
                type="intent",
                intents=["product_search", "price_query"],
            ),
            target="product_agent",
        )
        assert "product_search" in rule.condition.intents


class TestSubAgentConfig:
    """测试子 Agent 配置"""

    def test_routing_hints(self):
        """测试路由提示"""
        config = SubAgentConfig(
            agent_id="product_agent",
            name="商品助手",
            routing_hints=["推荐", "商品", "购买"],
            priority=10,
        )
        assert len(config.routing_hints) == 3
        assert "推荐" in config.routing_hints
        assert config.priority == 10

    def test_priority_sorting(self):
        """测试优先级排序"""
        configs = [
            SubAgentConfig(agent_id="a", name="A", priority=5),
            SubAgentConfig(agent_id="b", name="B", priority=10),
            SubAgentConfig(agent_id="c", name="C", priority=1),
        ]
        sorted_configs = sorted(configs, key=lambda x: x.priority, reverse=True)
        assert sorted_configs[0].agent_id == "b"
        assert sorted_configs[1].agent_id == "a"
        assert sorted_configs[2].agent_id == "c"


class TestKeywordMatching:
    """测试关键词匹配逻辑"""

    def test_keyword_in_message(self):
        """测试消息中包含关键词"""
        message = "请推荐一款手机"
        keywords = ["推荐", "手机"]
        for keyword in keywords:
            assert keyword in message

    def test_keyword_case_insensitive(self):
        """测试关键词大小写不敏感"""
        message = "FAQ question".lower()
        keyword = "faq"
        assert keyword in message

    def test_no_keyword_match(self):
        """测试无关键词匹配"""
        message = "今天天气怎么样"
        keywords = ["推荐", "商品", "购买"]
        for keyword in keywords:
            assert keyword not in message


class TestRoutingPolicyRules:
    """测试路由策略规则"""

    def test_policy_with_rules(self):
        """测试带规则的策略"""
        policy = RoutingPolicy(
            type="keyword",
            rules=[
                RoutingRule(
                    condition=RoutingCondition(type="keyword", keywords=["FAQ"]),
                    target="faq_agent",
                    priority=10,
                ),
                RoutingRule(
                    condition=RoutingCondition(type="keyword", keywords=["商品"]),
                    target="product_agent",
                    priority=5,
                ),
            ],
        )
        assert len(policy.rules) == 2

    def test_rules_priority_order(self):
        """测试规则优先级排序"""
        rules = [
            RoutingRule(
                condition=RoutingCondition(type="keyword", keywords=["a"]),
                target="a",
                priority=5,
            ),
            RoutingRule(
                condition=RoutingCondition(type="keyword", keywords=["b"]),
                target="b",
                priority=10,
            ),
        ]
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)
        assert sorted_rules[0].target == "b"

    def test_default_agent_fallback(self):
        """测试默认 Agent 回退"""
        policy = RoutingPolicy(
            type="keyword",
            default_agent="default_agent",
        )
        assert policy.default_agent == "default_agent"

    def test_multi_agent_allowed(self):
        """测试允许多 Agent 协作"""
        policy = RoutingPolicy(
            type="hybrid",
            allow_multi_agent=True,
        )
        assert policy.allow_multi_agent is True
