"""LLM 调用级别 SSE 事件中间件。

职责：
- 只负责把 LLM 调用开始/结束信号推送到前端（SSE）
- 不负责 logger 记录（logger 留给 LoggingMiddleware）

注意：历史文件名为 `sse_events.py`，为了兼容保留了同名模块作为转发入口。
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("middleware.sse")


def _get_emitter_from_request(request: ModelRequest) -> Any:
    """从 ModelRequest.runtime.context (ChatContext) 取 emitter。"""
    runtime = getattr(request, "runtime", None)
    chat_context = getattr(runtime, "context", None) if runtime is not None else None
    emitter = getattr(chat_context, "emitter", None)
    if emitter is not None and hasattr(emitter, "emit"):
        return emitter
    return None


def _emit(emitter: Any, event_type: StreamEventType, payload: dict[str, Any]) -> None:
    """向 orchestrator 的 domain queue 推送事件（最终会被编码成 SSE frame）。"""
    try:
        logger.debug(
            "SSE 事件发送",
            event_type=event_type.value,
            payload_keys=sorted(list(payload.keys()))[:50],
            llm_call_id=payload.get("llm_call_id"),
        )
        emitter.emit(event_type.value, payload)
    except Exception:
        # emitter 层面不应该影响业务路径
        return


class SSEMiddleware(AgentMiddleware):
    """LLM 调用事件中间件（SSE）。

    只负责发送：
    - llm.call.start
    - llm.call.end
    """

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        start_time = time.time()
        llm_call_id = uuid.uuid4().hex
        emitter = _get_emitter_from_request(request)

        if emitter:
            # LangChain 真正送入 model 的 messages = [system_message, *request.messages]
            effective_messages: list[Any] = list(request.messages)
            if request.system_message is not None:
                effective_messages = [request.system_message, *effective_messages]

            logger.debug(
                "llm.call.start",
                llm_call_id=llm_call_id,
                message_count=len(effective_messages),
            )
            _emit(
                emitter,
                StreamEventType.LLM_CALL_START,
                {
                    "llm_call_id": llm_call_id,
                    "message_count": len(effective_messages),
                },
            )

        try:
            response = await handler(request)
            elapsed_ms = int((time.time() - start_time) * 1000)
            if emitter:
                logger.debug(
                    "llm.call.end",
                    llm_call_id=llm_call_id,
                    elapsed_ms=elapsed_ms,
                    message_count=len(response.result),
                    has_error=False,
                )
                _emit(
                    emitter,
                    StreamEventType.LLM_CALL_END,
                    {
                        "llm_call_id": llm_call_id,
                        "elapsed_ms": elapsed_ms,
                        "message_count": len(response.result),
                    },
                )
            return response
        except Exception as exc:
            elapsed_ms = int((time.time() - start_time) * 1000)
            if emitter:
                logger.debug(
                    "llm.call.end",
                    llm_call_id=llm_call_id,
                    elapsed_ms=elapsed_ms,
                    has_error=True,
                    error_type=type(exc).__name__,
                )
                _emit(
                    emitter,
                    StreamEventType.LLM_CALL_END,
                    {
                        "llm_call_id": llm_call_id,
                        "elapsed_ms": elapsed_ms,
                        "error": str(exc),
                    },
                )
            raise
