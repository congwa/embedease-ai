"""日志中间件

负责记录每次 LLM 调用的完整输入输出。

注意：LLM 调用级别的 SSE 事件（`llm.call.start` / `llm.call.end`）由
`app.services.agent.middleware.llm_call_sse.SSEMiddleware` 负责发送；本中间件只做 logger
记录，不发送任何 SSE 事件。
"""

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import BaseMessage, get_buffer_string

from app.core.logging import get_logger

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
            item: dict[str, Any] = {}
            
            # 处理字典格式的 tool_call
            if isinstance(tc, dict):
                item["id"] = str(tc.get("id")) if tc.get("id") is not None else None
                item["name"] = str(tc.get("name")) if tc.get("name") is not None else None
                args = tc.get("args")
                if isinstance(args, dict):
                    item["args_keys"] = sorted(list(args.keys()))[:20]
                    # 添加 args 值的预览（截断长值，确保都是基本类型）
                    args_preview: dict[str, Any] = {}
                    for k, v in list(args.items())[:10]:
                        k_str = str(k)
                        if isinstance(v, str):
                            args_preview[k_str] = v[:100] + "..." if len(v) > 100 else v
                        elif isinstance(v, (int, float, bool)) or v is None:
                            args_preview[k_str] = v
                        elif isinstance(v, (list, tuple)):
                            args_preview[k_str] = f"[{len(v)} items]"
                        elif isinstance(v, dict):
                            args_preview[k_str] = f"{{dict with {len(v)} keys}}"
                        else:
                            args_preview[k_str] = str(type(v).__name__)
                    item["args_preview"] = args_preview
                else:
                    item["args_keys"] = None
                    item["args_preview"] = None
            # 处理 LangChain ToolCall 对象
            elif hasattr(tc, "id") or hasattr(tc, "name"):
                tc_id = getattr(tc, "id", None)
                tc_name = getattr(tc, "name", None)
                item["id"] = str(tc_id) if tc_id is not None else None
                item["name"] = str(tc_name) if tc_name is not None else None
                args = getattr(tc, "args", None)
                if isinstance(args, dict):
                    item["args_keys"] = sorted(list(args.keys()))[:20]
                    # 添加 args 值的预览（截断长值，确保都是基本类型）
                    args_preview: dict[str, Any] = {}
                    for k, v in list(args.items())[:10]:
                        k_str = str(k)
                        if isinstance(v, str):
                            args_preview[k_str] = v[:100] + "..." if len(v) > 100 else v
                        elif isinstance(v, (int, float, bool)) or v is None:
                            args_preview[k_str] = v
                        elif isinstance(v, (list, tuple)):
                            args_preview[k_str] = f"[{len(v)} items]"
                        elif isinstance(v, dict):
                            args_preview[k_str] = f"{{dict with {len(v)} keys}}"
                        else:
                            args_preview[k_str] = str(type(v).__name__)
                    item["args_preview"] = args_preview
                else:
                    item["args_keys"] = None
                    item["args_preview"] = None
            # 兜底：记录类型信息
            else:
                item["type"] = str(type(tc).__name__)
                # 尝试转换为字符串获取更多信息
                try:
                    tc_str = str(tc)
                    item["repr"] = tc_str[:200] + "..." if len(tc_str) > 200 else tc_str
                except Exception:
                    item["repr"] = None
            
            items.append(item)

        result = {
            "count": len(tool_calls),
            "items": items,
            "truncated": len(tool_calls) > 10,
        }
        return result

    # 兜底：只给类型信息
    return {"type": str(type(tool_calls).__name__)}


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


def _ensure_serializable(obj: Any, *, _max_depth: int = 10) -> Any:
    """确保对象可以被日志系统安全序列化，避免深层嵌套被截断。
    
    将嵌套结构转换为基本类型（str, int, float, bool, None, list, dict），
    确保日志系统能够正确显示内容。
    
    Args:
        obj: 要序列化的对象
        _max_depth: 最大递归深度，防止无限递归
    """
    if _max_depth <= 0:
        return "..."
    
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    if isinstance(obj, dict):
        # 对 tool_calls 字段进行特殊处理，确保 items 列表内容完整显示
        if "tool_calls" in obj:
            tool_calls = obj["tool_calls"]
            if isinstance(tool_calls, dict) and "items" in tool_calls:
                items = tool_calls["items"]
                if isinstance(items, list):
                    # 确保 items 列表中的每个元素都是完全序列化的
                    tool_calls["items"] = [
                        _ensure_serializable(item, _max_depth=_max_depth - 1)
                        for item in items
                    ]
        
        return {
            str(k): _ensure_serializable(v, _max_depth=_max_depth - 1)
            for k, v in obj.items()
        }
    
    if isinstance(obj, (list, tuple)):
        return [
            _ensure_serializable(v, _max_depth=_max_depth - 1)
            for v in obj
        ]
    
    # 其他类型转换为字符串
    return str(obj)


def _serialize_message(msg: BaseMessage) -> dict[str, Any]:
    """序列化消息用于日志"""
    content = getattr(msg, "content", None)
    content_text = content if isinstance(content, str) else str(content) if content is not None else ""
    additional = getattr(msg, "additional_kwargs", None)
    reasoning_text = ""
    if isinstance(additional, dict):
        rc = additional.get("reasoning_content")
        reasoning_text = rc if isinstance(rc, str) else str(rc) if rc is not None else ""
    
    # 序列化 tool_calls，确保它是完全可序列化的结构
    tool_calls_summary = _summarize_tool_calls(getattr(msg, "tool_calls", None))
    tool_calls_serialized = _ensure_serializable(tool_calls_summary) if tool_calls_summary else None
    
    return {
        "type": type(msg).__name__,
        "content": _truncate_text(getattr(msg, "content", None), limit=1200),
        "content_length": len(content_text) if content_text else 0,
        "tool_calls": tool_calls_serialized,
        # LangChain 常见字段：只保留摘要
        "usage": _summarize_usage_metadata(getattr(msg, "usage_metadata", None)),
        "response": _summarize_response_metadata(getattr(msg, "response_metadata", None)),
        "additional": _summarize_additional_kwargs(getattr(msg, "additional_kwargs", None)),
        "reasoning_length": len(reasoning_text) if reasoning_text else 0,
    }


def _serialize_messages(messages: list) -> list[dict[str, Any]]:
    """序列化消息列表"""
    return [_serialize_message(m) for m in messages if isinstance(m, BaseMessage)]


def _build_prompt_preview(messages: list[Any]) -> dict[str, Any]:
    """将最终送入 LLM 的 messages 转成便于观察的字符串预览（用于日志）。

    注意：真实请求给 provider 时通常是结构化 messages dict，而不是单一字符串。
    这里的字符串仅用于调试/观测：按 role 前缀拼接 message.text。
    """
    msg_objects = [m for m in messages if isinstance(m, BaseMessage)]
    prompt = get_buffer_string(msg_objects)
    return {
        "text_preview": _truncate_text(prompt, limit=5000),
        "text_length": len(prompt),
    }


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

    LLM 调用级别 SSE 事件发送不在这里处理，参见 `SSEMiddleware`。
    """

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """记录 LLM 调用的输入输出"""
        start_time = time.time()
        llm_call_id = uuid.uuid4().hex

        # LangChain 真正送入 model 的 messages = [system_message, *request.messages]
        effective_messages: list[Any] = list(request.messages)
        if request.system_message is not None:
            effective_messages = [request.system_message, *effective_messages]

        # 序列化输入
        request_data = {
            "llm_call_id": llm_call_id,
            # "model": _get_model_identity(request.model), # 无用 暂时不记录
            # "messages": _serialize_messages(effective_messages), # 无用 暂时不记录
            "message_count": len(effective_messages),
            "prompt": _build_prompt_preview(effective_messages),
            "additional_kwargs": _summarize_additional_kwargs(getattr(effective_messages, "additional_kwargs", None)),
            "tools": [_serialize_tool(t) for t in request.tools], # tools的完整信息
            "tools_types": [type(t).__name__ for t in request.tools], # tools的类型
            "tool_count": len(request.tools),
            "tool_choice": request.tool_choice, # 记录了模型选择的工具的配置
            # "response_format": _truncate_text(request.response_format, limit=200), # 无用 暂时不记录
            # "model_settings": request.model_settings, # 无用 暂时不记录
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

            # 在传递给日志系统之前，完全序列化 response_data，确保所有嵌套结构都是基本类型
            # 这样可以避免日志系统的 _safe_for_logging 因为嵌套层级过深而截断内容
            response_data_serialized = _ensure_serializable(response_data)

            logger.info("LLM 调用完成", llm_response=response_data_serialized)
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
