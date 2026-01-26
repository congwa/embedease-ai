"""AI 技能生成器

根据用户描述自动生成技能定义。
"""

import json

from app.core.llm import get_chat_model
from app.core.logging import get_logger
from app.prompts.registry import get_default_prompt_content
from app.schemas.skill import (
    SkillCategory,
    SkillCreate,
    SkillGenerateRequest,
    SkillGenerateResponse,
)

logger = get_logger("skill.generator")


# 从统一的 prompts 模块获取提示词模板
GENERATE_PROMPT = get_default_prompt_content("skill.generate") or ""
REFINE_PROMPT = get_default_prompt_content("skill.refine") or ""


class SkillGenerator:
    """AI 技能生成器"""

    def __init__(self):
        self.model = get_chat_model()

    async def generate(
        self,
        request: SkillGenerateRequest,
    ) -> SkillGenerateResponse:
        """根据描述生成技能"""
        # 构建提示词
        category_hint = request.category.value if request.category else "由AI判断"
        agents_hint = ", ".join(request.applicable_agents) if request.applicable_agents else "所有"
        examples_hint = "\n".join(request.examples) if request.examples else "无"

        prompt = GENERATE_PROMPT.format(
            description=request.description,
            category=category_hint,
            applicable_agents=agents_hint,
            examples=examples_hint,
        )

        try:
            response = await self.model.ainvoke(prompt)
            content = response.content

            # 解析 JSON
            skill_data = self._parse_json(content)

            # 构建 SkillCreate
            skill = SkillCreate(
                name=skill_data.get("name", "未命名技能"),
                description=skill_data.get("description", request.description),
                category=SkillCategory(skill_data.get("category", "prompt")),
                content=skill_data.get("content", ""),
                trigger_keywords=skill_data.get("trigger_keywords", []),
                trigger_intents=skill_data.get("trigger_intents", []),
                always_apply=skill_data.get("always_apply", False),
                applicable_agents=skill_data.get("applicable_agents", request.applicable_agents),
                applicable_modes=skill_data.get("applicable_modes", ["natural"]),
            )

            # 生成建议
            suggestions = self._generate_suggestions(skill)

            logger.info("AI 生成技能成功", name=skill.name)

            return SkillGenerateResponse(
                skill=skill,
                confidence=0.85,
                suggestions=suggestions,
            )

        except Exception as e:
            logger.error("AI 生成技能失败", error=str(e))
            raise ValueError(f"生成失败: {e}")

    async def refine(
        self,
        skill_data: dict,
        feedback: str,
    ) -> SkillGenerateResponse:
        """根据反馈优化技能"""
        prompt = REFINE_PROMPT.format(
            skill_json=json.dumps(skill_data, ensure_ascii=False, indent=2),
            feedback=feedback,
        )

        try:
            response = await self.model.ainvoke(prompt)
            content = response.content

            # 解析 JSON
            refined_data = self._parse_json(content)

            skill = SkillCreate(
                name=refined_data.get("name", skill_data.get("name", "")),
                description=refined_data.get("description", skill_data.get("description", "")),
                category=SkillCategory(refined_data.get("category", "prompt")),
                content=refined_data.get("content", skill_data.get("content", "")),
                trigger_keywords=refined_data.get("trigger_keywords", []),
                trigger_intents=refined_data.get("trigger_intents", []),
                always_apply=refined_data.get("always_apply", False),
                applicable_agents=refined_data.get("applicable_agents", []),
                applicable_modes=refined_data.get("applicable_modes", []),
            )

            suggestions = self._generate_suggestions(skill)

            logger.info("AI 优化技能成功", name=skill.name)

            return SkillGenerateResponse(
                skill=skill,
                confidence=0.9,
                suggestions=suggestions,
            )

        except Exception as e:
            logger.error("AI 优化技能失败", error=str(e))
            raise ValueError(f"优化失败: {e}")

    def _parse_json(self, content: str) -> dict:
        """解析 LLM 返回的 JSON"""
        # 尝试提取 JSON 块
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()

        # 清理可能的前后缀
        content = content.strip()
        if content.startswith("json"):
            content = content[4:].strip()

        return json.loads(content)

    def _generate_suggestions(self, skill: SkillCreate) -> list[str]:
        """生成改进建议"""
        suggestions = []

        if len(skill.trigger_keywords) < 3:
            suggestions.append("建议添加更多触发关键词以提高匹配率")

        if len(skill.content) < 100:
            suggestions.append("技能内容较短，建议添加更详细的指导规则")

        if not skill.applicable_agents:
            suggestions.append("建议指定适用的 Agent 类型")

        if not skill.applicable_modes:
            suggestions.append("建议指定适用的回答模式")

        if skill.always_apply and len(skill.content) > 500:
            suggestions.append("始终应用的技能内容较长，可能影响性能")

        return suggestions
