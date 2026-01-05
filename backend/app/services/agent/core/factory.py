"""Agent 工厂

从 AgentConfig 构建 LangGraph Agent 实例。
"""

from typing import Any

from langchain.agents import create_agent
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph

from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.schemas.agent import AgentConfig
from app.services.agent.middleware.registry import build_middlewares_for_agent
from app.services.agent.tools.registry import get_tools_for_agent
from app.services.streaming.context import ChatContext

logger = get_logger("agent.factory")


# ========== 模式策略提示词后缀 ==========

MODE_PROMPT_SUFFIX: dict[str, str] = {
    "natural": "",  # 默认模式无额外约束
    "free": """

## 自由模式
你可以与用户自由交流各种话题，不局限于特定领域。
当用户有明确需求时，可以帮助检索相关信息。
保持自然、友好的对话风格。
""",
    "strict": """

## 严格模式
- **数据驱动**：所有回答必须基于工具返回的真实数据
- **准确可靠**：推荐或回答时必须引用具体数据
- **诚实透明**：如果没有找到合适的信息，请如实告知
- **不编造信息**：只基于检索结果回答

如果没有调用工具或工具返回为空，请引导用户补充信息。
""",
}


def get_response_format_for_type(agent_type: str) -> type | None:
    """根据 Agent 类型获取结构化输出格式"""
    if agent_type == "product":
        from app.schemas.recommendation import RecommendationResult

        return RecommendationResult
    elif agent_type == "faq":
        # FAQ 暂不使用结构化输出
        return None
    else:
        return None


async def build_agent(
    config: AgentConfig,
    checkpointer: AsyncSqliteSaver,
    use_structured_output: bool = False,
) -> CompiledStateGraph:
    """从配置构建 Agent 实例

    Args:
        config: Agent 运行时配置
        checkpointer: LangGraph checkpoint saver
        use_structured_output: 是否使用结构化输出

    Returns:
        编译后的 LangGraph Agent
    """
    # 1. 获取 LLM
    model = get_chat_model()

    # 2. 构建完整 system prompt（基础 + 模式后缀）
    system_prompt = config.system_prompt
    mode_suffix = MODE_PROMPT_SUFFIX.get(config.mode, "")
    if mode_suffix:
        system_prompt = system_prompt + mode_suffix

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
            mode=config.mode,
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
