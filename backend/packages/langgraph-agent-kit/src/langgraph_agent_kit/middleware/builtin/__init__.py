"""内置中间件集合"""

from langgraph_agent_kit.middleware.builtin.sse_events import SSEEventsMiddleware
from langgraph_agent_kit.middleware.builtin.logging import LoggingMiddleware


class Middlewares:
    """内置中间件工厂
    
    提供预配置的内置中间件实例。
    """

    @staticmethod
    def sse_events(order: int = 30) -> SSEEventsMiddleware:
        """SSE 事件推送中间件"""
        from langgraph_agent_kit.middleware.base import MiddlewareConfig
        return SSEEventsMiddleware(MiddlewareConfig(order=order))

    @staticmethod
    def logging(order: int = 60) -> LoggingMiddleware:
        """日志记录中间件"""
        from langgraph_agent_kit.middleware.base import MiddlewareConfig
        return LoggingMiddleware(MiddlewareConfig(order=order))


__all__ = [
    "SSEEventsMiddleware",
    "LoggingMiddleware",
    "Middlewares",
]
