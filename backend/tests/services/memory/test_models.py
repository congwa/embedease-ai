"""Memory 数据模型测试"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.services.memory.models import (
    Entity,
    Fact,
    KnowledgeGraph,
    MemoryAction,
    Relation,
    UserProfile,
)


class TestMemoryAction:
    """测试记忆操作类型枚举"""

    def test_action_values(self):
        """测试枚举值"""
        assert MemoryAction.ADD == "ADD"
        assert MemoryAction.UPDATE == "UPDATE"
        assert MemoryAction.DELETE == "DELETE"
        assert MemoryAction.NONE == "NONE"

    def test_action_is_string(self):
        """测试枚举是字符串类型"""
        assert isinstance(MemoryAction.ADD, str)
        assert MemoryAction.ADD.lower() == "add"


class TestFact:
    """测试事实记录模型"""

    def test_required_fields(self):
        """测试必填字段"""
        fact = Fact(
            id="fact_123",
            user_id="user_456",
            content="用户喜欢红色",
            hash="abc123",
        )
        assert fact.id == "fact_123"
        assert fact.user_id == "user_456"
        assert fact.content == "用户喜欢红色"
        assert fact.hash == "abc123"

    def test_default_timestamps(self):
        """测试默认时间戳"""
        fact = Fact(
            id="fact_1",
            user_id="user_1",
            content="测试内容",
            hash="hash1",
        )
        assert isinstance(fact.created_at, datetime)
        assert isinstance(fact.updated_at, datetime)

    def test_default_metadata(self):
        """测试默认元数据"""
        fact = Fact(
            id="fact_1",
            user_id="user_1",
            content="测试",
            hash="hash",
        )
        assert fact.metadata == {}

    def test_custom_metadata(self):
        """测试自定义元数据"""
        fact = Fact(
            id="fact_1",
            user_id="user_1",
            content="测试",
            hash="hash",
            metadata={"source": "chat", "confidence": 0.9},
        )
        assert fact.metadata["source"] == "chat"
        assert fact.metadata["confidence"] == 0.9


class TestEntity:
    """测试图谱实体模型"""

    def test_required_fields(self):
        """测试必填字段"""
        entity = Entity(
            name="iPhone 15",
            entity_type="product",
        )
        assert entity.name == "iPhone 15"
        assert entity.entity_type == "product"

    def test_default_observations(self):
        """测试默认观察列表"""
        entity = Entity(name="用户A", entity_type="person")
        assert entity.observations == []

    def test_with_observations(self):
        """测试带观察的实体"""
        entity = Entity(
            name="小明",
            entity_type="person",
            observations=["喜欢电子产品", "预算5000元", "偏好黑色"],
        )
        assert len(entity.observations) == 3
        assert "喜欢电子产品" in entity.observations


class TestRelation:
    """测试图谱关系模型"""

    def test_required_fields(self):
        """测试必填字段"""
        relation = Relation(
            from_entity="小明",
            to_entity="iPhone 15",
            relation_type="wants_to_buy",
        )
        assert relation.from_entity == "小明"
        assert relation.to_entity == "iPhone 15"
        assert relation.relation_type == "wants_to_buy"

    def test_various_relation_types(self):
        """测试各种关系类型"""
        relations = [
            Relation(from_entity="A", to_entity="B", relation_type="owns"),
            Relation(from_entity="A", to_entity="B", relation_type="prefers"),
            Relation(from_entity="A", to_entity="B", relation_type="purchased"),
        ]
        assert len(relations) == 3


class TestKnowledgeGraph:
    """测试知识图谱模型"""

    def test_empty_graph(self):
        """测试空图谱"""
        graph = KnowledgeGraph()
        assert graph.entities == []
        assert graph.relations == []

    def test_graph_with_entities(self):
        """测试带实体的图谱"""
        graph = KnowledgeGraph(
            entities=[
                Entity(name="用户", entity_type="person"),
                Entity(name="手机", entity_type="product"),
            ]
        )
        assert len(graph.entities) == 2

    def test_graph_with_relations(self):
        """测试带关系的图谱"""
        graph = KnowledgeGraph(
            entities=[
                Entity(name="小明", entity_type="person"),
                Entity(name="iPhone", entity_type="product"),
            ],
            relations=[
                Relation(from_entity="小明", to_entity="iPhone", relation_type="wants"),
            ],
        )
        assert len(graph.relations) == 1
        assert graph.relations[0].relation_type == "wants"

    def test_complex_graph(self):
        """测试复杂图谱"""
        graph = KnowledgeGraph(
            entities=[
                Entity(
                    name="小明",
                    entity_type="person",
                    observations=["预算5000", "喜欢黑色"],
                ),
                Entity(name="iPhone 15", entity_type="product"),
                Entity(name="AirPods", entity_type="product"),
            ],
            relations=[
                Relation(from_entity="小明", to_entity="iPhone 15", relation_type="wants"),
                Relation(from_entity="小明", to_entity="AirPods", relation_type="owns"),
                Relation(from_entity="iPhone 15", to_entity="AirPods", relation_type="compatible_with"),
            ],
        )
        assert len(graph.entities) == 3
        assert len(graph.relations) == 3


class TestUserProfile:
    """测试用户画像模型"""

    def test_required_fields(self):
        """测试必填字段"""
        profile = UserProfile(user_id="user_123")
        assert profile.user_id == "user_123"

    def test_default_values(self):
        """测试默认值"""
        profile = UserProfile(user_id="user_1")
        assert profile.nickname is None
        assert profile.tone_preference is None
        assert profile.budget_min is None
        assert profile.budget_max is None
        assert profile.favorite_categories == []
        assert profile.task_progress == {}
        assert profile.feature_flags == {}
        assert profile.custom_data == {}

    def test_full_profile(self):
        """测试完整画像"""
        profile = UserProfile(
            user_id="user_456",
            nickname="小明",
            tone_preference="friendly",
            budget_min=1000.0,
            budget_max=5000.0,
            favorite_categories=["手机", "电脑", "耳机"],
            task_progress={"onboarding": "completed"},
            feature_flags={"beta_feature": True},
            custom_data={"referrer": "google"},
        )
        assert profile.nickname == "小明"
        assert profile.tone_preference == "friendly"
        assert profile.budget_min == 1000.0
        assert profile.budget_max == 5000.0
        assert "手机" in profile.favorite_categories
        assert profile.task_progress["onboarding"] == "completed"
        assert profile.feature_flags["beta_feature"] is True

    def test_updated_at_default(self):
        """测试更新时间默认值"""
        profile = UserProfile(user_id="user_1")
        assert isinstance(profile.updated_at, datetime)

    def test_budget_range(self):
        """测试预算范围"""
        profile = UserProfile(
            user_id="user_1",
            budget_min=500.5,
            budget_max=10000.99,
        )
        assert profile.budget_min == 500.5
        assert profile.budget_max == 10000.99
        assert profile.budget_max > profile.budget_min
