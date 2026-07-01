"""客诉领域 Schema

本文件的业务职责是统一定义客诉系统的核心状态枚举和基础结构化结果，
让后续 ticket、task、review、handoff 等服务都围绕同一套业务状态工作。
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ConversationMode(StrEnum):
    """会话通道模式。

    这个枚举表达当前会话的服务模式，而不是问题本身的处理进度。
    """

    AI = "ai"
    PENDING = "pending"
    HUMAN = "human"
    CLOSED = "closed"


class ComplaintStatus(StrEnum):
    """问题单处理状态。

    这个枚举表达单个客诉问题单当前推进到了哪一个业务阶段。
    """

    NEW = "new"
    TRIAGED = "triaged"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    REWORK_REQUIRED = "rework_required"
    BLOCKED = "blocked"
    HANDOFF_PENDING = "handoff_pending"
    HANDED_OFF = "handed_off"
    RESOLVED = "resolved"
    CLOSED = "closed"


ACTIVE_COMPLAINT_STATUSES: tuple[ComplaintStatus, ...] = (
    ComplaintStatus.NEW,
    ComplaintStatus.TRIAGED,
    ComplaintStatus.PLANNED,
    ComplaintStatus.IN_PROGRESS,
    ComplaintStatus.PENDING_REVIEW,
    ComplaintStatus.REWORK_REQUIRED,
    ComplaintStatus.BLOCKED,
    ComplaintStatus.HANDOFF_PENDING,
    ComplaintStatus.HANDED_OFF,
)


class ComplaintTaskStatus(StrEnum):
    """问题单任务状态。

    这个枚举表达单次 triage、plan、execute、review 任务的执行结果。
    """

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_REVIEW = "waiting_review"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class ComplaintReviewStatus(StrEnum):
    """执行结果审查状态。

    这个枚举表达 reviewer 对候选回复或处理结果的质量判断。
    """

    PENDING = "pending"
    PASSED = "passed"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class ComplaintPatrolStatus(StrEnum):
    """巡查事件状态。

    这个枚举表达巡查 Agent 对异常 ticket 的处理结果。
    """

    OPEN = "open"
    AUTO_RECOVERED = "auto_recovered"
    ESCALATED = "escalated"
    IGNORED = "ignored"


class IssueContinuity(StrEnum):
    """当前消息和主问题单的连续性判断。

    这个枚举帮助系统决定是继续归并到当前问题单，还是记录为次要问题，
    或者在高置信度下拆成新的问题单。
    """

    SAME_ISSUE = "same_issue"
    NEW_ISSUE = "new_issue"
    UNCERTAIN = "uncertain"


class TicketResolutionDecision(StrEnum):
    """当前消息对应的问题单处理决策。

    这个枚举用于约束归并服务的返回值，避免上层业务只依赖字符串约定。
    """

    CREATE_INITIAL_TICKET = "create_initial_ticket"
    REUSE_ACTIVE_TICKET = "reuse_active_ticket"
    RECORD_SECONDARY_ISSUE = "record_secondary_issue"
    CREATE_NEW_TICKET = "create_new_ticket"


class ActiveTicketResolution(BaseModel):
    """当前消息归并到哪个问题单的结构化结果。

    这个对象用于让 orchestrator、stream 和工作台都能知道本轮消息
    究竟是创建新单、继续归并，还是只记录次要问题。
    """

    decision: TicketResolutionDecision = Field(..., description="本轮 ticket 处理决策")
    ticket_id: str = Field(..., description="本轮最终归属的主问题单 ID")
    previous_ticket_id: str | None = Field(default=None, description="被替代或参考的旧 ticket ID")
    reason: str = Field(..., description="做出该决策的业务原因")
    issue_continuity: IssueContinuity = Field(..., description="当前消息与旧问题单的连续性判断")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="本轮判定置信度")


class ReviewDecision(BaseModel):
    """审查后的结构化决策结果。

    这个对象用于把 reviewer 的结果从模型输出转换成 ticket/task 可执行状态。
    """

    status: ComplaintReviewStatus = Field(..., description="reviewer 的最终状态")
    score: int | None = Field(default=None, ge=0, le=100, description="业务质量分数")
    risk_level: str | None = Field(default=None, description="当前回复的风险等级")
    reasons: list[str] = Field(default_factory=list, description="驳回或升级的业务原因")
    suggested_next_agent: str | None = Field(default=None, description="建议下一步接手的岗位")
    should_handoff: bool = Field(default=False, description="是否建议直接转人工")


class ComplaintTriageResult(BaseModel):
    """front desk 对当前消息的首轮识别结果。

    这个对象服务于 triage 阶段，用来统一表达主问题标签、风险、情绪和
    信息缺口，避免 planner 直接解析原始消息文本。
    """

    primary_issue_tag: str = Field(..., description="当前主问题标签")
    priority_level: str = Field(..., description="当前问题优先级")
    risk_level: str = Field(..., description="当前风险等级")
    sentiment: str = Field(..., description="当前用户情绪")
    severity: str = Field(..., description="当前问题严重程度")
    emotional_intensity: str = Field(default="normal", description="当前情绪强度")
    continuity: IssueContinuity = Field(..., description="当前消息与主问题的连续性")
    requested_human: bool = Field(default=False, description="用户是否明确请求人工")
    missing_slots: list[str] = Field(default_factory=list, description="当前仍缺失的业务槽位")
    extracted_slots: dict[str, Any] = Field(default_factory=dict, description="当前消息里识别出的槽位")
    summary: str = Field(..., description="供 planner 和工作台阅读的 triage 摘要")


class PlannerDecision(BaseModel):
    """planner 对当前轮应该分配给谁处理的决策。

    这个对象用于把“当前该由哪个岗位接手、目标是什么、下一节点是什么”
    固化成结构化合同，供 task、executor 和前端事件统一消费。
    """

    assigned_agent_tag: str = Field(..., description="本轮被分配的岗位标签")
    task_type: str = Field(..., description="本轮 executor 任务类型")
    goal: str = Field(..., description="本轮任务目标")
    success_criteria: list[str] = Field(default_factory=list, description="判定本轮任务达标的标准")
    should_handoff: bool = Field(default=False, description="planner 是否已经判定必须转人工")
    next_node_key: str = Field(..., description="问题单下一步所处节点")
    reasoning: str = Field(..., description="planner 做出当前分派的业务原因")


class ExecutorResult(BaseModel):
    """executor 产出的候选处理结果。

    这个对象用于承载候选回复文本、已收集槽位和是否建议 handoff，
    供 review、ticket 状态推进和聊天流共同消费。
    """

    content: str = Field(..., description="候选回复文本")
    task_completed: bool = Field(default=False, description="本轮任务是否已经达到目标")
    collected_slots: dict[str, Any] = Field(default_factory=dict, description="本轮补齐的业务槽位")
    handoff_recommended: bool = Field(default=False, description="executor 是否建议直接转人工")
    handoff_reason: str | None = Field(default=None, description="建议转人工的原因")
    next_hint: str | None = Field(default=None, description="供后续节点使用的推进提示")


class HandoffRequestResult(BaseModel):
    """客诉语义下的转人工请求结果。

    这个对象用于把 ticket 级 handoff 结果统一返回给 orchestrator、SSE
    和 WebSocket 推送逻辑，避免上层只依赖散乱字典。
    """

    requested: bool = Field(..., description="本轮是否已成功进入待人工接入状态")
    conversation_id: str = Field(..., description="所属会话 ID")
    ticket_id: str | None = Field(default=None, description="关联问题单 ID")
    handoff_reason: str = Field(..., description="当前转人工原因")
    handoff_summary: dict[str, Any] = Field(default_factory=dict, description="给人工客服的接手摘要")
    conversation_mode: str = Field(default=ConversationMode.PENDING.value, description="当前会话模式")
    handoff_state: str = Field(default=ConversationMode.PENDING.value, description="当前接入状态")


class TicketStreamSummary(BaseModel):
    """面向前端流式事件的 ticket 摘要。

    这个对象用于把当前主问题单的关键状态压缩成前端可直接消费的结构。
    """

    id: str = Field(..., description="当前主问题单 ID")
    status: str = Field(..., description="当前问题单状态")
    primary_issue_tag: str | None = Field(default=None, description="当前主问题标签")
    secondary_issue_tags: list[str] = Field(default_factory=list, description="当前已识别的次级问题标签")
    current_agent_tag: str | None = Field(default=None, description="当前负责岗位")
    priority_level: str | None = Field(default=None, description="当前优先级")
    risk_level: str | None = Field(default=None, description="当前风险等级")
    unresolved_turns: int = Field(default=0, description="连续未解决轮次")
    handoff_required: bool = Field(default=False, description="是否已经需要人工接入")
    handoff_reason: str | None = Field(default=None, description="当前转人工原因")
    merged_from_latest_message: bool = Field(default=False, description="本轮消息是否被归并到当前主问题单")
    secondary_issue_detected: bool = Field(default=False, description="本轮消息是否识别出次级问题")
    updated_at: datetime | None = Field(default=None, description="问题单最近更新时间")


class ComplaintMessageIntakeResult(BaseModel):
    """用户消息进入投诉域后的结构化结果。

    这个对象用于把归并决策、当前主问题单摘要和需要外发的流式事件统一打包给入口层。
    """

    resolution: ActiveTicketResolution = Field(..., description="本轮消息的 ticket 决策结果")
    ticket: TicketStreamSummary = Field(..., description="当前主问题单摘要")
    events: list[dict[str, Any]] = Field(default_factory=list, description="本轮需要发给前端的投诉域事件")
