"""客诉状态机规则

本文件的业务职责是集中定义 ticket、task、review 三类状态的允许流转，
避免编排链路把状态跳转规则散落在 router、service 和 handler 中。
"""

from __future__ import annotations

from collections.abc import Callable

from app.schemas.complaint import (
    ComplaintReviewStatus,
    ComplaintStatus,
    ComplaintTaskStatus,
)

TICKET_TRANSITIONS: dict[str, set[str]] = {
    ComplaintStatus.NEW.value: {
        ComplaintStatus.TRIAGED.value,
        ComplaintStatus.REWORK_REQUIRED.value,
        ComplaintStatus.HANDOFF_PENDING.value,
        ComplaintStatus.RESOLVED.value,
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.BLOCKED.value,
    },
    ComplaintStatus.TRIAGED.value: {
        ComplaintStatus.PLANNED.value,
        ComplaintStatus.HANDOFF_PENDING.value,
        ComplaintStatus.BLOCKED.value,
    },
    ComplaintStatus.PLANNED.value: {
        ComplaintStatus.IN_PROGRESS.value,
        ComplaintStatus.HANDOFF_PENDING.value,
        ComplaintStatus.BLOCKED.value,
    },
    ComplaintStatus.IN_PROGRESS.value: {
        ComplaintStatus.PENDING_REVIEW.value,
        ComplaintStatus.RESOLVED.value,
        ComplaintStatus.HANDOFF_PENDING.value,
        ComplaintStatus.BLOCKED.value,
    },
    ComplaintStatus.PENDING_REVIEW.value: {
        ComplaintStatus.IN_PROGRESS.value,
        ComplaintStatus.REWORK_REQUIRED.value,
        ComplaintStatus.HANDOFF_PENDING.value,
        ComplaintStatus.RESOLVED.value,
        ComplaintStatus.BLOCKED.value,
    },
    ComplaintStatus.REWORK_REQUIRED.value: {
        ComplaintStatus.PLANNED.value,
        ComplaintStatus.HANDOFF_PENDING.value,
        ComplaintStatus.BLOCKED.value,
    },
    ComplaintStatus.BLOCKED.value: {
        ComplaintStatus.PLANNED.value,
        ComplaintStatus.HANDOFF_PENDING.value,
        ComplaintStatus.CLOSED.value,
    },
    ComplaintStatus.HANDOFF_PENDING.value: {
        ComplaintStatus.HANDED_OFF.value,
        ComplaintStatus.CLOSED.value,
    },
    ComplaintStatus.HANDED_OFF.value: {
        ComplaintStatus.RESOLVED.value,
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.IN_PROGRESS.value,
    },
    ComplaintStatus.RESOLVED.value: {
        ComplaintStatus.CLOSED.value,
        ComplaintStatus.IN_PROGRESS.value,
    },
    ComplaintStatus.CLOSED.value: {
        ComplaintStatus.IN_PROGRESS.value,
    },
}

TASK_TRANSITIONS: dict[str, set[str]] = {
    ComplaintTaskStatus.QUEUED.value: {
        ComplaintTaskStatus.RUNNING.value,
        ComplaintTaskStatus.WAITING_REVIEW.value,
        ComplaintTaskStatus.DONE.value,
        ComplaintTaskStatus.FAILED.value,
        ComplaintTaskStatus.BLOCKED.value,
        ComplaintTaskStatus.CANCELLED.value,
    },
    ComplaintTaskStatus.RUNNING.value: {
        ComplaintTaskStatus.WAITING_REVIEW.value,
        ComplaintTaskStatus.DONE.value,
        ComplaintTaskStatus.FAILED.value,
        ComplaintTaskStatus.BLOCKED.value,
    },
    ComplaintTaskStatus.WAITING_REVIEW.value: {
        ComplaintTaskStatus.DONE.value,
        ComplaintTaskStatus.FAILED.value,
        ComplaintTaskStatus.BLOCKED.value,
    },
    ComplaintTaskStatus.DONE.value: set(),
    ComplaintTaskStatus.FAILED.value: {
        ComplaintTaskStatus.QUEUED.value,
        ComplaintTaskStatus.CANCELLED.value,
    },
    ComplaintTaskStatus.CANCELLED.value: set(),
    ComplaintTaskStatus.BLOCKED.value: {
        ComplaintTaskStatus.RUNNING.value,
        ComplaintTaskStatus.CANCELLED.value,
    },
}

REVIEW_TRANSITIONS: dict[str, set[str]] = {
    ComplaintReviewStatus.PENDING.value: {
        ComplaintReviewStatus.PASSED.value,
        ComplaintReviewStatus.REJECTED.value,
        ComplaintReviewStatus.ESCALATED.value,
    },
    ComplaintReviewStatus.PASSED.value: set(),
    ComplaintReviewStatus.REJECTED.value: set(),
    ComplaintReviewStatus.ESCALATED.value: set(),
}


def can_transition_ticket(from_status: str, to_status: str) -> bool:
    """判断问题单是否允许从当前状态流转到目标状态。

    这个方法服务于 ticket 状态推进校验，避免跳过 triage、review 或 handoff 节点。
    """

    if from_status == to_status:
        return True
    return to_status in TICKET_TRANSITIONS.get(from_status, set())


def can_transition_task(from_status: str, to_status: str) -> bool:
    """判断任务是否允许从当前状态流转到目标状态。

    这个方法服务于 triage、plan、execute、review 任务的统一约束。
    """

    if from_status == to_status:
        return True
    return to_status in TASK_TRANSITIONS.get(from_status, set())


def can_transition_review(from_status: str, to_status: str) -> bool:
    """判断审查记录是否允许从当前状态流转到目标状态。

    这个方法服务于 reviewer 从 pending 进入 passed、rejected 或 escalated 的校验。
    """

    if from_status == to_status:
        return True
    return to_status in REVIEW_TRANSITIONS.get(from_status, set())


def require_transition(
    *,
    entity_name: str,
    from_status: str,
    to_status: str,
    checker: Callable[[str, str], bool],
) -> None:
    """强制校验状态流转是否合法。

    这个方法服务于 service 层的保守状态控制，一旦发现非法跳转就立即中断请求，
    防止问题单出现不可解释的状态穿越。
    """

    if checker(from_status, to_status):
        return
    raise ValueError(f"{entity_name} 非法状态流转: {from_status} -> {to_status}")
