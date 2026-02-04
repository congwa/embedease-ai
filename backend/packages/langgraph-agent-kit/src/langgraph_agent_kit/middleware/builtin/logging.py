"""日志记录中间件"""

from __future__ import annotations

import logging
import time
from typing import Any

from langgraph_agent_kit.middleware.base import BaseMiddleware, MiddlewareConfig

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """日志记录中间件
    
    记录模型和工具调用的日志。
    """

    def __init__(self, config: MiddlewareConfig | None = None):
        super().__init__(config or MiddlewareConfig(order=60))
        self._model_start_time: float | None = None
        self._tool_start_times: dict[str, float] = {}

    async def before_model(self, request: Any, context: Any) -> Any:
        """记录模型调用开始"""
        self._model_start_time = time.time()
        logger.debug(
            "LLM call started",
            extra={
                "conversation_id": getattr(context, "conversation_id", None),
            },
        )
        return request

    async def after_model(self, response: Any, context: Any) -> Any:
        """记录模型调用结束"""
        elapsed_ms = 0
        if self._model_start_time:
            elapsed_ms = int((time.time() - self._model_start_time) * 1000)
        
        logger.debug(
            "LLM call completed",
            extra={
                "conversation_id": getattr(context, "conversation_id", None),
                "elapsed_ms": elapsed_ms,
            },
        )
        return response

    async def before_tool(self, tool_call: Any, context: Any) -> Any:
        """记录工具调用开始"""
        tool_call_id = getattr(tool_call, "id", str(id(tool_call)))
        self._tool_start_times[tool_call_id] = time.time()
        
        logger.debug(
            "Tool call started",
            extra={
                "tool_call_id": tool_call_id,
                "tool_name": getattr(tool_call, "name", "unknown"),
            },
        )
        return tool_call

    async def after_tool(self, tool_result: Any, context: Any) -> Any:
        """记录工具调用结束"""
        tool_call_id = getattr(tool_result, "tool_call_id", None)
        elapsed_ms = 0
        if tool_call_id and tool_call_id in self._tool_start_times:
            elapsed_ms = int((time.time() - self._tool_start_times[tool_call_id]) * 1000)
            del self._tool_start_times[tool_call_id]
        
        logger.debug(
            "Tool call completed",
            extra={
                "tool_call_id": tool_call_id,
                "elapsed_ms": elapsed_ms,
            },
        )
        return tool_result
