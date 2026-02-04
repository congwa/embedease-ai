"""LangGraph Agent Kit - 统一的流式聊天 Agent 框架

提供统一的事件协议、上下文管理、事件发射器和流编排器。
支持工具和中间件内部推送 SSE 事件。
"""

__version__ = "0.1.0"

from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.core.stream_event import StreamEvent
from langgraph_agent_kit.core.context import ChatContext, DomainEmitter
from langgraph_agent_kit.core.emitter import QueueDomainEmitter
from langgraph_agent_kit.streaming.sse import make_event, encode_sse, new_event_id, now_ms
from langgraph_agent_kit.streaming.orchestrator import BaseOrchestrator
from langgraph_agent_kit.streaming.response_handler import StreamingResponseHandler
from langgraph_agent_kit.helpers import (
    get_emitter_from_runtime,
    get_emitter_from_request,
    emit_tool_start,
    emit_tool_end,
)

from langgraph_agent_kit.middleware.base import MiddlewareSpec, MiddlewareConfig, BaseMiddleware
from langgraph_agent_kit.middleware.registry import MiddlewareRegistry
from langgraph_agent_kit.middleware.builtin import Middlewares

from langgraph_agent_kit.tools.base import ToolSpec, ToolConfig
from langgraph_agent_kit.tools.registry import ToolRegistry
from langgraph_agent_kit.tools.decorators import with_tool_events

from langgraph_agent_kit.kit import ChatStreamKit


def create_sse_response(*args, **kwargs):
    """创建 SSE 响应（需要安装 fastapi 可选依赖）"""
    from langgraph_agent_kit.integrations.fastapi import create_sse_response as _create
    return _create(*args, **kwargs)


__all__ = [
    # Version
    "__version__",
    # Core
    "StreamEventType",
    "StreamEvent",
    "ChatContext",
    "DomainEmitter",
    "QueueDomainEmitter",
    # Streaming
    "make_event",
    "encode_sse",
    "new_event_id",
    "now_ms",
    "BaseOrchestrator",
    "StreamingResponseHandler",
    # Helpers
    "get_emitter_from_runtime",
    "get_emitter_from_request",
    "emit_tool_start",
    "emit_tool_end",
    # Middleware
    "MiddlewareSpec",
    "MiddlewareConfig",
    "BaseMiddleware",
    "MiddlewareRegistry",
    "Middlewares",
    # Tools
    "ToolSpec",
    "ToolConfig",
    "ToolRegistry",
    "with_tool_events",
    # Main
    "ChatStreamKit",
    # Integrations
    "create_sse_response",
]
