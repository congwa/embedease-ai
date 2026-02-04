"""中间件基类定义"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

from pydantic import BaseModel


class MiddlewareConfig(BaseModel):
    """中间件配置基类"""
    enabled: bool = True
    order: int = 50


@dataclass
class MiddlewareSpec:
    """中间件规格
    
    定义一个中间件的元信息和处理函数。
    
    Attributes:
        name: 中间件名称
        order: 执行顺序（越小越先执行）
        enabled: 是否启用
        before_model: 模型调用前的处理函数
        after_model: 模型调用后的处理函数
        before_tool: 工具调用前的处理函数
        after_tool: 工具调用后的处理函数
    """
    name: str
    order: int = 50
    enabled: bool = True
    before_model: Callable[..., Any] | None = None
    after_model: Callable[..., Any] | None = None
    before_tool: Callable[..., Any] | None = None
    after_tool: Callable[..., Any] | None = None
    config: MiddlewareConfig | None = None


T = TypeVar("T", bound="BaseMiddleware")


class BaseMiddleware(ABC):
    """中间件基类
    
    提供中间件的基本接口和生命周期管理。
    """

    def __init__(self, config: MiddlewareConfig | None = None):
        self._config = config or MiddlewareConfig()

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def order(self) -> int:
        return self._config.order

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    async def before_model(self, request: Any, context: Any) -> Any:
        """模型调用前的处理"""
        return request

    async def after_model(self, response: Any, context: Any) -> Any:
        """模型调用后的处理"""
        return response

    async def before_tool(self, tool_call: Any, context: Any) -> Any:
        """工具调用前的处理"""
        return tool_call

    async def after_tool(self, tool_result: Any, context: Any) -> Any:
        """工具调用后的处理"""
        return tool_result

    def to_spec(self) -> MiddlewareSpec:
        """转换为 MiddlewareSpec"""
        return MiddlewareSpec(
            name=self.name,
            order=self.order,
            enabled=self.enabled,
            before_model=self.before_model,
            after_model=self.after_model,
            before_tool=self.before_tool,
            after_tool=self.after_tool,
            config=self._config,
        )
