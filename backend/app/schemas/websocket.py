"""WebSocket 协议数据结构定义

本模块定义 WebSocket 通讯的所有数据结构，包括：
- 基础消息信封
- 各 Action 的 Payload 类型
- 错误码枚举
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ========== 协议版本 ==========
WS_PROTOCOL_VERSION = 1


# ========== 错误码枚举 ==========
class WSErrorCode(StrEnum):
    """WebSocket 错误码"""

    # 认证相关
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FAILED = "AUTH_FAILED"
    AUTH_EXPIRED = "AUTH_EXPIRED"

    # 权限相关
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_IN_HUMAN_MODE = "NOT_IN_HUMAN_MODE"

    # 请求相关
    INVALID_ACTION = "INVALID_ACTION"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    MISSING_FIELD = "MISSING_FIELD"

    # 业务相关
    CONVERSATION_NOT_FOUND = "CONVERSATION_NOT_FOUND"
    MESSAGE_SEND_FAILED = "MESSAGE_SEND_FAILED"
    HANDOFF_FAILED = "HANDOFF_FAILED"

    # 系统相关
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    CONNECTION_CLOSED = "CONNECTION_CLOSED"


# ========== 角色枚举 ==========
class WSRole(StrEnum):
    """WebSocket 连接角色"""
    USER = "user"
    AGENT = "agent"


# ========== Action 常量定义 ==========
class WSAction(StrEnum):
    """WebSocket Action 枚举"""

    # System
    SYSTEM_PING = "system.ping"
    SYSTEM_PONG = "system.pong"
    SYSTEM_ACK = "system.ack"
    SYSTEM_ERROR = "system.error"
    SYSTEM_CONNECTED = "system.connected"
    SYSTEM_DISCONNECTED = "system.disconnected"

    # Client User
    CLIENT_USER_SEND_MESSAGE = "client.user.send_message"
    CLIENT_USER_TYPING = "client.user.typing"
    CLIENT_USER_READ = "client.user.read"
    CLIENT_USER_REQUEST_HANDOFF = "client.user.request_handoff"

    # Client Agent
    CLIENT_AGENT_SEND_MESSAGE = "client.agent.send_message"
    CLIENT_AGENT_TYPING = "client.agent.typing"
    CLIENT_AGENT_READ = "client.agent.read"
    CLIENT_AGENT_START_HANDOFF = "client.agent.start_handoff"
    CLIENT_AGENT_END_HANDOFF = "client.agent.end_handoff"
    CLIENT_AGENT_TRANSFER = "client.agent.transfer"

    # Server Push
    SERVER_MESSAGE = "server.message"
    SERVER_TYPING = "server.typing"
    SERVER_READ_RECEIPT = "server.read_receipt"
    SERVER_HANDOFF_STARTED = "server.handoff_started"
    SERVER_HANDOFF_ENDED = "server.handoff_ended"
    SERVER_USER_ONLINE = "server.user_online"
    SERVER_USER_OFFLINE = "server.user_offline"
    SERVER_AGENT_ONLINE = "server.agent_online"
    SERVER_AGENT_OFFLINE = "server.agent_offline"
    SERVER_CONVERSATION_STATE = "server.conversation_state"


# ========== 基础结构 ==========
class WSError(BaseModel):
    """错误信息"""
    code: str
    message: str
    detail: Any = None


class WSMessageBase(BaseModel):
    """WebSocket 消息基础结构（信封）"""
    v: int = Field(default=WS_PROTOCOL_VERSION, description="协议版本")
    id: str = Field(..., description="消息唯一 ID")
    ts: int = Field(..., description="时间戳（毫秒）")
    action: str = Field(..., description="动作类型")
    payload: dict[str, Any] = Field(default_factory=dict, description="载荷")

    conversation_id: str | None = Field(None, description="会话 ID")
    reply_to: str | None = Field(None, description="响应的原消息 ID")
    error: WSError | None = Field(None, description="错误信息")


# ========== System Payloads ==========
class PingPayload(BaseModel):
    """心跳请求"""
    pass


class PongPayload(BaseModel):
    """心跳响应"""
    server_ts: int = Field(..., description="服务器时间戳")


class AckPayload(BaseModel):
    """消息确认"""
    received_id: str = Field(..., description="确认的消息 ID")
    status: Literal["ok", "error"] = Field(..., description="处理状态")


class ConnectedPayload(BaseModel):
    """连接成功"""
    connection_id: str = Field(..., description="连接 ID")
    role: str = Field(..., description="连接角色")
    conversation_id: str = Field(..., description="会话 ID")
    handoff_state: str = Field(..., description="当前客服介入状态")
    peer_online: bool = Field(False, description="对方是否在线")
    peer_last_online_at: str | None = Field(None, description="对方最后在线时间")
    unread_count: int = Field(0, description="未读消息数")


class ErrorPayload(BaseModel):
    """错误通知"""
    code: str
    message: str
    detail: Any = None


# ========== Client User Payloads ==========
class UserSendMessagePayload(BaseModel):
    """用户发送消息"""
    content: str = Field(..., min_length=1, max_length=10000)
    message_id: str | None = Field(None, description="客户端生成的消息 ID（用于幂等）")


class TypingPayload(BaseModel):
    """输入状态"""
    is_typing: bool = Field(..., description="是否正在输入")


class ReadReceiptPayload(BaseModel):
    """已读回执"""
    message_ids: list[str] = Field(..., min_length=1, description="已读消息 ID 列表")


class RequestHandoffPayload(BaseModel):
    """请求人工客服"""
    reason: str = Field(default="", description="请求原因")


# ========== Client Agent Payloads ==========
class AgentSendMessagePayload(BaseModel):
    """客服发送消息"""
    content: str = Field(..., min_length=1, max_length=10000)
    message_id: str | None = Field(None, description="客户端生成的消息 ID")


class StartHandoffPayload(BaseModel):
    """客服主动介入"""
    reason: str = Field(default="", description="介入原因")


class EndHandoffPayload(BaseModel):
    """结束客服介入"""
    summary: str = Field(default="", description="客服总结")


class TransferPayload(BaseModel):
    """转接客服"""
    target_agent_id: str = Field(..., description="目标客服 ID")
    reason: str = Field(default="", description="转接原因")


# ========== Server Push Payloads ==========
class ServerMessagePayload(BaseModel):
    """服务器推送新消息"""
    message_id: str
    role: str  # "user" | "assistant" | "human_agent" | "system"
    content: str
    created_at: str  # ISO 格式时间
    operator: str | None = None  # 客服标识（human_agent 时存在）
    images: list[dict] | None = None  # 图片附件列表
    is_delivered: bool = False  # 是否已送达
    delivered_at: str | None = None  # 送达时间
    read_at: str | None = None  # 已读时间
    read_by: str | None = None  # 阅读者


class ServerTypingPayload(BaseModel):
    """对方输入状态"""
    role: str
    is_typing: bool


class ServerReadReceiptPayload(BaseModel):
    """已读回执推送"""
    role: str
    message_ids: list[str]
    read_at: str  # ISO 格式时间
    read_by: str  # 阅读者 ID


class HandoffStartedPayload(BaseModel):
    """客服介入开始"""
    operator: str
    reason: str = ""


class HandoffEndedPayload(BaseModel):
    """客服介入结束"""
    operator: str
    summary: str = ""


class UserPresencePayload(BaseModel):
    """用户在线状态"""
    user_id: str
    conversation_id: str
    online: bool = True  # 是否在线
    last_online_at: str | None = None  # 最后在线时间


class AgentPresencePayload(BaseModel):
    """客服在线状态"""
    operator: str
    online: bool = True  # 是否在线
    last_online_at: str | None = None  # 最后在线时间


class ConversationStatePayload(BaseModel):
    """会话状态"""
    handoff_state: str
    operator: str | None = None


# ========== Payload 映射表 ==========
ACTION_PAYLOAD_MAP: dict[str, type[BaseModel]] = {
    # System
    WSAction.SYSTEM_PING: PingPayload,
    WSAction.SYSTEM_PONG: PongPayload,
    WSAction.SYSTEM_ACK: AckPayload,
    WSAction.SYSTEM_ERROR: ErrorPayload,
    WSAction.SYSTEM_CONNECTED: ConnectedPayload,

    # Client User
    WSAction.CLIENT_USER_SEND_MESSAGE: UserSendMessagePayload,
    WSAction.CLIENT_USER_TYPING: TypingPayload,
    WSAction.CLIENT_USER_READ: ReadReceiptPayload,
    WSAction.CLIENT_USER_REQUEST_HANDOFF: RequestHandoffPayload,

    # Client Agent
    WSAction.CLIENT_AGENT_SEND_MESSAGE: AgentSendMessagePayload,
    WSAction.CLIENT_AGENT_TYPING: TypingPayload,
    WSAction.CLIENT_AGENT_READ: ReadReceiptPayload,
    WSAction.CLIENT_AGENT_START_HANDOFF: StartHandoffPayload,
    WSAction.CLIENT_AGENT_END_HANDOFF: EndHandoffPayload,
    WSAction.CLIENT_AGENT_TRANSFER: TransferPayload,

    # Server Push
    WSAction.SERVER_MESSAGE: ServerMessagePayload,
    WSAction.SERVER_TYPING: ServerTypingPayload,
    WSAction.SERVER_READ_RECEIPT: ServerReadReceiptPayload,
    WSAction.SERVER_HANDOFF_STARTED: HandoffStartedPayload,
    WSAction.SERVER_HANDOFF_ENDED: HandoffEndedPayload,
    WSAction.SERVER_USER_ONLINE: UserPresencePayload,
    WSAction.SERVER_USER_OFFLINE: UserPresencePayload,
    WSAction.SERVER_AGENT_ONLINE: AgentPresencePayload,
    WSAction.SERVER_AGENT_OFFLINE: AgentPresencePayload,
    WSAction.SERVER_CONVERSATION_STATE: ConversationStatePayload,
}
