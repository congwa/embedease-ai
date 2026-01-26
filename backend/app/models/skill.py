"""技能数据模型

定义 Skill 和 AgentSkill 关联表。
"""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class SkillType(str, PyEnum):
    """技能类型"""

    SYSTEM = "system"  # 系统内置（不可修改/删除）
    USER = "user"  # 用户创建
    AI_GENERATED = "ai"  # AI 生成


class SkillCategory(str, PyEnum):
    """技能分类"""

    PROMPT = "prompt"  # 提示词增强
    RETRIEVAL = "retrieval"  # 检索增强
    TOOL = "tool"  # 工具扩展
    WORKFLOW = "workflow"  # 工作流


class Skill(Base, TimestampMixin):
    """技能模型"""

    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # 基础信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # 类型和分类
    type: Mapped[SkillType] = mapped_column(
        Enum(SkillType),
        default=SkillType.USER,
        nullable=False,
    )
    category: Mapped[SkillCategory] = mapped_column(
        Enum(SkillCategory),
        default=SkillCategory.PROMPT,
        nullable=False,
    )

    # 技能内容
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 触发配置
    trigger_keywords: Mapped[list] = mapped_column(JSON, default=list)
    trigger_intents: Mapped[list] = mapped_column(JSON, default=list)
    always_apply: Mapped[bool] = mapped_column(Boolean, default=False)

    # 适用范围
    applicable_agents: Mapped[list] = mapped_column(JSON, default=list)
    applicable_modes: Mapped[list] = mapped_column(JSON, default=list)

    # 元数据
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    author: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    # 关联
    agent_skills: Mapped[list["AgentSkill"]] = relationship(
        "AgentSkill",
        back_populates="skill",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Skill {self.name} ({self.type.value})>"


class AgentSkill(Base, TimestampMixin):
    """Agent-Skill 关联表"""

    __tablename__ = "agent_skills"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    agent_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("skills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 优先级（数值越小优先级越高）
    priority: Mapped[int] = mapped_column(Integer, default=100)

    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # 关联
    skill: Mapped["Skill"] = relationship("Skill", back_populates="agent_skills")

    def __repr__(self) -> str:
        return f"<AgentSkill agent={self.agent_id} skill={self.skill_id}>"
