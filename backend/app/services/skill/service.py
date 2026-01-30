"""技能管理服务

提供技能的 CRUD 操作和查询功能。
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.skill import AgentSkill, Skill, SkillCategory, SkillType
from app.schemas.skill import (
    AgentSkillConfig,
    AgentSkillRead,
    SkillCreate,
    SkillListResponse,
    SkillRead,
    SkillUpdate,
)

logger = get_logger("skill.service")


class SkillService:
    """技能管理服务"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========== CRUD ==========

    async def create_skill(
        self,
        data: SkillCreate,
        skill_type: SkillType = SkillType.USER,
        author: str | None = None,
        is_system: bool = False,
    ) -> Skill:
        """创建技能"""
        skill = Skill(
            name=data.name,
            description=data.description,
            type=skill_type,
            category=SkillCategory(data.category.value),
            content=data.content,
            trigger_keywords=data.trigger_keywords,
            trigger_intents=data.trigger_intents,
            always_apply=data.always_apply,
            applicable_agents=data.applicable_agents,
            author=author,
            is_system=is_system,
        )
        self.session.add(skill)
        await self.session.flush()
        await self.session.refresh(skill)

        logger.info("创建技能", skill_id=skill.id, name=skill.name, type=skill_type.value)
        return skill

    async def get_skill(self, skill_id: str) -> Skill | None:
        """获取技能"""
        stmt = select(Skill).where(Skill.id == skill_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_skill_by_name(self, name: str) -> Skill | None:
        """根据名称获取技能"""
        stmt = select(Skill).where(Skill.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_skills(
        self,
        skill_type: SkillType | None = None,
        category: SkillCategory | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SkillListResponse:
        """列出技能"""
        # 构建查询条件
        conditions = []
        if skill_type is not None:
            conditions.append(Skill.type == skill_type)
        if category is not None:
            conditions.append(Skill.category == category)
        if is_active is not None:
            conditions.append(Skill.is_active == is_active)

        # 查询总数
        count_stmt = select(func.count(Skill.id))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar() or 0

        # 查询数据
        stmt = select(Skill).order_by(Skill.is_system.desc(), Skill.created_at.desc())
        if conditions:
            stmt = stmt.where(*conditions)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        skills = result.scalars().all()

        return SkillListResponse(
            items=[SkillRead.model_validate(s) for s in skills],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_skill(self, skill_id: str, data: SkillUpdate) -> Skill | None:
        """更新技能（系统技能不可更新）"""
        skill = await self.get_skill(skill_id)
        if not skill:
            return None

        if skill.is_system:
            raise ValueError("系统内置技能不可修改")

        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(skill, key):
                setattr(skill, key, value)

        await self.session.flush()
        await self.session.refresh(skill)

        logger.info("更新技能", skill_id=skill_id)
        return skill

    async def delete_skill(self, skill_id: str) -> bool:
        """删除技能（系统技能不可删除）"""
        skill = await self.get_skill(skill_id)
        if not skill:
            return False

        if skill.is_system:
            raise ValueError("系统内置技能不可删除")

        await self.session.delete(skill)
        await self.session.flush()

        logger.info("删除技能", skill_id=skill_id)
        return True

    # ========== Agent 关联 ==========

    async def get_skills_for_agent(
        self,
        agent_id: str,
        include_disabled: bool = False,
    ) -> list[AgentSkillRead]:
        """获取 Agent 的技能列表"""
        stmt = (
            select(AgentSkill)
            .options(selectinload(AgentSkill.skill))
            .where(AgentSkill.agent_id == agent_id)
            .order_by(AgentSkill.priority)
        )

        if not include_disabled:
            stmt = stmt.where(AgentSkill.is_enabled == True)  # noqa: E712

        result = await self.session.execute(stmt)
        agent_skills = result.scalars().all()

        return [
            AgentSkillRead(
                skill_id=as_.skill_id,
                skill_name=as_.skill.name,
                skill_description=as_.skill.description,
                priority=as_.priority,
                is_enabled=as_.is_enabled,
            )
            for as_ in agent_skills
            if as_.skill and as_.skill.is_active
        ]

    async def update_agent_skills(
        self,
        agent_id: str,
        skills: list[AgentSkillConfig],
    ) -> None:
        """更新 Agent 的技能配置"""
        # 删除现有关联
        stmt = select(AgentSkill).where(AgentSkill.agent_id == agent_id)
        result = await self.session.execute(stmt)
        existing = result.scalars().all()
        for as_ in existing:
            await self.session.delete(as_)

        # 创建新关联
        for config in skills:
            agent_skill = AgentSkill(
                agent_id=agent_id,
                skill_id=config.skill_id,
                priority=config.priority,
                is_enabled=config.is_enabled,
            )
            self.session.add(agent_skill)

        await self.session.flush()
        logger.info("更新 Agent 技能配置", agent_id=agent_id, skill_count=len(skills))

    # ========== 技能匹配 ==========

    async def get_applicable_skills(
        self,
        agent_type: str,
        message: str | None = None,
    ) -> list[Skill]:
        """获取适用的技能

        根据 agent_type 和用户消息匹配：
        1. always_apply=True 的技能
        2. 关键词匹配的技能
        3. 意图匹配的技能
        """
        # 查询所有活跃技能
        stmt = select(Skill).where(Skill.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        all_skills = result.scalars().all()

        matched_skills = []
        for skill in all_skills:
            # 检查适用范围
            if skill.applicable_agents and agent_type not in skill.applicable_agents:
                continue

            # always_apply 技能
            if skill.always_apply:
                matched_skills.append(skill)
                continue

            # 关键词匹配
            if message and skill.trigger_keywords:
                message_lower = message.lower()
                if any(kw.lower() in message_lower for kw in skill.trigger_keywords):
                    matched_skills.append(skill)
                    continue

        return matched_skills

    async def get_always_apply_skills(
        self,
        agent_type: str,
    ) -> list[Skill]:
        """获取始终应用的技能"""
        stmt = select(Skill).where(
            Skill.is_active == True,  # noqa: E712
            Skill.always_apply == True,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        all_skills = result.scalars().all()

        matched_skills = []
        for skill in all_skills:
            if skill.applicable_agents and agent_type not in skill.applicable_agents:
                continue
            matched_skills.append(skill)

        return matched_skills

    # ========== 系统技能 ==========

    async def get_system_skills(self) -> list[Skill]:
        """获取所有系统技能"""
        stmt = select(Skill).where(Skill.is_system == True)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def init_system_skills(self, skills_data: list[dict]) -> int:
        """初始化系统内置技能

        Args:
            skills_data: 技能数据列表

        Returns:
            新增的技能数量
        """
        created_count = 0
        for data in skills_data:
            # 检查是否已存在
            existing = await self.get_skill_by_name(data["name"])
            if existing:
                continue

            skill = Skill(
                name=data["name"],
                description=data["description"],
                type=SkillType.SYSTEM,
                category=SkillCategory(data.get("category", "prompt")),
                content=data["content"],
                trigger_keywords=data.get("trigger_keywords", []),
                trigger_intents=data.get("trigger_intents", []),
                always_apply=data.get("always_apply", False),
                applicable_agents=data.get("applicable_agents", []),
                is_system=True,
                is_active=True,
            )
            self.session.add(skill)
            created_count += 1

        await self.session.flush()
        logger.info("初始化系统技能", created=created_count, total=len(skills_data))
        return created_count
