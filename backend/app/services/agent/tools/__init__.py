"""Agent 工具模块

目录结构：
├── registry.py     # 工具注册表
├── product/        # 商品工具（搜索、详情、对比、筛选、分类等）
├── knowledge/      # 知识库工具（FAQ、KB）
└── common/         # 通用工具（引导）
"""

from app.services.agent.tools.product import search_products
from app.services.agent.tools.registry import get_tools, get_tools_for_agent

__all__ = [
    "get_tools",
    "get_tools_for_agent",
    "search_products",
]

# 配置：是否使用增强检索策略
USE_ENHANCED_RETRIEVAL = True
