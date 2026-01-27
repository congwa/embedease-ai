"""Supervisor 全局配置服务测试"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

pytestmark = pytest.mark.anyio

from app.schemas.system_config import (
    SupervisorGlobalConfig,
    SupervisorGlobalConfigResponse,
    SupervisorGlobalConfigUpdate,
    SupervisorSubAgent,
    SupervisorRoutingPolicy,
)
from app.services.system_config import (
    SupervisorGlobalConfigService,
    get_effective_supervisor_config,
    CONFIG_KEYS,
)


class TestSupervisorGlobalConfig:
    """SupervisorGlobalConfig Schema 测试"""

    def test_default_values(self):
        """测试默认值"""
        config = SupervisorGlobalConfig()
        assert config.enabled is False
        assert config.supervisor_prompt is None
        assert config.sub_agents == []
        assert config.routing_policy.type == "hybrid"
        assert config.intent_timeout == 3.0
        assert config.allow_multi_agent is False

    def test_custom_values(self):
        """测试自定义值"""
        sub_agent = SupervisorSubAgent(
            agent_id="agent-123",
            name="测试助手",
            description="测试描述",
            routing_hints=["测试", "关键词"],
            priority=100,
        )
        config = SupervisorGlobalConfig(
            enabled=True,
            supervisor_prompt="自定义提示词",
            sub_agents=[sub_agent],
            intent_timeout=5.0,
            allow_multi_agent=True,
        )
        assert config.enabled is True
        assert config.supervisor_prompt == "自定义提示词"
        assert len(config.sub_agents) == 1
        assert config.sub_agents[0].agent_id == "agent-123"
        assert config.intent_timeout == 5.0
        assert config.allow_multi_agent is True

    def test_intent_timeout_validation(self):
        """测试意图超时验证"""
        # 最小值
        config = SupervisorGlobalConfig(intent_timeout=0.5)
        assert config.intent_timeout == 0.5

        # 最大值
        config = SupervisorGlobalConfig(intent_timeout=30.0)
        assert config.intent_timeout == 30.0

        # 超出范围应抛出错误
        with pytest.raises(ValueError):
            SupervisorGlobalConfig(intent_timeout=0.1)

        with pytest.raises(ValueError):
            SupervisorGlobalConfig(intent_timeout=31.0)

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        sub_agent = SupervisorSubAgent(
            agent_id="agent-123",
            name="测试助手",
        )
        config = SupervisorGlobalConfig(
            enabled=True,
            supervisor_prompt="测试提示词",
            sub_agents=[sub_agent],
            intent_timeout=5.0,
            allow_multi_agent=True,
        )
        json_str = config.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["enabled"] is True
        assert parsed["supervisor_prompt"] == "测试提示词"
        assert len(parsed["sub_agents"]) == 1
        assert parsed["intent_timeout"] == 5.0
        assert parsed["allow_multi_agent"] is True

    def test_json_deserialization(self):
        """测试 JSON 反序列化"""
        json_str = '{"enabled": true, "supervisor_prompt": null, "sub_agents": [], "routing_policy": {"type": "hybrid", "rules": [], "default_agent_id": null}, "intent_timeout": 2.5, "allow_multi_agent": false}'
        config = SupervisorGlobalConfig(**json.loads(json_str))

        assert config.enabled is True
        assert config.supervisor_prompt is None
        assert config.sub_agents == []
        assert config.intent_timeout == 2.5
        assert config.allow_multi_agent is False


class TestSupervisorGlobalConfigUpdate:
    """SupervisorGlobalConfigUpdate Schema 测试"""

    def test_partial_update(self):
        """测试部分更新"""
        update = SupervisorGlobalConfigUpdate(enabled=True)
        assert update.enabled is True
        assert update.supervisor_prompt is None
        assert update.sub_agents is None
        assert update.intent_timeout is None
        assert update.allow_multi_agent is None

    def test_full_update(self):
        """测试完整更新"""
        sub_agent = SupervisorSubAgent(agent_id="agent-789", name="测试")
        update = SupervisorGlobalConfigUpdate(
            enabled=True,
            supervisor_prompt="测试提示词",
            sub_agents=[sub_agent],
            intent_timeout=4.0,
            allow_multi_agent=True,
        )
        assert update.enabled is True
        assert update.supervisor_prompt == "测试提示词"
        assert len(update.sub_agents) == 1
        assert update.intent_timeout == 4.0
        assert update.allow_multi_agent is True


class TestSupervisorGlobalConfigService:
    """SupervisorGlobalConfigService 测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库会话"""
        db = AsyncMock()
        return db

    async def test_get_config_from_env(self, mock_db):
        """测试从环境变量获取配置（无数据库配置时）"""
        service = SupervisorGlobalConfigService(mock_db)
        service._get_value = AsyncMock(return_value=None)

        config = await service.get_config()

        assert config.source == "env"

    async def test_get_config_from_database(self, mock_db):
        """测试从数据库获取配置"""
        db_config = SupervisorGlobalConfig(
            enabled=True,
            supervisor_prompt="数据库提示词",
            intent_timeout=2.0,
            allow_multi_agent=False,
        )

        service = SupervisorGlobalConfigService(mock_db)
        service._get_value = AsyncMock(return_value=db_config.model_dump_json())

        config = await service.get_config()

        assert config.enabled is True
        assert config.supervisor_prompt == "数据库提示词"
        assert config.intent_timeout == 2.0
        assert config.allow_multi_agent is False
        assert config.source == "database"

    async def test_update_config(self, mock_db):
        """测试更新配置"""
        initial_config = SupervisorGlobalConfig(
            enabled=False,
            intent_timeout=3.0,
            allow_multi_agent=False,
        )

        service = SupervisorGlobalConfigService(mock_db)
        
        get_value_results = [initial_config.model_dump_json()]
        async def mock_get_value(key):
            if get_value_results:
                return get_value_results.pop(0)
            return '{"enabled": true, "supervisor_prompt": null, "sub_agents": [], "routing_policy": {"type": "hybrid", "rules": [], "default_agent_id": null}, "intent_timeout": 3.0, "allow_multi_agent": false}'
        
        service._get_value = mock_get_value
        service._set_value = AsyncMock()
        mock_db.commit = AsyncMock()

        update = SupervisorGlobalConfigUpdate(enabled=True)

        with patch("app.services.system_config.clear_config_cache"):
            result = await service.update_config(update)

        service._set_value.assert_called_once()
        call_args = service._set_value.call_args[0]
        assert call_args[0] == CONFIG_KEYS["supervisor"]

        saved_config = json.loads(call_args[1])
        assert saved_config["enabled"] is True


class TestGetEffectiveSupervisorConfig:
    """get_effective_supervisor_config 函数测试"""

    async def test_get_from_database(self):
        """测试从数据库获取生效配置"""
        db_config = SupervisorGlobalConfig(
            enabled=True,
            supervisor_prompt="生效配置提示词",
            intent_timeout=4.0,
            allow_multi_agent=True,
        )

        mock_db = AsyncMock()
        mock_row = MagicMock()
        mock_row.value = db_config.model_dump_json()
        mock_db.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_row)

        config = await get_effective_supervisor_config(mock_db)

        assert config.enabled is True
        assert config.supervisor_prompt == "生效配置提示词"
        assert config.intent_timeout == 4.0
        assert config.allow_multi_agent is True

    async def test_fallback_to_env(self):
        """测试回退到环境变量"""
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

        # 无数据库配置时回退到环境变量
        config = await get_effective_supervisor_config(mock_db)

        # 验证返回了配置（具体值取决于环境变量）
        assert isinstance(config.enabled, bool)
        assert isinstance(config.intent_timeout, float)
