"""Agent 工具集合

本模块包含所有可用的商品推荐工具。
每个工具都有独立的文件，包含其实现、结构化输出模型和文档。
"""

from app.services.agent.tools.search_products import search_products
from app.services.agent.tools.get_product_details import get_product_details
from app.services.agent.tools.compare_products import compare_products
from app.services.agent.tools.filter_by_price import filter_by_price
from app.services.agent.tools.guide_user import guide_user
from app.services.agent.tools.list_all_categories import list_all_categories
from app.services.agent.tools.get_category_overview import get_category_overview
from app.services.agent.tools.list_products_by_category import list_products_by_category
from app.services.agent.tools.find_similar_products import find_similar_products
from app.services.agent.tools.list_featured_products import list_featured_products
from app.services.agent.tools.list_products_by_attribute import list_products_by_attribute
from app.services.agent.tools.suggest_related_categories import suggest_related_categories
from app.services.agent.tools.get_product_purchase_links import get_product_purchase_links

__all__ = [
    "search_products",
    "get_product_details",
    "compare_products",
    "filter_by_price",
    "guide_user",
    "list_all_categories",
    "get_category_overview",
    "list_products_by_category",
    "find_similar_products",
    "list_featured_products",
    "list_products_by_attribute",
    "suggest_related_categories",
    "get_product_purchase_links",
]

# 配置：是否使用增强检索策略
USE_ENHANCED_RETRIEVAL = True
