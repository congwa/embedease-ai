"""工具基类定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel


class ToolConfig(BaseModel):
    """工具配置"""
    enabled: bool = True
    emit_events: bool = True
    timeout_seconds: float | None = None


@dataclass
class ToolSpec:
    """工具规格
    
    定义一个工具的元信息和处理函数。
    
    Attributes:
        name: 工具名称
        description: 工具描述
        func: 工具执行函数
        config: 工具配置
        args_schema: 参数 Schema（可选）
    """
    name: str
    description: str
    func: Callable[..., Any]
    config: ToolConfig = field(default_factory=ToolConfig)
    args_schema: type | None = None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """调用工具"""
        return self.func(*args, **kwargs)
