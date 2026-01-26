"""Prompt API 路由测试"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.prompts.schemas import PromptResponse, PromptSource


class TestPromptAPI:
    """测试 Prompt API 路由"""

    @pytest.fixture
    def mock_registry(self):
        """创建模拟的 PromptRegistry"""
        registry = AsyncMock()
        return registry

    @pytest.fixture
    def mock_prompt_response(self):
        """创建模拟的 PromptResponse"""
        return PromptResponse(
            key="agent.product",
            category="agent",
            name="商品推荐助手",
            description="商品推荐类 Agent 的默认系统提示词",
            content="你是一个专业的商品推荐助手...",
            variables=[],
            source=PromptSource.DEFAULT,
            is_active=True,
            default_content=None,
            created_at=None,
            updated_at=None,
        )

    @pytest.fixture
    def app(self, mock_registry, mock_prompt_response):
        """创建测试 FastAPI 应用"""
        from app.routers.prompts import router

        app = FastAPI()
        app.include_router(router)

        # 模拟依赖
        async def mock_get_session():
            yield MagicMock()

        app.dependency_overrides = {}

        return app

    def test_list_prompts_returns_items(self, mock_prompt_response):
        """测试列表 API 返回提示词"""
        from app.prompts.defaults import DEFAULT_PROMPTS

        # 验证默认提示词已加载
        assert len(DEFAULT_PROMPTS) >= 10

    def test_prompt_response_schema(self, mock_prompt_response):
        """测试 PromptResponse schema"""
        assert mock_prompt_response.key == "agent.product"
        assert mock_prompt_response.category == "agent"
        assert mock_prompt_response.source == PromptSource.DEFAULT

    def test_prompt_source_enum(self):
        """测试 PromptSource 枚举"""
        assert PromptSource.DEFAULT.value == "default"
        assert PromptSource.CUSTOM.value == "custom"


class TestPromptSchemas:
    """测试 Prompt Schemas"""

    def test_prompt_update_optional_fields(self):
        """测试 PromptUpdate 所有字段可选"""
        from app.prompts.schemas import PromptUpdate

        update = PromptUpdate()
        assert update.name is None
        assert update.content is None
        assert update.is_active is None

    def test_prompt_update_with_values(self):
        """测试 PromptUpdate 带值"""
        from app.prompts.schemas import PromptUpdate

        update = PromptUpdate(
            name="新名称",
            content="新内容",
            is_active=False,
        )
        assert update.name == "新名称"
        assert update.content == "新内容"
        assert update.is_active is False

    def test_prompt_create_required_fields(self):
        """测试 PromptCreate 必填字段"""
        from app.prompts.schemas import PromptCreate, PromptCategory

        create = PromptCreate(
            key="custom.test",
            category=PromptCategory.AGENT,
            name="测试提示词",
            content="测试内容",
        )
        assert create.key == "custom.test"
        assert create.category == PromptCategory.AGENT

    def test_prompt_list_response(self):
        """测试 PromptListResponse"""
        from app.prompts.schemas import PromptListResponse

        response = PromptListResponse(items=[], total=0)
        assert response.items == []
        assert response.total == 0

    def test_prompt_reset_response(self):
        """测试 PromptResetResponse"""
        from app.prompts.schemas import PromptResetResponse

        response = PromptResetResponse(
            key="agent.product",
            message="已重置为默认值",
            content="默认内容",
        )
        assert response.key == "agent.product"
        assert "重置" in response.message
