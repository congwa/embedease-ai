"""客诉领域服务

本目录的业务职责是承载 AI 虚拟人客诉系统的核心业务流转，
包括问题单归并、任务推进、审查决策和人工升级等能力。
"""

from app.services.complaint.executor_service import ExecutorService
from app.services.complaint.handoff_service import ComplaintHandoffService
from app.services.complaint.message_intake_service import ComplaintMessageIntakeService
from app.services.complaint.orchestrator import (
    ComplaintChatStreamOrchestrator,
    ComplaintConversationOrchestrator,
    ComplaintRunContext,
)
from app.services.complaint.patrol_service import PatrolOutcome, PatrolService
from app.services.complaint.planner_service import PlannerService
from app.services.complaint.review_service import ReviewService
from app.services.complaint.score_snapshot_service import ScoreSnapshotService
from app.services.complaint.state_machine import (
    can_transition_review,
    can_transition_task,
    can_transition_ticket,
    require_transition,
)
from app.services.complaint.task_service import TaskService
from app.services.complaint.ticket_merge_service import TicketMergeService
from app.services.complaint.ticket_service import TicketService

__all__ = [
    "ComplaintMessageIntakeService",
    "ComplaintChatStreamOrchestrator",
    "ComplaintConversationOrchestrator",
    "ComplaintHandoffService",
    "ComplaintRunContext",
    "ExecutorService",
    "PatrolOutcome",
    "PatrolService",
    "PlannerService",
    "ReviewService",
    "ScoreSnapshotService",
    "TaskService",
    "TicketMergeService",
    "TicketService",
    "can_transition_review",
    "can_transition_task",
    "can_transition_ticket",
    "require_transition",
]
