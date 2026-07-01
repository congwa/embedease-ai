"""客诉巡查事件模型

本文件的业务职责是为后续巡查、自愈和阻塞恢复保留业务事件记录表，
让系统能够解释某张问题单为什么被自动恢复、升级或忽略。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint_ticket import ComplaintTicket


class ComplaintPatrolEvent(Base, TimestampMixin):
    """客诉巡查事件。

    Phase 1 先落模型，Phase 2 再接入真实巡查任务和自动恢复逻辑。
    """

    __tablename__ = "complaint_patrol_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("complaint_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    detected_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    action_taken: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    ticket: Mapped["ComplaintTicket"] = relationship(
        "ComplaintTicket",
        back_populates="patrol_events",
    )
