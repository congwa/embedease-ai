"""严格模式中间件

在 strict 模式下，确保模型必须调用工具才能给出回答。
如果模型没有调用工具就直接回答，则替换为受控失败消息。
"""

from collections.abc import Awaitable, Callable

from langchain.agents.middleware.types import (
    AgentMiddleware,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import AIMessage

from app.core.logging import get_logger

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

    在 strict 模式下：
    - 如果模型返回的是纯文本回答（没有工具调用），则替换为受控失败消息
    - 如果模型调用了工具，则正常放行

    注意：这个中间件只在 strict 模式下生效
    """

    def __init__(self, custom_fallback_message: str | None = None):
        self.fallback_message = custom_fallback_message or STRICT_MODE_FALLBACK_MESSAGE

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        mode = _get_mode_from_request(request)

        if mode != "strict":
            return await handler(request)

        response = await handler(request)

        for i, msg in enumerate(response.result):
            if not isinstance(msg, AIMessage):
                continue

            if _has_tool_calls(msg):
                logger.debug(
                    "strict 模式：检测到工具调用，正常放行",
                    tool_calls=getattr(msg, "tool_calls", None),
                )
                continue

            content = msg.content
            if isinstance(content, list):
                content = "".join(str(x) for x in content)

            if isinstance(content, str) and content.strip():
                logger.warning(
                    "strict 模式：检测到无工具调用的直接回答，替换为受控失败消息",
                    content_preview=content[:100],
                )
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
