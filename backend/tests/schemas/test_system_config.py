"""系统配置 Schema 测试

测试配置 Schema 的验证逻辑。
"""

import pytest
from pydantic import ValidationError

from app.schemas.system_config import (
    ConfigTestRequest,
    EmbeddingConfigBase,
    FullConfigUpdate,
    LLMConfigBase,
    ProviderPreset,
    PROVIDER_PRESETS,
    QuickConfigUpdate,
    RerankConfigBase,
    SystemConfigRead,
    SystemConfigReadMasked,
)


class TestLLMConfigBase:
    """测试 LLMConfigBase Schema"""

    def test_default_values(self):
        """测试默认值"""
        config = LLMConfigBase()
        assert config.provider == "siliconflow"
        assert config.api_key == ""
        assert config.base_url == "https://api.siliconflow.cn/v1"
        assert config.chat_model == "moonshotai/Kimi-K2-Thinking"

    def test_custom_values(self):
        """测试自定义值"""
        config = LLMConfigBase(
            provider="openai",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            chat_model="gpt-4o",
        )
        assert config.provider == "openai"
        assert config.api_key == "sk-test"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.chat_model == "gpt-4o"


class TestEmbeddingConfigBase:
    """测试 EmbeddingConfigBase Schema"""

    def test_default_values(self):
        """测试默认值"""
        config = EmbeddingConfigBase()
        assert config.provider == "siliconflow"
        assert config.api_key is None
        assert config.base_url is None
        assert config.model == "Qwen/Qwen3-Embedding-4B"
        assert config.dimension == 2560

    def test_custom_values(self):
        """测试自定义值"""
        config = EmbeddingConfigBase(
            provider="openai",
            api_key="sk-embed",
            base_url="https://api.openai.com/v1",
            model="text-embedding-3-large",
            dimension=3072,
        )
        assert config.provider == "openai"
        assert config.api_key == "sk-embed"
        assert config.dimension == 3072


class TestRerankConfigBase:
    """测试 RerankConfigBase Schema"""

    def test_default_values(self):
        """测试默认值"""
        config = RerankConfigBase()
        assert config.enabled is False
        assert config.provider is None
        assert config.api_key is None
        assert config.model is None
        assert config.top_n == 5

    def test_enabled_with_model(self):
        """测试启用 Rerank"""
        config = RerankConfigBase(
            enabled=True,
            provider="siliconflow",
            model="Qwen/Qwen3-Reranker-8B",
            top_n=10,
        )
        assert config.enabled is True
        assert config.model == "Qwen/Qwen3-Reranker-8B"
        assert config.top_n == 10


class TestQuickConfigUpdate:
    """测试 QuickConfigUpdate Schema"""

    def test_required_api_key(self):
        """测试 API Key 必填"""
        with pytest.raises(ValidationError):
            QuickConfigUpdate()

    def test_api_key_min_length(self):
        """测试 API Key 最小长度"""
        with pytest.raises(ValidationError):
            QuickConfigUpdate(api_key="")

    def test_valid_quick_config(self):
        """测试有效的快速配置"""
        config = QuickConfigUpdate(api_key="sk-test-key")
        assert config.api_key == "sk-test-key"
        assert config.provider == "siliconflow"  # 默认值
        assert config.base_url is None

    def test_custom_provider(self):
        """测试自定义提供商"""
        config = QuickConfigUpdate(
            api_key="sk-openai",
            provider="openai",
            base_url="https://api.openai.com/v1",
        )
        assert config.provider == "openai"
        assert config.base_url == "https://api.openai.com/v1"


class TestFullConfigUpdate:
    """测试 FullConfigUpdate Schema"""

    def test_required_fields(self):
        """测试必填字段"""
        with pytest.raises(ValidationError):
            FullConfigUpdate()

    def test_api_key_min_length(self):
        """测试 API Key 最小长度"""
        with pytest.raises(ValidationError):
            FullConfigUpdate(
                llm_provider="siliconflow",
                llm_api_key="",
                llm_base_url="https://api.siliconflow.cn/v1",
                llm_chat_model="test",
                embedding_provider="siliconflow",
                embedding_model="test",
                embedding_dimension=4096,
            )

    def test_embedding_dimension_positive(self):
        """测试 Embedding 维度必须为正数"""
        with pytest.raises(ValidationError):
            FullConfigUpdate(
                llm_provider="siliconflow",
                llm_api_key="sk-test",
                llm_base_url="https://api.siliconflow.cn/v1",
                llm_chat_model="test",
                embedding_provider="siliconflow",
                embedding_model="test",
                embedding_dimension=0,
            )

    def test_valid_full_config(self):
        """测试有效的完整配置"""
        config = FullConfigUpdate(
            llm_provider="openai",
            llm_api_key="sk-test",
            llm_base_url="https://api.openai.com/v1",
            llm_chat_model="gpt-4o",
            embedding_provider="openai",
            embedding_model="text-embedding-3-large",
            embedding_dimension=3072,
        )
        assert config.llm_provider == "openai"
        assert config.llm_api_key == "sk-test"
        assert config.embedding_dimension == 3072

    def test_rerank_optional_fields(self):
        """测试 Rerank 可选字段"""
        config = FullConfigUpdate(
            llm_provider="siliconflow",
            llm_api_key="sk-test",
            llm_base_url="https://api.siliconflow.cn/v1",
            llm_chat_model="test",
            embedding_provider="siliconflow",
            embedding_model="test",
            embedding_dimension=4096,
            rerank_enabled=True,
            rerank_model="rerank-model",
            rerank_top_n=10,
        )
        assert config.rerank_enabled is True
        assert config.rerank_model == "rerank-model"
        assert config.rerank_top_n == 10


class TestConfigTestRequest:
    """测试 ConfigTestRequest Schema"""

    def test_required_fields(self):
        """测试必填字段"""
        with pytest.raises(ValidationError):
            ConfigTestRequest()

    def test_api_key_min_length(self):
        """测试 API Key 最小长度"""
        with pytest.raises(ValidationError):
            ConfigTestRequest(
                provider="test",
                api_key="",
                base_url="https://example.com",
            )

    def test_valid_test_request(self):
        """测试有效的测试请求"""
        request = ConfigTestRequest(
            provider="siliconflow",
            api_key="sk-test",
            base_url="https://api.siliconflow.cn/v1",
        )
        assert request.provider == "siliconflow"
        assert request.api_key == "sk-test"
        assert request.model is None

    def test_with_model(self):
        """测试带模型的请求"""
        request = ConfigTestRequest(
            provider="openai",
            api_key="sk-test",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
        )
        assert request.model == "gpt-4o"


class TestSystemConfigRead:
    """测试 SystemConfigRead Schema"""

    def test_default_values(self):
        """测试默认值"""
        config = SystemConfigRead()
        assert config.initialized is False
        assert config.source == "env"
        assert isinstance(config.llm, LLMConfigBase)
        assert isinstance(config.embedding, EmbeddingConfigBase)
        assert isinstance(config.rerank, RerankConfigBase)

    def test_initialized_config(self):
        """测试已初始化的配置"""
        config = SystemConfigRead(
            initialized=True,
            llm=LLMConfigBase(provider="openai", api_key="sk-test"),
            source="database",
        )
        assert config.initialized is True
        assert config.source == "database"
        assert config.llm.provider == "openai"


class TestSystemConfigReadMasked:
    """测试 SystemConfigReadMasked Schema"""

    def test_all_fields_required(self):
        """测试所有字段"""
        masked = SystemConfigReadMasked(
            initialized=True,
            llm_provider="siliconflow",
            llm_api_key_masked="sk-1...cdef",
            llm_base_url="https://api.siliconflow.cn/v1",
            llm_chat_model="test-model",
            embedding_provider="siliconflow",
            embedding_api_key_masked=None,
            embedding_base_url=None,
            embedding_model="test-embed",
            embedding_dimension=4096,
            rerank_enabled=False,
            rerank_provider=None,
            rerank_api_key_masked=None,
            rerank_base_url=None,
            rerank_model=None,
            rerank_top_n=5,
            source="database",
        )
        assert masked.llm_api_key_masked == "sk-1...cdef"
        assert masked.source == "database"


class TestProviderPresets:
    """测试提供商预设常量"""

    def test_all_presets_have_required_fields(self):
        """测试所有预设都有必填字段"""
        required_fields = ["name", "base_url", "default_model", "default_embedding_model", "default_embedding_dimension"]
        
        for provider_id, preset in PROVIDER_PRESETS.items():
            for field in required_fields:
                assert field in preset, f"Provider {provider_id} missing field: {field}"

    def test_siliconflow_preset(self):
        """测试 SiliconFlow 预设"""
        preset = PROVIDER_PRESETS["siliconflow"]
        assert preset["name"] == "SiliconFlow"
        assert "siliconflow" in preset["base_url"]

    def test_openai_preset(self):
        """测试 OpenAI 预设"""
        preset = PROVIDER_PRESETS["openai"]
        assert preset["name"] == "OpenAI"
        assert "openai" in preset["base_url"]
        assert preset["default_model"] == "gpt-4o"

    def test_deepseek_preset(self):
        """测试 DeepSeek 预设"""
        preset = PROVIDER_PRESETS["deepseek"]
        assert preset["name"] == "DeepSeek"
        assert "deepseek" in preset["base_url"]

    def test_anthropic_preset(self):
        """测试 Anthropic 预设"""
        preset = PROVIDER_PRESETS["anthropic"]
        assert preset["name"] == "Anthropic"
        assert "anthropic" in preset["base_url"]

    def test_openrouter_preset(self):
        """测试 OpenRouter 预设"""
        preset = PROVIDER_PRESETS["openrouter"]
        assert preset["name"] == "OpenRouter"
        assert "openrouter" in preset["base_url"]


class TestProviderPresetModel:
    """测试 ProviderPreset Pydantic 模型"""

    def test_create_preset(self):
        """测试创建预设模型"""
        preset = ProviderPreset(
            id="custom",
            name="Custom Provider",
            base_url="https://api.custom.com/v1",
            default_model="custom-model",
            default_embedding_model="custom-embed",
            default_embedding_dimension=1536,
        )
        assert preset.id == "custom"
        assert preset.name == "Custom Provider"
        assert preset.default_embedding_dimension == 1536
