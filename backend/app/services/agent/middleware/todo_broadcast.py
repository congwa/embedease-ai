"""TODO 广播中间件

监听 state.todos 变化，通过 SSE 推送给前端。
"""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langgraph.prebuilt.tool_node import ToolCallRequest

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("middleware.todo_broadcast")


def _hash_todos(todos: list[dict[str, Any]] | None) -> str:
    """计算 todos 的 hash，用于变更检测"""
    if not todos:
        return ""
    try:
        return json.dumps(todos, sort_keys=True, ensure_ascii=False)
    except Exception:
        return ""


class TodoBroadcastMiddleware(AgentMiddleware):
    """TODO 广播中间件

    在每次模型调用后检测 state.todos 是否变化，
    若变化则通过 context.emitter 推送 SSE 事件给前端。
    """

    def __init__(self) -> None:
        super().__init__()
        self._last_todos_hash: str = ""

    async def aafter_model(
        self,
        state: dict[str, Any],
        runtime: Any,
    ) -> dict[str, Any] | None:
        """模型调用后检测 todos 变化并广播"""
        try:
            # 获取当前 todos
            todos = state.get("todos")
            if todos is None:
                return None

            # 计算 hash 检测变化
            current_hash = _hash_todos(todos)
            if current_hash == self._last_todos_hash:
                return None
            logger.debug("TODO 列表内容", todos=todos)
            # 更新 hash
            self._last_todos_hash = current_hash

            # 获取 emitter
            context = getattr(runtime, "context", None)
            if context is None:
                return None

            emitter = getattr(context, "emitter", None)
            if emitter is None or not hasattr(emitter, "aemit"):
                return None

            # 广播 todos 变更
            await emitter.aemit(
                StreamEventType.ASSISTANT_TODOS.value,
                {"todos": todos},
            )

            logger.debug(
                "TODO 列表已广播",
                todo_count=len(todos),
                statuses=[t.get("status") for t in todos],
            )

        except Exception as e:
            # 广播失败不影响主流程
            logger.warning("TODO 广播失败", error=str(e))

        return None

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """透传模型调用，不做修改"""
        return await handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """工具调用后检测 todos 变化并立即广播

        注意：write_todos 工具返回 Command 对象，todos 在 Command.update["todos"] 中
        """
        # 从 ToolCallRequest 获取工具名（格式如 "write_todos" 或带前缀）
        tool_call = getattr(request, "tool_call", None) or {}
        tool_name = tool_call.get("name", "")

        logger.debug(
            "awrap_tool_call 被调用",
            tool_name=tool_name,
            request_type=type(request).__name__,
        )

        # 执行工具调用
        response = await handler(request)

        # 如果是 write_todos 工具，从 Command.update 中提取 todos 并广播
        if "write_todos" in tool_name:
            try:
                logger.debug(
                    "write_todos 工具调用完成",
                    response_type=type(response).__name__,
                    has_update=hasattr(response, "update"),
                )

                # write_todos 返回 Command 对象，todos 在 Command.update 中
                update = getattr(response, "update", None)
                if update and isinstance(update, dict):
                    todos = update.get("todos")
                    if todos is not None:
                        current_hash = _hash_todos(todos)

                        # 只在实际变化时广播（避免重复发送）
                        if current_hash != self._last_todos_hash:
                            self._last_todos_hash = current_hash

                            logger.debug(
                                "write_todos 检测到 TODO 变化",
                                todo_count=len(todos),
                            )

                            # 从 ToolCallRequest.runtime.context 获取（与 llm_call_sse.py 保持一致）
                            runtime = getattr(request, "runtime", None)
                            context = getattr(runtime, "context", None) if runtime else None

                            if context:
                                emitter = getattr(context, "emitter", None)
                                if emitter and hasattr(emitter, "aemit"):
                                    await emitter.aemit(
                                        StreamEventType.ASSISTANT_TODOS.value,
                                        {"todos": todos},
                                    )
                                    logger.info(
                                        "write_todos 后立即广播 TODO 列表",
                                        todo_count=len(todos),
                                        statuses=[t.get("status") for t in todos],
                                    )
                                else:
                                    logger.warning("emitter 不可用", context_attrs=dir(context))
                            else:
                                logger.warning(
                                    "context 不可用",
                                    has_runtime=runtime is not None,
                                )
                    else:
                        logger.warning("Command.update 中没有 todos")
                else:
                    logger.warning(
                        "response 不是预期的 Command 对象或没有 update",
                        response_type=type(response).__name__,
                    )
            except Exception as e:
                logger.exception("write_todos 后广播失败", error=str(e))

        return response
