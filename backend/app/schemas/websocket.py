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
    MESSAGE_NOT_FOUND = "MESSAGE_NOT_FOUND"
    MESSAGE_SEND_FAILED = "MESSAGE_SEND_FAILED"
    MESSAGE_ALREADY_WITHDRAWN = "MESSAGE_ALREADY_WITHDRAWN"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
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
    CLIENT_AGENT_WITHDRAW_MESSAGE = "client.agent.withdraw_message"
    CLIENT_AGENT_EDIT_MESSAGE = "client.agent.edit_message"

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
    SERVER_SUPPORT_QUEUE_CHANGED = "server.support_queue_changed"
    SERVER_TICKET_UPDATED = "server.ticket_updated"
    SERVER_REVIEW_UPDATED = "server.review_updated"
    SERVER_MESSAGE_WITHDRAWN = "server.message_withdrawn"
    SERVER_MESSAGE_EDITED = "server.message_edited"
    SERVER_MESSAGES_DELETED = "server.messages_deleted"


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
    """连接成功。

    这个 payload 用于在 WebSocket 建连瞬间把当前会话的完整工作台状态发给前端。
    """
    connection_id: str = Field(..., description="连接 ID")
    role: str = Field(..., description="连接角色")
    conversation_id: str = Field(..., description="会话 ID")
    conversation_mode: str = Field(default="ai", description="当前会话服务模式")
    handoff_state: str = Field(..., description="当前客服介入状态")
    peer_online: bool = Field(False, description="对方是否在线")
    peer_last_online_at: str | None = Field(None, description="对方最后在线时间")
    unread_count: int = Field(0, description="未读消息数")
    current_ticket: dict[str, Any] | None = Field(default=None, description="当前主问题单摘要")
    review_summary: dict[str, Any] | None = Field(default=None, description="最近一次审查摘要")
    recent_tasks: list[dict[str, Any]] = Field(default_factory=list, description="当前主问题单最近任务链")
    secondary_issues: list[dict[str, Any]] = Field(default_factory=list, description="当前主问题单次级诉求")
    handoff_summary: dict[str, Any] | None = Field(default=None, description="当前转人工接手摘要")


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
    """服务器推送新消息。

    这个 payload 同时服务于实时发送和离线补发，因此需要完整表达送达、已读、撤回、编辑状态，
    让前端在重连后仍能恢复同一条消息的最终业务状态。
    """
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
    is_withdrawn: bool = False  # 是否已撤回
    withdrawn_at: str | None = None  # 撤回时间
    withdrawn_by: str | None = None  # 撤回操作人
    is_edited: bool = False  # 是否已编辑
    edited_at: str | None = None  # 编辑时间
    edited_by: str | None = None  # 编辑操作人


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


class TicketStatePayload(BaseModel):
    """WebSocket 问题单状态摘要。

    这个 payload 用于把当前主问题单的关键状态推送给工作台和用户侧状态管理。
    """

    id: str
    status: str
    primary_issue_tag: str | None = None
    secondary_issue_tags: list[str] = Field(default_factory=list)
    current_agent_tag: str | None = None
    priority_level: str | None = None
    risk_level: str | None = None
    unresolved_turns: int = 0
    handoff_required: bool = False
    handoff_reason: str | None = None
    merged_from_latest_message: bool = False
    secondary_issue_detected: bool = False
    updated_at: str | None = None


class ReviewStatePayload(BaseModel):
    """WebSocket 审查状态摘要。

    这个 payload 用于工作台实时显示最近一次 review 的结果和原因。
    """

    status: str
    score: int | None = None
    risk_level: str | None = None
    reasons: list[str] = Field(default_factory=list)
    suggested_next_agent: str | None = None
    created_at: str | None = None


class RecentTaskPayload(BaseModel):
    """最近任务链条摘要。

    这个 payload 用于工作台展示最近经过的 triage、plan、execute、review 节点。
    """

    id: str
    ticket_id: str
    task_type: str
    agent_tag: str
    status: str
    goal: str | None = None
    success_criteria: list[str] = Field(default_factory=list)
    review_required: bool = False
    review_status: str | None = None
    business_summary: str | None = None
    failure_reason: str | None = None
    output_payload: dict[str, Any] | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str | None = None


class SecondaryIssuePayload(BaseModel):
    """主问题单下的次级诉求。

    这个 payload 用于客服工作台理解当前会话是否已经从主问题延伸出附带诉求。
    """

    issue_tag: str
    reason: str | None = None
    raw_message: str | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)


class ConversationStatePayload(BaseModel):
    """会话状态。

    这个 payload 用于在会话状态变更时向客服端和用户端广播完整 ticket 驱动状态。
    """
    conversation_mode: str = Field(default="ai", description="当前会话服务模式")
    handoff_state: str
    operator: str | None = None
    handoff_reason: str | None = None
    user_online: bool = False
    peer_last_online_at: str | None = None
    unread_count: int = 0
    current_ticket: TicketStatePayload | None = None
    review_summary: ReviewStatePayload | None = None
    recent_tasks: list[RecentTaskPayload] = Field(default_factory=list)
    secondary_issues: list[SecondaryIssuePayload] = Field(default_factory=list)
    handoff_summary: dict[str, Any] | None = None


class SupportQueueChangedPayload(BaseModel):
    """客服工作台全局队列变更通知。

    这个 payload 用于提醒客服列表页：某个未必正在订阅的会话发生了 handoff 队列变化，
    应主动刷新待接入/处理中队列，而不是等下一轮轮询。
    """

    conversation_id: str
    handoff_state: str
    reason: str | None = None
    source: str | None = None
    changed_at: str | None = None


class TicketUpdatedPayload(BaseModel):
    """问题单更新推送。

    这个 payload 用于局部更新当前主问题单，避免前端总是全量刷新整个会话状态。
    """

    ticket: TicketStatePayload


class ReviewUpdatedPayload(BaseModel):
    """审查结果更新推送。

    这个 payload 用于在 review 状态变化时独立刷新工作台风险提示。
    """

    review_summary: ReviewStatePayload


# ========== 消息撤回/编辑 Payloads ==========
class WithdrawMessagePayload(BaseModel):
    """撤回消息请求"""
    message_id: str = Field(..., description="要撤回的消息 ID")
    reason: str = Field(default="", description="撤回原因")


class EditMessagePayload(BaseModel):
    """编辑消息请求"""
    message_id: str = Field(..., description="要编辑的消息 ID")
    new_content: str = Field(..., min_length=1, max_length=10000, description="新内容")
    regenerate: bool = Field(default=True, description="是否重新生成后续 AI 回复")


class MessageWithdrawnPayload(BaseModel):
    """消息已撤回通知"""
    message_id: str
    withdrawn_by: str
    withdrawn_at: str  # ISO 格式时间
    reason: str = ""


class MessageEditedPayload(BaseModel):
    """消息已编辑通知"""
    message_id: str
    old_content: str
    new_content: str
    edited_by: str
    edited_at: str  # ISO 格式时间
    deleted_message_ids: list[str] = []  # 被删除的后续消息 ID
    regenerate_triggered: bool = False  # 是否触发了重新生成


class MessagesDeletedPayload(BaseModel):
    """消息已删除通知（编辑时删除后续消息）"""
    message_ids: list[str]
    reason: str = "edit_regenerate"  # 删除原因


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
    WSAction.CLIENT_AGENT_WITHDRAW_MESSAGE: WithdrawMessagePayload,
    WSAction.CLIENT_AGENT_EDIT_MESSAGE: EditMessagePayload,

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
    WSAction.SERVER_SUPPORT_QUEUE_CHANGED: SupportQueueChangedPayload,
    WSAction.SERVER_TICKET_UPDATED: TicketUpdatedPayload,
    WSAction.SERVER_REVIEW_UPDATED: ReviewUpdatedPayload,
    WSAction.SERVER_MESSAGE_WITHDRAWN: MessageWithdrawnPayload,
    WSAction.SERVER_MESSAGE_EDITED: MessageEditedPayload,
    WSAction.SERVER_MESSAGES_DELETED: MessagesDeletedPayload,
}
