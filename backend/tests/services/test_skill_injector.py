"""技能注入器测试"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.skill.injector import SkillInjector


class TestSkillInjectorAlwaysApply:
    """测试 always_apply 技能注入"""

    def test_inject_no_skills(self):
        """测试无技能时返回原始提示词"""
        mock_registry = MagicMock()
        mock_registry.get_always_apply_skills.return_value = []

        injector = SkillInjector(mock_registry)
        result = injector.inject_always_apply_skills(
            system_prompt="原始提示词",
            agent_type="product",
            mode="natural",
        )

        assert result == "原始提示词"

    def test_inject_with_skills(self):
        """测试有技能时注入内容"""
        mock_skill = MagicMock()
        mock_skill.name = "测试技能"
        mock_skill.content = "技能内容"

        mock_registry = MagicMock()
        mock_registry.get_always_apply_skills.return_value = [mock_skill]
        mock_registry.build_skill_context.return_value = "## 已加载技能\n\n### 测试技能\n技能内容"

        injector = SkillInjector(mock_registry)
        result = injector.inject_always_apply_skills(
            system_prompt="原始提示词",
            agent_type="product",
            mode="natural",
        )

        assert "原始提示词" in result
        assert "已加载技能" in result
        mock_registry.get_always_apply_skills.assert_called_once_with("product", "natural")


class TestSkillInjectorMatchAndActivate:
    """测试关键词匹配和激活"""

    @pytest.mark.anyio
    async def test_no_match(self):
        """测试无匹配时返回空列表"""
        mock_registry = MagicMock()
        mock_registry.match_skills.return_value = []

        mock_emitter = MagicMock()
        mock_emitter.emit = AsyncMock()

        injector = SkillInjector(mock_registry)
        result = await injector.match_and_activate_skills(
            message="普通消息",
            agent_type="product",
            mode="natural",
            emitter=mock_emitter,
        )

        assert result == []
        mock_emitter.emit.assert_not_called()

    @pytest.mark.anyio
    async def test_match_keyword_triggered(self):
        """测试关键词触发技能"""
        mock_skill = MagicMock()
        mock_skill.id = "skill-123"
        mock_skill.name = "商品对比专家"
        mock_skill.always_apply = False
        mock_skill.trigger_keywords = ["对比", "比较"]

        mock_registry = MagicMock()
        mock_registry.match_skills.return_value = [mock_skill]

        mock_emitter = MagicMock()
        mock_emitter.emit = AsyncMock()

        injector = SkillInjector(mock_registry)
        result = await injector.match_and_activate_skills(
            message="帮我对比一下这两个商品",
            agent_type="product",
            mode="natural",
            emitter=mock_emitter,
        )

        assert len(result) == 1
        assert result[0].name == "商品对比专家"
        mock_emitter.emit.assert_called_once()

        # 验证事件内容
        call_args = mock_emitter.emit.call_args
        assert call_args[0][0] == "skill.activated"
        assert call_args[0][1]["skill_id"] == "skill-123"
        assert call_args[0][1]["skill_name"] == "商品对比专家"
        assert call_args[0][1]["trigger_type"] == "keyword"
        assert call_args[0][1]["trigger_keyword"] == "对比"

    @pytest.mark.anyio
    async def test_filter_always_apply(self):
        """测试过滤掉 always_apply 技能"""
        mock_skill_always = MagicMock()
        mock_skill_always.id = "skill-always"
        mock_skill_always.name = "始终应用技能"
        mock_skill_always.always_apply = True
        mock_skill_always.trigger_keywords = []

        mock_skill_keyword = MagicMock()
        mock_skill_keyword.id = "skill-keyword"
        mock_skill_keyword.name = "关键词技能"
        mock_skill_keyword.always_apply = False
        mock_skill_keyword.trigger_keywords = ["测试"]

        mock_registry = MagicMock()
        mock_registry.match_skills.return_value = [mock_skill_always, mock_skill_keyword]

        mock_emitter = MagicMock()
        mock_emitter.emit = AsyncMock()

        injector = SkillInjector(mock_registry)
        result = await injector.match_and_activate_skills(
            message="这是测试消息",
            agent_type="product",
            mode="natural",
            emitter=mock_emitter,
        )

        # 只返回非 always_apply 的技能
        assert len(result) == 1
        assert result[0].name == "关键词技能"

        # 只发送一个事件（关键词技能）
        assert mock_emitter.emit.call_count == 1


class TestSkillInjectorFindKeyword:
    """测试关键词查找"""

    def test_find_matched_keyword(self):
        """测试找到匹配的关键词"""
        mock_skill = MagicMock()
        mock_skill.trigger_keywords = ["对比", "比较", "VS"]

        mock_registry = MagicMock()
        injector = SkillInjector(mock_registry)

        result = injector._find_matched_keyword("帮我对比一下", mock_skill)
        assert result == "对比"

    def test_find_matched_keyword_case_insensitive(self):
        """测试关键词匹配不区分大小写"""
        mock_skill = MagicMock()
        mock_skill.trigger_keywords = ["VS", "compare"]

        mock_registry = MagicMock()
        injector = SkillInjector(mock_registry)

        result = injector._find_matched_keyword("iPhone vs Samsung", mock_skill)
        assert result == "VS"

    def test_find_no_matched_keyword(self):
        """测试找不到匹配的关键词"""
        mock_skill = MagicMock()
        mock_skill.trigger_keywords = ["对比", "比较"]

        mock_registry = MagicMock()
        injector = SkillInjector(mock_registry)

        result = injector._find_matched_keyword("普通消息", mock_skill)
        assert result is None


class TestSkillInjectorBuildContext:
    """测试构建技能上下文"""

    def test_build_skill_context(self):
        """测试构建技能上下文"""
        mock_skills = [MagicMock(), MagicMock()]
        expected_context = "技能上下文内容"

        mock_registry = MagicMock()
        mock_registry.build_skill_context.return_value = expected_context

        injector = SkillInjector(mock_registry)
        result = injector.build_skill_context_for_message(mock_skills)

        assert result == expected_context
        mock_registry.build_skill_context.assert_called_once_with(mock_skills)
