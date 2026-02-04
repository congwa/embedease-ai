"""辅助工具函数 - 供工具和中间件使用"""

from __future__ import annotations

from typing import Any


def get_emitter_from_runtime(runtime: Any) -> Any | None:
    """从 ToolRuntime 获取 emitter（工具使用）
    
    Args:
        runtime: LangChain ToolRuntime 对象
        
    Returns:
        emitter 实例，如果不存在或无效则返回 None
    """
    context = getattr(runtime, "context", None)
    emitter = getattr(context, "emitter", None)
    return emitter if emitter and hasattr(emitter, "emit") else None


def get_emitter_from_request(request: Any) -> Any | None:
    """从 ModelRequest 获取 emitter（中间件使用）
    
    Args:
        request: LangChain ModelRequest 对象
        
    Returns:
        emitter 实例，如果不存在或无效则返回 None
    """
    runtime = getattr(request, "runtime", None)
    context = getattr(runtime, "context", None) if runtime else None
    emitter = getattr(context, "emitter", None)
    return emitter if emitter and hasattr(emitter, "emit") else None


def emit_tool_start(
    runtime: Any,
    tool_call_id: str,
    name: str,
    input: dict | None = None,
) -> None:
    """便捷方法：发射 tool.start 事件
    
    Args:
        runtime: ToolRuntime 对象
        tool_call_id: 工具调用 ID
        name: 工具名称
        input: 工具输入参数
    """
    emitter = get_emitter_from_runtime(runtime)
    if emitter:
        emitter.emit("tool.start", {
            "tool_call_id": tool_call_id,
            "name": name,
            "input": input or {},
        })


def emit_tool_end(
    runtime: Any,
    tool_call_id: str,
    name: str,
    status: str = "success",
    **kwargs: Any,
) -> None:
    """便捷方法：发射 tool.end 事件
    
    Args:
        runtime: ToolRuntime 对象
        tool_call_id: 工具调用 ID
        name: 工具名称
        status: 状态（success/error/empty）
        **kwargs: 额外字段（如 count, error, output_preview）
    """
    emitter = get_emitter_from_runtime(runtime)
    if emitter:
        emitter.emit("tool.end", {
            "tool_call_id": tool_call_id,
            "name": name,
            "status": status,
            **kwargs,
        })
