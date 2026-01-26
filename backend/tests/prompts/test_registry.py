"""PromptRegistry 测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.prompts.registry import PromptRegistry, get_default_prompt_content
from app.prompts.schemas import PromptSource, PromptUpdate


class TestPromptRegistry:
    """测试 PromptRegistry 服务"""

    @pytest.fixture
    def mock_session(self):
        """创建模拟的数据库会话"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.delete = AsyncMock()
        return session

    @pytest.fixture
    def registry(self, mock_session):
        """创建 PromptRegistry 实例"""
        return PromptRegistry(mock_session)

    @pytest.mark.anyio
    async def test_get_default_prompt(self, registry, mock_session):
        """测试获取默认提示词（数据库无记录）"""
        # 模拟数据库返回空
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        prompt = await registry.get("agent.product")

        assert prompt is not None
        assert prompt.key == "agent.product"
        assert prompt.source == PromptSource.DEFAULT
        assert prompt.category == "agent"
        assert len(prompt.content) > 0

    @pytest.mark.anyio
    async def test_get_nonexistent_prompt(self, registry, mock_session):
        """测试获取不存在的提示词"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        prompt = await registry.get("nonexistent.key")

        assert prompt is None

    @pytest.mark.anyio
    async def test_get_content_default(self, registry, mock_session):
        """测试获取默认提示词内容"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        content = await registry.get_content("agent.product")

        assert content is not None
        assert len(content) > 0

    @pytest.mark.anyio
    async def test_get_content_with_variables(self, registry, mock_session):
        """测试带变量的提示词内容格式化"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        content = await registry.get_content(
            "skill.generate",
            description="测试",
            category="prompt",
            applicable_agents="all",
            examples="无",
        )

        assert content is not None
        assert "测试" in content

    @pytest.mark.anyio
    async def test_list_all_default_prompts(self, registry, mock_session):
        """测试列出所有默认提示词"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        prompts = await registry.list_all()

        assert len(prompts) >= 10
        assert all(p.source == PromptSource.DEFAULT for p in prompts)

    @pytest.mark.anyio
    async def test_list_all_filter_category(self, registry, mock_session):
        """测试按分类过滤提示词"""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        prompts = await registry.list_all(category="agent")

        assert len(prompts) >= 5
        assert all(p.category == "agent" for p in prompts)

    @pytest.mark.anyio
    async def test_update_creates_new_record(self, registry, mock_session):
        """测试更新时创建新记录（数据库无记录）"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        update_data = PromptUpdate(content="新内容")
        prompt = await registry.update("agent.product", update_data)

        assert prompt is not None
        assert prompt.source == PromptSource.CUSTOM
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.anyio
    async def test_update_nonexistent_raises(self, registry, mock_session):
        """测试更新不存在的提示词抛出异常"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        update_data = PromptUpdate(content="新内容")

        with pytest.raises(ValueError, match="不存在"):
            await registry.update("nonexistent.key", update_data)

    @pytest.mark.anyio
    async def test_reset_deletes_record(self, registry, mock_session):
        """测试重置删除数据库记录"""
        from app.models.prompt import Prompt, PromptCategory
        from datetime import datetime

        # 创建模拟的数据库记录
        mock_prompt = MagicMock(spec=Prompt)
        mock_prompt.key = "agent.product"
        mock_prompt.category = PromptCategory.AGENT
        mock_prompt.name = "商品推荐助手"
        mock_prompt.content = "自定义内容"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prompt
        mock_session.execute.return_value = mock_result

        prompt = await registry.reset("agent.product")

        assert prompt is not None
        assert prompt.source == PromptSource.DEFAULT
        mock_session.delete.assert_called_once_with(mock_prompt)

    @pytest.mark.anyio
    async def test_reset_nonexistent_raises(self, registry, mock_session):
        """测试重置不存在的提示词抛出异常"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="无默认值"):
            await registry.reset("nonexistent.key")

    @pytest.mark.anyio
    async def test_delete_custom_prompt(self, registry, mock_session):
        """测试删除自定义提示词"""
        from app.models.prompt import Prompt

        mock_prompt = MagicMock(spec=Prompt)
        mock_prompt.key = "custom.new"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_prompt
        mock_session.execute.return_value = mock_result

        # 临时添加一个不存在于默认值中的 key
        with patch.dict("app.prompts.registry.DEFAULT_PROMPTS", {}, clear=False):
            deleted = await registry.delete("custom.new")

        assert deleted is True
        mock_session.delete.assert_called_once()

    @pytest.mark.anyio
    async def test_delete_default_prompt_raises(self, registry, mock_session):
        """测试删除有默认值的提示词抛出异常"""
        with pytest.raises(ValueError, match="有默认值"):
            await registry.delete("agent.product")


class TestGetDefaultPromptContent:
    """测试便捷函数"""

    def test_get_existing_prompt(self):
        """测试获取存在的提示词"""
        content = get_default_prompt_content("agent.product")
        assert content is not None
        assert len(content) > 0

    def test_get_nonexistent_prompt(self):
        """测试获取不存在的提示词"""
        content = get_default_prompt_content("nonexistent.key")
        assert content is None

    def test_format_with_variables(self):
        """测试变量格式化"""
        content = get_default_prompt_content(
            "skill.generate",
            description="测试描述",
            category="prompt",
            applicable_agents="all",
            examples="无",
        )
        assert "测试描述" in content
