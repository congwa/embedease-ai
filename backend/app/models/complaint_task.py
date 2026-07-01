"""客诉任务模型

本文件的业务职责是定义问题单处理过程中的可执行任务，
例如 triage、plan、emotion、faq、review 等业务动作。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint_review import ComplaintReview
    from app.models.complaint_ticket import ComplaintTicket


class ComplaintTask(Base, TimestampMixin):
    """客诉处理任务。

    一条任务记录当前主问题单在某一阶段由哪个岗位执行了什么工作，
    便于后续 review、handoff 和工作台追踪。
    """

    __tablename__ = "complaint_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("complaint_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    agent_tag: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    goal: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    success_criteria: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    input_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    output_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    review_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    ticket: Mapped["ComplaintTicket"] = relationship(
        "ComplaintTicket",
        back_populates="tasks",
    )
    reviews: Mapped[list["ComplaintReview"]] = relationship(
        "ComplaintReview",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="ComplaintReview.created_at",
    )
