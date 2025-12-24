"""数据访问层"""

from app.repositories.conversation import ConversationRepository
from app.repositories.crawler import (
    CrawlPageRepository,
    CrawlSiteRepository,
    CrawlTaskRepository,
)
from app.repositories.message import MessageRepository
from app.repositories.product import ProductRepository
from app.repositories.user import UserRepository

__all__ = [
    "ConversationRepository",
    "CrawlPageRepository",
    "CrawlSiteRepository",
    "CrawlTaskRepository",
    "MessageRepository",
    "ProductRepository",
    "UserRepository",
]
