"""技能服务测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.skill import Skill, SkillCategory, SkillType
from app.schemas.skill import (
    AgentSkillConfig,
    SkillCreate,
    SkillUpdate,
)
from app.services.skill.service import SkillService


class TestSkillServiceCreate:
    """测试技能创建"""

    @pytest.mark.anyio
    async def test_create_user_skill(self):
        """测试创建用户技能"""
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = SkillService(mock_session)
        data = SkillCreate(
            name="测试技能",
            description="这是一个测试技能的详细描述信息",
            content="这是技能内容的详细说明和使用指南",
            trigger_keywords=["测试", "关键词"],
        )

        skill = await service.create_skill(data)

        assert skill.name == "测试技能"
        assert skill.type == SkillType.USER
        assert skill.is_system is False
        mock_session.add.assert_called_once()

    @pytest.mark.anyio
    async def test_create_system_skill(self):
        """测试创建系统技能"""
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = SkillService(mock_session)
        data = SkillCreate(
            name="系统技能",
            description="这是一个系统技能的详细描述信息",
            content="这是技能内容的详细说明和使用指南",
        )

        skill = await service.create_skill(
            data, skill_type=SkillType.SYSTEM, is_system=True
        )

        assert skill.type == SkillType.SYSTEM
        assert skill.is_system is True

    @pytest.mark.anyio
    async def test_create_skill_with_author(self):
        """测试创建带作者的技能"""
        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = SkillService(mock_session)
        data = SkillCreate(
            name="测试技能",
            description="这是一个测试技能的详细描述信息",
            content="这是技能内容的详细说明和使用指南",
        )

        skill = await service.create_skill(data, author="admin")

        assert skill.author == "admin"


class TestSkillServiceGet:
    """测试技能查询"""

    @pytest.mark.anyio
    async def test_get_skill_exists(self):
        """测试获取存在的技能"""
        mock_skill = Skill(
            id="test-id",
            name="测试技能",
            description="描述",
            content="内容",
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        skill = await service.get_skill("test-id")

        assert skill is not None
        assert skill.id == "test-id"

    @pytest.mark.anyio
    async def test_get_skill_not_exists(self):
        """测试获取不存在的技能"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        skill = await service.get_skill("not-exists")

        assert skill is None

    @pytest.mark.anyio
    async def test_get_skill_by_name(self):
        """测试根据名称获取技能"""
        mock_skill = Skill(
            id="test-id",
            name="测试技能",
            description="描述",
            content="内容",
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        skill = await service.get_skill_by_name("测试技能")

        assert skill is not None
        assert skill.name == "测试技能"


class TestSkillServiceList:
    """测试技能列表"""

    @pytest.mark.anyio
    async def test_list_skills_empty(self):
        """测试空列表"""
        mock_session = MagicMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_list_result]
        )

        service = SkillService(mock_session)
        result = await service.list_skills()

        assert result.total == 0
        assert len(result.items) == 0

    @pytest.mark.anyio
    async def test_list_skills_with_filter(self):
        """测试带筛选条件的列表"""
        mock_session = MagicMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1
        
        mock_skill = MagicMock(spec=Skill)
        mock_skill.id = "test-id"
        mock_skill.name = "测试技能"
        mock_skill.description = "这是测试描述的详细信息和说明"
        mock_skill.content = "这是技能内容的详细说明和使用指南"
        mock_skill.type = SkillType.USER
        mock_skill.category = SkillCategory.PROMPT
        mock_skill.version = "1.0.0"
        mock_skill.author = None
        mock_skill.is_active = True
        mock_skill.is_system = False
        mock_skill.trigger_keywords = []
        mock_skill.trigger_intents = []
        mock_skill.always_apply = False
        mock_skill.applicable_agents = []
        mock_skill.created_at = MagicMock()
        mock_skill.updated_at = MagicMock()

        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [mock_skill]

        mock_session.execute = AsyncMock(
            side_effect=[mock_count_result, mock_list_result]
        )

        service = SkillService(mock_session)
        result = await service.list_skills(skill_type=SkillType.USER, is_active=True)

        assert result.total == 1


class TestSkillServiceUpdate:
    """测试技能更新"""

    @pytest.mark.anyio
    async def test_update_user_skill(self):
        """测试更新用户技能"""
        mock_skill = Skill(
            id="test-id",
            name="旧名称",
            description="旧描述",
            content="旧内容",
            is_system=False,
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()

        service = SkillService(mock_session)
        data = SkillUpdate(name="新名称")
        skill = await service.update_skill("test-id", data)

        assert skill is not None
        assert skill.name == "新名称"

    @pytest.mark.anyio
    async def test_update_system_skill_raises(self):
        """测试更新系统技能抛出异常"""
        mock_skill = Skill(
            id="test-id",
            name="系统技能",
            description="描述",
            content="内容",
            is_system=True,
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        data = SkillUpdate(name="新名称")

        with pytest.raises(ValueError, match="系统内置技能不可修改"):
            await service.update_skill("test-id", data)

    @pytest.mark.anyio
    async def test_update_not_exists(self):
        """测试更新不存在的技能"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        data = SkillUpdate(name="新名称")
        skill = await service.update_skill("not-exists", data)

        assert skill is None


class TestSkillServiceDelete:
    """测试技能删除"""

    @pytest.mark.anyio
    async def test_delete_user_skill(self):
        """测试删除用户技能"""
        mock_skill = Skill(
            id="test-id",
            name="用户技能",
            description="描述",
            content="内容",
            is_system=False,
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        service = SkillService(mock_session)
        success = await service.delete_skill("test-id")

        assert success is True
        mock_session.delete.assert_called_once_with(mock_skill)

    @pytest.mark.anyio
    async def test_delete_system_skill_raises(self):
        """测试删除系统技能抛出异常"""
        mock_skill = Skill(
            id="test-id",
            name="系统技能",
            description="描述",
            content="内容",
            is_system=True,
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)

        with pytest.raises(ValueError, match="系统内置技能不可删除"):
            await service.delete_skill("test-id")

    @pytest.mark.anyio
    async def test_delete_not_exists(self):
        """测试删除不存在的技能"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        success = await service.delete_skill("not-exists")

        assert success is False


class TestSkillServiceApplicable:
    """测试技能匹配"""

    @pytest.mark.anyio
    async def test_get_applicable_skills_always_apply(self):
        """测试获取始终应用的技能"""
        mock_skill = MagicMock(spec=Skill)
        mock_skill.is_active = True
        mock_skill.always_apply = True
        mock_skill.applicable_agents = ["product"]
        mock_skill.trigger_keywords = []

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_skill]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        skills = await service.get_applicable_skills("product")

        assert len(skills) == 1

    @pytest.mark.anyio
    async def test_get_applicable_skills_keyword_match(self):
        """测试关键词匹配"""
        mock_skill = MagicMock(spec=Skill)
        mock_skill.is_active = True
        mock_skill.always_apply = False
        mock_skill.applicable_agents = []
        mock_skill.trigger_keywords = ["对比", "比较"]

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_skill]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        skills = await service.get_applicable_skills(
            "product", "帮我对比这两个商品"
        )

        assert len(skills) == 1

    @pytest.mark.anyio
    async def test_get_applicable_skills_agent_filter(self):
        """测试 Agent 类型过滤"""
        mock_skill = MagicMock(spec=Skill)
        mock_skill.is_active = True
        mock_skill.always_apply = True
        mock_skill.applicable_agents = ["faq"]  # 只适用于 faq
        mock_skill.trigger_keywords = []

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_skill]
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = SkillService(mock_session)
        skills = await service.get_applicable_skills("product")

        assert len(skills) == 0  # product 不匹配


class TestSkillServiceAgentSkills:
    """测试 Agent 技能配置"""

    @pytest.mark.anyio
    async def test_update_agent_skills(self):
        """测试更新 Agent 技能配置"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.delete = AsyncMock()
        mock_session.flush = AsyncMock()

        service = SkillService(mock_session)
        skills = [
            AgentSkillConfig(skill_id="skill-1", priority=10),
            AgentSkillConfig(skill_id="skill-2", priority=20),
        ]
        await service.update_agent_skills("agent-123", skills)

        assert mock_session.add.call_count == 2


class TestSkillServiceSystemSkills:
    """测试系统技能初始化"""

    @pytest.mark.anyio
    async def test_init_system_skills(self):
        """测试初始化系统技能"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # 不存在
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        service = SkillService(mock_session)
        skills_data = [
            {
                "name": "测试系统技能",
                "description": "这是系统技能描述",
                "content": "这是技能内容",
            }
        ]
        count = await service.init_system_skills(skills_data)

        assert count == 1
        mock_session.add.assert_called_once()

    @pytest.mark.anyio
    async def test_init_system_skills_skip_existing(self):
        """测试跳过已存在的系统技能"""
        mock_skill = Skill(
            id="existing",
            name="已存在技能",
            description="描述",
            content="内容",
        )

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_skill
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.flush = AsyncMock()

        service = SkillService(mock_session)
        skills_data = [
            {
                "name": "已存在技能",
                "description": "描述",
                "content": "内容",
            }
        ]
        count = await service.init_system_skills(skills_data)

        assert count == 0
