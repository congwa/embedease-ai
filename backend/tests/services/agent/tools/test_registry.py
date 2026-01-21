"""工具注册表测试"""

import pytest

from app.services.agent.tools.registry import (
    ToolSpec,
    _get_tool_specs,
    get_tools,
    get_tool_names,
)


class TestToolSpec:
    """测试 ToolSpec 数据类"""

    def test_default_values(self):
        """测试默认值"""
        spec = ToolSpec(name="test_tool", tool=lambda: None)
        assert spec.name == "test_tool"
        assert spec.categories == []
        assert spec.modes is None  # None 表示所有模式可用
        assert spec.enabled is True

    def test_custom_values(self):
        """测试自定义值"""
        spec = ToolSpec(
            name="search",
            tool=lambda: None,
            categories=["search", "core"],
            modes=["natural", "strict"],
            enabled=False,
        )
        assert spec.name == "search"
        assert spec.categories == ["search", "core"]
        assert spec.modes == ["natural", "strict"]
        assert spec.enabled is False

    def test_callable_tool(self):
        """测试工具是可调用的"""
        def my_tool(x: int) -> int:
            return x * 2

        spec = ToolSpec(name="my_tool", tool=my_tool)
        assert callable(spec.tool)
        assert spec.tool(5) == 10


class TestGetToolSpecs:
    """测试 _get_tool_specs 函数"""

    def test_returns_list(self):
        """测试返回列表"""
        specs = _get_tool_specs()
        assert isinstance(specs, list)

    def test_has_specs(self):
        """测试列表不为空"""
        specs = _get_tool_specs()
        assert len(specs) > 0

    def test_all_specs_are_toolspec(self):
        """测试所有元素都是 ToolSpec"""
        specs = _get_tool_specs()
        for spec in specs:
            assert isinstance(spec, ToolSpec)

    def test_core_tools_present(self):
        """测试核心工具存在"""
        specs = _get_tool_specs()
        names = [s.name for s in specs]
        assert "search_products" in names
        assert "get_product_details" in names

    def test_all_tools_have_names(self):
        """测试所有工具都有名称"""
        specs = _get_tool_specs()
        for spec in specs:
            assert spec.name
            assert len(spec.name) > 0

    def test_all_tools_have_invoke_method(self):
        """测试所有工具都有 invoke 方法（StructuredTool）"""
        specs = _get_tool_specs()
        for spec in specs:
            # StructuredTool 对象有 invoke 方法
            assert hasattr(spec.tool, "invoke") or callable(spec.tool)


class TestGetTools:
    """测试 get_tools 函数"""

    def test_returns_list(self):
        """测试返回列表"""
        tools = get_tools()
        assert isinstance(tools, list)

    def test_returns_tools_with_invoke(self):
        """测试返回的工具都有 invoke 方法"""
        tools = get_tools()
        for tool in tools:
            # StructuredTool 对象有 invoke 方法
            assert hasattr(tool, "invoke") or callable(tool)

    def test_natural_mode(self):
        """测试 natural 模式"""
        tools = get_tools(mode="natural")
        assert len(tools) > 0

    def test_free_mode(self):
        """测试 free 模式"""
        tools = get_tools(mode="free")
        assert isinstance(tools, list)

    def test_strict_mode(self):
        """测试 strict 模式"""
        tools = get_tools(mode="strict")
        assert isinstance(tools, list)

    def test_filter_by_categories_include(self):
        """测试按类别包含过滤"""
        tools = get_tools(categories=["search"])
        assert len(tools) > 0
        # 至少应该有 search_products

    def test_filter_by_categories_exclude(self):
        """测试按类别排除过滤"""
        all_tools = get_tools()
        filtered_tools = get_tools(exclude_categories=["guide"])
        # 排除后工具数量应该小于等于全部
        assert len(filtered_tools) <= len(all_tools)

    def test_filter_by_multiple_categories(self):
        """测试多类别过滤"""
        tools = get_tools(categories=["search", "query"])
        assert len(tools) > 0

    def test_empty_categories_filter(self):
        """测试空类别过滤"""
        tools = get_tools(categories=[])
        # 空类别应该返回空列表（没有工具匹配）
        assert len(tools) == 0


class TestGetToolNames:
    """测试 get_tool_names 函数"""

    def test_returns_list(self):
        """测试返回列表"""
        names = get_tool_names()
        assert isinstance(names, list)

    def test_returns_strings(self):
        """测试返回字符串列表"""
        names = get_tool_names()
        for name in names:
            assert isinstance(name, str)

    def test_has_names(self):
        """测试列表不为空"""
        names = get_tool_names()
        assert len(names) > 0

    def test_core_tool_names_present(self):
        """测试核心工具名称存在"""
        names = get_tool_names()
        assert "search_products" in names
        assert "get_product_details" in names

    def test_natural_mode(self):
        """测试 natural 模式"""
        names = get_tool_names(mode="natural")
        assert len(names) > 0

    def test_names_match_tools_count(self):
        """测试名称数量与工具数量一致"""
        names = get_tool_names(mode="natural")
        tools = get_tools(mode="natural")
        assert len(names) == len(tools)


class TestToolCategories:
    """测试工具类别"""

    def test_search_category(self):
        """测试 search 类别"""
        specs = _get_tool_specs()
        search_tools = [s for s in specs if "search" in s.categories]
        assert len(search_tools) > 0

    def test_core_category(self):
        """测试 core 类别"""
        specs = _get_tool_specs()
        core_tools = [s for s in specs if "core" in s.categories]
        assert len(core_tools) > 0

    def test_category_category(self):
        """测试 category 类别"""
        specs = _get_tool_specs()
        category_tools = [s for s in specs if "category" in s.categories]
        assert len(category_tools) > 0

    def test_filter_category(self):
        """测试 filter 类别"""
        specs = _get_tool_specs()
        filter_tools = [s for s in specs if "filter" in s.categories]
        assert len(filter_tools) > 0

    def test_guide_category(self):
        """测试 guide 类别"""
        specs = _get_tool_specs()
        guide_tools = [s for s in specs if "guide" in s.categories]
        assert len(guide_tools) > 0
