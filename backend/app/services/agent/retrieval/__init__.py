"""Agent 检索模块

提供各类检索器实现：
- product: 商品向量检索
- enhanced: 增强检索（向量 + 关键词 + 重排序）
"""

from app.services.agent.retrieval.product import (
    get_qdrant_client,
    get_retriever,
    get_vector_store,
)

__all__ = [
    "get_qdrant_client",
    "get_retriever",
    "get_vector_store",
]
