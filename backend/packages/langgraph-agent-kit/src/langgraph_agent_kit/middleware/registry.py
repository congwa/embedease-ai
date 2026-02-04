"""中间件注册表"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langgraph_agent_kit.middleware.base import MiddlewareSpec, BaseMiddleware


class MiddlewareRegistry:
    """中间件注册表
    
    管理中间件的注册、排序和获取。
    """

    def __init__(self):
        self._middlewares: dict[str, "MiddlewareSpec"] = {}

    def register(self, middleware: "MiddlewareSpec | BaseMiddleware") -> None:
        """注册中间件"""
        from langgraph_agent_kit.middleware.base import BaseMiddleware
        
        if isinstance(middleware, BaseMiddleware):
            spec = middleware.to_spec()
        else:
            spec = middleware
        self._middlewares[spec.name] = spec

    def unregister(self, name: str) -> None:
        """注销中间件"""
        self._middlewares.pop(name, None)

    def get(self, name: str) -> "MiddlewareSpec | None":
        """获取中间件"""
        return self._middlewares.get(name)

    def get_all(self, enabled_only: bool = True) -> list["MiddlewareSpec"]:
        """获取所有中间件（按 order 排序）"""
        middlewares = list(self._middlewares.values())
        if enabled_only:
            middlewares = [m for m in middlewares if m.enabled]
        return sorted(middlewares, key=lambda m: m.order)

    def clear(self) -> None:
        """清空所有中间件"""
        self._middlewares.clear()

    def __len__(self) -> int:
        return len(self._middlewares)

    def __contains__(self, name: str) -> bool:
        return name in self._middlewares
