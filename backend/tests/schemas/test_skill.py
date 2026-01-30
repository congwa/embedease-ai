"""技能 Schema 测试"""

import pytest
from pydantic import ValidationError

from app.schemas.skill import (
    AgentSkillConfig,
    AgentSkillsUpdate,
    SkillBase,
    SkillCategory,
    SkillCreate,
    SkillGenerateRequest,
    SkillGenerateResponse,
    SkillListResponse,
    SkillRead,
    SkillRefineRequest,
    SkillType,
    SkillUpdate,
)


class TestSkillBase:
    """测试 SkillBase Schema"""

    def test_valid_skill_base(self):
        """测试有效的技能基础数据"""
        skill = SkillBase(
            name="测试技能",
            description="这是一个测试技能的详细描述，至少需要10个字符",
            content="这是技能内容的详细说明，包含使用规则和指导原则",
        )
        assert skill.name == "测试技能"
        assert skill.category == SkillCategory.PROMPT

    def test_name_min_length(self):
        """测试名称最小长度"""
        with pytest.raises(ValidationError):
            SkillBase(
                name="",
                description="这是一个测试技能描述",
                content="这是技能内容",
            )

    def test_description_min_length(self):
        """测试描述最小长度"""
        with pytest.raises(ValidationError):
            SkillBase(
                name="测试",
                description="短",
                content="这是技能内容的详细说明",
            )

    def test_content_min_length(self):
        """测试内容最小长度"""
        with pytest.raises(ValidationError):
            SkillBase(
                name="测试",
                description="这是一个测试技能的详细描述",
                content="短",
            )

    def test_default_values(self):
        """测试默认值"""
        skill = SkillBase(
            name="测试技能",
            description="这是一个测试技能的详细描述信息",
            content="这是技能内容的详细说明和使用指南",
        )
        assert skill.category == SkillCategory.PROMPT
        assert skill.trigger_keywords == []
        assert skill.trigger_intents == []
        assert skill.always_apply is False
        assert skill.applicable_agents == []

    def test_all_categories(self):
        """测试所有分类"""
        for category in SkillCategory:
            skill = SkillBase(
                name="测试技能",
                description="这是一个测试技能的详细描述信息",
                content="这是技能内容的详细说明和使用指南",
                category=category,
            )
            assert skill.category == category


class TestSkillCreate:
    """测试 SkillCreate Schema"""

    def test_create_with_all_fields(self):
        """测试创建包含所有字段"""
        skill = SkillCreate(
            name="商品对比",
            description="帮助用户对比多个商品",
            content="## 对比规则\n1. 列出价格...",
            category=SkillCategory.PROMPT,
            trigger_keywords=["对比", "比较"],
            trigger_intents=["compare"],
            always_apply=False,
            applicable_agents=["product"],
        )
        assert skill.name == "商品对比"
        assert "对比" in skill.trigger_keywords


class TestSkillUpdate:
    """测试 SkillUpdate Schema"""

    def test_partial_update(self):
        """测试部分更新"""
        update = SkillUpdate(name="新名称")
        assert update.name == "新名称"
        assert update.description is None
        assert update.content is None

    def test_full_update(self):
        """测试完整更新"""
        update = SkillUpdate(
            name="新名称",
            description="新描述内容详细说明至少十个字符",
            content="新技能内容详细说明至少十个字符",
            is_active=False,
        )
        assert update.name == "新名称"
        assert update.is_active is False

    def test_empty_update(self):
        """测试空更新"""
        update = SkillUpdate()
        assert update.name is None


class TestSkillRead:
    """测试 SkillRead Schema"""

    def test_from_attributes(self):
        """测试 from_attributes 配置"""
        from datetime import datetime

        data = {
            "id": "test-id",
            "name": "测试技能",
            "description": "这是测试描述的详细信息和说明",
            "content": "这是技能内容的详细说明和使用指南",
            "category": SkillCategory.PROMPT,
            "type": SkillType.USER,
            "version": "1.0.0",
            "author": "admin",
            "is_active": True,
            "is_system": False,
            "trigger_keywords": [],
            "trigger_intents": [],
            "always_apply": False,
            "applicable_agents": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        skill = SkillRead(**data)
        assert skill.id == "test-id"
        assert skill.type == SkillType.USER


class TestSkillListResponse:
    """测试 SkillListResponse Schema"""

    def test_empty_list(self):
        """测试空列表"""
        response = SkillListResponse(items=[], total=0, page=1, page_size=20)
        assert response.total == 0
        assert len(response.items) == 0

    def test_with_items(self):
        """测试有数据"""
        from datetime import datetime

        item = SkillRead(
            id="test-id",
            name="测试技能",
            description="这是测试描述的详细信息和说明",
            content="这是技能内容的详细说明和使用指南",
            category=SkillCategory.PROMPT,
            type=SkillType.USER,
            version="1.0.0",
            author=None,
            is_active=True,
            is_system=False,
            trigger_keywords=[],
            trigger_intents=[],
            always_apply=False,
            applicable_agents=[],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        response = SkillListResponse(items=[item], total=1, page=1, page_size=20)
        assert response.total == 1


class TestSkillGenerateRequest:
    """测试 SkillGenerateRequest Schema"""

    def test_valid_request(self):
        """测试有效请求"""
        request = SkillGenerateRequest(
            description="我需要一个帮助用户对比多个商品的专业技能，能够分析优劣势",
            category=SkillCategory.PROMPT,
            applicable_agents=["product"],
        )
        assert "对比" in request.description

    def test_description_min_length(self):
        """测试描述最小长度"""
        with pytest.raises(ValidationError):
            SkillGenerateRequest(description="太短")

    def test_with_examples(self):
        """测试带示例"""
        request = SkillGenerateRequest(
            description="我需要一个帮助用户对比多个商品的专业技能，能够分析优劣势",
            examples=["用户: 这两个手机哪个好？", "用户: 帮我对比一下价格"],
        )
        assert len(request.examples) == 2


class TestSkillGenerateResponse:
    """测试 SkillGenerateResponse Schema"""

    def test_valid_response(self):
        """测试有效响应"""
        skill = SkillCreate(
            name="商品对比",
            description="帮助用户对比多个商品的专业技能",
            content="对比规则的详细说明和使用指南",
        )
        response = SkillGenerateResponse(
            skill=skill,
            confidence=0.85,
            suggestions=["建议添加更多关键词"],
        )
        assert response.confidence == 0.85

    def test_confidence_range(self):
        """测试置信度范围"""
        skill = SkillCreate(
            name="测试",
            description="测试描述内容的详细信息和说明",
            content="测试内容的详细说明和使用指南",
        )

        with pytest.raises(ValidationError):
            SkillGenerateResponse(skill=skill, confidence=1.5, suggestions=[])

        with pytest.raises(ValidationError):
            SkillGenerateResponse(skill=skill, confidence=-0.1, suggestions=[])


class TestSkillRefineRequest:
    """测试 SkillRefineRequest Schema"""

    def test_valid_request(self):
        """测试有效请求"""
        request = SkillRefineRequest(feedback="请添加更多触发关键词")
        assert "关键词" in request.feedback

    def test_feedback_min_length(self):
        """测试反馈最小长度"""
        with pytest.raises(ValidationError):
            SkillRefineRequest(feedback="短")


class TestAgentSkillConfig:
    """测试 AgentSkillConfig Schema"""

    def test_valid_config(self):
        """测试有效配置"""
        config = AgentSkillConfig(skill_id="skill-123", priority=50, is_enabled=True)
        assert config.skill_id == "skill-123"
        assert config.priority == 50

    def test_default_values(self):
        """测试默认值"""
        config = AgentSkillConfig(skill_id="skill-123")
        assert config.priority == 100
        assert config.is_enabled is True

    def test_priority_range(self):
        """测试优先级范围"""
        with pytest.raises(ValidationError):
            AgentSkillConfig(skill_id="skill-123", priority=0)

        with pytest.raises(ValidationError):
            AgentSkillConfig(skill_id="skill-123", priority=1001)


class TestAgentSkillsUpdate:
    """测试 AgentSkillsUpdate Schema"""

    def test_valid_update(self):
        """测试有效更新"""
        update = AgentSkillsUpdate(
            skills=[
                AgentSkillConfig(skill_id="skill-1", priority=10),
                AgentSkillConfig(skill_id="skill-2", priority=20),
            ]
        )
        assert len(update.skills) == 2

    def test_empty_skills(self):
        """测试空技能列表"""
        update = AgentSkillsUpdate(skills=[])
        assert len(update.skills) == 0


class TestSkillType:
    """测试 SkillType 枚举"""

    def test_all_types(self):
        """测试所有类型"""
        assert SkillType.SYSTEM == "system"
        assert SkillType.USER == "user"
        assert SkillType.AI_GENERATED == "ai"


class TestSkillCategory:
    """测试 SkillCategory 枚举"""

    def test_all_categories(self):
        """测试所有分类"""
        assert SkillCategory.PROMPT == "prompt"
        assert SkillCategory.RETRIEVAL == "retrieval"
        assert SkillCategory.TOOL == "tool"
        assert SkillCategory.WORKFLOW == "workflow"
