"""客服支持相关 Schema

本文件的业务职责是定义客服工作台、人工接入和会话状态查询使用的结构化返回对象。
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.chat import ImageAttachment


class HandoffStartRequest(BaseModel):
    """开始客服介入请求。

    这个请求用于把会话从 AI 模式切换到人工客服处理模式。
    """

    operator: str = Field(..., description="客服标识（用户名/ID）")
    reason: str = Field(default="", description="介入原因")


class HandoffEndRequest(BaseModel):
    """结束客服介入请求。

    这个请求用于结束人工处理并把会话恢复到 AI 接管状态。
    """

    operator: str = Field(..., description="客服标识")
    summary: str = Field(default="", description="客服总结")


class HandoffResponse(BaseModel):
    """介入操作响应。

    这个响应给前端返回最新 handoff 状态，避免按钮状态和服务端状态不同步。
    """

    success: bool
    conversation_id: str | None = None
    operator: str | None = None
    error: str | None = None
    handoff_at: str | None = None
    ended_by: str | None = None
    current_operator: str | None = None
    handoff_state: str | None = None  # 保底机制：返回最新状态让前端同步


class HumanMessageRequest(BaseModel):
    """人工客服发送消息请求。

    这个请求用于客服在人工模式下发送文本或图片消息。
    """

    content: str = Field(default="", description="消息内容（可为空，但必须有图片）")
    operator: str = Field(..., description="客服标识")
    images: list[ImageAttachment] | None = Field(default=None, description="图片附件列表")

    @property
    def has_images(self) -> bool:
        """判断是否携带图片附件。

        这个属性服务于客服消息发送校验，避免内容和图片同时为空。
        """
        return bool(self.images and len(self.images) > 0)


class HumanMessageResponse(BaseModel):
    """人工客服消息响应。

    这个响应用于告知客服端消息是否成功进入人工客服通道。
    """

    success: bool
    message_id: str | None = None
    conversation_id: str | None = None
    error: str | None = None
    created_at: str | None = None


class TicketSummarySchema(BaseModel):
    """客服工作台问题单摘要。

    这个对象用于让工作台列表、详情页和 WebSocket 状态都围绕同一张主问题单展示。
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
    updated_at: datetime | None = None


class ReviewSummarySchema(BaseModel):
    """客服工作台最近审查摘要。

    这个对象用于让客服知道上一轮 AI 处理为什么被通过、驳回或升级人工。
    """

    status: str
    score: int | None = None
    risk_level: str | None = None
    reasons: list[str] = Field(default_factory=list)
    suggested_next_agent: str | None = None
    created_at: datetime | None = None


class RecentTaskSummarySchema(BaseModel):
    """客服工作台最近任务摘要。

    这个对象用于让人工客服直接看到当前主问题单最近经过了哪些岗位和阶段，
    避免接手时还要回读整段聊天历史。
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
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class SecondaryIssueSchema(BaseModel):
    """主问题单下的次级诉求摘要。

    这个对象用于明确告诉人工客服：用户当前主问题之外，还夹带了哪些额外诉求，
    但这些诉求尚未达到自动拆单条件。
    """

    issue_tag: str
    reason: str | None = None
    raw_message: str | None = None
    extra_data: dict[str, Any] = Field(default_factory=dict)


class TicketDetailSchema(BaseModel):
    """客服问题单详情。

    这个对象用于客服工作台以“问题单”而不是“会话”视角查看完整处理上下文，
    支撑人工判断是否接手、解决或重新打开问题。
    """

    id: str
    conversation_id: str
    user_id: str
    status: str
    is_primary_active: bool
    parent_ticket_id: str | None = None
    superseded_by_ticket_id: str | None = None
    issue_fingerprint: str | None = None
    primary_issue_tag: str | None = None
    secondary_issue_tags: list[str] = Field(default_factory=list)
    secondary_issues: list[SecondaryIssueSchema] = Field(default_factory=list)
    sentiment: str | None = None
    severity: str | None = None
    priority_level: str | None = None
    risk_level: str | None = None
    current_agent_tag: str | None = None
    current_task_id: str | None = None
    current_node_key: str | None = None
    unresolved_turns: int = 0
    rework_count: int = 0
    handoff_required: bool = False
    handoff_reason: str | None = None
    handoff_summary: dict[str, Any] | None = None
    resolved_summary: str | None = None
    slot_data: dict[str, Any] = Field(default_factory=dict)
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    version: int = 1
    latest_review: ReviewSummarySchema | None = None
    recent_tasks: list[RecentTaskSummarySchema] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None


class ConversationStateResponse(BaseModel):
    """客服详情页会话状态响应。

    这个响应用于客服详情页初始化时一次拿全 handoff、ticket 和 review 状态。
    """

    conversation_id: str
    conversation_mode: str
    handoff_state: str
    handoff_operator: str | None = None
    handoff_reason: str | None = None
    handoff_at: datetime | None = None
    last_notification_at: datetime | None = None
    current_ticket: TicketSummarySchema | None = None
    recent_tasks: list[RecentTaskSummarySchema] = Field(default_factory=list)
    review_summary: ReviewSummarySchema | None = None
    latest_review: ReviewSummarySchema | None = None
    secondary_issues: list[SecondaryIssueSchema] = Field(default_factory=list)
    handoff_summary: dict[str, Any] | None = None
    user_online: bool = False
    peer_last_online_at: datetime | None = None
    unread_count: int = 0


class ConversationTicketsResponse(BaseModel):
    """会话问题单列表响应。

    这个响应用于客服工作台按会话查看历史 ticket，支持人工回溯和二次处理。
    """

    conversation_id: str
    items: list[TicketSummarySchema]
    total: int


class TicketResolveRequest(BaseModel):
    """手动解决问题单请求。

    这个请求用于客服明确确认某张问题单已经处理完成，并写入解决摘要。
    """

    operator: str = Field(default="", description="执行该操作的客服标识")
    summary: str = Field(default="", description="当前问题单的解决摘要")


class TicketReopenRequest(BaseModel):
    """手动重开问题单请求。

    这个请求用于客服发现问题未真正解决时，把已结束的问题单重新交回处理主链路。
    """

    operator: str = Field(default="", description="执行该操作的客服标识")
    reason: str = Field(default="", description="本次重开的业务原因")


class TicketActionResponse(BaseModel):
    """问题单操作响应。

    这个响应统一承载 resolve / reopen 等人工操作的执行结果和最新 ticket 快照。
    """

    success: bool
    ticket: TicketDetailSchema | None = None
    error: str | None = None


class ConversationListItem(BaseModel):
    """客服工作台会话列表项。

    这个对象用于列表页直接做高风险、等待人工、审查驳回和次级问题提醒。
    """

    id: str
    user_id: str
    title: str
    conversation_mode: str | None = None
    handoff_state: str
    handoff_operator: str | None = None
    handoff_reason: str | None = None
    user_online: bool = False
    updated_at: datetime
    created_at: datetime
    heat_score: int = 0  # 热度得分
    unread_count: int = 0  # 未读消息数
    current_ticket_id: str | None = None
    ticket_status: str | None = None
    primary_issue_tag: str | None = None
    current_agent_tag: str | None = None
    risk_level: str | None = None
    review_status: str | None = None
    review_score: int | None = None
    secondary_issue_detected: bool = False
    last_message: str | None = None
    last_message_at: datetime | None = None
    last_message_role: str | None = None


class ConversationListResponse(BaseModel):
    """客服工作台会话列表响应。

    这个响应用于列表页分页加载和排序。
    """

    items: list[ConversationListItem]
    total: int
    offset: int
    limit: int


class SupportStatsResponse(BaseModel):
    """客服统计数据（用于红点提醒）。

    这个响应用于工作台顶部统计和高优先级提示。
    """

    pending_count: int = 0  # 等待接入数
    human_count: int = 0  # 人工服务中数
    total_unread: int = 0  # 总未读消息数
    high_heat_count: int = 0  # 高热会话数(得分>60)


class AgentScoreSnapshotSchema(BaseModel):
    """Agent 绩效快照响应。

    这个对象用于把后台统计任务生成的质量与效率指标返回给运营后台或后续排行榜页面。
    """

    id: str
    agent_tag: str
    window_type: str
    window_start: datetime
    window_end: datetime
    pass_rate: float | None = None
    handoff_rate: float | None = None
    avg_review_score: float | None = None
    avg_resolution_time_ms: int | None = None
    rework_rate: float | None = None
    violation_rate: float | None = None
    payload: dict[str, Any] | None = None
    created_at: datetime


class AgentScoreSnapshotListResponse(BaseModel):
    """Agent 绩效快照列表响应。

    这个响应服务于运营后台读取某个窗口类型下的最近一批绩效快照。
    """

    items: list[AgentScoreSnapshotSchema]
    total: int
    window_type: str
