"""技能注入器

在 Agent 构建和消息处理时注入技能。
"""

from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.services.skill.registry import SkillRegistry

if TYPE_CHECKING:
    from app.models.skill import Skill
    from app.services.streaming.emitter import DomainEmitter

logger = get_logger("skill.injector")


class SkillInjector:
    """技能注入器 - 在 Agent 构建和消息处理时注入技能"""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def inject_always_apply_skills(
        self,
        system_prompt: str,
        agent_type: str,
        mode: str,
    ) -> str:
        """注入 always_apply 技能到 system prompt（静默，无事件）

        Args:
            system_prompt: 原始系统提示词
            agent_type: Agent 类型
            mode: 回答模式

        Returns:
            注入技能后的系统提示词
        """
        skills = self.registry.get_always_apply_skills(agent_type, mode)
        if not skills:
            return system_prompt

        skill_context = self.registry.build_skill_context(skills)
        logger.debug(
            "注入 always_apply 技能",
            agent_type=agent_type,
            mode=mode,
            skill_count=len(skills),
            skill_names=[s.name for s in skills],
        )
        return f"{system_prompt}\n\n{skill_context}"

    async def match_and_activate_skills(
        self,
        message: str,
        agent_type: str,
        mode: str,
        emitter: "DomainEmitter",
    ) -> list["Skill"]:
        """匹配关键词并激活技能，发送事件

        Args:
            message: 用户消息
            agent_type: Agent 类型
            mode: 回答模式
            emitter: 事件发射器

        Returns:
            被激活的技能列表（不含 always_apply）
        """
        matched = self.registry.match_skills(agent_type, mode, message)

        # 过滤掉 always_apply（已静默注入）
        triggered = [s for s in matched if not s.always_apply]

        for skill in triggered:
            # 发送 skill.activated 事件
            await emitter.emit(
                "skill.activated",
                {
                    "skill_id": skill.id,
                    "skill_name": skill.name,
                    "trigger_type": "keyword",
                    "trigger_keyword": self._find_matched_keyword(message, skill),
                },
            )
            logger.info(
                "技能被激活",
                skill_id=skill.id,
                skill_name=skill.name,
                trigger_type="keyword",
            )

        return triggered

    def _find_matched_keyword(self, message: str, skill: "Skill") -> str | None:
        """找到匹配的关键词"""
        message_lower = message.lower()
        for kw in skill.trigger_keywords:
            if kw.lower() in message_lower:
                return kw
        return None

    def build_skill_context_for_message(
        self,
        skills: list["Skill"],
    ) -> str:
        """构建技能上下文（用于当前轮次注入）

        Args:
            skills: 技能列表

        Returns:
            技能上下文字符串
        """
        return self.registry.build_skill_context(skills)
