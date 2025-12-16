"""日志中间件

负责记录每次 LLM 调用的完整输入输出。
这是最外层的中间件，包裹所有其他中间件。
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import BaseMessage

from app.core.logging import get_logger
from app.schemas.events import StreamEventType

logger = get_logger("middleware.llm")


def _truncate_text(value: Any, *, limit: int = 500) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def _summarize_tool_calls(tool_calls: Any) -> dict[str, Any] | None:
    """将 tool_calls 压缩成可读摘要，避免在日志里展开巨大 args。"""
    if not tool_calls:
        return None

    if isinstance(tool_calls, list):
        items: list[dict[str, Any]] = []
        for tc in tool_calls[:10]:
            if isinstance(tc, dict):
                args = tc.get("args")
                items.append(
                    {
                        "id": tc.get("id"),
                        "name": tc.get("name"),
                        "args_keys": sorted(list(args.keys()))[:20] if isinstance(args, dict) else None,
                    }
                )
            else:
                items.append({"type": type(tc).__name__})

        return {
            "count": len(tool_calls),
            "items": items,
            "truncated": len(tool_calls) > 10,
        }

    # 兜底：只给类型信息
    return {"type": type(tool_calls).__name__}


def _summarize_usage_metadata(usage: Any) -> dict[str, Any] | None:
    """只保留 token 统计，丢弃 *_token_details 等大字段。"""
    if not isinstance(usage, dict):
        return None
    return {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def _summarize_response_metadata(meta: Any) -> dict[str, Any] | None:
    """只保留稳定且高价值的响应元信息。"""
    if not isinstance(meta, dict):
        return None
    return {
        "finish_reason": meta.get("finish_reason"),
        "model_name": meta.get("model_name"),
        "model_provider": meta.get("model_provider"),
    }


def _summarize_additional_kwargs(kwargs: Any) -> dict[str, Any] | None:
    """只保留 keys + reasoning_content 截断预览，避免日志爆炸。"""
    if not isinstance(kwargs, dict):
        return None
    reasoning = kwargs.get("reasoning_content")
    return {
        "keys": sorted(list(kwargs.keys()))[:50],
        "reasoning_preview": _truncate_text(reasoning, limit=800) if reasoning else None,
    }


def _serialize_message(msg: BaseMessage) -> dict[str, Any]:
    """序列化消息用于日志"""
    return {
        "type": type(msg).__name__,
        "content": _truncate_text(getattr(msg, "content", None), limit=1200),
        "tool_calls": _summarize_tool_calls(getattr(msg, "tool_calls", None)),
        # LangChain 常见字段：只保留摘要
        "usage": _summarize_usage_metadata(getattr(msg, "usage_metadata", None)),
        "response": _summarize_response_metadata(getattr(msg, "response_metadata", None)),
        "additional": _summarize_additional_kwargs(getattr(msg, "additional_kwargs", None)),
    }


def _serialize_messages(messages: list) -> list[dict[str, Any]]:
    """序列化消息列表"""
    return [_serialize_message(m) for m in messages if isinstance(m, BaseMessage)]


def _serialize_tool(tool: Any) -> dict[str, Any]:
    """序列化工具信息（BaseTool 或 provider dict tool）。"""
    if isinstance(tool, dict):
        # provider tools: dict 格式，尽量保留识别字段但避免巨大 payload
        name = tool.get("name") or tool.get("function", {}).get("name") or tool.get("id")
        return {
            "type": "provider_dict",
            "name": name,
            "keys": sorted(list(tool.keys()))[:50],
        }
    return {
        "type": type(tool).__name__,
        "name": getattr(tool, "name", None),
        "description": _truncate_text(getattr(tool, "description", None), limit=200),
    }


def _get_model_identity(model: Any) -> dict[str, Any]:
    return {
        "type": type(model).__name__,
        "model": getattr(model, "model", None),
        "model_name": getattr(model, "model_name", None),
        "model_id": getattr(model, "model_id", None),
    }


def _get_emitter_from_request(request: ModelRequest) -> Any:
    """从 ModelRequest.runtime.context (ChatContext) 取 emitter。"""
    runtime = getattr(request, "runtime", None)
    chat_context = getattr(runtime, "context", None) if runtime is not None else None
    emitter = getattr(chat_context, "emitter", None)
    if emitter is not None and hasattr(emitter, "emit"):
        return emitter
    return None


def _emit(emitter: Any, event_type: StreamEventType, payload: dict[str, Any]) -> None:
    try:
        emitter.emit(event_type.value, payload)
    except Exception:
        # emitter 层面不应该影响业务路径
        return


class LoggingMiddleware(AgentMiddleware):
    """日志中间件

    记录每次 LLM 调用的：
    - 系统提示词
    - 输入消息
    - 工具列表
    - 响应格式
    - 输出消息
    - 结构化响应
    - 调用耗时
    """

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """记录 LLM 调用的输入输出"""
        start_time = time.time()
        llm_call_id = uuid.uuid4().hex
        emitter = _get_emitter_from_request(request)

        # LangChain 真正送入 model 的 messages = [system_message, *request.messages]
        effective_messages: list[Any] = list(request.messages)
        if request.system_message is not None:
            effective_messages = [request.system_message, *effective_messages]

        if emitter:
            _emit(
                emitter,
                StreamEventType.LLM_CALL_START,
                {
                    "llm_call_id": llm_call_id,
                    "message_count": len(effective_messages),
                },
            )

        # 序列化输入
        request_data = {
            "llm_call_id": llm_call_id,
            "model": _get_model_identity(request.model),
            "messages": _serialize_messages(effective_messages),
            "message_count": len(effective_messages),
            "tools": [_serialize_tool(t) for t in request.tools],
            "tool_count": len(request.tools),
            "tool_choice": request.tool_choice,
            "response_format": _truncate_text(request.response_format, limit=200),
            "model_settings": request.model_settings,
        }

        logger.info("LLM 调用开始", llm_request=request_data)

        try:
            response = await handler(request)
            elapsed_ms = int((time.time() - start_time) * 1000)

            # 序列化输出
            response_data = {
                "llm_call_id": llm_call_id,
                "messages": _serialize_messages(response.result),
                "message_count": len(response.result),
                "has_structured_response": response.structured_response is not None,
                "structured_response": (
                    self._serialize_structured(response.structured_response)
                    if response.structured_response
                    else None
                ),
                "elapsed_ms": elapsed_ms,
            }

            logger.info("LLM 调用完成", llm_response=response_data)
            if emitter:
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

        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "LLM 调用失败",
                llm_call_id=llm_call_id,
                error=str(e),
                error_type=type(e).__name__,
                elapsed_ms=elapsed_ms,
                exc_info=True,
            )
            if emitter:
                _emit(
                    emitter,
                    StreamEventType.LLM_CALL_END,
                    {
                        "llm_call_id": llm_call_id,
                        "elapsed_ms": elapsed_ms,
                        "error": str(e),
                    },
                )
            raise

    def _serialize_structured(self, obj: Any) -> dict[str, Any] | str:
        """序列化结构化响应"""
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
            # 截断长文本
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 500:
                    data[key] = value[:500] + "..."
            return data
        return str(obj)[:500]
