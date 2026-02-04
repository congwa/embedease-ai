"""框架集成模块"""

__all__ = [
    "create_sse_response",
]


def create_sse_response(*args, **kwargs):
    """创建 SSE 响应（需要安装 fastapi 可选依赖）"""
    from langgraph_agent_kit.integrations.fastapi import create_sse_response as _create
    return _create(*args, **kwargs)
