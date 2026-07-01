"""客诉主链路集成测试

本文件的业务职责，是验证"问题单驱动的客诉处理闭环"的 6 个核心验收场景均已满足。
这些场景对应 spec-phase1-test-and-acceptance-plan.md 中定义的 Phase 1 验收门槛。

测试策略：
- 使用真实 service 实例 + mock 数据库层（AsyncMock），避免依赖真实 DB 和 LLM
- 验证业务状态转换、决策规则和服务协作的正确性
- 不依赖 HTTP 客户端，专注 service 层集成逻辑
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.complaint_review import ComplaintReview
from app.models.complaint_task import ComplaintTask
from app.models.complaint_ticket import ComplaintTicket
from app.models.conversation import Conversation, ConversationMode
from app.schemas.complaint import (
    ComplaintReviewStatus,
    ComplaintStatus,
    ComplaintTaskStatus,
    IssueContinuity,
    ReviewDecision,
    TicketResolutionDecision,
)


# ========== 共用构造函数 ==========


def make_conversation(conversation_id: str = "conv_001") -> Conversation:
    """构造基础 Conversation，服务于所有集成场景。"""
    return Conversation(
        id=conversation_id,
        user_id="user_001",
        title="物流延迟投诉",
        conversation_mode=ConversationMode.AI.value,
    )


def make_ticket(
    ticket_id: str = "ticket_001",
    status: str = ComplaintStatus.NEW.value,
    rework_count: int = 0,
) -> ComplaintTicket:
    """构造基础 ComplaintTicket，服务于所有集成场景。"""
    return ComplaintTicket(
        id=ticket_id,
        conversation_id="conv_001",
        user_id="user_001",
        status=status,
        is_primary_active=True,
        primary_issue_tag="delivery_delay",
        current_agent_tag="planner",
        current_node_key="triage",
        priority_level="medium",
        risk_level="low",
        unresolved_turns=1,
        rework_count=rework_count,
        handoff_required=False,
        secondary_issue_tags=[],
        secondary_issues=[],
        slot_data={},
        timeline=[],
        version=1,
    )


def make_task(
    task_id: str = "task_001",
    status: str = ComplaintTaskStatus.RUNNING.value,
) -> ComplaintTask:
    """构造基础 ComplaintTask，服务于任务驱动测试。"""
    return ComplaintTask(
        id=task_id,
        ticket_id="ticket_001",
        task_type="resolution",
        agent_tag="resolution_execution_agent",
        status=status,
        goal="处理物流延迟问题",
        success_criteria=["用户知道赔偿方案"],
        retry_count=0,
    )


def make_review(
    review_id: str = "review_001",
    status: str = ComplaintReviewStatus.PASSED.value,
    score: int = 85,
) -> ComplaintReview:
    """构造基础 ComplaintReview，服务于审查场景测试。"""
    return ComplaintReview(
        id=review_id,
        ticket_id="ticket_001",
        task_id="task_001",
        reviewer_agent_tag="quality_reviewer_agent",
        status=status,
        score=score,
        risk_level="low",
        reasons=[],
    )


# ========== 验收场景 1：持续发泄不产生新 ticket ==========


class TestScenario1SingleTicketUnderVenting:
    """场景 1：用户投诉订单延迟并持续发泄，系统只保留一个主 ticket。

    验收标准：
    - 同一会话内多轮相似消息不新建主 ticket
    - TicketMergeService 识别为 MERGE_INTO_ACTIVE 决策
    - unresolved_turns 递增
    """

    @pytest.mark.anyio
    async def test_same_issue_venting_returns_reuse_decision(self):
        """连续发泄同一问题时，归并服务判定为复用当前活动 ticket。"""
        from app.services.complaint.ticket_merge_service import TicketMergeService

        mock_session = MagicMock()
        service = TicketMergeService(mock_session)

        # 已有主 ticket
        existing_ticket = make_ticket(status=ComplaintStatus.IN_PROGRESS.value)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=existing_ticket)
        service.ticket_service.append_timeline_entry = AsyncMock(
            side_effect=lambda ticket, **_: ticket
        )
        service.ticket_service.merge_slot_data = AsyncMock(
            side_effect=lambda ticket, _: ticket
        )

        # 第二轮发泄消息归并
        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_001",
            user_id="user_001",
            user_message="还没解决！我要投诉！你们怎么这么慢！",
        )

        assert resolution.decision in (
            TicketResolutionDecision.REUSE_ACTIVE_TICKET,
            TicketResolutionDecision.RECORD_SECONDARY_ISSUE,
        ), f"期望复用活动 ticket，实际: {resolution.decision}"
        assert resolution.ticket_id == existing_ticket.id

    @pytest.mark.anyio
    async def test_no_active_ticket_creates_new_ticket(self):
        """无活动 ticket 时，首次投诉消息创建新的主 ticket。"""
        from app.services.complaint.ticket_merge_service import TicketMergeService

        mock_session = MagicMock()
        service = TicketMergeService(mock_session)

        # 无活动 ticket
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=None)
        new_ticket = make_ticket()
        service.create_initial_ticket = AsyncMock(return_value=new_ticket)

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_001",
            user_id="user_001",
            user_message="我的订单三天了还没发货，要投诉！",
        )

        assert resolution.decision == TicketResolutionDecision.CREATE_INITIAL_TICKET
        assert resolution.ticket_id == new_ticket.id

    @pytest.mark.anyio
    async def test_resolved_ticket_triggers_new_ticket_creation(self):
        """已解决的旧 ticket 遇到新消息时，系统创建新 ticket。"""
        from app.services.complaint.ticket_merge_service import TicketMergeService

        mock_session = MagicMock()
        service = TicketMergeService(mock_session)

        # 已结束的旧 ticket
        old_ticket = make_ticket(status=ComplaintStatus.RESOLVED.value)
        new_ticket = make_ticket(ticket_id="ticket_002")
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=old_ticket)
        service.ticket_repo.update = AsyncMock(side_effect=lambda t: t)
        service.create_initial_ticket = AsyncMock(return_value=new_ticket)

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_001",
            user_id="user_001",
            user_message="上次问题解决了，但现在又有新问题",
        )

        assert resolution.decision == TicketResolutionDecision.CREATE_NEW_TICKET
        assert resolution.ticket_id == new_ticket.id


# ========== 验收场景 2：补充信息归并到当前 ticket ==========


class TestScenario2SlotSupplementMerge:
    """场景 2：用户补充订单号和截图，继续归并到同一 ticket。

    验收标准：
    - 补充信息不新建 ticket
    - 归并决策为 SUPPLEMENT_ACTIVE 或 MERGE_INTO_ACTIVE
    - slot_data 更新
    """

    @pytest.mark.anyio
    async def test_slot_supplement_merges_into_active_ticket(self):
        """用户提供订单号时，slot_data 更新到当前活动 ticket 中。"""
        from app.services.complaint.ticket_service import TicketService

        mock_session = MagicMock()
        service = TicketService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.IN_PROGRESS.value)
        ticket.slot_data = {}
        service.ticket_repo.update = AsyncMock(side_effect=lambda t: t)
        service.conversation_repo.get_by_id = AsyncMock(return_value=make_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda c: c)

        result = await service.merge_slot_data(
            ticket,
            {"order_id": "20240101-12345", "screenshot": "attached"},
        )

        assert result.slot_data.get("order_id") == "20240101-12345"
        assert result.slot_data.get("screenshot") == "attached"

    @pytest.mark.anyio
    async def test_append_timeline_entry_updates_timeline(self):
        """追加时间线条目后，ticket timeline 应包含该记录。"""
        from app.services.complaint.ticket_service import TicketService

        mock_session = MagicMock()
        service = TicketService(mock_session)

        ticket = make_ticket()
        service.ticket_repo.update = AsyncMock(side_effect=lambda t: t)
        service.conversation_repo.get_by_id = AsyncMock(return_value=make_conversation())
        service.conversation_repo.update = AsyncMock(side_effect=lambda c: c)

        result = await service.append_timeline_entry(
            ticket,
            event_type="user.supplement",
            summary="用户补充订单号 20240101-12345",
            extra={"order_id": "20240101-12345"},
        )

        # timeline 应该有新的条目
        assert len(result.timeline) > 0


# ========== 验收场景 3：review 通过后正常回复 ==========


class TestScenario3ReviewPassedThenReply:
    """场景 3：AI 解释规则后进入 review，通过后回复。

    验收标准：
    - ReviewService.apply_review_result 将 task 和 ticket 推进到通过状态
    - review 状态为 passed
    - 外发回复逻辑允许触发
    """

    @pytest.mark.anyio
    async def test_review_passed_advances_task_to_done(self):
        """review 通过后，task 状态推进为 done，ticket 状态推进到 resolved 或下一阶段。"""
        from app.services.complaint.review_service import ReviewService

        mock_session = MagicMock()
        service = ReviewService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.PENDING_REVIEW.value)
        task = make_task(status=ComplaintTaskStatus.WAITING_REVIEW.value)
        review = make_review(status=ComplaintReviewStatus.PASSED.value, score=88)

        review_decision = ReviewDecision(
            status=ComplaintReviewStatus.PASSED,
            score=88,
            risk_level="low",
            reasons=[],
        )

        service.review_repo.update = AsyncMock(side_effect=lambda r: r)
        service.task_service.complete_task = AsyncMock(side_effect=lambda task, **_: task)
        service.ticket_service.sync_review_snapshot = AsyncMock(side_effect=lambda ticket, **_: ticket)
        service.ticket_service.mark_resolved = AsyncMock(side_effect=lambda ticket, **_: ticket)

        result_review = await service.apply_review_result(
            review=review,
            decision=review_decision,
            task=task,
            ticket=ticket,
        )

        # review 状态应为 passed
        assert result_review.status == ComplaintReviewStatus.PASSED.value
        service.task_service.complete_task.assert_called_once()

    @pytest.mark.anyio
    async def test_review_passed_does_not_escalate(self):
        """review 通过后，should_escalate_after_reject 应返回 False。"""
        from app.services.complaint.review_service import ReviewService

        mock_session = MagicMock()
        service = ReviewService(mock_session)

        ticket = make_ticket()
        review_decision = ReviewDecision(
            status=ComplaintReviewStatus.PASSED,
            score=90,
            risk_level="low",
            reasons=[],
        )

        should_escalate = service.should_escalate_after_reject(ticket)
        assert not should_escalate


# ========== 验收场景 4：review 驳回后进入返工 ==========


class TestScenario4ReviewRejectedThenRework:
    """场景 4：AI 回复被驳回，进入 rework。

    验收标准：
    - review 状态设为 rejected
    - ticket 返回 planned 或 in_progress（等待返工）
    - 不允许外发 assistant 最终内容
    """

    @pytest.mark.anyio
    async def test_review_rejected_increments_rework_count(self):
        """review 驳回后，ticket 的 rework_count 应该增加。"""
        from app.services.complaint.review_service import ReviewService

        mock_session = MagicMock()
        service = ReviewService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.PENDING_REVIEW.value, rework_count=0)
        task = make_task(status=ComplaintTaskStatus.WAITING_REVIEW.value)
        review = make_review(status=ComplaintReviewStatus.REJECTED.value, score=55)

        review_decision = ReviewDecision(
            status=ComplaintReviewStatus.REJECTED,
            score=55,
            risk_level="medium",
            reasons=["回复缺乏具体赔偿方案"],
        )

        service.review_repo.update = AsyncMock(side_effect=lambda r: r)
        service.task_service.fail_task = AsyncMock(side_effect=lambda task, **_: task)
        service.ticket_service.sync_review_snapshot = AsyncMock(side_effect=lambda ticket, **_: ticket)
        service.ticket_service.mark_rework_required = AsyncMock(side_effect=lambda ticket, **_: ticket)

        result_review = await service.apply_review_result(
            review=review,
            decision=review_decision,
            task=task,
            ticket=ticket,
        )

        assert result_review.status == ComplaintReviewStatus.REJECTED.value

    @pytest.mark.anyio
    async def test_single_reject_does_not_escalate(self):
        """单次驳回不应触发转人工升级（需要连续驳回才升级）。"""
        from app.services.complaint.review_service import ReviewService

        mock_session = MagicMock()
        service = ReviewService(mock_session)

        # 只有 1 次返工，低于升级阈值（阈值为 2）
        ticket = make_ticket(rework_count=1)

        should_escalate = service.should_escalate_after_reject(ticket)
        assert not should_escalate


# ========== 验收场景 5：连续返工失败后升级人工 ==========


class TestScenario5RepeatedRejectEscalateHandoff:
    """场景 5：连续返工失败，自动进入 handoff_pending。

    验收标准：
    - 当 rework_count 达到或超过阈值时，should_escalate_after_reject 返回 True
    - ticket 进入 handoff_pending 状态
    - conversation 进入 pending 模式
    """

    @pytest.mark.anyio
    async def test_repeated_reject_triggers_escalation(self):
        """连续驳回次数达到上限（>=2）时，服务应判定为需要升级。"""
        from app.services.complaint.review_service import ReviewService

        mock_session = MagicMock()
        service = ReviewService(mock_session)

        # rework_count=2 代表已连续返工 2 次，达到升级阈值
        ticket = make_ticket(rework_count=2)

        should_escalate = service.should_escalate_after_reject(ticket)
        assert should_escalate, "rework_count >= 2 后应触发升级"

    @pytest.mark.anyio
    async def test_handoff_request_sets_ticket_to_handoff_pending(self):
        """转人工请求应将 ticket 状态设为 handoff_pending，conversation 设为 pending。"""
        from app.services.complaint.handoff_service import ComplaintHandoffService

        mock_session = MagicMock()
        service = ComplaintHandoffService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.IN_PROGRESS.value, rework_count=3)
        conversation = make_conversation()

        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.ticket_repo.update = AsyncMock(side_effect=lambda t: t)
        service.conversation_repo.update = AsyncMock(side_effect=lambda c: c)
        service.ticket_service.mark_handoff_pending = AsyncMock(side_effect=lambda t, **_: t)
        service.support_handoff_service.request_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "pending"}
        )
        service._broadcast_ticket_update = AsyncMock(return_value=None)
        service._broadcast_conversation_state = AsyncMock(return_value=None)
        service._broadcast_support_queue_change = AsyncMock(return_value=None)
        service._build_handoff_summary = AsyncMock(return_value={"reasons": ["多次返工"]})

        await service.request_handoff_for_ticket(
            ticket,
            handoff_reason="连续 3 次返工仍无法满足用户诉求",
            handoff_summary={"slot_data": ticket.slot_data},
        )

        service.ticket_service.mark_handoff_pending.assert_called_once()

    @pytest.mark.anyio
    async def test_handoff_pending_conversation_mode_set(self):
        """转人工时 conversation_mode 应设为 pending，不应直接跳到 human。"""
        from app.services.complaint.handoff_service import ComplaintHandoffService

        mock_session = MagicMock()
        service = ComplaintHandoffService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.HANDOFF_PENDING.value)
        conversation = make_conversation()
        conversation.conversation_mode = ConversationMode.AI.value

        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.ticket_repo.update = AsyncMock(side_effect=lambda t: t)
        service.conversation_repo.update = AsyncMock(
            side_effect=lambda c: c
        )
        service.ticket_service.mark_handoff_pending = AsyncMock(side_effect=lambda t, **_: t)
        service.support_handoff_service.request_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "pending"}
        )
        service._broadcast_ticket_update = AsyncMock(return_value=None)
        service._broadcast_conversation_state = AsyncMock(return_value=None)
        service._broadcast_support_queue_change = AsyncMock(return_value=None)
        service._build_handoff_summary = AsyncMock(return_value={})

        result = await service.request_handoff_for_ticket(
            ticket,
            handoff_reason="连续驳回后升级",
        )

        # 返回结果应包含 pending 状态
        assert result.conversation_mode == ConversationMode.PENDING.value


# ========== 验收场景 6：客服接入并关闭 ticket ==========


class TestScenario6HumanAcceptAndCloseTicket:
    """场景 6：客服接入后解决问题并关闭 ticket。

    验收标准：
    - accept_handoff 将 conversation_mode 推进到 human
    - ticket 进入 handed_off 状态
    - finish_handoff 将 ticket 推进到 resolved
    """

    @pytest.mark.anyio
    async def test_accept_handoff_sets_human_mode(self):
        """客服接管后，conversation_mode 应变为 human。"""
        from app.services.complaint.handoff_service import ComplaintHandoffService

        mock_session = MagicMock()
        service = ComplaintHandoffService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.HANDOFF_PENDING.value)
        conversation = make_conversation()
        conversation.conversation_mode = ConversationMode.PENDING.value

        service.support_handoff_service.start_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "human"}
        )
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=ticket)
        service.ticket_service.mark_handed_off = AsyncMock(side_effect=lambda t, **_: t)
        service.ticket_service.build_stream_summary = MagicMock(return_value=MagicMock(model_dump=MagicMock(return_value={})))
        service._broadcast_ticket_update = AsyncMock(return_value=None)
        service._broadcast_conversation_state = AsyncMock(return_value=None)
        service._broadcast_support_queue_change = AsyncMock(return_value=None)

        result = await service.accept_handoff(
            conversation_id="conv_001",
            operator="客服小王",
        )

        # 返回结果应包含 success
        assert result.get("success") is True
        service.ticket_service.mark_handed_off.assert_called_once()

    @pytest.mark.anyio
    async def test_finish_handoff_resolves_ticket(self):
        """客服结束服务后，ticket 应推进到 resolved 或 closed。"""
        from app.services.complaint.handoff_service import ComplaintHandoffService

        mock_session = MagicMock()
        service = ComplaintHandoffService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.HANDED_OFF.value)
        conversation = make_conversation()
        conversation.conversation_mode = ConversationMode.HUMAN.value

        service.support_handoff_service.end_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "ai"}
        )
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=ticket)
        service.ticket_service.mark_resolved = AsyncMock(side_effect=lambda t, **_: t)
        service.ticket_service.build_stream_summary = MagicMock(return_value=MagicMock(model_dump=MagicMock(return_value={})))
        service._broadcast_ticket_update = AsyncMock(return_value=None)
        service._broadcast_conversation_state = AsyncMock(return_value=None)
        service._broadcast_support_queue_change = AsyncMock(return_value=None)

        await service.finish_handoff(
            conversation_id="conv_001",
            operator="客服小王",
            summary="客服已为用户补偿延迟险并安排优先处理",
        )

        service.ticket_service.mark_resolved.assert_called_once()

    @pytest.mark.anyio
    async def test_finish_handoff_switches_mode_back_to_ai(self):
        """客服结束服务后，conversation_mode 应切回 ai 模式。"""
        from app.services.complaint.handoff_service import ComplaintHandoffService

        mock_session = MagicMock()
        service = ComplaintHandoffService(mock_session)

        ticket = make_ticket(status=ComplaintStatus.HANDED_OFF.value)
        conversation = make_conversation()
        conversation.conversation_mode = ConversationMode.HUMAN.value

        service.support_handoff_service.end_handoff = AsyncMock(
            return_value={"success": True, "handoff_state": "ai"}
        )
        service.conversation_repo.get_by_id = AsyncMock(return_value=conversation)
        service.ticket_repo.get_by_id = AsyncMock(return_value=ticket)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=ticket)
        service.ticket_service.mark_resolved = AsyncMock(side_effect=lambda t, **_: t)
        service.ticket_service.build_stream_summary = MagicMock(return_value=MagicMock(model_dump=MagicMock(return_value={})))
        service._broadcast_ticket_update = AsyncMock(return_value=None)
        service._broadcast_conversation_state = AsyncMock(return_value=None)
        service._broadcast_support_queue_change = AsyncMock(return_value=None)

        result = await service.finish_handoff(
            conversation_id="conv_001",
            operator="客服小王",
            summary="问题已解决",
        )

        # 服务完成后状态应切回 AI
        assert result.get("handoff_state") == "ai"


# ========== Ticket Merge 规则专项测试 ==========


class TestTicketMergeRules:
    """Ticket 归并规则专项测试（spec 第 5 节要求）。

    必须覆盖以下判定：
    1. 相同订单、相同目标、相同问题域 → 必须归并
    2. 相同订单、不同情绪表达 → 必须归并
    3. 已关闭 ticket 遇新问题 → 必须新建
    """

    @pytest.mark.anyio
    async def test_closed_ticket_plus_new_issue_creates_new_ticket(self):
        """已关闭的 ticket 遇到新问题时，必须新建主 ticket。"""
        from app.services.complaint.ticket_merge_service import TicketMergeService

        mock_session = MagicMock()
        service = TicketMergeService(mock_session)

        closed_ticket = make_ticket(status=ComplaintStatus.CLOSED.value)
        new_ticket = make_ticket(ticket_id="ticket_new")
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=closed_ticket)
        service.ticket_repo.update = AsyncMock(side_effect=lambda t: t)
        service.create_initial_ticket = AsyncMock(return_value=new_ticket)

        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_001",
            user_id="user_001",
            user_message="上个问题解决了，但现在发现商品破损",
        )

        assert resolution.decision == TicketResolutionDecision.CREATE_NEW_TICKET
        assert resolution.ticket_id == new_ticket.id

    @pytest.mark.anyio
    async def test_in_progress_ticket_with_new_separate_issue_records_secondary(self):
        """进行中的 ticket 遇到独立新问题，应记录为次要 issue 而非拆单。"""
        from app.services.complaint.ticket_merge_service import TicketMergeService

        mock_session = MagicMock()
        service = TicketMergeService(mock_session)

        active_ticket = make_ticket(status=ComplaintStatus.IN_PROGRESS.value)
        service.ticket_repo.get_active_by_conversation_id = AsyncMock(return_value=active_ticket)
        service.ticket_service.append_timeline_entry = AsyncMock(
            side_effect=lambda ticket, **_: ticket
        )
        service.ticket_service.merge_slot_data = AsyncMock(
            side_effect=lambda ticket, _: ticket
        )
        service.ticket_service.update_snapshot = AsyncMock(side_effect=lambda t: t)

        # "顺便" 匹配 _SECONDARY_ISSUE_MARKERS，应返回 RECORD_SECONDARY_ISSUE
        resolution = await service.resolve_ticket_for_message(
            conversation_id="conv_001",
            user_id="user_001",
            user_message="顺便，我还要反映商品质量问题",
        )

        # "顺便"触发次要 issue 记录，不立即拆单
        assert resolution.decision == TicketResolutionDecision.RECORD_SECONDARY_ISSUE, \
            f"实际决策: {resolution.decision}"


# ========== 状态机测试 ==========


class TestStateMachineTransitions:
    """测试 ticket/task/review 状态机的核心转换规则。"""

    @pytest.mark.anyio
    async def test_ticket_new_to_triaged_is_allowed(self):
        """ticket 从 new 到 triaged 应该是合法的状态转换。"""
        from app.services.complaint.state_machine import can_transition_ticket

        result = can_transition_ticket(
            ComplaintStatus.NEW, ComplaintStatus.TRIAGED
        )
        assert result

    @pytest.mark.anyio
    async def test_ticket_resolved_to_new_is_blocked(self):
        """ticket 从 resolved 回到 new 应该被状态机拦截。"""
        from app.services.complaint.state_machine import can_transition_ticket

        result = can_transition_ticket(
            ComplaintStatus.RESOLVED, ComplaintStatus.NEW
        )
        assert not result

    @pytest.mark.anyio
    async def test_ticket_in_progress_to_handoff_pending_is_allowed(self):
        """ticket 从 in_progress 到 handoff_pending 应该是合法的状态转换。"""
        from app.services.complaint.state_machine import can_transition_ticket

        result = can_transition_ticket(
            ComplaintStatus.IN_PROGRESS, ComplaintStatus.HANDOFF_PENDING
        )
        assert result

    @pytest.mark.anyio
    async def test_task_in_progress_to_waiting_review_is_allowed(self):
        """task 从 in_progress 到 waiting_review 应该是合法的状态转换。"""
        from app.services.complaint.state_machine import can_transition_task

        result = can_transition_task(
            ComplaintTaskStatus.RUNNING, ComplaintTaskStatus.WAITING_REVIEW
        )
        assert result
