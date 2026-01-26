"""技能注册表

管理运行时技能的加载和匹配。
"""

import asyncio
from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.models.skill import Skill

logger = get_logger("skill.registry")


class SkillRegistry:
    """技能注册表 - 管理运行时技能加载"""

    _instance: "SkillRegistry | None" = None
    _skills: dict[str, "Skill"]
    _agent_skills: dict[str, list[str]]  # agent_id -> [skill_ids]
    _lock: asyncio.Lock | None

    def __new__(cls) -> "SkillRegistry":
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._skills = {}
            cls._instance._agent_skills = {}
            cls._instance._lock = asyncio.Lock()
        return cls._instance

    async def reload(self) -> None:
        """重新加载所有技能"""
        from app.core.database import get_db_context
        from app.services.skill.service import SkillService

        async with self._lock:
            async with get_db_context() as session:
                service = SkillService(session)
                result = await service.list_skills(is_active=True, page_size=1000)

                self._skills = {s.id: s for s in result.items}
                logger.info("重新加载技能", count=len(self._skills))

    def get_skill(self, skill_id: str) -> "Skill | None":
        """获取技能"""
        return self._skills.get(skill_id)

    def get_skill_by_name(self, name: str) -> "Skill | None":
        """根据名称获取技能"""
        for skill in self._skills.values():
            if skill.name == name:
                return skill
        return None

    def get_all_skills(self) -> list["Skill"]:
        """获取所有技能"""
        return list(self._skills.values())

    def get_skills_for_agent(
        self,
        agent_type: str,
        mode: str,
    ) -> list["Skill"]:
        """获取 Agent 可用的技能列表"""
        matched = []
        for skill in self._skills.values():
            # 检查适用范围
            if skill.applicable_agents and agent_type not in skill.applicable_agents:
                continue
            if skill.applicable_modes and mode not in skill.applicable_modes:
                continue
            matched.append(skill)
        return matched

    def get_always_apply_skills(
        self,
        agent_type: str,
        mode: str,
    ) -> list["Skill"]:
        """获取始终应用的技能"""
        matched = []
        for skill in self._skills.values():
            if not skill.always_apply:
                continue
            if skill.applicable_agents and agent_type not in skill.applicable_agents:
                continue
            if skill.applicable_modes and mode not in skill.applicable_modes:
                continue
            matched.append(skill)
        return matched

    def match_skills(
        self,
        agent_type: str,
        mode: str,
        message: str,
    ) -> list["Skill"]:
        """匹配适用的技能（基于关键词）"""
        matched = []
        message_lower = message.lower()

        for skill in self._skills.values():
            # 检查适用范围
            if skill.applicable_agents and agent_type not in skill.applicable_agents:
                continue
            if skill.applicable_modes and mode not in skill.applicable_modes:
                continue

            # always_apply 技能
            if skill.always_apply:
                matched.append(skill)
                continue

            # 关键词匹配
            if skill.trigger_keywords:
                if any(kw.lower() in message_lower for kw in skill.trigger_keywords):
                    matched.append(skill)

        return matched

    def build_skill_context(self, skills: list["Skill"]) -> str:
        """构建技能上下文（注入到 system prompt）"""
        if not skills:
            return ""

        parts = ["## 已加载技能"]
        for skill in skills:
            parts.append(f"\n### {skill.name}\n")
            parts.append(skill.content)

        return "\n".join(parts)

    def invalidate(self) -> None:
        """清除缓存"""
        self._skills = {}
        self._agent_skills = {}
        logger.info("技能缓存已清除")


# 全局单例
skill_registry = SkillRegistry()
