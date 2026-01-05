"""知识源服务

提供各类知识源的检索器工厂和实现。
"""

from app.services.knowledge.factory import create_retriever
from app.services.knowledge.faq_retriever import FAQRetriever
from app.services.knowledge.kb_retriever import KBRetriever

__all__ = [
    "FAQRetriever",
    "KBRetriever",
    "create_retriever",
]
