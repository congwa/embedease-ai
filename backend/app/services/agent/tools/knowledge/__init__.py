"""知识库工具

- faq: FAQ 搜索工具
- kb: 知识库搜索工具
"""

from app.services.agent.tools.knowledge.faq import create_faq_search_tool
from app.services.agent.tools.knowledge.kb import create_kb_search_tool

__all__ = [
    "create_faq_search_tool",
    "create_kb_search_tool",
]
