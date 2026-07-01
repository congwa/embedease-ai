"""数据访问层"""

from app.repositories.agent_score_snapshot import AgentScoreSnapshotRepository
from app.repositories.complaint_patrol_event import ComplaintPatrolEventRepository
from app.repositories.complaint_review import ComplaintReviewRepository
from app.repositories.complaint_task import ComplaintTaskRepository
from app.repositories.complaint_ticket import ComplaintTicketRepository
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
    "AgentScoreSnapshotRepository",
    "ComplaintPatrolEventRepository",
    "ComplaintReviewRepository",
    "ComplaintTaskRepository",
    "ComplaintTicketRepository",
    "ConversationRepository",
    "CrawlPageRepository",
    "CrawlSiteRepository",
    "CrawlTaskRepository",
    "MessageRepository",
    "ProductRepository",
    "UserRepository",
]
