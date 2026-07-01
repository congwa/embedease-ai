"""客诉模型测试

测试投诉域新增模型的表名、关键字段和主链路关系，确保 Phase 1 的数据库建模方向稳定。
"""

from app.models.agent_score_snapshot import AgentScoreSnapshot
from app.models.complaint_patrol_event import ComplaintPatrolEvent
from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket


class TestComplaintTicketModel:
    """测试问题单模型。"""

    def test_table_name(self):
        """测试问题单使用预期表名。"""
        assert ComplaintTicket.__tablename__ == "complaint_tickets"

    def test_has_primary_active_flag(self):
        """测试问题单具备主活动单标记字段。"""
        assert hasattr(ComplaintTicket, "is_primary_active")

    def test_has_issue_fields(self):
        """测试问题单包含主问题和次级问题字段。"""
        assert hasattr(ComplaintTicket, "primary_issue_tag")
        assert hasattr(ComplaintTicket, "secondary_issues")
        assert hasattr(ComplaintTicket, "secondary_issue_tags")

    def test_has_process_snapshot_fields(self):
        """测试问题单包含当前处理链路快照字段。"""
        assert hasattr(ComplaintTicket, "current_agent_tag")
        assert hasattr(ComplaintTicket, "current_node_key")
        assert hasattr(ComplaintTicket, "current_task_id")
        assert hasattr(ComplaintTicket, "unresolved_turns")

    def test_has_handoff_and_resolution_fields(self):
        """测试问题单包含转人工和结案字段。"""
        assert hasattr(ComplaintTicket, "handoff_required")
        assert hasattr(ComplaintTicket, "handoff_summary")
        assert hasattr(ComplaintTicket, "resolved_summary")
        assert hasattr(ComplaintTicket, "resolved_at")
        assert hasattr(ComplaintTicket, "closed_at")


class TestComplaintTaskModel:
    """测试问题单任务模型。"""

    def test_table_name(self):
        """测试任务模型表名正确。"""
        assert ComplaintTask.__tablename__ == "complaint_tasks"

    def test_has_execution_fields(self):
        """测试任务模型包含执行态字段。"""
        assert hasattr(ComplaintTask, "task_type")
        assert hasattr(ComplaintTask, "agent_tag")
        assert hasattr(ComplaintTask, "status")
        assert hasattr(ComplaintTask, "input_payload")
        assert hasattr(ComplaintTask, "output_payload")

    def test_has_review_fields(self):
        """测试任务模型包含 review 关联字段。"""
        assert hasattr(ComplaintTask, "review_required")
        assert hasattr(ComplaintTask, "review_status")
        assert hasattr(ComplaintTask, "retry_count")


class TestComplaintReviewModel:
    """测试审查记录模型。"""

    def test_table_name(self):
        """测试审查记录表名正确。"""
        assert ComplaintReview.__tablename__ == "complaint_reviews"

    def test_has_quality_fields(self):
        """测试审查记录包含质量判定字段。"""
        assert hasattr(ComplaintReview, "reviewer_agent_tag")
        assert hasattr(ComplaintReview, "status")
        assert hasattr(ComplaintReview, "score")
        assert hasattr(ComplaintReview, "reasons")
        assert hasattr(ComplaintReview, "suggested_next_agent")


class TestComplaintPatrolEventModel:
    """测试巡查事件模型。"""

    def test_table_name(self):
        """测试巡查事件表名正确。"""
        assert ComplaintPatrolEvent.__tablename__ == "complaint_patrol_events"

    def test_has_patrol_fields(self):
        """测试巡查事件包含异常检测字段。"""
        assert hasattr(ComplaintPatrolEvent, "event_type")
        assert hasattr(ComplaintPatrolEvent, "status")
        assert hasattr(ComplaintPatrolEvent, "detected_reason")
        assert hasattr(ComplaintPatrolEvent, "action_taken")


class TestAgentScoreSnapshotModel:
    """测试绩效快照模型。"""

    def test_table_name(self):
        """测试绩效快照表名正确。"""
        assert AgentScoreSnapshot.__tablename__ == "agent_score_snapshots"

    def test_has_score_fields(self):
        """测试绩效快照包含运营评分字段。"""
        assert hasattr(AgentScoreSnapshot, "agent_tag")
        assert hasattr(AgentScoreSnapshot, "pass_rate")
        assert hasattr(AgentScoreSnapshot, "handoff_rate")
        assert hasattr(AgentScoreSnapshot, "avg_review_score")
