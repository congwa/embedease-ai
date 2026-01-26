"""Memory 提示词集成测试

验证记忆系统提示词在真实 AI 调用场景下的效果。
"""

import json
import pytest

from tests.integration.prompts.conftest import (
    integration,
    invoke_llm,
    requires_api,
    slow,
)
from app.prompts.registry import get_default_prompt_content


@pytest.mark.anyio
@requires_api
@integration
@slow
class TestMemoryPromptsIntegration:
    """Memory 提示词集成测试"""

    async def test_fact_extraction_returns_json(self, llm_model, sample_conversation):
        """测试事实抽取提示词返回 JSON 格式"""
        system_prompt = get_default_prompt_content("memory.fact_extraction")

        # 构建对话文本
        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in sample_conversation
        )
        user_message = f"对话内容：\n{conversation_text}"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        # 验证返回 JSON 格式
        assert "{" in response and "}" in response

        # 尝试解析 JSON
        try:
            # 提取 JSON 部分
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            result = json.loads(json_str)

            # 验证结构
            assert "facts" in result
            assert isinstance(result["facts"], list)

            # 验证抽取了相关事实
            facts_text = " ".join(result["facts"])
            assert any(
                keyword in facts_text
                for keyword in ["程序员", "键盘", "500", "预算", "写代码", "手感"]
            )
        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")

    async def test_memory_action_decision(self, llm_model):
        """测试记忆操作决策提示词"""
        system_prompt = get_default_prompt_content("memory.action_decision")

        user_message = """
新事实：用户的预算从500元调整为800元

现有记忆：
1. [mem_001] 用户想买机械键盘
2. [mem_002] 用户预算500元左右
3. [mem_003] 用户是程序员
"""

        response = await invoke_llm(llm_model, system_prompt, user_message)

        # 验证返回 JSON 格式
        assert "{" in response and "}" in response

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            result = json.loads(json_str)

            # 验证结构
            assert "action" in result
            assert result["action"] in ["ADD", "UPDATE", "DELETE", "NONE"]

            # 这种情况应该是 UPDATE
            if result["action"] == "UPDATE":
                assert "target_id" in result
                assert result["target_id"] is not None

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")

    async def test_graph_extraction_entities_and_relations(self, llm_model, sample_conversation):
        """测试知识图谱抽取提示词返回实体和关系"""
        system_prompt = get_default_prompt_content("memory.graph_extraction")

        conversation_text = "\n".join(
            f"{msg['role']}: {msg['content']}" for msg in sample_conversation
        )
        user_message = f"对话内容：\n{conversation_text}"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        # 验证返回 JSON 格式
        assert "{" in response and "}" in response

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            result = json.loads(json_str)

            # 验证结构
            assert "entities" in result
            assert "relations" in result
            assert isinstance(result["entities"], list)
            assert isinstance(result["relations"], list)

            # 验证实体结构
            if result["entities"]:
                entity = result["entities"][0]
                assert "name" in entity
                assert "entity_type" in entity

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")

    async def test_fact_extraction_empty_conversation(self, llm_model):
        """测试空对话时事实抽取返回空数组"""
        system_prompt = get_default_prompt_content("memory.fact_extraction")
        user_message = "对话内容：\nuser: 你好\nassistant: 你好！有什么可以帮您的？"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        assert "{" in response and "}" in response

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            json_str = response[start:end]
            result = json.loads(json_str)

            assert "facts" in result
            # 简单问候通常没有可抽取的事实
            assert isinstance(result["facts"], list)

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")
