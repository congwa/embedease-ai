"""Skill 提示词集成测试

验证技能生成提示词在真实 AI 调用场景下的效果。
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
class TestSkillPromptsIntegration:
    """Skill 提示词集成测试"""

    async def test_skill_generate_returns_valid_json(
        self, llm_model, sample_skill_description
    ):
        """测试技能生成提示词返回有效 JSON"""
        system_prompt = get_default_prompt_content(
            "skill.generate",
            description=sample_skill_description,
            category="prompt",
            applicable_agents="product",
            examples="无",
        )

        user_message = "请根据上述描述生成技能定义"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        # 验证返回包含 JSON
        assert "{" in response and "}" in response

        try:
            # 提取 JSON 部分（可能包含 markdown 代码块）
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            result = json.loads(json_str)

            # 验证必需字段
            required_fields = [
                "name",
                "description",
                "category",
                "content",
                "trigger_keywords",
            ]
            for field in required_fields:
                assert field in result, f"缺少必需字段: {field}"

            # 验证 name 简洁
            assert len(result["name"]) <= 20

            # 验证 trigger_keywords 是列表
            assert isinstance(result["trigger_keywords"], list)
            assert len(result["trigger_keywords"]) >= 3

            # 验证 content 有实质内容
            assert len(result["content"]) > 20

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")

    async def test_skill_refine_improves_skill(self, llm_model):
        """测试技能优化提示词改进技能"""
        original_skill = {
            "name": "价格筛选",
            "description": "筛选价格",
            "category": "prompt",
            "content": "帮用户筛选价格",
            "trigger_keywords": ["价格", "多少钱"],
        }

        system_prompt = get_default_prompt_content(
            "skill.refine",
            skill_json=json.dumps(original_skill, ensure_ascii=False, indent=2),
            feedback="描述太简单，trigger_keywords 不够丰富，content 需要更详细的指导",
        )

        user_message = "请根据反馈优化技能"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        # 验证返回包含 JSON
        assert "{" in response and "}" in response

        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            result = json.loads(json_str)

            # 验证优化后内容更丰富
            assert len(result.get("description", "")) > len(original_skill["description"])
            assert len(result.get("trigger_keywords", [])) > len(
                original_skill["trigger_keywords"]
            )
            assert len(result.get("content", "")) > len(original_skill["content"])

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")

    async def test_skill_generate_with_examples(self, llm_model):
        """测试带示例的技能生成"""
        examples = """
用户: 500块以内有什么好的键盘？
助手: 让我帮您筛选500元以下的键盘...

用户: 推荐一些200-300价位的鼠标
助手: 这个价位有几款不错的鼠标...
"""

        system_prompt = get_default_prompt_content(
            "skill.generate",
            description="根据价格区间筛选商品",
            category="prompt",
            applicable_agents="product",
            examples=examples,
        )

        user_message = "请根据上述描述和示例生成技能定义"

        response = await invoke_llm(llm_model, system_prompt, user_message)

        assert "{" in response and "}" in response

        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]

            result = json.loads(json_str)

            # 验证 trigger_keywords 包含价格相关词
            keywords = " ".join(result.get("trigger_keywords", []))
            assert any(
                word in keywords for word in ["价格", "价位", "多少钱", "块", "元"]
            )

        except json.JSONDecodeError:
            pytest.fail(f"返回内容不是有效 JSON: {response}")
