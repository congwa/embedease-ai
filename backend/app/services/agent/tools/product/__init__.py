"""商品相关工具

按功能分类：
- search: 商品搜索
- details: 商品详情
- compare: 商品对比
- filter_price: 价格筛选
- filter_attribute: 属性筛选
- categories: 分类列表
- category_overview: 分类概览
- by_category: 按分类查商品
- related_categories: 相关分类推荐
- similar: 相似商品
- featured: 精选商品
- purchase: 购买链接
"""

from app.services.agent.tools.product.by_category import list_products_by_category
from app.services.agent.tools.product.categories import list_all_categories
from app.services.agent.tools.product.category_overview import get_category_overview
from app.services.agent.tools.product.compare import compare_products
from app.services.agent.tools.product.details import get_product_details
from app.services.agent.tools.product.featured import list_featured_products
from app.services.agent.tools.product.filter_attribute import list_products_by_attribute
from app.services.agent.tools.product.filter_price import filter_by_price
from app.services.agent.tools.product.purchase import get_product_purchase_links
from app.services.agent.tools.product.related_categories import suggest_related_categories
from app.services.agent.tools.product.search import search_products
from app.services.agent.tools.product.similar import find_similar_products

__all__ = [
    "search_products",
    "get_product_details",
    "compare_products",
    "filter_by_price",
    "list_products_by_attribute",
    "list_all_categories",
    "get_category_overview",
    "list_products_by_category",
    "suggest_related_categories",
    "find_similar_products",
    "list_featured_products",
    "get_product_purchase_links",
]
