"""客诉问题单模型

本文件的业务职责是定义客诉系统的主业务对象 ComplaintTicket。
一张 ticket 表示用户当前正在处理或历史已经处理过的一个独立问题，
后续 task、review、handoff、patrol 都围绕它展开。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint_patrol_event import ComplaintPatrolEvent
    from app.models.complaint_review import ComplaintReview
    from app.models.complaint_task import ComplaintTask
    from app.models.conversation import Conversation
    from app.models.user import User


class ComplaintTicket(Base, TimestampMixin):
    """客诉问题单。

    这个模型表达一个独立客诉问题从创建、归并、返工、升级到关闭的完整生命周期。
    第一阶段的核心约束是：一个会话默认只有一张主活动问题单。
    """

    __tablename__ = "complaint_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    is_primary_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )  # 当前是否为会话主活动问题单
    parent_ticket_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )  # 若由旧问题拆分而来，记录源 ticket
    superseded_by_ticket_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )  # 若当前 ticket 被新 ticket 替代，记录替代者
    issue_fingerprint: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
    )  # 问题语义指纹，帮助后续归并判断
    primary_issue_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    secondary_issue_tags: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    secondary_issues: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    severity: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    priority_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )
    current_agent_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    current_task_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )  # 第一阶段先不强绑外键，避免循环依赖
    current_node_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    unresolved_turns: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    rework_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    handoff_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    handoff_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    handoff_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    resolved_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    slot_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )  # 已经收集到的业务槽位
    timeline: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
    )  # 业务关键动作时间线
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    resolved_at: Mapped["datetime | None"] = mapped_column(
        DateTime,
        nullable=True,
    )
    closed_at: Mapped["datetime | None"] = mapped_column(
        DateTime,
        nullable=True,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="tickets",
    )
    user: Mapped["User"] = relationship("User")
    tasks: Mapped[list["ComplaintTask"]] = relationship(
        "ComplaintTask",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="ComplaintTask.created_at",
    )
    reviews: Mapped[list["ComplaintReview"]] = relationship(
        "ComplaintReview",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="ComplaintReview.created_at",
    )
    patrol_events: Mapped[list["ComplaintPatrolEvent"]] = relationship(
        "ComplaintPatrolEvent",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="ComplaintPatrolEvent.created_at",
    )
