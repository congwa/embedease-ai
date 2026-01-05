"""客服支持相关 Schema"""

from datetime import datetime

from pydantic import BaseModel, Field


class HandoffStartRequest(BaseModel):
    """开始客服介入请求"""

    operator: str = Field(..., description="客服标识（用户名/ID）")
    reason: str = Field(default="", description="介入原因")


class HandoffEndRequest(BaseModel):
    """结束客服介入请求"""

    operator: str = Field(..., description="客服标识")
    summary: str = Field(default="", description="客服总结")


class HandoffResponse(BaseModel):
    """介入操作响应"""

    success: bool
    conversation_id: str | None = None
    operator: str | None = None
    error: str | None = None
    handoff_at: str | None = None
    ended_by: str | None = None
    current_operator: str | None = None
    handoff_state: str | None = None  # 保底机制：返回最新状态让前端同步


class HumanMessageRequest(BaseModel):
    """人工客服发送消息请求"""

    content: str = Field(..., min_length=1, description="消息内容")
    operator: str = Field(..., description="客服标识")


class HumanMessageResponse(BaseModel):
    """人工客服消息响应"""

    success: bool
    message_id: str | None = None
    conversation_id: str | None = None
    error: str | None = None
    created_at: str | None = None


class ConversationStateResponse(BaseModel):
    """会话状态响应"""

    conversation_id: str
    handoff_state: str
    handoff_operator: str | None = None
    handoff_reason: str | None = None
    handoff_at: str | None = None
    last_notification_at: str | None = None


class ConversationListItem(BaseModel):
    """会话列表项"""

    id: str
    user_id: str
    title: str
    handoff_state: str
    handoff_operator: str | None = None
    updated_at: datetime
    created_at: datetime


class ConversationListResponse(BaseModel):
    """会话列表响应"""

    items: list[ConversationListItem]
    total: int
    offset: int
    limit: int
