"""Agent 绩效快照模型

本文件的业务职责是为后续客诉运营统计预留绩效快照表，
让系统可以按时间窗口统计各岗位的通过率、返工率和转人工率。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentScoreSnapshot(Base):
    """Agent 绩效快照。

    Phase 1 先落表结构，Phase 3 再接入真实统计任务和报表能力。
    """

    __tablename__ = "agent_score_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_tag: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    window_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    window_start: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    window_end: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
    pass_rate: Mapped[float | None] = mapped_column(nullable=True)
    handoff_rate: Mapped[float | None] = mapped_column(nullable=True)
    avg_review_score: Mapped[float | None] = mapped_column(nullable=True)
    avg_resolution_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    rework_rate: Mapped[float | None] = mapped_column(nullable=True)
    violation_rate: Mapped[float | None] = mapped_column(nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )
