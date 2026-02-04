"""工具注册表"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Any

if TYPE_CHECKING:
    from langgraph_agent_kit.tools.base import ToolSpec


class ToolRegistry:
    """工具注册表
    
    管理工具的注册和获取。
    """

    def __init__(self):
        self._tools: dict[str, "ToolSpec"] = {}

    def register(self, tool: "ToolSpec") -> None:
        """注册工具"""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """注销工具"""
        self._tools.pop(name, None)

    def get(self, name: str) -> "ToolSpec | None":
        """获取工具"""
        return self._tools.get(name)

    def get_all(self, enabled_only: bool = True) -> list["ToolSpec"]:
        """获取所有工具"""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.config.enabled]
        return tools

    def get_langchain_tools(self) -> list[Any]:
        """获取 LangChain 格式的工具列表"""
        from langchain_core.tools import StructuredTool
        
        result = []
        for tool in self.get_all():
            lc_tool = StructuredTool.from_function(
                func=tool.func,
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
            )
            result.append(lc_tool)
        return result

    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
