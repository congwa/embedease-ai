"""记忆系统 Prompt 模板

从 prompts 模块统一加载，保持向后兼容。
"""

from app.prompts.registry import get_default_prompt_content

# 从统一的 prompts 模块获取，保持向后兼容
FACT_EXTRACTION_PROMPT = get_default_prompt_content("memory.fact_extraction") or ""
MEMORY_ACTION_PROMPT = get_default_prompt_content("memory.action_decision") or ""
GRAPH_EXTRACTION_PROMPT = get_default_prompt_content("memory.graph_extraction") or ""
