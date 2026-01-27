"""默认 Agent 初始化模块

从配置文件读取默认 Agent 定义，幂等写入数据库。

使用方式：
    # 在 main.py 启动时调用
    from app.services.agent.bootstrap import bootstrap_default_agents
    await bootstrap_default_agents()

    # 或手动运行脚本
    uv run python -m app.services.agent.bootstrap
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.agent import Agent, AgentStatus, AgentType, KnowledgeConfig, KnowledgeType

logger = get_logger("agent.bootstrap")


class AgentBootstrapper:
    """Agent 初始化器"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._override_policy = settings.DEFAULT_AGENTS_OVERRIDE_POLICY

    async def bootstrap(self) -> list[str]:
        """执行初始化，返回创建/更新的 Agent ID 列表"""
        agent_configs = settings.default_agents
        if not agent_configs:
            logger.debug("未配置默认 Agent，跳过初始化")
            return []

        created_ids: list[str] = []

        for config in agent_configs:
            try:
                agent_id = await self._process_agent_config(config)
                if agent_id:
                    created_ids.append(agent_id)
            except Exception as e:
                logger.error(
                    "处理默认 Agent 配置失败",
                    config_id=config.get("id"),
                    config_name=config.get("name"),
                    error=str(e),
                )

        if created_ids:
            await self._session.commit()
            logger.info("默认 Agent 初始化完成", count=len(created_ids), agent_ids=created_ids)

        return created_ids

    async def _process_agent_config(self, config: dict[str, Any]) -> str | None:
        """处理单个 Agent 配置

        Returns:
            创建或更新的 Agent ID，跳过时返回 None
        """
        agent_id = config.get("id") or str(uuid.uuid4())
        agent_name = config.get("name", "")

        if not agent_name:
            logger.warning("Agent 配置缺少 name 字段，跳过", config=config)
            return None

        # 检查是否已存在
        existing = await self._get_agent_by_id(agent_id)

        if existing:
            if self._override_policy == "skip":
                logger.debug("Agent 已存在，跳过", agent_id=agent_id, name=agent_name)
                return None
            elif self._override_policy == "update":
                return await self._update_agent(existing, config)
        else:
            return await self._create_agent(agent_id, config)

    async def _get_agent_by_id(self, agent_id: str) -> Agent | None:
        """根据 ID 获取 Agent"""
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_agent(self, agent_id: str, config: dict[str, Any]) -> str:
        """创建新 Agent"""
        # 1. 处理知识库配置（如果有）
        knowledge_config_id = await self._process_knowledge_config(config, agent_id)

        # 2. 构建 Agent 字段
        agent_type = config.get("type", "product")
        if agent_type not in [t.value for t in AgentType]:
            agent_type = AgentType.PRODUCT.value

        system_prompt = config.get("system_prompt", "")
        if not system_prompt:
            from app.services.agent.core.config import DEFAULT_PROMPTS
            system_prompt = DEFAULT_PROMPTS.get(agent_type, DEFAULT_PROMPTS["custom"])

        agent = Agent(
            id=agent_id,
            name=config.get("name", ""),
            description=config.get("description"),
            type=agent_type,
            system_prompt=system_prompt,
            mode_default=config.get("mode_default", "natural"),
            middleware_flags=config.get("middleware_flags"),
            tool_policy=config.get("tool_policy"),
            tool_categories=config.get("tool_categories"),
            knowledge_config_id=knowledge_config_id,
            response_format=config.get("response_format"),
            status=AgentStatus.ENABLED.value,
            is_default=config.get("is_default", False),
        )

        self._session.add(agent)
        await self._session.flush()

        logger.info(
            "创建默认 Agent",
            agent_id=agent_id,
            name=agent.name,
            type=agent_type,
            is_default=agent.is_default,
        )

        return agent_id

    async def _update_agent(self, agent: Agent, config: dict[str, Any]) -> str:
        """更新已存在的 Agent"""
        # 1. 处理知识库配置
        knowledge_config_id = await self._process_knowledge_config(config, agent.id)

        # 2. 更新字段（仅更新配置中提供的字段）
        if "name" in config:
            agent.name = config["name"]
        if "description" in config:
            agent.description = config["description"]
        if "type" in config:
            agent.type = config["type"]
        if "system_prompt" in config:
            agent.system_prompt = config["system_prompt"]
        if "mode_default" in config:
            agent.mode_default = config["mode_default"]
        if "middleware_flags" in config:
            agent.middleware_flags = config["middleware_flags"]
        if "tool_policy" in config:
            agent.tool_policy = config["tool_policy"]
        if "tool_categories" in config:
            agent.tool_categories = config["tool_categories"]
        if "response_format" in config:
            agent.response_format = config["response_format"]
        if "is_default" in config:
            agent.is_default = config["is_default"]
        if knowledge_config_id:
            agent.knowledge_config_id = knowledge_config_id

        await self._session.flush()

        logger.info(
            "更新默认 Agent",
            agent_id=agent.id,
            name=agent.name,
        )

        return agent.id

    async def _process_knowledge_config(
        self, config: dict[str, Any], agent_id: str
    ) -> str | None:
        """处理嵌套的知识库配置

        Returns:
            知识库配置 ID，无配置时返回 None
        """
        kb_config = config.get("knowledge_config")
        if not kb_config:
            return None

        kb_id = kb_config.get("id") or f"kb-{agent_id}"
        kb_name = kb_config.get("name", f"{config.get('name', 'Agent')} 知识库")

        # 检查是否已存在
        stmt = select(KnowledgeConfig).where(KnowledgeConfig.id == kb_id)
        result = await self._session.execute(stmt)
        existing_kb = result.scalar_one_or_none()

        kb_type = kb_config.get("type", "vector")
        if kb_type not in [t.value for t in KnowledgeType]:
            kb_type = KnowledgeType.VECTOR.value

        if existing_kb:
            if self._override_policy == "update":
                # 更新知识库配置
                if "name" in kb_config:
                    existing_kb.name = kb_config["name"]
                if "type" in kb_config:
                    existing_kb.type = kb_type
                if "index_name" in kb_config:
                    existing_kb.index_name = kb_config["index_name"]
                if "collection_name" in kb_config:
                    existing_kb.collection_name = kb_config["collection_name"]
                if "embedding_model" in kb_config:
                    existing_kb.embedding_model = kb_config["embedding_model"]
                if "top_k" in kb_config:
                    existing_kb.top_k = kb_config["top_k"]
                if "similarity_threshold" in kb_config:
                    existing_kb.similarity_threshold = kb_config["similarity_threshold"]
                if "rerank_enabled" in kb_config:
                    existing_kb.rerank_enabled = kb_config["rerank_enabled"]
                if "filters" in kb_config:
                    existing_kb.filters = kb_config["filters"]

                await self._session.flush()
                logger.debug("更新知识库配置", kb_id=kb_id, name=existing_kb.name)
            return kb_id
        else:
            # 创建知识库配置
            kb = KnowledgeConfig(
                id=kb_id,
                name=kb_name,
                type=kb_type,
                index_name=kb_config.get("index_name"),
                collection_name=kb_config.get("collection_name"),
                embedding_model=kb_config.get("embedding_model"),
                top_k=kb_config.get("top_k", 10),
                similarity_threshold=kb_config.get("similarity_threshold"),
                rerank_enabled=kb_config.get("rerank_enabled", False),
                filters=kb_config.get("filters"),
            )

            self._session.add(kb)
            await self._session.flush()

            logger.info("创建知识库配置", kb_id=kb_id, name=kb_name, type=kb_type)
            return kb_id


async def bootstrap_default_agents() -> list[str]:
    """初始化默认 Agent（对外接口）

    从配置文件读取默认 Agent 定义，幂等写入数据库。

    Returns:
        创建/更新的 Agent ID 列表
    """
    if not settings.DEFAULT_AGENTS_BOOTSTRAP_ENABLED:
        logger.debug("默认 Agent 初始化已禁用")
        return []

    from app.core.database import get_db_context

    async with get_db_context() as session:
        bootstrapper = AgentBootstrapper(session)
        return await bootstrapper.bootstrap()


if __name__ == "__main__":
    import asyncio

    from app.core.database import init_db

    async def main():
        """手动运行初始化脚本"""
        await init_db()
        agent_ids = await bootstrap_default_agents()
        if agent_ids:
            print(f"✅ 初始化完成，创建/更新了 {len(agent_ids)} 个 Agent: {agent_ids}")
        else:
            print("ℹ️ 无需初始化（配置为空或 Agent 已存在）")

    asyncio.run(main())
