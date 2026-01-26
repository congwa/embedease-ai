"""默认提示词定义

所有默认提示词集中定义在此模块，作为数据库无记录时的 fallback。
"""

from app.prompts.defaults.agent import AGENT_PROMPTS
from app.prompts.defaults.crawler import CRAWLER_PROMPTS
from app.prompts.defaults.memory import MEMORY_PROMPTS
from app.prompts.defaults.skill import SKILL_PROMPTS

# 合并所有默认提示词
DEFAULT_PROMPTS: dict[str, dict] = {
    **AGENT_PROMPTS,
    **MEMORY_PROMPTS,
    **SKILL_PROMPTS,
    **CRAWLER_PROMPTS,
}

__all__ = [
    "DEFAULT_PROMPTS",
    "AGENT_PROMPTS",
    "MEMORY_PROMPTS",
    "SKILL_PROMPTS",
    "CRAWLER_PROMPTS",
]
