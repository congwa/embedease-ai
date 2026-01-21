"""Agent Schema 测试"""

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    AgentBase,
    AgentCreate,
    AgentUpdate,
    FAQEntryBase,
    FAQEntryCreate,
    FAQEntryUpdate,
    GreetingConfigSchema,
    GreetingCTASchema,
    GreetingChannelSchema,
    KnowledgeConfigBase,
    KnowledgeConfigCreate,
    KnowledgeConfigUpdate,
    MiddlewareFlagsSchema,
    RoutingPolicy,
    RoutingRule,
    RoutingCondition,
    SubAgentConfig,
    SupervisorConfigSchema,
    ToolPolicySchema,
)


class TestGreetingCTASchema:
    """测试开场白 CTA 按钮 Schema"""

    def test_valid_cta(self):
        """测试有效的 CTA"""
        cta = GreetingCTASchema(text="开始对话", payload="start_chat")
        assert cta.text == "开始对话"
        assert cta.payload == "start_chat"

    def test_empty_text_invalid(self):
        """测试空文本无效"""
        with pytest.raises(ValidationError):
            GreetingCTASchema(text="", payload="test")

    def test_text_max_length(self):
        """测试文本长度限制"""
        long_text = "a" * 51
        with pytest.raises(ValidationError):
            GreetingCTASchema(text=long_text, payload="test")


class TestGreetingChannelSchema:
    """测试渠道开场白配置 Schema"""

    def test_valid_channel(self):
        """测试有效的渠道配置"""
        channel = GreetingChannelSchema(
            title="欢迎",
            subtitle="有什么可以帮您？",
            body="您好，我是智能助手。",
        )
        assert channel.title == "欢迎"
        assert channel.body == "您好，我是智能助手。"

    def test_body_required(self):
        """测试正文必填"""
        with pytest.raises(ValidationError):
            GreetingChannelSchema(title="欢迎")

    def test_optional_fields(self):
        """测试可选字段"""
        channel = GreetingChannelSchema(body="正文内容")
        assert channel.title is None
        assert channel.subtitle is None
        assert channel.cta is None


class TestGreetingConfigSchema:
    """测试开场白完整配置 Schema"""

    def test_defaults(self):
        """测试默认值"""
        config = GreetingConfigSchema()
        assert config.enabled is False
        assert config.trigger == "first_visit"
        assert config.delay_ms == 1000
        assert config.channels == {}

    def test_full_config(self):
        """测试完整配置"""
        config = GreetingConfigSchema(
            enabled=True,
            trigger="every_session",
            delay_ms=2000,
            channels={
                "web": GreetingChannelSchema(body="网页端欢迎"),
            },
            cta=GreetingCTASchema(text="开始", payload="start"),
        )
        assert config.enabled is True
        assert config.trigger == "every_session"
        assert "web" in config.channels

    def test_delay_range(self):
        """测试延迟范围限制"""
        with pytest.raises(ValidationError):
            GreetingConfigSchema(delay_ms=-1)

        with pytest.raises(ValidationError):
            GreetingConfigSchema(delay_ms=10001)


class TestToolPolicySchema:
    """测试工具调用策略 Schema"""

    def test_defaults(self):
        """测试默认值"""
        policy = ToolPolicySchema()
        assert policy.min_tool_calls == 0
        assert policy.allow_direct_answer is True
        assert policy.fallback_tool is None
        assert policy.clarification_tool is None

    def test_custom_policy(self):
        """测试自定义策略"""
        policy = ToolPolicySchema(
            min_tool_calls=1,
            allow_direct_answer=False,
            fallback_tool="search_products",
        )
        assert policy.min_tool_calls == 1
        assert policy.allow_direct_answer is False


class TestSubAgentConfig:
    """测试子 Agent 配置 Schema"""

    def test_valid_config(self):
        """测试有效配置"""
        config = SubAgentConfig(
            agent_id="agent_123",
            name="商品推荐助手",
            description="专门负责商品推荐",
            routing_hints=["推荐", "商品"],
            priority=10,
        )
        assert config.agent_id == "agent_123"
        assert config.name == "商品推荐助手"
        assert config.priority == 10

    def test_defaults(self):
        """测试默认值"""
        config = SubAgentConfig(agent_id="test", name="Test")
        assert config.description is None
        assert config.routing_hints == []
        assert config.priority == 0


class TestRoutingCondition:
    """测试路由条件 Schema"""

    def test_keyword_condition(self):
        """测试关键词条件"""
        condition = RoutingCondition(
            type="keyword",
            keywords=["推荐", "查询"],
        )
        assert condition.type == "keyword"
        assert "推荐" in condition.keywords

    def test_intent_condition(self):
        """测试意图条件"""
        condition = RoutingCondition(
            type="intent",
            intents=["product_search", "price_query"],
        )
        assert condition.type == "intent"


class TestRoutingRule:
    """测试路由规则 Schema"""

    def test_valid_rule(self):
        """测试有效规则"""
        rule = RoutingRule(
            condition=RoutingCondition(type="keyword", keywords=["测试"]),
            target="agent_123",
            priority=5,
        )
        assert rule.target == "agent_123"
        assert rule.priority == 5


class TestRoutingPolicy:
    """测试路由策略 Schema"""

    def test_defaults(self):
        """测试默认值"""
        policy = RoutingPolicy()
        assert policy.type == "hybrid"
        assert policy.rules == []
        assert policy.default_agent is None
        assert policy.allow_multi_agent is False

    def test_full_policy(self):
        """测试完整策略"""
        policy = RoutingPolicy(
            type="keyword",
            rules=[
                RoutingRule(
                    condition=RoutingCondition(type="keyword", keywords=["FAQ"]),
                    target="faq_agent",
                )
            ],
            default_agent="default_agent",
            allow_multi_agent=True,
        )
        assert len(policy.rules) == 1


class TestMiddlewareFlagsSchema:
    """测试中间件开关配置 Schema"""

    def test_all_none_defaults(self):
        """测试所有字段默认为 None"""
        flags = MiddlewareFlagsSchema()
        assert flags.todo_enabled is None
        assert flags.tool_retry_enabled is None
        assert flags.memory_enabled is None
        assert flags.sliding_window_enabled is None
        assert flags.summarization_enabled is None
        assert flags.noise_filter_enabled is None

    def test_partial_config(self):
        """测试部分配置"""
        flags = MiddlewareFlagsSchema(
            todo_enabled=True,
            memory_enabled=False,
            sliding_window_max_messages=100,
        )
        assert flags.todo_enabled is True
        assert flags.memory_enabled is False
        assert flags.sliding_window_max_messages == 100

    def test_sliding_window_range(self):
        """测试滑动窗口范围限制"""
        with pytest.raises(ValidationError):
            MiddlewareFlagsSchema(sliding_window_max_messages=5)

        with pytest.raises(ValidationError):
            MiddlewareFlagsSchema(sliding_window_max_messages=600)


class TestKnowledgeConfigBase:
    """测试知识源配置 Schema"""

    def test_required_fields(self):
        """测试必填字段"""
        config = KnowledgeConfigBase(name="商品知识库")
        assert config.name == "商品知识库"
        assert config.type == "vector"
        assert config.top_k == 10

    def test_full_config(self):
        """测试完整配置"""
        config = KnowledgeConfigBase(
            name="FAQ知识库",
            type="faq",
            index_name="faq_index",
            collection_name="faq_collection",
            top_k=5,
            similarity_threshold=0.8,
            rerank_enabled=True,
        )
        assert config.type == "faq"
        assert config.similarity_threshold == 0.8

    def test_top_k_range(self):
        """测试 top_k 范围"""
        with pytest.raises(ValidationError):
            KnowledgeConfigBase(name="test", top_k=0)

        with pytest.raises(ValidationError):
            KnowledgeConfigBase(name="test", top_k=101)


class TestKnowledgeConfigUpdate:
    """测试知识源配置更新 Schema"""

    def test_all_optional(self):
        """测试所有字段可选"""
        update = KnowledgeConfigUpdate()
        assert update.name is None
        assert update.type is None

    def test_partial_update(self):
        """测试部分更新"""
        update = KnowledgeConfigUpdate(top_k=20, rerank_enabled=True)
        assert update.top_k == 20
        assert update.rerank_enabled is True


class TestAgentBase:
    """测试 Agent 基础 Schema"""

    def test_required_fields(self):
        """测试必填字段"""
        agent = AgentBase(
            name="测试助手",
            system_prompt="你是一个测试助手。",
        )
        assert agent.name == "测试助手"
        assert agent.type == "product"
        assert agent.mode_default == "natural"
        assert agent.status == "enabled"
        assert agent.is_default is False

    def test_full_config(self):
        """测试完整配置"""
        agent = AgentBase(
            name="商品助手",
            description="专业商品推荐",
            type="product",
            system_prompt="你是商品推荐专家。",
            mode_default="strict",
            status="disabled",
            is_default=True,
            is_supervisor=True,
        )
        assert agent.description == "专业商品推荐"
        assert agent.is_supervisor is True

    def test_name_length(self):
        """测试名称长度限制"""
        with pytest.raises(ValidationError):
            AgentBase(name="", system_prompt="test")

        long_name = "a" * 101
        with pytest.raises(ValidationError):
            AgentBase(name=long_name, system_prompt="test")


class TestAgentUpdate:
    """测试 Agent 更新 Schema"""

    def test_all_optional(self):
        """测试所有字段可选"""
        update = AgentUpdate()
        assert update.name is None
        assert update.system_prompt is None

    def test_partial_update(self):
        """测试部分更新"""
        update = AgentUpdate(
            name="新名称",
            status="disabled",
        )
        assert update.name == "新名称"
        assert update.status == "disabled"


class TestFAQEntryBase:
    """测试 FAQ 条目 Schema"""

    def test_required_fields(self):
        """测试必填字段"""
        entry = FAQEntryBase(
            question="如何退款？",
            answer="请联系客服处理退款。",
        )
        assert entry.question == "如何退款？"
        assert entry.answer == "请联系客服处理退款。"
        assert entry.enabled is True
        assert entry.priority == 0

    def test_full_entry(self):
        """测试完整条目"""
        entry = FAQEntryBase(
            question="配送时间？",
            answer="一般3-5个工作日。",
            category="物流",
            tags=["配送", "时效"],
            source="官网FAQ",
            priority=10,
            enabled=False,
        )
        assert entry.category == "物流"
        assert "配送" in entry.tags


class TestFAQEntryUpdate:
    """测试 FAQ 更新 Schema"""

    def test_all_optional(self):
        """测试所有字段可选"""
        update = FAQEntryUpdate()
        assert update.question is None
        assert update.answer is None

    def test_partial_update(self):
        """测试部分更新"""
        update = FAQEntryUpdate(
            answer="新答案",
            enabled=False,
        )
        assert update.answer == "新答案"
        assert update.enabled is False
