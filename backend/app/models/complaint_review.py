"""客诉审查模型

本文件的业务职责是记录 reviewer 对执行结果的业务审查，
确保低质量、越权或高风险的回复不会直接发给用户。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.complaint_task import ComplaintTask
    from app.models.complaint_ticket import ComplaintTicket


class ComplaintReview(Base, TimestampMixin):
    """客诉审查记录。

    一条 review 记录描述某次任务结果是通过、驳回还是直接升级人工，
    也是工作台解释“为什么 AI 没有直接回复用户”的关键依据。
    """

    __tablename__ = "complaint_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("complaint_tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("complaint_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_agent_tag: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    risk_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    reasons: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    suggested_next_agent: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    review_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    ticket: Mapped["ComplaintTicket"] = relationship(
        "ComplaintTicket",
        back_populates="reviews",
    )
    task: Mapped["ComplaintTask"] = relationship(
        "ComplaintTask",
        back_populates="reviews",
    )
