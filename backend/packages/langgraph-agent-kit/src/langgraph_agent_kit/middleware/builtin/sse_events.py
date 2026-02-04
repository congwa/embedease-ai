"""SSE 事件推送中间件"""

from __future__ import annotations

import time
from typing import Any

from langgraph_agent_kit.middleware.base import BaseMiddleware, MiddlewareConfig
from langgraph_agent_kit.core.events import StreamEventType


class SSEEventsMiddleware(BaseMiddleware):
    """SSE 事件推送中间件
    
    在模型调用前后发射 llm.call.start / llm.call.end 事件。
    """

    def __init__(self, config: MiddlewareConfig | None = None):
        super().__init__(config or MiddlewareConfig(order=30))
        self._call_start_time: float | None = None

    async def before_model(self, request: Any, context: Any) -> Any:
        """模型调用开始时发射事件"""
        self._call_start_time = time.time()
        
        emitter = getattr(context, "emitter", None)
        if emitter and hasattr(emitter, "aemit"):
            messages = getattr(request, "messages", [])
            await emitter.aemit(
                StreamEventType.LLM_CALL_START.value,
                {"message_count": len(messages)},
            )
        
        return request

    async def after_model(self, response: Any, context: Any) -> Any:
        """模型调用结束时发射事件"""
        elapsed_ms = 0
        if self._call_start_time:
            elapsed_ms = int((time.time() - self._call_start_time) * 1000)
        
        emitter = getattr(context, "emitter", None)
        if emitter and hasattr(emitter, "aemit"):
            await emitter.aemit(
                StreamEventType.LLM_CALL_END.value,
                {"elapsed_ms": elapsed_ms},
            )
        
        if hasattr(context, "response_latency_ms"):
            context.response_latency_ms = elapsed_ms
        
        return response
