"""Agent 工厂

从 AgentConfig 构建 LangGraph Agent 实例。
支持单 Agent 模式和 Supervisor 多 Agent 编排模式。
"""

from typing import TYPE_CHECKING, Any

from langchain.agents import create_agent
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph.state import CompiledStateGraph

from langchain.agents.structured_output import ProviderStrategy

from app.core.config import settings
from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.schemas.agent import AgentConfig
from app.services.agent.middleware.registry import build_middlewares_for_agent
from app.services.agent.tools.registry import get_tools_for_agent
from langgraph_agent_kit import ChatContext

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("agent.factory")




def get_response_format_for_type(agent_type: str) -> ProviderStrategy | None:
    """根据 Agent 类型获取结构化输出格式（启用 strict 模式）
    
    strict=True 时，模型必须严格按照 JSON Schema 输出，
    不符合 schema 的响应会在模型侧被拒绝。
    """
    if agent_type == "product":
        from app.schemas.recommendation import RecommendationResult

        return ProviderStrategy(RecommendationResult, strict=True)
    elif agent_type == "faq":
        # FAQ 暂不使用结构化输出
        return None
    else:
        return None


async def build_agent(
    config: AgentConfig,
    checkpointer: BaseCheckpointSaver,
    use_structured_output: bool = False,
    session: "AsyncSession | None" = None,
) -> CompiledStateGraph:
    """从配置构建 Agent 实例

    Args:
        config: Agent 运行时配置
        checkpointer: LangGraph checkpoint saver
        use_structured_output: 是否使用结构化输出
        session: 数据库会话（Supervisor 模式需要）

    Returns:
        编译后的 LangGraph Agent
    """
    # 单 Agent 模式
    return await _build_single_agent(config, checkpointer, use_structured_output, session)


async def build_supervisor_from_global_config(
    checkpointer: BaseCheckpointSaver,
    session: "AsyncSession",
) -> CompiledStateGraph | None:
    """从全局配置构建 Supervisor Agent

    Args:
        checkpointer: LangGraph checkpoint saver
        session: 数据库会话

    Returns:
        编译后的 Supervisor Agent 或 None
    """
    from app.services.system_config import get_effective_supervisor_config

    supervisor_config = await get_effective_supervisor_config(session)

    if not supervisor_config.enabled:
        return None

    if not supervisor_config.sub_agents:
        logger.warning("Supervisor 已启用但无子 Agent 配置")
        return None

    return await build_supervisor_agent_from_config(
        supervisor_config, checkpointer, session
    )


async def _build_single_agent(
    config: AgentConfig,
    checkpointer: BaseCheckpointSaver,
    use_structured_output: bool = False,
    session: "AsyncSession | None" = None,
) -> CompiledStateGraph:
    """构建单个 Agent 实例（内部函数）"""
    # 1. 获取 LLM（优先使用数据库配置）
    if session:
        from app.services.system_config import get_effective_llm_config
        llm_config = await get_effective_llm_config(session)
        model = get_chat_model(
            model=llm_config.chat_model,
            provider=llm_config.provider,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url,
        )
    else:
        model = get_chat_model()

    # 2. 获取系统提示词
    system_prompt = config.system_prompt

    # 3. 获取工具列表
    tools = get_tools_for_agent(config)

    # 4. 构建中间件链
    middlewares = build_middlewares_for_agent(config, model)

    # 5. 确定结构化输出格式
    response_format = None
    if use_structured_output:
        if config.response_format:
            # 自定义格式（暂不支持动态加载）
            pass
        else:
            response_format = get_response_format_for_type(config.type)

    # 6. 创建 Agent
    try:
        agent_kwargs: dict[str, Any] = {
            "model": model,
            "tools": tools,
            "system_prompt": system_prompt,
            "checkpointer": checkpointer,
            "middleware": middlewares,
            "context_schema": ChatContext,
        }

        if response_format:
            agent_kwargs["response_format"] = response_format

        agent = create_agent(**agent_kwargs)

        logger.info(
            "构建 Agent 实例",
            agent_id=config.agent_id,
            agent_type=config.type,
            tool_count=len(tools),
            middleware_count=len(middlewares) if middlewares else 0,
        )

        return agent

    except TypeError:
        # 兼容较老版本：不支持某些参数时回退
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
            checkpointer=checkpointer,
        )
        logger.warning(
            "使用兼容模式构建 Agent（部分功能不可用）",
            agent_id=config.agent_id,
        )
        return agent


# ========== Supervisor 多 Agent 编排 ==========

DEFAULT_SUPERVISOR_PROMPT = """你是一个智能助手调度器（Supervisor）。

你的职责是分析用户的问题，并将其路由到最合适的专业助手处理。

## 可用助手
{agent_descriptions}

## 路由规则
1. 分析用户意图，选择最匹配的助手
2. 如果问题涉及多个领域，选择主要相关的助手
3. 如果无法确定，使用默认助手

## 输出格式
直接调用 transfer_to_xxx 工具将对话转交给对应助手。
"""


async def build_supervisor_agent_from_config(
    supervisor_config: "SupervisorGlobalConfig",
    checkpointer: BaseCheckpointSaver,
    session: "AsyncSession",
) -> CompiledStateGraph:
    """从全局配置构建 Supervisor Agent

    Args:
        supervisor_config: 全局 Supervisor 配置
        checkpointer: LangGraph checkpoint saver
        session: 数据库会话

    Returns:
        编译后的 Supervisor Agent
    """
    from app.schemas.system_config import SupervisorGlobalConfig

    try:
        from langgraph_supervisor import create_supervisor
    except ImportError:
        logger.error("langgraph-supervisor 未安装")
        raise ImportError("langgraph-supervisor 未安装")

    if not supervisor_config.sub_agents:
        raise ValueError("Supervisor 无子 Agent 配置")

    # 1. 获取 LLM（使用数据库配置）
    from app.services.system_config import get_effective_llm_config
    llm_config = await get_effective_llm_config(session)
    model = get_chat_model(
        model=llm_config.chat_model,
        provider=llm_config.provider,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
    )

    # 2. 构建子 Agent 列表
    sub_agents_compiled = []
    agent_descriptions = []

    for sub_config in supervisor_config.sub_agents:
        try:
            # 加载子 Agent 配置
            sub_agent_config = await _load_sub_agent_config(
                sub_config.agent_id, session
            )
            if not sub_agent_config:
                logger.warning(f"子 Agent 配置加载失败: {sub_config.agent_id}")
                continue

            # 构建子 Agent
            sub_agent = await _build_single_agent(sub_agent_config, checkpointer)
            sub_agents_compiled.append({
                "name": sub_config.name,
                "agent": sub_agent,
                "description": sub_config.description or sub_agent_config.name,
            })

            # 收集描述信息
            hints = ", ".join(sub_config.routing_hints) if sub_config.routing_hints else ""
            desc = f"- **{sub_config.name}**: {sub_config.description or ''}"
            if hints:
                desc += f" (关键词: {hints})"
            agent_descriptions.append(desc)

            logger.debug(
                "子 Agent 构建成功",
                name=sub_config.name,
                agent_id=sub_config.agent_id,
            )

        except Exception as e:
            logger.error(f"构建子 Agent 失败: {sub_config.agent_id}", error=str(e))
            continue

    if not sub_agents_compiled:
        raise ValueError("无有效子 Agent")

    # 3. 构建 Supervisor 提示词
    supervisor_prompt = supervisor_config.supervisor_prompt or DEFAULT_SUPERVISOR_PROMPT
    supervisor_prompt = supervisor_prompt.replace(
        "{agent_descriptions}", "\n".join(agent_descriptions)
    )

    # 4. 创建 Supervisor
    supervisor = create_supervisor(
        agents=[a["agent"] for a in sub_agents_compiled],
        model=model,
        prompt=supervisor_prompt,
    ).compile(checkpointer=checkpointer)

    logger.info(
        "构建 Supervisor Agent 成功",
        sub_agent_count=len(sub_agents_compiled),
        sub_agents=[a["name"] for a in sub_agents_compiled],
    )

    return supervisor


async def _load_sub_agent_config(
    agent_id: str,
    session: "AsyncSession | None" = None,
) -> AgentConfig | None:
    """加载子 Agent 配置

    Args:
        agent_id: 子 Agent ID
        session: 数据库会话

    Returns:
        AgentConfig 或 None
    """
    if not session:
        logger.warning("无数据库会话，无法加载子 Agent 配置")
        return None

    from app.services.agent.core.config import AgentConfigLoader

    loader = AgentConfigLoader(session)
    return await loader.load_config(agent_id)
