"""工具调用模型"""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.message import Message


class ToolCall(Base):
    """工具调用表 - 记录 AI 的工具调用及执行结果"""

    __tablename__ = "tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_call_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )  # LangGraph/LangChain tool_call_id，用于精确匹配
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # 工具名称
    tool_input: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )  # 工具输入参数
    tool_output: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # 工具执行结果
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )  # pending / success / error / empty
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )  # 错误信息
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )  # 执行耗时（毫秒）
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
    )

    # 关联
    message: Mapped["Message"] = relationship(
        "Message",
        back_populates="tool_calls",
    )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "message_id": self.message_id,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input or {},
            "tool_output": self.tool_output,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
