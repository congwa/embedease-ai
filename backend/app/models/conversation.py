"""会话模型"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.user import User


class HandoffState(StrEnum):
    """客服介入状态"""

    AI = "ai"  # AI 模式（默认）
    PENDING = "pending"  # 等待人工接入
    HUMAN = "human"  # 人工客服模式


class Conversation(Base):
    """会话表"""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), default="新对话", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ========== 客服介入相关字段 ==========
    handoff_state: Mapped[str] = mapped_column(
        String(20),
        default=HandoffState.AI.value,
        nullable=False,
        index=True,
    )
    handoff_operator: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    handoff_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    handoff_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    last_notification_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    # ========== 在线状态追踪 ==========
    user_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )  # 用户是否在线
    user_last_online_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )  # 用户最后在线时间
    agent_online: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )  # 客服是否在线
    agent_last_online_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )  # 客服最后在线时间
    current_agent_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # 当前在线的客服 ID

    # ========== 开场白相关 ==========
    greeting_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )  # 开场白是否已发送（用于 first_visit 触发策略）
    agent_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )  # 关联的 Agent ID

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
