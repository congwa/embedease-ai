"""Agent 配置加载器

从数据库加载 Agent 配置，合并默认值，生成运行时 AgentConfig。
"""

import hashlib
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.agent import Agent, AgentModeOverride, AgentType
from app.schemas.agent import (
    AgentConfig,
    KnowledgeConfigResponse,
    MiddlewareFlagsSchema,
    ToolPolicySchema,
)

logger = get_logger("agent.config")


# ========== 默认 System Prompts ==========

DEFAULT_PROMPTS: dict[str, str] = {
    "product": """你是一个专业的商品推荐助手，帮助用户发现和选择合适的商品。

## 核心原则
- 理解用户的购物需求和偏好，提供个性化的商品推荐
- 只推荐基于真实数据的商品，不编造信息
- 突出商品的核心卖点和性价比
- 保持友好、专业的语气

## 输出格式
当推荐商品时，请使用以下格式：

根据您的需求，我为您推荐以下商品：

### 1. **商品名称** - ¥价格
**推荐理由**：...
**适合人群**：...

如果用户询问非商品相关的问题，礼貌地引导他们回到商品推荐话题。
""",
    "faq": """你是一个专业的问答助手，基于 FAQ 知识库回答用户问题。

## 核心原则
- 优先使用 FAQ 工具检索相关问答
- 基于检索结果准确回答，不编造信息
- 如果没有找到相关答案，诚实告知用户
- 回答要简洁清晰，直接解决用户问题

## 输出格式
- 直接回答问题，不需要引用来源编号
- 如有多个相关答案，综合整理后回答
- 无法回答时，建议用户联系人工客服
""",
    "kb": """你是一个专业的知识库助手，基于内部知识库回答用户问题。

## 核心原则
- 使用知识检索工具获取相关文档
- 基于检索结果准确回答，引用来源
- 如果信息不足，诚实告知并建议补充
- 保持专业、准确的回答风格

## 输出格式
- 回答后注明信息来源
- 对于复杂问题，分点阐述
- 不确定的内容明确标注
""",
    "custom": """你是一个智能助手，根据配置的能力帮助用户完成任务。

## 核心原则
- 理解用户意图，提供有价值的帮助
- 诚实回答，不确定时如实告知
- 保持友好、专业的对话风格
""",
}


# ========== 默认工具类别 ==========

DEFAULT_TOOL_CATEGORIES: dict[str, list[str]] = {
    "product": [
        "search",
        "query",
        "compare",
        "filter",
        "category",
        "featured",
        "purchase",
        "guide",
    ],
    "faq": ["faq"],
    "kb": ["kb", "search"],
    "custom": [],
}


# ========== 默认工具策略 ==========

DEFAULT_TOOL_POLICIES: dict[str, dict[str, Any]] = {
    "product": {
        "min_tool_calls": 0,
        "allow_direct_answer": True,
        "fallback_tool": None,
    },
    "faq": {
        "min_tool_calls": 0,
        "allow_direct_answer": True,  # FAQ 可以直接回答简单问题
        "fallback_tool": "faq_search",
    },
    "kb": {
        "min_tool_calls": 1,
        "allow_direct_answer": False,  # KB 必须基于检索结果
        "fallback_tool": "kb_search",
    },
    "custom": {
        "min_tool_calls": 0,
        "allow_direct_answer": True,
        "fallback_tool": None,
    },
}


class AgentConfigLoader:
    """Agent 配置加载器"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_default_agent_id(self) -> str | None:
        """获取默认 Agent ID"""
        stmt = select(Agent).where(Agent.is_default == True, Agent.status == "enabled")  # noqa: E712
        result = await self._session.execute(stmt)
        agent = result.scalar_one_or_none()
        return agent.id if agent else None

    async def get_agent(self, agent_id: str) -> Agent | None:
        """获取 Agent 实体"""
        stmt = (
            select(Agent)
            .where(Agent.id == agent_id)
            .options(selectinload(Agent.knowledge_config), selectinload(Agent.tools))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_mode_override(self, agent_id: str, mode: str) -> AgentModeOverride | None:
        """获取模式覆盖配置"""
        stmt = select(AgentModeOverride).where(
            AgentModeOverride.agent_id == agent_id,
            AgentModeOverride.mode == mode,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def load_config(self, agent_id: str, mode: str = "natural") -> AgentConfig | None:
        """加载完整的 Agent 配置

        Args:
            agent_id: Agent ID
            mode: 回答策略模式

        Returns:
            运行时 AgentConfig，或 None（未找到）
        """
        agent = await self.get_agent(agent_id)
        if agent is None:
            logger.warning("Agent 不存在", agent_id=agent_id)
            return None

        if agent.status != "enabled":
            logger.warning("Agent 已禁用", agent_id=agent_id)
            return None

        # 加载模式覆盖
        mode_override = await self.get_mode_override(agent_id, mode)

        # 构建配置
        config = self._build_config(agent, mode, mode_override)

        logger.debug(
            "加载 Agent 配置",
            agent_id=agent_id,
            agent_type=agent.type,
            mode=mode,
            has_override=mode_override is not None,
        )

        return config

    def _build_config(
        self,
        agent: Agent,
        mode: str,
        mode_override: AgentModeOverride | None,
    ) -> AgentConfig:
        """构建运行时配置"""
        agent_type = agent.type

        # 1. System Prompt：优先 mode_override > agent > 默认
        if mode_override and mode_override.system_prompt_override:
            system_prompt = mode_override.system_prompt_override
        elif agent.system_prompt:
            system_prompt = agent.system_prompt
        else:
            system_prompt = DEFAULT_PROMPTS.get(agent_type, DEFAULT_PROMPTS["custom"])

        # 2. 工具类别：agent 配置 > 默认
        tool_categories = agent.tool_categories
        if not tool_categories:
            tool_categories = DEFAULT_TOOL_CATEGORIES.get(agent_type, [])

        # 3. 工具白名单（从 agent_tools 表加载）
        tool_whitelist: list[str] | None = None
        if agent.tools:
            tool_whitelist = [t.tool_name for t in agent.tools if t.enabled]

        # 4. 工具策略：mode_override > agent > 默认
        tool_policy_dict: dict[str, Any] = DEFAULT_TOOL_POLICIES.get(agent_type, {}).copy()
        if agent.tool_policy:
            tool_policy_dict.update(agent.tool_policy)
        if mode_override and mode_override.tool_policy_override:
            tool_policy_dict.update(mode_override.tool_policy_override)

        tool_policy = ToolPolicySchema(**tool_policy_dict) if tool_policy_dict else None

        # 5. 中间件配置：mode_override > agent
        middleware_dict: dict[str, Any] = {}
        if agent.middleware_flags:
            middleware_dict.update(agent.middleware_flags)
        if mode_override and mode_override.middleware_overrides:
            middleware_dict.update(mode_override.middleware_overrides)

        middleware_flags = MiddlewareFlagsSchema(**middleware_dict) if middleware_dict else None

        # 6. 知识源配置
        knowledge_config: KnowledgeConfigResponse | None = None
        if agent.knowledge_config:
            kc = agent.knowledge_config
            knowledge_config = KnowledgeConfigResponse(
                id=kc.id,
                name=kc.name,
                type=kc.type,
                index_name=kc.index_name,
                collection_name=kc.collection_name,
                embedding_model=kc.embedding_model,
                top_k=kc.top_k,
                similarity_threshold=kc.similarity_threshold,
                rerank_enabled=kc.rerank_enabled,
                filters=kc.filters,
                data_version=kc.data_version,
                fingerprint=kc.fingerprint,
                created_at=kc.created_at,
                updated_at=kc.updated_at,
            )

        # 7. 计算配置版本（用于缓存失效）
        config_version = self._compute_version(agent, mode_override)

        # 8. Supervisor 配置
        sub_agents_config = None
        routing_policy_config = None

        if agent.is_supervisor and agent.sub_agents:
            from app.schemas.agent import SubAgentConfig, RoutingPolicy

            # 解析子 Agent 配置
            sub_agents_config = [
                SubAgentConfig(**sa) for sa in agent.sub_agents
            ]

            # 解析路由策略
            if agent.routing_policy:
                routing_policy_config = RoutingPolicy(**agent.routing_policy)

        return AgentConfig(
            agent_id=agent.id,
            name=agent.name,
            type=agent_type,
            system_prompt=system_prompt,
            mode=mode,
            tool_categories=tool_categories,
            tool_whitelist=tool_whitelist,
            tool_policy=tool_policy,
            middleware_flags=middleware_flags,
            knowledge_config=knowledge_config,
            response_format=agent.response_format,
            config_version=config_version,
            # Supervisor 相关
            is_supervisor=agent.is_supervisor,
            sub_agents=sub_agents_config,
            routing_policy=routing_policy_config,
            supervisor_prompt=agent.supervisor_prompt,
        )

    def _compute_version(
        self,
        agent: Agent,
        mode_override: AgentModeOverride | None,
    ) -> str:
        """计算配置版本哈希"""
        parts = [
            agent.id,
            str(agent.updated_at.timestamp()),
        ]
        if agent.knowledge_config:
            parts.append(agent.knowledge_config.data_version or "")
            parts.append(str(agent.knowledge_config.updated_at.timestamp()))
        if mode_override:
            parts.append(str(mode_override.id))

        content = "|".join(parts)
        return hashlib.md5(content.encode()).hexdigest()[:16]


async def get_or_create_default_agent(session: AsyncSession) -> str:
    """获取或创建默认 Agent

    如果没有默认 Agent，创建一个商品推荐类型的默认 Agent。
    """
    loader = AgentConfigLoader(session)
    default_id = await loader.get_default_agent_id()

    if default_id:
        return default_id

    # 创建默认商品推荐 Agent
    default_agent = Agent(
        id=str(uuid.uuid4()),
        name="商品推荐助手",
        description="默认商品推荐智能体",
        type=AgentType.PRODUCT.value,
        system_prompt=DEFAULT_PROMPTS["product"],
        mode_default="natural",
        tool_categories=DEFAULT_TOOL_CATEGORIES["product"],
        status="enabled",
        is_default=True,
    )
    session.add(default_agent)
    await session.flush()

    logger.info("创建默认 Agent", agent_id=default_agent.id)
    return default_agent.id
