"""会话相关 Schema"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    """创建会话请求"""

    user_id: str = Field(..., description="用户 ID")


class ConversationResponse(BaseModel):
    """会话响应"""

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    handoff_state: str | None = None

    model_config = {"from_attributes": True}


class ToolCallResponse(BaseModel):
    """工具调用响应"""

    id: int
    tool_call_id: str | None = None
    tool_name: str
    tool_input: dict[str, Any] | None = None
    tool_output: str | None = None
    status: str = "pending"
    error_message: str | None = None
    duration_ms: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """消息响应"""

    id: str
    role: str
    content: str
    products: str | None = None
    message_type: str = "text"
    extra_metadata: dict[str, Any] | None = None
    token_count: int | None = None
    tool_calls: list[ToolCallResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationWithMessages(ConversationResponse):
    """带消息的会话响应"""

    messages: list[MessageResponse] = []
