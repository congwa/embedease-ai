"""技能路由测试"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.skill import (
    SkillCategory,
    SkillCreate,
    SkillGenerateResponse,
    SkillListResponse,
    SkillRead,
    SkillType,
)


class TestSkillsRouter:
    """测试技能路由"""

    def test_router_exists(self):
        """测试路由存在"""
        from app.routers.skills import router

        assert router is not None
        assert router.prefix == "/api/v1/admin/skills"

    def test_router_tags(self):
        """测试路由标签"""
        from app.routers.skills import router

        assert "skills" in router.tags

    def test_list_endpoint_exists(self):
        """测试列表端点存在"""
        from app.routers.skills import router

        routes = [route.path for route in router.routes]
        assert any("skills" in r for r in routes)

    def test_create_endpoint_exists(self):
        """测试创建端点存在"""
        from app.routers.skills import router

        routes = [route.path for route in router.routes]
        assert any("skills" in r for r in routes)

    def test_get_endpoint_exists(self):
        """测试获取端点存在"""
        from app.routers.skills import router

        routes = [route.path for route in router.routes]
        assert any("{skill_id}" in r for r in routes)

    def test_generate_endpoint_exists(self):
        """测试生成端点存在"""
        from app.routers.skills import router

        routes = [route.path for route in router.routes]
        assert any("generate" in r for r in routes)

    def test_system_endpoint_exists(self):
        """测试系统技能端点存在"""
        from app.routers.skills import router

        routes = [route.path for route in router.routes]
        assert any("system" in r for r in routes)


class TestListSkillsEndpoint:
    """测试列表技能端点"""

    @pytest.mark.anyio
    async def test_list_skills(self):
        """测试列表技能"""
        from app.routers.skills import list_skills

        mock_db = MagicMock()

        with patch("app.routers.skills.SkillService") as MockService:
            mock_service = MockService.return_value
            mock_service.list_skills = AsyncMock(
                return_value=SkillListResponse(
                    items=[],
                    total=0,
                    page=1,
                    page_size=20,
                )
            )

            result = await list_skills(
                type=None,
                category=None,
                is_active=None,
                page=1,
                page_size=20,
                db=mock_db,
            )

            assert result.total == 0
            mock_service.list_skills.assert_called_once()


class TestCreateSkillEndpoint:
    """测试创建技能端点"""

    @pytest.mark.anyio
    async def test_create_skill(self):
        """测试创建技能"""
        from datetime import datetime

        from app.routers.skills import create_skill

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()

        mock_skill = MagicMock()
        mock_skill.id = "new-skill-id"
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
        mock_skill.applicable_modes = []
        mock_skill.created_at = datetime.now()
        mock_skill.updated_at = datetime.now()

        with patch("app.routers.skills.SkillService") as MockService:
            mock_service = MockService.return_value
            mock_service.create_skill = AsyncMock(return_value=mock_skill)

            with patch("app.routers.skills.skill_registry") as mock_registry:
                mock_registry.reload = AsyncMock()

                data = SkillCreate(
                    name="测试技能",
                    description="这是测试描述的详细信息和说明",
                    content="这是技能内容的详细说明和使用指南",
                )
                result = await create_skill(data=data, db=mock_db)

                assert result.id == "new-skill-id"
                mock_service.create_skill.assert_called_once()
                mock_registry.reload.assert_called_once()


class TestGetSkillEndpoint:
    """测试获取技能端点"""

    @pytest.mark.anyio
    async def test_get_skill_exists(self):
        """测试获取存在的技能"""
        from datetime import datetime

        from app.routers.skills import get_skill

        mock_db = MagicMock()

        mock_skill = MagicMock()
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
        mock_skill.applicable_modes = []
        mock_skill.created_at = datetime.now()
        mock_skill.updated_at = datetime.now()

        with patch("app.routers.skills.SkillService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_skill = AsyncMock(return_value=mock_skill)

            result = await get_skill(skill_id="test-id", db=mock_db)

            assert result.id == "test-id"

    @pytest.mark.anyio
    async def test_get_skill_not_exists(self):
        """测试获取不存在的技能"""
        from fastapi import HTTPException

        from app.routers.skills import get_skill

        mock_db = MagicMock()

        with patch("app.routers.skills.SkillService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_skill = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_skill(skill_id="not-exists", db=mock_db)

            assert exc_info.value.status_code == 404


class TestUpdateSkillEndpoint:
    """测试更新技能端点"""

    @pytest.mark.anyio
    async def test_update_skill_system_raises(self):
        """测试更新系统技能抛出异常"""
        from fastapi import HTTPException

        from app.routers.skills import update_skill
        from app.schemas.skill import SkillUpdate

        mock_db = MagicMock()

        with patch("app.routers.skills.SkillService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_skill = AsyncMock(
                side_effect=ValueError("系统内置技能不可修改")
            )

            with pytest.raises(HTTPException) as exc_info:
                await update_skill(
                    skill_id="system-id",
                    data=SkillUpdate(name="新名称"),
                    db=mock_db,
                )

            assert exc_info.value.status_code == 400


class TestDeleteSkillEndpoint:
    """测试删除技能端点"""

    @pytest.mark.anyio
    async def test_delete_skill_system_raises(self):
        """测试删除系统技能抛出异常"""
        from fastapi import HTTPException

        from app.routers.skills import delete_skill

        mock_db = MagicMock()

        with patch("app.routers.skills.SkillService") as MockService:
            mock_service = MockService.return_value
            mock_service.delete_skill = AsyncMock(
                side_effect=ValueError("系统内置技能不可删除")
            )

            with pytest.raises(HTTPException) as exc_info:
                await delete_skill(skill_id="system-id", db=mock_db)

            assert exc_info.value.status_code == 400


class TestGenerateSkillEndpoint:
    """测试 AI 生成技能端点"""

    @pytest.mark.anyio
    async def test_generate_skill(self):
        """测试 AI 生成技能"""
        from app.routers.skills import generate_skill
        from app.schemas.skill import SkillGenerateRequest

        mock_db = MagicMock()

        mock_response = SkillGenerateResponse(
            skill=SkillCreate(
                name="生成的技能",
                description="这是 AI 生成的技能详细描述信息",
                content="这是技能内容的详细说明和使用指南",
            ),
            confidence=0.85,
            suggestions=["建议1"],
        )

        with patch("app.routers.skills.SkillGenerator") as MockGenerator:
            mock_generator = MockGenerator.return_value
            mock_generator.generate = AsyncMock(return_value=mock_response)

            data = SkillGenerateRequest(
                description="我需要一个帮助用户对比多个商品的专业技能，能够分析商品的优劣势并给出推荐"
            )
            result = await generate_skill(data=data, db=mock_db)

            assert result.confidence == 0.85
            mock_generator.generate.assert_called_once()


class TestSystemSkillsEndpoint:
    """测试系统技能端点"""

    @pytest.mark.anyio
    async def test_init_system_skills(self):
        """测试初始化系统技能"""
        from app.routers.skills import init_system_skills

        mock_db = MagicMock()
        mock_db.commit = AsyncMock()

        with patch("app.routers.skills.SkillService") as MockService:
            mock_service = MockService.return_value
            mock_service.init_system_skills = AsyncMock(return_value=5)

            with patch("app.routers.skills.skill_registry") as mock_registry:
                mock_registry.reload = AsyncMock()

                result = await init_system_skills(db=mock_db)

                assert result["created"] == 5
                mock_service.init_system_skills.assert_called_once()


class TestCacheEndpoints:
    """测试缓存端点"""

    @pytest.mark.anyio
    async def test_reload_cache(self):
        """测试重新加载缓存"""
        from app.routers.skills import reload_skill_cache

        with patch("app.routers.skills.skill_registry") as mock_registry:
            mock_registry.reload = AsyncMock()

            await reload_skill_cache()

            mock_registry.reload.assert_called_once()

    @pytest.mark.anyio
    async def test_clear_cache(self):
        """测试清除缓存"""
        from app.routers.skills import clear_skill_cache

        with patch("app.routers.skills.skill_registry") as mock_registry:
            await clear_skill_cache()

            mock_registry.invalidate.assert_called_once()
