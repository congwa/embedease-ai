"""配置模块测试

测试应用配置的加载和验证。
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.config import settings


class TestSettingsBasic:
    """测试基本配置"""

    def test_settings_exists(self):
        """测试 settings 对象存在"""
        assert settings is not None

    def test_has_llm_provider(self):
        """测试有 LLM 提供商配置"""
        assert hasattr(settings, 'LLM_PROVIDER')

    def test_has_api_port(self):
        """测试有 API 端口配置"""
        assert hasattr(settings, 'API_PORT')


class TestDatabaseConfig:
    """测试数据库配置"""

    def test_has_database_url(self):
        """测试有数据库 URL"""
        assert hasattr(settings, 'DATABASE_URL') or hasattr(settings, 'database_url')


class TestLLMConfig:
    """测试 LLM 配置"""

    def test_has_llm_provider(self):
        """测试有 LLM 提供商配置"""
        assert hasattr(settings, 'LLM_PROVIDER') or hasattr(settings, 'llm_provider')


class TestSettingsValidation:
    """测试配置验证"""

    def test_settings_is_pydantic_model(self):
        """测试 settings 是 Pydantic 模型"""
        # Pydantic 模型有 model_fields 或 __fields__ 属性
        assert hasattr(settings, 'model_fields') or hasattr(settings, '__fields__')

    def test_settings_can_export_dict(self):
        """测试可以导出为字典"""
        # Pydantic v2 使用 model_dump，v1 使用 dict
        if hasattr(settings, 'model_dump'):
            result = settings.model_dump()
        else:
            result = settings.dict()
        assert isinstance(result, dict)
