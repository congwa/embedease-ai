"""提示词数据模型

存储用户自定义的提示词，覆盖默认值。
"""

from enum import Enum as PyEnum

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PromptCategory(str, PyEnum):
    """提示词分类"""

    AGENT = "agent"  # Agent 系统提示词
    MEMORY = "memory"  # 记忆系统提示词
    SKILL = "skill"  # 技能生成提示词
    CRAWLER = "crawler"  # 爬虫提取提示词


class Prompt(Base, TimestampMixin):
    """提示词模型

    存储用户自定义的提示词。
    key 对应 defaults 中的 key，如 "agent.product"。
    """

    __tablename__ = "prompts"

    # 主键：提示词唯一标识
    key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="提示词唯一标识，如 agent.product",
    )

    # 分类
    category: Mapped[PromptCategory] = mapped_column(
        Enum(PromptCategory),
        nullable=False,
        index=True,
        comment="提示词分类",
    )

    # 显示名称
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="显示名称",
    )

    # 描述
    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="提示词说明",
    )

    # 提示词内容
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="提示词内容",
    )

    # 支持的变量列表
    variables: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="支持的模板变量",
    )

    # 是否启用
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="是否启用",
    )

    def __repr__(self) -> str:
        return f"<Prompt {self.key}>"
