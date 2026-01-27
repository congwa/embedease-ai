"""系统配置服务

负责管理存储在数据库中的系统配置（LLM、Embedding、Rerank 等）。
配置优先级：数据库 > 环境变量
"""

import asyncio
import json
from functools import lru_cache
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.app_metadata import AppMetadata
from app.schemas.system_config import (
    AvailableAgentForSupervisor,
    ConfigTestRequest,
    ConfigTestResponse,
    EmbeddingConfigBase,
    FullConfigUpdate,
    LLMConfigBase,
    ProviderPreset,
    ProviderPresetsResponse,
    PROVIDER_PRESETS,
    QuickConfigUpdate,
    RerankConfigBase,
    SupervisorGlobalConfig,
    SupervisorGlobalConfigResponse,
    SupervisorGlobalConfigUpdate,
    SupervisorRoutingPolicy,
    SupervisorSubAgent,
    SystemConfigRead,
    SystemConfigReadMasked,
)

logger = get_logger("services.system_config")

# 配置 Key 前缀
CONFIG_KEY_PREFIX = "system_config."

# 配置项 Key
CONFIG_KEYS = {
    "llm": f"{CONFIG_KEY_PREFIX}llm",
    "embedding": f"{CONFIG_KEY_PREFIX}embedding",
    "rerank": f"{CONFIG_KEY_PREFIX}rerank",
    "initialized": f"{CONFIG_KEY_PREFIX}initialized",
    "supervisor": f"{CONFIG_KEY_PREFIX}supervisor",
}


class SystemConfigService:
    """系统配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self) -> SystemConfigRead:
        """获取系统配置（优先从数据库读取）"""
        # 检查是否已初始化
        initialized = await self._get_value(CONFIG_KEYS["initialized"])

        if initialized != "true":
            # 未初始化，返回环境变量配置
            return self._get_env_config()

        # 从数据库读取配置
        llm_json = await self._get_value(CONFIG_KEYS["llm"])
        embedding_json = await self._get_value(CONFIG_KEYS["embedding"])
        rerank_json = await self._get_value(CONFIG_KEYS["rerank"])

        llm = LLMConfigBase(**json.loads(llm_json)) if llm_json else LLMConfigBase()
        embedding = (
            EmbeddingConfigBase(**json.loads(embedding_json))
            if embedding_json
            else EmbeddingConfigBase()
        )
        rerank = (
            RerankConfigBase(**json.loads(rerank_json))
            if rerank_json
            else RerankConfigBase()
        )

        return SystemConfigRead(
            initialized=True,
            llm=llm,
            embedding=embedding,
            rerank=rerank,
            source="database",
        )

    async def get_config_masked(self) -> SystemConfigReadMasked:
        """获取系统配置（API Key 脱敏）"""
        config = await self.get_config()

        def mask_key(key: str | None) -> str | None:
            if not key:
                return None
            if len(key) < 8:
                return "***"
            return f"{key[:4]}...{key[-4:]}"

        return SystemConfigReadMasked(
            initialized=config.initialized,
            llm_provider=config.llm.provider,
            llm_api_key_masked=mask_key(config.llm.api_key) or "未配置",
            llm_base_url=config.llm.base_url,
            llm_chat_model=config.llm.chat_model,
            embedding_provider=config.embedding.provider,
            embedding_api_key_masked=mask_key(config.embedding.api_key),
            embedding_base_url=config.embedding.base_url,
            embedding_model=config.embedding.model,
            embedding_dimension=config.embedding.dimension,
            rerank_enabled=config.rerank.enabled,
            rerank_provider=config.rerank.provider,
            rerank_api_key_masked=mask_key(config.rerank.api_key),
            rerank_base_url=config.rerank.base_url,
            rerank_model=config.rerank.model,
            rerank_top_n=config.rerank.top_n,
            source=config.source,
        )

    async def update_quick_config(self, data: QuickConfigUpdate) -> SystemConfigReadMasked:
        """快速配置更新（只设置 API Key）"""
        # 获取提供商预设
        preset = PROVIDER_PRESETS.get(data.provider, PROVIDER_PRESETS["siliconflow"])
        base_url = data.base_url or preset["base_url"]

        # 构建完整配置
        llm = LLMConfigBase(
            provider=data.provider,
            api_key=data.api_key,
            base_url=base_url,
            chat_model=preset["default_model"],
        )

        embedding = EmbeddingConfigBase(
            provider=data.provider,
            api_key=None,  # 使用 LLM 的 API Key
            base_url=None,  # 使用 LLM 的 Base URL
            model=preset["default_embedding_model"],
            dimension=int(preset["default_embedding_dimension"] or 4096),
        )

        rerank = RerankConfigBase(enabled=False)

        # 保存到数据库
        await self._set_value(CONFIG_KEYS["llm"], llm.model_dump_json())
        await self._set_value(CONFIG_KEYS["embedding"], embedding.model_dump_json())
        await self._set_value(CONFIG_KEYS["rerank"], rerank.model_dump_json())
        await self._set_value(CONFIG_KEYS["initialized"], "true")
        await self.db.commit()

        logger.info(
            "快速配置已保存",
            provider=data.provider,
            base_url=base_url,
        )

        # 清除配置缓存
        clear_config_cache()

        return await self.get_config_masked()

    async def update_full_config(self, data: FullConfigUpdate) -> SystemConfigReadMasked:
        """完整配置更新"""
        llm = LLMConfigBase(
            provider=data.llm_provider,
            api_key=data.llm_api_key,
            base_url=data.llm_base_url,
            chat_model=data.llm_chat_model,
        )

        embedding = EmbeddingConfigBase(
            provider=data.embedding_provider,
            api_key=data.embedding_api_key,
            base_url=data.embedding_base_url,
            model=data.embedding_model,
            dimension=data.embedding_dimension,
        )

        rerank = RerankConfigBase(
            enabled=data.rerank_enabled,
            provider=data.rerank_provider,
            api_key=data.rerank_api_key,
            base_url=data.rerank_base_url,
            model=data.rerank_model,
            top_n=data.rerank_top_n,
        )

        # 保存到数据库
        await self._set_value(CONFIG_KEYS["llm"], llm.model_dump_json())
        await self._set_value(CONFIG_KEYS["embedding"], embedding.model_dump_json())
        await self._set_value(CONFIG_KEYS["rerank"], rerank.model_dump_json())
        await self._set_value(CONFIG_KEYS["initialized"], "true")
        await self.db.commit()

        logger.info(
            "完整配置已保存",
            llm_provider=data.llm_provider,
            embedding_provider=data.embedding_provider,
            rerank_enabled=data.rerank_enabled,
        )

        # 清除配置缓存
        clear_config_cache()

        return await self.get_config_masked()

    async def test_config(self, data: ConfigTestRequest) -> ConfigTestResponse:
        """测试配置是否可用"""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = f"{data.base_url.rstrip('/')}/models"
                headers = {"Authorization": f"Bearer {data.api_key}"}

                start = asyncio.get_event_loop().time()
                response = await client.get(url, headers=headers)
                latency = (asyncio.get_event_loop().time() - start) * 1000

                if response.status_code == 200:
                    # 尝试解析模型列表
                    models: list[str] = []
                    try:
                        result = response.json()
                        if "data" in result:
                            models = [m.get("id", "") for m in result["data"][:20]]
                    except Exception:
                        pass

                    return ConfigTestResponse(
                        success=True,
                        message=f"{data.provider} API 连接成功",
                        latency_ms=round(latency, 2),
                        models=models if models else None,
                    )
                elif response.status_code in (401, 403):
                    return ConfigTestResponse(
                        success=False,
                        message="API Key 无效或权限不足",
                        latency_ms=round(latency, 2),
                    )
                else:
                    return ConfigTestResponse(
                        success=False,
                        message=f"API 返回错误状态码: {response.status_code}",
                        latency_ms=round(latency, 2),
                    )
        except httpx.ConnectError:
            return ConfigTestResponse(
                success=False,
                message=f"无法连接到 {data.base_url}，请检查网络或 URL",
            )
        except httpx.TimeoutException:
            return ConfigTestResponse(
                success=False,
                message="连接超时，请检查网络",
            )
        except Exception as e:
            return ConfigTestResponse(
                success=False,
                message=f"测试失败: {str(e)}",
            )

    def get_provider_presets(self) -> ProviderPresetsResponse:
        """获取提供商预设列表"""
        items = [
            ProviderPreset(
                id=key,
                name=preset["name"],
                base_url=preset["base_url"],
                default_model=preset["default_model"],
                default_embedding_model=preset["default_embedding_model"],
                default_embedding_dimension=int(preset["default_embedding_dimension"] or 0),
            )
            for key, preset in PROVIDER_PRESETS.items()
        ]
        return ProviderPresetsResponse(items=items)

    async def is_configured(self) -> bool:
        """检查是否已配置（数据库或环境变量）"""
        # 检查数据库
        initialized = await self._get_value(CONFIG_KEYS["initialized"])
        if initialized == "true":
            return True

        # 检查环境变量
        from app.core.config import settings

        return bool(getattr(settings, "LLM_API_KEY", None))

    def _get_env_config(self) -> SystemConfigRead:
        """从环境变量获取配置"""
        from app.core.config import settings

        llm = LLMConfigBase(
            provider=getattr(settings, "LLM_PROVIDER", "siliconflow"),
            api_key=getattr(settings, "LLM_API_KEY", "") or "",
            base_url=getattr(settings, "LLM_BASE_URL", "https://api.siliconflow.cn/v1"),
            chat_model=getattr(settings, "LLM_CHAT_MODEL", "moonshotai/Kimi-K2-Thinking"),
        )

        embedding = EmbeddingConfigBase(
            provider=getattr(settings, "EMBEDDING_PROVIDER", "siliconflow"),
            api_key=getattr(settings, "EMBEDDING_API_KEY", None),
            base_url=getattr(settings, "EMBEDDING_BASE_URL", None),
            model=getattr(settings, "EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B"),
            dimension=getattr(settings, "EMBEDDING_DIMENSION", 4096),
        )

        rerank = RerankConfigBase(
            enabled=getattr(settings, "RERANK_ENABLED", False),
            provider=getattr(settings, "RERANK_PROVIDER", None),
            api_key=getattr(settings, "RERANK_API_KEY", None),
            base_url=getattr(settings, "RERANK_BASE_URL", None),
            model=getattr(settings, "RERANK_MODEL", None),
            top_n=getattr(settings, "RERANK_TOP_N", 5),
        )

        return SystemConfigRead(
            initialized=bool(llm.api_key),
            llm=llm,
            embedding=embedding,
            rerank=rerank,
            source="env",
        )

    async def _get_value(self, key: str) -> str | None:
        """从数据库获取配置值"""
        stmt = select(AppMetadata).where(AppMetadata.key == key)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        return row.value if row else None

    async def _set_value(self, key: str, value: str) -> None:
        """设置配置值到数据库"""
        stmt = select(AppMetadata).where(AppMetadata.key == key)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row:
            row.value = value
        else:
            self.db.add(AppMetadata(key=key, value=value))


# 配置缓存（用于运行时读取）
_config_cache: dict[str, Any] = {}


def clear_config_cache() -> None:
    """清除配置缓存（配置更新后调用）"""
    global _config_cache
    _config_cache.clear()

    # 同时清除 LLM 模块的缓存
    try:
        from app.core.llm import get_chat_model, get_embeddings, get_memory_model

        get_chat_model.cache_clear()
        get_embeddings.cache_clear()
        get_memory_model.cache_clear()
    except Exception:
        pass

    logger.info("配置缓存已清除")


async def get_effective_llm_config(db: AsyncSession) -> LLMConfigBase:
    """获取生效的 LLM 配置（优先数据库，其次环境变量）"""
    service = SystemConfigService(db)
    config = await service.get_config()
    return config.llm


async def get_effective_embedding_config(db: AsyncSession) -> EmbeddingConfigBase:
    """获取生效的 Embedding 配置"""
    service = SystemConfigService(db)
    config = await service.get_config()
    return config.embedding


async def get_effective_rerank_config(db: AsyncSession) -> RerankConfigBase:
    """获取生效的 Rerank 配置"""
    service = SystemConfigService(db)
    config = await service.get_config()
    return config.rerank


# ========== Supervisor 全局配置服务 ==========


class SupervisorGlobalConfigService:
    """全局 Supervisor 配置服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self) -> SupervisorGlobalConfigResponse:
        """获取全局 Supervisor 配置（数据库优先）"""
        from app.core.config import settings

        # 尝试从数据库读取
        supervisor_json = await self._get_value(CONFIG_KEYS["supervisor"])

        if supervisor_json:
            # 数据库配置
            config = SupervisorGlobalConfig(**json.loads(supervisor_json))
            source = "database"
        else:
            # 回退到环境变量（仅基础配置）
            config = SupervisorGlobalConfig(
                enabled=settings.SUPERVISOR_ENABLED,
                intent_timeout=settings.SUPERVISOR_INTENT_TIMEOUT,
                allow_multi_agent=settings.SUPERVISOR_ALLOW_MULTI_AGENT,
            )
            source = "env"

        return SupervisorGlobalConfigResponse(
            enabled=config.enabled,
            supervisor_prompt=config.supervisor_prompt,
            sub_agents=config.sub_agents,
            routing_policy=config.routing_policy,
            intent_timeout=config.intent_timeout,
            allow_multi_agent=config.allow_multi_agent,
            source=source,
        )

    async def update_config(
        self, data: SupervisorGlobalConfigUpdate
    ) -> SupervisorGlobalConfigResponse:
        """更新全局 Supervisor 配置"""
        # 获取当前配置
        current = await self.get_config()

        # 合并更新
        new_config = SupervisorGlobalConfig(
            enabled=data.enabled if data.enabled is not None else current.enabled,
            supervisor_prompt=data.supervisor_prompt if data.supervisor_prompt is not None else current.supervisor_prompt,
            sub_agents=data.sub_agents if data.sub_agents is not None else current.sub_agents,
            routing_policy=data.routing_policy if data.routing_policy is not None else current.routing_policy,
            intent_timeout=data.intent_timeout if data.intent_timeout is not None else current.intent_timeout,
            allow_multi_agent=data.allow_multi_agent if data.allow_multi_agent is not None else current.allow_multi_agent,
        )

        # 保存到数据库
        await self._set_value(CONFIG_KEYS["supervisor"], new_config.model_dump_json())
        await self.db.commit()

        logger.info(
            "Supervisor 全局配置已更新",
            enabled=new_config.enabled,
            sub_agent_count=len(new_config.sub_agents),
        )

        # 清除配置缓存
        clear_config_cache()

        return await self.get_config()

    async def get_available_agents(self) -> list[AvailableAgentForSupervisor]:
        """获取可选为子 Agent 的 Agent 列表"""
        from app.models.agent import Agent

        # 获取当前配置中的子 Agent
        current = await self.get_config()
        selected_ids = {sa.agent_id for sa in current.sub_agents}

        # 查询所有启用的 Agent
        stmt = select(Agent).where(Agent.status == "enabled")
        result = await self.db.execute(stmt)
        agents = result.scalars().all()

        return [
            AvailableAgentForSupervisor(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                type=agent.type,
                status=agent.status,
                is_selected=agent.id in selected_ids,
            )
            for agent in agents
        ]

    async def add_sub_agent(
        self, agent_id: str, name: str, description: str | None = None,
        routing_hints: list[str] | None = None, priority: int = 100
    ) -> SupervisorGlobalConfigResponse:
        """添加子 Agent"""
        current = await self.get_config()

        # 检查是否已存在
        if any(sa.agent_id == agent_id for sa in current.sub_agents):
            raise ValueError(f"Agent {agent_id} 已在子 Agent 列表中")

        # 添加新的子 Agent
        new_sub_agent = SupervisorSubAgent(
            agent_id=agent_id,
            name=name,
            description=description,
            routing_hints=routing_hints or [],
            priority=priority,
        )
        new_sub_agents = list(current.sub_agents) + [new_sub_agent]

        return await self.update_config(
            SupervisorGlobalConfigUpdate(sub_agents=new_sub_agents)
        )

    async def remove_sub_agent(self, agent_id: str) -> SupervisorGlobalConfigResponse:
        """移除子 Agent"""
        current = await self.get_config()

        new_sub_agents = [sa for sa in current.sub_agents if sa.agent_id != agent_id]

        if len(new_sub_agents) == len(current.sub_agents):
            raise ValueError(f"Agent {agent_id} 不在子 Agent 列表中")

        return await self.update_config(
            SupervisorGlobalConfigUpdate(sub_agents=new_sub_agents)
        )

    async def _get_value(self, key: str) -> str | None:
        """从数据库获取配置值"""
        stmt = select(AppMetadata).where(AppMetadata.key == key)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        return row.value if row else None

    async def _set_value(self, key: str, value: str) -> None:
        """设置配置值到数据库"""
        stmt = select(AppMetadata).where(AppMetadata.key == key)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()

        if row:
            row.value = value
        else:
            self.db.add(AppMetadata(key=key, value=value))


async def get_effective_supervisor_config(db: AsyncSession) -> SupervisorGlobalConfig:
    """获取生效的 Supervisor 全局配置（优先数据库，其次环境变量）"""
    from app.core.config import settings

    # 尝试从数据库读取
    stmt = select(AppMetadata).where(AppMetadata.key == CONFIG_KEYS["supervisor"])
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()

    if row:
        return SupervisorGlobalConfig(**json.loads(row.value))

    # 回退到环境变量
    return SupervisorGlobalConfig(
        enabled=settings.SUPERVISOR_ENABLED,
        intent_timeout=settings.SUPERVISOR_INTENT_TIMEOUT,
        allow_multi_agent=settings.SUPERVISOR_ALLOW_MULTI_AGENT,
    )
