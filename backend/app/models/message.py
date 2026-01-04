"""消息模型"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.tool_call import ToolCall


class Message(Base):
    """消息表"""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # user / assistant / human_agent / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    products: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: 推荐的商品
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )

    # ========== 送达和已读状态 ==========
    is_delivered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )  # 是否已送达对方
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )  # 送达时间
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )  # 已读时间
    read_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )  # 阅读者 (user_id 或 agent_id)

    # ========== 扩展字段：元数据与工具调用 ==========
    message_type: Mapped[str] = mapped_column(
        String(30),
        default="text",
        nullable=False,
    )  # text / tool_call / tool_result / multimodal_image
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )  # 完整消息 dump（含 tool_calls、usage_metadata、response_metadata 等）
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # Token 计数（可选）

    # 关联
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
    tool_calls: Mapped[list["ToolCall"]] = relationship(
        "ToolCall",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="ToolCall.created_at",
    )
