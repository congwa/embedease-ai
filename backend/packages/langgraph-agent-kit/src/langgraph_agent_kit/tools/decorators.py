"""工具装饰器"""

from __future__ import annotations

import functools
import time
import uuid
from typing import Any, Callable, TypeVar

from langgraph_agent_kit.core.events import StreamEventType
from langgraph_agent_kit.helpers import get_emitter_from_runtime

F = TypeVar("F", bound=Callable[..., Any])


def with_tool_events(
    tool_name: str | None = None,
    emit_input: bool = False,
) -> Callable[[F], F]:
    """工具事件装饰器
    
    自动在工具执行前后发射 tool.start / tool.end 事件。
    
    Args:
        tool_name: 工具名称（默认使用函数名）
        emit_input: 是否在 tool.start 中包含输入参数
    
    Usage:
        @with_tool_events()
        def my_tool(query: str, *, runtime: ToolRuntime) -> str:
            return f"Result for {query}"
    """
    def decorator(func: F) -> F:
        name = tool_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            runtime = kwargs.get("runtime")
            emitter = get_emitter_from_runtime(runtime) if runtime else None
            tool_call_id = f"tc_{uuid.uuid4().hex[:8]}"
            start_time = time.time()

            if emitter:
                payload: dict[str, Any] = {
                    "tool_call_id": tool_call_id,
                    "name": name,
                }
                if emit_input:
                    payload["input"] = {
                        k: v for k, v in kwargs.items()
                        if k != "runtime" and not k.startswith("_")
                    }
                emitter.emit(StreamEventType.TOOL_START.value, payload)

            try:
                result = await func(*args, **kwargs)
                
                if emitter:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    emitter.emit(
                        StreamEventType.TOOL_END.value,
                        {
                            "tool_call_id": tool_call_id,
                            "name": name,
                            "status": "success",
                            "elapsed_ms": elapsed_ms,
                        },
                    )
                return result

            except Exception as e:
                if emitter:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    emitter.emit(
                        StreamEventType.TOOL_END.value,
                        {
                            "tool_call_id": tool_call_id,
                            "name": name,
                            "status": "error",
                            "error": str(e),
                            "elapsed_ms": elapsed_ms,
                        },
                    )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            runtime = kwargs.get("runtime")
            emitter = get_emitter_from_runtime(runtime) if runtime else None
            tool_call_id = f"tc_{uuid.uuid4().hex[:8]}"
            start_time = time.time()

            if emitter:
                payload: dict[str, Any] = {
                    "tool_call_id": tool_call_id,
                    "name": name,
                }
                if emit_input:
                    payload["input"] = {
                        k: v for k, v in kwargs.items()
                        if k != "runtime" and not k.startswith("_")
                    }
                emitter.emit(StreamEventType.TOOL_START.value, payload)

            try:
                result = func(*args, **kwargs)
                
                if emitter:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    emitter.emit(
                        StreamEventType.TOOL_END.value,
                        {
                            "tool_call_id": tool_call_id,
                            "name": name,
                            "status": "success",
                            "elapsed_ms": elapsed_ms,
                        },
                    )
                return result

            except Exception as e:
                if emitter:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    emitter.emit(
                        StreamEventType.TOOL_END.value,
                        {
                            "tool_call_id": tool_call_id,
                            "name": name,
                            "status": "error",
                            "error": str(e),
                            "elapsed_ms": elapsed_ms,
                        },
                    )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator
