"""Agent 工具集合

本模块包含所有可用的商品推荐工具。
每个工具都有独立的文件，包含其实现、结构化输出模型和文档。
"""

from app.services.agent.tools.search_products import search_products
from app.services.agent.tools.get_product_details import get_product_details
from app.services.agent.tools.compare_products import compare_products
from app.services.agent.tools.filter_by_price import filter_by_price
from app.services.agent.tools.guide_user import guide_user

__all__ = [
    "search_products",
    "get_product_details",
    "compare_products",
    "filter_by_price",
    "guide_user",
]

# 配置：是否使用增强检索策略
USE_ENHANCED_RETRIEVAL = True
