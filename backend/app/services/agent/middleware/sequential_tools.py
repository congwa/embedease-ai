"""串行工具执行中间件

当模型一次返回多个 tool_calls 时，强制按顺序执行（避免并行调用）。

说明：
- LangGraph 默认会 fan-out 多个工具调用（并行调度）
- 本中间件在工具执行层加锁，确保工具调用串行执行
- 不丢弃任何工具调用，只是改变执行顺序：并行 → 串行
"""

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware
from langgraph.prebuilt.tool_node import ToolCallRequest

from app.core.logging import get_logger

logger = get_logger("middleware.sequential_tools")


class SequentialToolExecutionMiddleware(AgentMiddleware):
    """让同一轮返回的多个 tool_calls 按顺序执行（不丢弃）"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._alock = asyncio.Lock()
        logger.verbose("初始化串行工具执行中间件")

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Any],
    ) -> Any:
        """同步工具调用串行化"""
        tool_call = getattr(request, "tool_call", None) or {}
        tool_name = tool_call.get("name", "")
        logger.debug("串行执行工具（同步）", tool_name=tool_name)
        context = getattr(getattr(request, "runtime", None), "context", None)
        with getattr(context, "_sync_tool_lock", self._lock):
            return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """异步工具调用串行化"""
        tool_call = getattr(request, "tool_call", None) or {}
        tool_name = tool_call.get("name", "")
        logger.debug("串行执行工具（异步）", tool_name=tool_name)
        context = getattr(getattr(request, "runtime", None), "context", None)
        async with getattr(context, "_async_tool_lock", self._alock):
            return await handler(request)
