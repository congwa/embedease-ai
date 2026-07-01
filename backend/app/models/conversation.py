"""会话模型

本文件的业务职责是承载用户会话的当前服务快照。
在客诉系统中，Conversation 不再只表示消息容器，还负责表达当前主问题单、
当前服务模式、当前责任岗位和当前风险快照，方便聊天页和客服工作台快速读取。
"""

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.complaint_ticket import ComplaintTicket
    from app.models.message import Message
    from app.models.user import User


class HandoffState(StrEnum):
    """客服介入状态"""

    AI = "ai"  # AI 模式（默认）
    PENDING = "pending"  # 等待人工接入
    HUMAN = "human"  # 人工客服模式


class ConversationMode(StrEnum):
    """会话服务模式。

    这个枚举表达当前会话是由 AI 处理、等待人工、人工处理中还是已经关闭。
    它服务于客诉系统的对话通道层，而不是 ticket 处理明细。
    """

    AI = "ai"
    PENDING = "pending"
    HUMAN = "human"
    CLOSED = "closed"


class Conversation(Base):
    """会话表。

    这个模型保存会话层的当前快照，重点回答“当前这个会话正在处理哪一张主问题单、
    当前由谁处理、风险如何、是否正在等待人工”。
    """

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

    # ========== 客诉快照字段 ==========
    conversation_mode: Mapped[str] = mapped_column(
        String(20),
        default=ConversationMode.AI.value,
        nullable=False,
        index=True,
    )  # 当前会话模式快照
    current_ticket_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )  # 当前主活动问题单 ID（避免循环外键，第一阶段不强绑 FK）
    complaint_status: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
        index=True,
    )  # 当前主问题单处理状态快照
    primary_issue_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )  # 当前主问题标签快照
    current_agent_tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # 当前负责处理该问题的 AI 岗位
    current_node_key: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # 当前流程节点快照
    priority_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )  # 当前主问题优先级
    risk_level: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )  # 当前主问题风险等级
    unresolved_turns: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )  # 当前主问题连续未解决轮次
    review_status: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )  # 最近一次审查状态快照
    review_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # 最近一次审查分数快照
    block_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )  # 当前阻塞原因
    secondary_issues: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON,
        nullable=True,
    )  # 当前主问题下挂起的次级问题列表

    # 关联
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    tickets: Mapped[list["ComplaintTicket"]] = relationship(
        "ComplaintTicket",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ComplaintTicket.updated_at",
    )
