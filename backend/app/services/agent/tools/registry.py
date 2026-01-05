"""工具注册表 - 集中管理，支持按 Agent 配置/模式/类别过滤

使用方式：
    from app.services.agent.tools.registry import get_tools, get_tools_for_agent

    # 传统方式（兼容）
    tools = get_tools(mode="natural")

    # 基于 Agent 配置（推荐）
    from app.schemas.agent import AgentConfig
    tools = get_tools_for_agent(config)

扩展方式：
    在 _get_tool_specs() 中添加新的 ToolSpec 即可
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger

logger = get_logger("tools.registry")


@dataclass
class ToolSpec:
    """工具规格定义

    Attributes:
        name: 工具名称（用于日志和过滤）
        tool: 工具函数
        categories: 工具类别（用于按类别过滤）
        modes: 可用的聊天模式列表，None 表示所有模式可用
        enabled: 是否启用
    """

    name: str
    tool: Callable[..., Any]
    categories: list[str] = field(default_factory=list)
    modes: list[str] | None = None  # None = 所有模式可用
    enabled: bool = True


# ========== 工具列表（一目了然） ==========
#
# 名称                        │ 类别           │ 说明
# ────────────────────────────┼────────────────┼────────────────────
# search_products             │ search, core   │ 搜索商品
# get_product_details         │ query, core    │ 获取商品详情
# compare_products            │ compare        │ 对比商品
# filter_by_price             │ filter         │ 价格筛选
# guide_user                  │ guide          │ 引导用户
# list_all_categories         │ category       │ 列出所有类目
# get_category_overview       │ category       │ 类目概览
# list_products_by_category   │ category       │ 按类目列商品
# find_similar_products       │ search         │ 查找相似商品
# list_featured_products      │ featured       │ 精选商品
# list_products_by_attribute  │ filter         │ 按属性筛选
# suggest_related_categories  │ category       │ 推荐相关类目
# get_product_purchase_links  │ purchase       │ 获取购买链接
# ────────────────────────────┴────────────────┴────────────────────


def _get_tool_specs() -> list[ToolSpec]:
    """获取所有工具规格列表

    Returns:
        工具规格列表
    """
    # 商品工具
    from app.services.agent.tools.product.search import search_products
    from app.services.agent.tools.product.details import get_product_details
    from app.services.agent.tools.product.compare import compare_products
    from app.services.agent.tools.product.filter_price import filter_by_price
    from app.services.agent.tools.product.filter_attribute import list_products_by_attribute
    from app.services.agent.tools.product.categories import list_all_categories
    from app.services.agent.tools.product.category_overview import get_category_overview
    from app.services.agent.tools.product.by_category import list_products_by_category
    from app.services.agent.tools.product.related_categories import suggest_related_categories
    from app.services.agent.tools.product.similar import find_similar_products
    from app.services.agent.tools.product.featured import list_featured_products
    from app.services.agent.tools.product.purchase import get_product_purchase_links
    # 通用工具
    from app.services.agent.tools.common.guide import guide_user

    return [
        # 核心搜索工具
        ToolSpec(
            name="search_products",
            tool=search_products,
            categories=["search", "core"],
        ),
        ToolSpec(
            name="get_product_details",
            tool=get_product_details,
            categories=["query", "core"],
        ),
        # 对比工具
        ToolSpec(
            name="compare_products",
            tool=compare_products,
            categories=["compare"],
        ),
        # 筛选工具
        ToolSpec(
            name="filter_by_price",
            tool=filter_by_price,
            categories=["filter"],
        ),
        ToolSpec(
            name="list_products_by_attribute",
            tool=list_products_by_attribute,
            categories=["filter"],
        ),
        # 引导工具
        ToolSpec(
            name="guide_user",
            tool=guide_user,
            categories=["guide"],
        ),
        # 类目工具
        ToolSpec(
            name="list_all_categories",
            tool=list_all_categories,
            categories=["category"],
        ),
        ToolSpec(
            name="get_category_overview",
            tool=get_category_overview,
            categories=["category"],
        ),
        ToolSpec(
            name="list_products_by_category",
            tool=list_products_by_category,
            categories=["category"],
        ),
        ToolSpec(
            name="suggest_related_categories",
            tool=suggest_related_categories,
            categories=["category"],
        ),
        # 相似商品
        ToolSpec(
            name="find_similar_products",
            tool=find_similar_products,
            categories=["search"],
        ),
        # 精选商品
        ToolSpec(
            name="list_featured_products",
            tool=list_featured_products,
            categories=["featured"],
        ),
        # 购买链接
        ToolSpec(
            name="get_product_purchase_links",
            tool=get_product_purchase_links,
            categories=["purchase"],
        ),
    ]


def get_tools(
    mode: str = "natural",
    categories: list[str] | None = None,
    exclude_categories: list[str] | None = None,
) -> list[Callable[..., Any]]:
    """获取工具列表（对外接口）

    Args:
        mode: 聊天模式（natural/free/strict）
        categories: 只返回指定类别的工具（可选）
        exclude_categories: 排除指定类别的工具（可选）

    Returns:
        工具函数列表

    Examples:
        # 获取所有工具
        tools = get_tools()

        # 只获取搜索类工具
        tools = get_tools(categories=["search"])

        # 排除引导类工具
        tools = get_tools(exclude_categories=["guide"])
    """
    specs = _get_tool_specs()
    tools: list[Callable[..., Any]] = []

    for spec in specs:
        # 检查是否启用
        if not spec.enabled:
            continue

        # 模式过滤
        if spec.modes is not None and mode not in spec.modes:
            continue

        # 包含类别过滤
        if categories is not None:
            if not any(c in spec.categories for c in categories):
                continue

        # 排除类别过滤
        if exclude_categories is not None:
            if any(c in spec.categories for c in exclude_categories):
                continue

        tools.append(spec.tool)

    logger.debug(f"加载 {len(tools)} 个工具", mode=mode)
    return tools


def get_tool_names(mode: str = "natural") -> list[str]:
    """获取工具名称列表（用于日志/调试）

    Args:
        mode: 聊天模式

    Returns:
        工具名称列表
    """
    specs = _get_tool_specs()
    names: list[str] = []

    for spec in specs:
        if not spec.enabled:
            continue
        if spec.modes is not None and mode not in spec.modes:
            continue
        names.append(spec.name)

    return names


def get_tools_for_agent(config: "AgentConfig") -> list[Callable[..., Any]]:
    """根据 Agent 配置获取工具列表

    过滤流程：
    1. 全量工具 -> 按 tool_categories 过滤（如有）
    2. -> 按 tool_whitelist 过滤（如有）
    3. -> 按 mode 过滤
    4. -> 按 agent_type 注入专用工具（FAQ/KB）

    Args:
        config: Agent 运行时配置

    Returns:
        工具函数列表
    """

    specs = _get_tool_specs()
    tools: list[Callable[..., Any]] = []
    mode = config.mode

    for spec in specs:
        # 1. 检查是否启用
        if not spec.enabled:
            continue

        # 2. 模式过滤
        if spec.modes is not None and mode not in spec.modes:
            continue

        # 3. 工具类别过滤（如果配置了 tool_categories）
        if config.tool_categories:
            if not any(c in spec.categories for c in config.tool_categories):
                continue

        # 4. 工具白名单过滤（如果配置了 tool_whitelist）
        if config.tool_whitelist is not None:
            if spec.name not in config.tool_whitelist:
                continue

        tools.append(spec.tool)

    # 5. 按 Agent 类型注入专用工具
    type_specific_tools = _get_type_specific_tools(config.type, config)
    tools.extend(type_specific_tools)

    logger.debug(
        "为 Agent 加载工具",
        agent_id=config.agent_id,
        agent_type=config.type,
        mode=mode,
        tool_count=len(tools),
    )
    return tools


def _get_type_specific_tools(
    agent_type: str,
    config: "AgentConfig",
) -> list[Callable[..., Any]]:
    """获取 Agent 类型专用工具

    Args:
        agent_type: Agent 类型
        config: Agent 配置

    Returns:
        类型专用工具列表
    """
    tools: list[Callable[..., Any]] = []

    if agent_type == "faq":
        # FAQ 工具
        from app.services.agent.tools.knowledge.faq import create_faq_search_tool

        faq_tool = create_faq_search_tool(config)
        if faq_tool:
            tools.append(faq_tool)

    elif agent_type == "kb":
        # 知识库工具
        from app.services.agent.tools.knowledge.kb import create_kb_search_tool

        kb_tool = create_kb_search_tool(config)
        if kb_tool:
            tools.append(kb_tool)

    return tools


# 类型提示（避免循环导入）
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.agent import AgentConfig
