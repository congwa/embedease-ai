"""严格模式中间件

基于工具策略（ToolPolicy）确保模型遵循工具调用约束，而不是依赖硬编码的提示词。
"""

from collections.abc import Awaitable, Callable

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import AIMessage

from app.core.logging import get_logger
from app.services.agent.policy import ToolPolicy, get_policy

logger = get_logger("middleware.strict_mode")

STRICT_MODE_FALLBACK_MESSAGE = """**严格模式提示**

我需要先通过工具获取真实数据才能回答您的问题。

当前这轮对话我没有获取到可引用的工具输出，因此无法给出可靠的推荐。

您可以：
1. **补充关键信息**：告诉我您的预算范围、品类偏好、使用场景等
2. **让我先检索**：我会调用工具获取商品数据后再回答
3. **切换模式**：如果您只是想随便聊聊，可以切换到自由聊天模式
"""


def _get_mode_from_request(request: ModelRequest) -> str:
    """从 ModelRequest.runtime.context 获取当前聊天模式"""
    runtime = getattr(request, "runtime", None)
    chat_context = getattr(runtime, "context", None) if runtime is not None else None
    mode = getattr(chat_context, "mode", None)
    return mode if isinstance(mode, str) else "natural"


def _has_tool_calls(msg: AIMessage) -> bool:
    """检查 AIMessage 是否包含工具调用"""
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls and len(tool_calls) > 0:
        return True
    additional_kwargs = getattr(msg, "additional_kwargs", {}) or {}
    if additional_kwargs.get("tool_calls"):
        return True
    return False


class StrictModeMiddleware(AgentMiddleware):
    """严格模式中间件

    基于工具策略（ToolPolicy）执行工具调用约束：
    - 如果策略要求必须调用工具但模型没有调用，则替换为受控失败消息
    - 如果策略允许直接回答，则正常放行
    - 支持配置回退工具和最小工具调用次数
    """

    def __init__(
        self, policy: ToolPolicy | None = None, custom_fallback_message: str | None = None
    ):
        self.policy = policy
        self.fallback_message = custom_fallback_message or STRICT_MODE_FALLBACK_MESSAGE

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        mode = _get_mode_from_request(request)

        # 获取当前模式的策略，如果没有传入策略则使用默认策略
        policy = self.policy or get_policy(mode)

        logger.debug(
            "应用严格模式策略",
            mode=mode,
            policy_description=policy.description,
            min_tool_calls=policy.min_tool_calls,
            allow_direct_answer=policy.allow_direct_answer,
        )

        # 如果策略允许直接回答，直接放行
        if policy.allow_direct_answer:
            return await handler(request)

        response = await handler(request)

        # 检查工具调用次数是否满足策略要求
        total_tool_calls = 0
        for msg in response.result:
            if isinstance(msg, AIMessage) and _has_tool_calls(msg):
                total_tool_calls += 1

        # 如果满足最小工具调用要求，正常放行
        if total_tool_calls >= policy.min_tool_calls:
            logger.debug(
                "工具调用次数满足策略要求",
                tool_calls=total_tool_calls,
                min_required=policy.min_tool_calls,
            )
            return response

        # 不满足策略要求，替换为受控失败消息
        logger.warning(
            "工具调用次数不满足策略要求，替换为受控失败消息",
            tool_calls=total_tool_calls,
            min_required=policy.min_tool_calls,
            policy=policy.description,
        )

        for i, msg in enumerate(response.result):
            if isinstance(msg, AIMessage):
                content = msg.content
                if isinstance(content, list):
                    content = "".join(str(x) for x in content)

                if isinstance(content, str) and content.strip():
                    response.result[i] = AIMessage(
                        content=self.fallback_message,
                        additional_kwargs=(
                            msg.additional_kwargs if hasattr(msg, "additional_kwargs") else {}
                        ),
                        response_metadata=(
                            msg.response_metadata if hasattr(msg, "response_metadata") else {}
                        ),
                    )

        return response
