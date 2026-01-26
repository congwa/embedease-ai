"""默认提示词测试"""

import pytest

from app.prompts.defaults import (
    AGENT_PROMPTS,
    CRAWLER_PROMPTS,
    DEFAULT_PROMPTS,
    MEMORY_PROMPTS,
    SKILL_PROMPTS,
)
from app.prompts.registry import get_default_prompt_content


class TestDefaultPrompts:
    """测试默认提示词定义"""

    def test_all_prompts_loaded(self):
        """测试所有默认提示词被加载"""
        assert len(DEFAULT_PROMPTS) >= 10
        assert len(AGENT_PROMPTS) >= 5
        assert len(MEMORY_PROMPTS) >= 3
        assert len(SKILL_PROMPTS) >= 2
        assert len(CRAWLER_PROMPTS) >= 1

    def test_prompt_structure(self):
        """测试提示词结构正确"""
        required_fields = {"category", "name", "content"}

        for key, prompt in DEFAULT_PROMPTS.items():
            assert isinstance(prompt, dict), f"{key} 应该是字典"
            for field in required_fields:
                assert field in prompt, f"{key} 缺少 {field} 字段"
            assert isinstance(prompt["content"], str), f"{key}.content 应该是字符串"
            assert len(prompt["content"]) > 0, f"{key}.content 不应为空"

    def test_agent_prompts_keys(self):
        """测试 Agent 提示词包含必要的 key"""
        required_keys = [
            "agent.product",
            "agent.faq",
            "agent.kb",
            "agent.custom",
        ]
        for key in required_keys:
            assert key in AGENT_PROMPTS, f"缺少 {key}"

    def test_memory_prompts_keys(self):
        """测试记忆系统提示词包含必要的 key"""
        required_keys = [
            "memory.fact_extraction",
            "memory.action_decision",
            "memory.graph_extraction",
        ]
        for key in required_keys:
            assert key in MEMORY_PROMPTS, f"缺少 {key}"

    def test_skill_prompts_keys(self):
        """测试技能生成提示词包含必要的 key"""
        required_keys = [
            "skill.generate",
            "skill.refine",
        ]
        for key in required_keys:
            assert key in SKILL_PROMPTS, f"缺少 {key}"

    def test_get_default_prompt_content(self):
        """测试获取默认提示词内容"""
        content = get_default_prompt_content("agent.product")
        assert content is not None
        assert len(content) > 0
        assert "商品" in content or "推荐" in content

    def test_get_default_prompt_content_not_found(self):
        """测试获取不存在的提示词返回 None"""
        content = get_default_prompt_content("nonexistent.key")
        assert content is None

    def test_get_default_prompt_content_with_variables(self):
        """测试带变量的提示词格式化"""
        content = get_default_prompt_content(
            "skill.generate",
            description="测试描述",
            category="prompt",
            applicable_agents="all",
            examples="无",
        )
        assert content is not None
        assert "测试描述" in content

    def test_prompt_categories_valid(self):
        """测试所有提示词分类有效"""
        valid_categories = {"agent", "memory", "skill", "crawler"}
        for key, prompt in DEFAULT_PROMPTS.items():
            assert prompt["category"] in valid_categories, f"{key} 分类无效: {prompt['category']}"

    def test_prompt_variables_are_list(self):
        """测试提示词变量是列表"""
        for key, prompt in DEFAULT_PROMPTS.items():
            if "variables" in prompt:
                assert isinstance(prompt["variables"], list), f"{key}.variables 应该是列表"
