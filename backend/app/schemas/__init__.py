"""Pydantic 模型"""

from app.schemas.chat import ChatEvent, ChatRequest
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    MessageResponse,
)
from app.schemas.crawler import (
    CrawlPageResponse,
    CrawlSiteCreate,
    CrawlSiteResponse,
    CrawlSiteStatus,
    CrawlSiteUpdate,
    CrawlStats,
    CrawlTaskCreate,
    CrawlTaskResponse,
    CrawlTaskStatus,
    ExtractionConfig,
    ExtractionMode,
    FieldExtractionConfig,
    ParsedProductData,
)
from app.schemas.product import (
    ProductCreate,
    ProductResponse,
    ProductSearchResult,
)

__all__ = [
    "ChatRequest",
    "ChatEvent",
    "ConversationCreate",
    "ConversationResponse",
    "ConversationWithMessages",
    "MessageResponse",
    "ProductCreate",
    "ProductResponse",
    "ProductSearchResult",
    "CrawlSiteStatus",
    "CrawlTaskStatus",
    "ExtractionMode",
    "FieldExtractionConfig",
    "ExtractionConfig",
    "ParsedProductData",
    "CrawlSiteCreate",
    "CrawlSiteUpdate",
    "CrawlSiteResponse",
    "CrawlTaskCreate",
    "CrawlTaskResponse",
    "CrawlPageResponse",
    "CrawlStats",
]
