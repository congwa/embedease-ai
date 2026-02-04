"""FastAPI 集成"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from langgraph_agent_kit.streaming.sse import encode_sse

if TYPE_CHECKING:
    from langgraph_agent_kit.core.stream_event import StreamEvent


def create_sse_response(
    event_generator: AsyncGenerator["StreamEvent", None],
    *,
    media_type: str = "text/event-stream",
    headers: dict[str, str] | None = None,
) -> Any:
    """创建 FastAPI SSE 响应
    
    Args:
        event_generator: StreamEvent 异步生成器
        media_type: 响应媒体类型
        headers: 额外的响应头
    
    Returns:
        FastAPI StreamingResponse
    """
    try:
        from fastapi.responses import StreamingResponse
    except ImportError as e:
        raise ImportError(
            "FastAPI is required for create_sse_response. "
            "Install it with: pip install langgraph-agent-kit[fastapi]"
        ) from e

    async def sse_generator() -> AsyncGenerator[str, None]:
        async for event in event_generator:
            yield encode_sse(event)

    default_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    if headers:
        default_headers.update(headers)

    return StreamingResponse(
        sse_generator(),
        media_type=media_type,
        headers=default_headers,
    )
