# AI 虚拟人客诉系统实施状态分析

> 本文档基于 `phase1-detailed-execution-plan.md` 和 `virtual-customer-complaint-system-full-implementation-plan.md` 对当前代码实现进行全面对比分析，标注已完成、部分完成和未完成的模块。
>
> **最后更新**：Phase 1 完整交付 + Executor/Planner 架构升级为 LLM + Tools（`langchain>=1.2.15` / `langgraph>=1.1.6`）

---

## 1. 总体完成度概览

| 阶段　　| 计划模块数 | 已完成 | 部分完成 | 未完成 | 完成度　　　　　|
| ---------| ------------| --------| ----------| --------| -----------------|
| Phase 1 | 15 步　　　| 15　　 | 0　　　　| 0　　　| **100%**　　　　|
| Phase 2 | 4 项　　　 | 4　　　| 0　　　　| 0　　　| 100% (提前实现) |
| Phase 3 | 4 项　　　 | 4　　　| 0　　　　| 0　　　| **100%**　　　　|

**核心判断**：Phase 1 全部 15 步均已完成，系统具备完整的"识别 → 执行 → 审查 → 升级/解决"主闭环，并附带调度任务、联调测试和 Phase 2/3 提前实现。此后 `PlannerService` 和 `ExecutorService` 均已升级为 **LLM + Tools 架构**（带规则引擎降级保障），complaint tools 首次真正接入主处理链路。

---

## 2. Phase 1 详细对比

### 2.1 第 1 步：领域枚举与 Schema ✅ 100%

**计划要求**：
- `backend/app/schemas/complaint.py` 定义核心枚举
- `complaint_ticket.py`, `complaint_task.py`, `complaint_review.py`, `complaint_patrol.py`

**实现状态**：
- `@/backend/app/schemas/complaint.py:1-249` 已定义：
  - `ConversationMode`, `ComplaintStatus`, `ComplaintTaskStatus`, `ComplaintReviewStatus`, `ComplaintPatrolStatus`
  - `IssueContinuity`, `TicketResolutionDecision`
  - `ActiveTicketResolution`, `ReviewDecision`, `ComplaintTriageResult`, `PlannerDecision`, `ExecutorResult`, `HandoffRequestResult`, `TicketStreamSummary`, `ComplaintMessageIntakeResult`
- 所有枚举和结构化结果均已实现，无裸字符串状态值

**完成判定**：✅ 没有任何 service 再使用裸字符串写状态值

---

### 2.2 第 2 步：数据库模型与迁移 ✅ 100%

**计划要求**：
- 修改 `Conversation` 模型，新增客诉快照字段
- 新增 `ComplaintTicket`, `ComplaintTask`, `ComplaintReview`, `ComplaintPatrolEvent`, `AgentScoreSnapshot`

**实现状态**：

**Conversation 扩展** (`@/backend/app/models/conversation.py:133-194`)：
- `conversation_mode` ✅
- `current_ticket_id` ✅
- `complaint_status` ✅
- `primary_issue_tag` ✅
- `current_agent_tag` ✅
- `current_node_key` ✅
- `priority_level` ✅
- `risk_level` ✅
- `unresolved_turns` ✅
- `review_status` ✅
- `review_score` ✅
- `block_reason` ✅
- `secondary_issues` ✅
- 保留 `handoff_state` 兼容字段 ✅

**ComplaintTicket** (`@/backend/app/models/complaint_ticket.py:26-188`)：
- 完整字段集：`id`, `conversation_id`, `user_id`, `status`, `is_primary_active`, `parent_ticket_id`, `superseded_by_ticket_id`, `issue_fingerprint`, `primary_issue_tag`, `secondary_issue_tags`, `secondary_issues`, `sentiment`, `severity`, `priority_level`, `risk_level`, `current_agent_tag`, `current_task_id`, `current_node_key`, `unresolved_turns`, `rework_count`, `handoff_required`, `handoff_reason`, `handoff_summary`, `resolved_summary`, `slot_data`, `timeline`, `version`, `resolved_at`, `closed_at`
- 关联关系：`conversation`, `user`, `tasks`, `reviews`, `patrol_events`

**ComplaintTask** (`@/backend/app/models/complaint_task.py`)：
- 完整字段集：`id`, `ticket_id`, `task_type`, `assigned_agent_tag`, `status`, `goal`, `success_criteria`, `input_snapshot`, `output_payload`, `failure_reason`, `started_at`, `finished_at`, `created_at`, `updated_at`

**ComplaintReview** (`@/backend/app/models/complaint_review.py`)：
- 完整字段集：`id`, `ticket_id`, `task_id`, `reviewer_agent_tag`, `status`, `score`, `risk_level`, `reasons`, `suggested_next_agent`, `review_payload`, `created_at`

**ComplaintPatrolEvent** (`@/backend/app/models/complaint_patrol_event.py`)：
- 完整字段集：`id`, `ticket_id`, `task_id`, `event_type`, `status`, `detected_reason`, `action_taken`, `result_payload`, `created_at`, `resolved_at`

**AgentScoreSnapshot** (`@/backend/app/models/agent_score_snapshot.py`)：
- Phase 3 模型已提前实现

**完成判定**：✅ 本地迁移可执行，ORM 能成功创建和查询 ticket/task/review/patrol 数据

---

### 2.3 第 3 步：Repository 层 ✅ 100%

**计划要求**：
- 新增 5 个 repository 文件

**实现状态**：
- `@/backend/app/repositories/complaint_ticket.py` ✅
  - `get_by_id`, `get_active_by_conversation_id`, `list_by_conversation_id`, `create_ticket`, `update_ticket`, `set_primary_active`, `close_ticket`, `list_primary_active_by_statuses`, `list_primary_active_with_rework_at_least`
- `@/backend/app/repositories/complaint_task.py` ✅
- `@/backend/app/repositories/complaint_review.py` ✅
- `@/backend/app/repositories/complaint_patrol_event.py` ✅
- `@/backend/app/repositories/agent_score_snapshot.py` ✅

**完成判定**：✅ 所有 complaint service 不直接写 SQLAlchemy 业务逻辑细节

---

### 2.4 第 4 步：Service 层 ✅ 100%

**计划要求**：
- 新增 6 个 service 文件

**实现状态**：

**state_machine.py** (`@/backend/app/services/complaint/state_machine.py:1-170`)：
- `TICKET_TRANSITIONS` 状态流转表 ✅
- `TASK_TRANSITIONS` 状态流转表 ✅
- `REVIEW_TRANSITIONS` 状态流转表 ✅
- `can_transition_ticket()`, `can_transition_task()`, `can_transition_review()`, `require_transition()` ✅

**ticket_service.py** (`@/backend/app/services/complaint/ticket_service.py`)：
- `get_or_create_active_ticket()` ✅
- `resolve_active_ticket_for_message()` ✅
- `append_message_context_to_ticket()` ✅
- `mark_ticket_handoff_pending()` ✅
- `mark_ticket_resolved()` ✅
- `mark_ticket_closed()` ✅
- `set_current_agent()`, `set_current_node()`, `set_current_task()` ✅
- `update_classification()` ✅
- `merge_slot_data()` ✅
- `append_timeline_entry()` ✅
- `build_stream_summary()` ✅

**task_service.py** (`@/backend/app/services/complaint/task_service.py`)：
- `create_task()`, `create_task_from_plan()` ✅
- `start_task()` ✅
- `complete_task()` ✅
- `mark_task_waiting_review()` ✅
- `mark_task_failed()` ✅
- `update_output_payload()` ✅

**review_service.py** (`@/backend/app/services/complaint/review_service.py`)：
- `build_review_input()` ✅
- `create_pending_review()` ✅
- `apply_review_result()` ✅
- `run_review()` ✅
- `should_escalate_after_reject()` ✅

**handoff_service.py** (`@/backend/app/services/complaint/handoff_service.py:1-359`)：
- `request_handoff_for_ticket()` ✅
- `request_handoff_for_conversation()` ✅
- `accept_handoff()` ✅
- `finish_handoff()` ✅
- `_build_handoff_summary()` ✅
- `_broadcast_*` 系列方法 ✅

**orchestrator.py** (`@/backend/app/services/complaint/orchestrator.py:1-915`)：
- `handle_user_message()` ✅
- `prepare_run()` ✅
- `execute_run()` ✅
- `_run_front_desk()` ✅
- `_detect_primary_issue_tag()`, `_detect_sentiment()`, `_detect_risk_level()` ✅
- `_broadcast_ticket_update()`, `_broadcast_conversation_state()` ✅

**额外实现**（计划外但已存在）：
- `ticket_merge_service.py` - 归并/拆单服务
- `message_intake_service.py` - 消息入口服务
- `planner_service.py` - 规划服务（**LLM 结构化输出** `with_structured_output(PlannerDecision)`，降级为 5 优先级规则引擎）
- `executor_service.py` - 执行服务（**LLM + 4 个 complaint tools ReAct 循环**，降级为规则模板）
- `patrol_service.py` - 巡查服务（Phase 2 提前实现）
- `score_snapshot_service.py` - 绩效快照服务（Phase 3 提前实现）

**完成判定**：✅ 主业务流已经不需要在 router 中直接写复杂逻辑

---

### 2.5 第 5 步：Handoff 服务改造 ✅ 100%

**计划要求**：
- 改造 `backend/app/services/support/handoff.py`
- 新增 `request_handoff()` 实现 pending 状态
- 保留但重定义 `start_handoff()` 实现 pending → human

**实现状态**：
- `ComplaintHandoffService` 完整实现了两段式 handoff
- `request_handoff_for_ticket()` 设置 `conversation_mode = pending`, `ticket.status = handoff_pending`
- `accept_handoff()` 实现 `pending → human`
- `finish_handoff()` 实现人工处理完成后 ticket 状态更新

**完成判定**：✅ 系统不再出现 AI 直接跳 HUMAN 的粗暴切换

---

### 2.6 第 6 步：Chat 主入口改造 ✅ 100%

**计划要求**：
- 修改 `backend/app/routers/chat.py`
- AI mode 调 `ComplaintConversationOrchestrator.handle_user_message()`

**实现状态** (`@/backend/app/routers/chat.py:100-114`)：
```python
if not is_human_mode:
    complaint_run_context = await complaint_orchestrator.handle_user_message(
        conversation_id=request_data.conversation_id,
        user_id=request_data.user_id,
        user_message_id=user_message.id,
        user_message=request_data.message,
    )
    complaint_initial_events = complaint_run_context.pre_stream_events
```

**完成判定**：✅ `chat.py` 中已经出现 complaint orchestrator

---

### 2.7 第 7 步：Chat Stream 事件 ✅ 100%

**计划要求**：
- 修改 `backend/app/services/chat_stream.py`, `backend/app/schemas/events.py`
- 在事件流中插入 complaint 领域事件

**实现状态** (`@/backend/app/schemas/events.py:81-96`)：
- `ComplaintEventType` 枚举定义了全部事件：
  - `COMPLAINT_TICKET_CREATED`, `COMPLAINT_TICKET_MERGED`, `COMPLAINT_TICKET_UPDATED`
  - `COMPLAINT_SECONDARY_ISSUE_DETECTED`
  - `COMPLAINT_TASK_CREATED`, `COMPLAINT_TASK_STARTED`, `COMPLAINT_TASK_COMPLETED`
  - `COMPLAINT_REVIEW_PENDING`, `COMPLAINT_REVIEW_PASSED`, `COMPLAINT_REVIEW_REJECTED`
  - `COMPLAINT_BLOCKED`, `COMPLAINT_HANDOFF_REQUESTED`
- `StreamEventType` 已包含所有 complaint 事件 (`@/backend/app/schemas/events.py:205-217`)

**完成判定**：✅ 前端收到事件后，可以画出当前处理阶段

---

### 2.8 第 8 步：Agent 配置与运行时 ✅ 100%

**计划要求**：
- 修改 `backend/app/models/agent.py`, `backend/app/schemas/agent.py`
- 新增字段：`role_tag`, `business_domain`, `skill_bundle_ids`, `knowledge_scope`, `review_schema_name`, `handoff_rules`
- factory 层增加 complaint 角色构建分支

**实现状态**：
- `@/backend/app/models/agent.py` 新增全部 6 个 complaint 角色字段 ✅
- `@/backend/app/schemas/agent.py` 所有 Agent schema 和 `AgentConfig` 均已扩展对应字段 ✅
- 数据库自动迁移兼容旧数据（`migrate_schema` / `ALTER TABLE IF NOT EXISTS`）✅
- `@/backend/app/services/agent/tools/registry.py` 已按 `role_tag=complaint` 路由加载专属工具 ✅

**完成判定**：✅ Agent 角色字段可通过配置管理，启动时自动迁移兼容旧数据

---

### 2.9 第 9 步：Complaint Tools ✅ 100%

**计划要求**：
- 新增 `backend/app/services/agent/tools/complaint/` 目录
- 新增 `faq_search.py`, `policy_search.py`, `case_sop_search.py`, `handoff_create.py`

**实现状态**：
- `@/backend/app/services/agent/tools/complaint/__init__.py` ✅
- `@/backend/app/services/agent/tools/complaint/faq_search.py` ✅
- `@/backend/app/services/agent/tools/complaint/policy_search.py` ✅
- `@/backend/app/services/agent/tools/complaint/case_sop_search.py` ✅
- `@/backend/app/services/agent/tools/complaint/handoff_create.py` ✅
- `@/backend/app/services/agent/tools/registry.py` 已注册全部 4 个工具并按 `role_tag=complaint` 路由 ✅

**完成判定**：✅ complaint 角色 agent 可通过工具调用 FAQ、政策、SOP 检索和转人工创建

---

### 2.10 第 10 步：Support API ✅ 100%

**计划要求**：
- 新增 ticket 相关接口
- 扩展会话列表响应

**实现状态** (`@/backend/app/routers/support.py:1-524`)：
- `GET /api/v1/support/conversations/{conversation_id}/active-ticket` ✅
- `GET /api/v1/support/conversations/{conversation_id}/tickets` ✅
- `GET /api/v1/support/tickets/{ticket_id}` ✅
- `POST /api/v1/support/tickets/{ticket_id}/resolve` ✅
- `POST /api/v1/support/tickets/{ticket_id}/reopen` ✅
- 会话列表响应包含：`ticket_status`, `primary_issue_tag`, `current_agent_tag`, `priority_level`, `review_status`, `review_score`, `block_reason` ✅

**完成判定**：✅ 客服端已经能以问题单视角取数

---

### 2.11 第 11 步：前端 Store ✅ 100%

**计划要求**：
- 修改 `frontend/stores/support-store.ts`
- 新增状态字段和 action

**实现状态**：

**support-workbench-store.ts** (`@/frontend/stores/support-workbench-store.ts:1-257`)：
- `ticket_status` ✅
- `primary_issue_tag` ✅
- `current_agent_tag` ✅
- `priority_level` ✅
- `risk_level` ✅
- `review_status` ✅
- `review_score` ✅
- `secondary_issues` ✅
- `pendingConversationCount`, `highRiskConversationCount`, `reworkConversationCount`, `activeComplaintCount` ✅
- `patchConversation()` action ✅

**support-store.ts**（会话详情页）：
- `currentTicket`, `reviewSummary`, `recentTasks`, `secondaryIssues`, `handoffSummary`, `handoffReason` ✅
- `updateConversationState()` action ✅

**完成判定**：✅ 前端不再只能维护 handoff 状态

---

### 2.12 第 12 步：用户侧聊天页 ✅ 100%

**计划要求**：
- 用户侧展示：当前问题标签、当前处理阶段、是否待补充资料、是否已提交人工
- 最小展示，不做复杂 UI

**实现状态**：
- `@/frontend/components/features/chat/ComplaintStatusBar.tsx` 新增状态栏组件 ✅
  - 显示当前问题标签（`primary_issue_tag`）
  - 显示处理阶段（已识别 / 处理中 / 审查中 / 已解决 / 转人工等）
  - 转人工时展示明确提示
- `@/frontend/components/features/chat/ChatContent.tsx` 已集成 `ComplaintStatusBar` ✅
  - 从 SSE timeline 中提取 complaint 事件并传入状态栏
- complaint SSE 事件消费已在 timeline reducer 中处理 ✅

**完成判定**：✅ 用户侧可看到问题处理进度，并在转人工时看到明确提示

---

### 2.13 第 13 步：客服工作台 ✅ 100%

**计划要求**：
- 会话列表页增加：状态筛选、标签筛选、风险等级展示、blocked 标记
- 详情页增加：当前主 ticket 卡片、当前 task 卡片、review 卡片、collected slots 卡片、handoff 摘要卡片

**实现状态**：

**列表页** (`@/frontend/app/support/page.tsx:1-392`)：
- 按 `priorityState` 分组（pending/human/ai）✅
- 显示 `pendingConversationCount`, `highRiskConversationCount`, `reworkConversationCount`, `activeComplaintCount` ✅
- 支持筛选和排序 ✅

**详情页** (`@/frontend/app/support/[conversationId]/page.tsx:1-1346`)：
- `ComplaintWorkbenchPanel` 组件 ✅
- `ComplaintTicketHistoryPanel` 组件 ✅
- `ComplaintLiveEventStream` 组件 ✅
- 显示 `currentTicket`, `reviewSummary`, `recentTasks`, `secondaryIssues`, `handoffSummary` ✅

**完成判定**：✅ 客服打开会话时，能第一眼看到"这单是什么问题、处理到哪一步、为什么转人工"

---

### 2.14 第 14 步：测试 ✅ 100%

**计划要求**：
- 新增 `backend/tests/services/complaint/` 目录
- 必测场景覆盖

**实现状态** (`@/backend/tests/services/complaint/`)：
- `test_complaint_handoff_service.py` ✅
- `test_executor_service.py` ✅
- `test_message_intake_service.py` ✅
- `test_orchestrator_realtime.py` ✅
- `test_orchestrator_stream.py` ✅
- `test_patrol_service.py` ✅
- `test_planner_service.py` ✅
- `test_review_service.py` ✅
- `test_score_snapshot_service.py` ✅
- `test_task_service.py` ✅
- `test_ticket_merge_service.py` ✅
- `test_ticket_service.py` ✅
- `__init__.py` ✅

**必测场景覆盖**：
1. 无活动 ticket 时新建 ticket ✅
2. 有活动 ticket 时归并消息 ✅
3. 新问题高置信度拆单 ✅
4. review 通过 ✅
5. review 驳回返工 ✅
6. review 连续驳回后转人工 ✅
7. pending → human ✅
8. human → resolved ✅

**完成判定**：✅ complaint 主链路的关键状态转换都有测试保护

---

### 2.15 第 15 步：联调验收 ✅ 100%

**计划要求**：
- 后端 API 自测
- SSE 事件联调
- WebSocket 状态联调
- 前端工作台联调
- 人工升级联调

**实现状态**：`@/backend/tests/integration/chat/test_complaint_flow.py` 覆盖全部 6 个验收用例（21 个测试，全部通过）

| 验收用例 | 对应测试 | 状态 |
|---------|---------|------|
| 1. 持续发泄不新建 ticket | `TestScenario1SingleTicketUnderVenting` | ✅ |
| 2. 补充信息归并同一 ticket | `TestScenario2SlotSupplementMerge` | ✅ |
| 3. review 通过后正常回复 | `TestScenario3ReviewPassedThenReply` | ✅ |
| 4. review 驳回进入 rework | `TestScenario4ReviewRejectedThenRework` | ✅ |
| 5. 连续返工自动进入 handoff_pending | `TestScenario5RepeatedRejectEscalateHandoff` | ✅ |
| 6. 客服接入并关闭 ticket | `TestScenario6HumanAcceptAndCloseTicket` | ✅ |

额外覆盖：`TestTicketMergeRules`（归并规则专项）、`TestStateMachineTransitions`（状态机转换）

**完成判定**：✅ 21 个验收测试全部通过，业务主链路关键路径均有自动化保护

---

## 3. Phase 2 完成状态（提前实现）

**计划要求**：
- 新增 `ComplaintPatrolEvent` ✅
- 新增 `complaint_patrol_task` ✅
- 支持 blocked 自动恢复 ✅
- 支持 pending_review 超时升级 ✅
- 支持 handoff_pending 超时告警 ✅

**实现状态**：
- `@/backend/app/services/complaint/patrol_service.py:1-449` 完整实现
- `@/backend/app/scheduler/tasks/complaint_patrol.py` ✅
- `run_patrol()` 方法覆盖所有场景
- 返工死循环升级 ✅

---

## 4. Phase 3 完成状态（提前实现）

**计划要求**：
- 新增 `AgentScoreSnapshot` ✅
- 新增分数统计任务 ✅
- 新增驳回原因分析 ✅
- 新增知识缺口任务 ✅

**实现状态**：
- `@/backend/app/models/agent_score_snapshot.py` ✅
- `@/backend/app/services/complaint/score_snapshot_service.py` ✅
- `@/backend/app/scheduler/tasks/complaint_score_snapshot.py` ✅
- `@/backend/app/repositories/agent_score_snapshot.py` ✅
- `@/backend/app/scheduler/tasks/complaint_knowledge_gap.py` ✅
  - 每周一凌晨 3 点运行（`COMPLAINT_KNOWLEDGE_GAP_CRON`）
  - 聚合最近 7 天 `AgentScoreSnapshot`，按 `agent_tag` 分组
  - 提炼高频 `reject_reasons_top` / `handoff_reasons_top`
  - 平均通过率 < 60% 时输出 `warning` 级别告警

---

## 5. 待完成事项清单

### 5.1 高优先级（影响核心功能）—— 全部已完成 ✅

| 序号 | 模块 | 具体任务 | 状态 |
|------|------|----------|------|
| 1 | Agent 配置扩展 | 新增 `role_tag` 等 6 个字段，启动时自动迁移，config/registry 已支持 | ✅ 已完成 |
| 2 | Complaint Tools | 创建 `tools/complaint/` 目录，实现 4 个工具，registry 注入 role_tag 路由 | ✅ 已完成 |
| 3 | 用户侧状态展示 | `ComplaintStatusBar` 组件已创建，timeline 事件消费已验证，ChatContent 已集成 | ✅ 已完成 |

### 5.2 中优先级（优化体验）—— 全部已完成 ✅

| 序号 | 模块 | 具体任务 | 状态 |
|------|------|----------|------|
| 4 | 知识缺口任务 | 实现独立的知识缺口分析 scheduler 任务（`complaint_knowledge_gap.py`） | ✅ 已完成 |
| 5 | 联调验收 | 执行 6 个验收用例（`test_complaint_flow.py` 21 个测试全部通过） | ✅ 已完成 |

---

## 6. 架构亮点

### 6.1 已实现的优秀设计

1. **状态机集中管理**：`state_machine.py` 避免状态流转规则散落
2. **两段式 Handoff**：`pending → human` 避免粗暴切换
3. **Ticket 归并规则**：保守策略防止 ticket 爆炸
4. **事件驱动架构**：SSE + WebSocket 双通道推送
5. **前端 Store 分层**：`support-workbench-store` + `support-store` 职责清晰
6. **测试覆盖完整**：14 个测试文件，84 个测试用例全部通过；Planner/Executor 测试已适配 `async` + `anyio`
7. **LLM Planner**：`PlannerService._plan_with_llm()` 使用 `with_structured_output(PlannerDecision)` 强制结构化规划输出；LLM 不可用时自动降级为 5 优先级规则引擎，主链路不中断
8. **LLM Executor + Tools**：`ExecutorService._execute_with_llm()` 绑定 4 个 complaint tools（`complaint_faq_search` / `complaint_policy_search` / `complaint_case_sop_search` / `handoff_create`），ReAct 最多 5 轮工具调用循环；LLM 失败时降级为规则模板

### 6.2 可改进点

1. ~~**Executor/Planner 架构升级**：升级为 LLM + Tools 架构~~ ✅ **已完成**（见 6.1 第 7、8 条）
2. **Agent 角色配置 UI**：`role_tag` 等 6 个字段已在数据库，但管理后台缺少角色配置界面（待实现）
3. **知识缺口运营闭环**：`complaint_knowledge_gap` 任务已输出分析报告，但知识库更新仍需人工介入（待实现）

---

## 7. 结论

**Phase 1 全部 15 步已 100% 完成**：
> 同一个会话中的客诉问题，已经不再是"直接 AI 回答"，而是"有 ticket、有 task、有 review、有状态机"的正式处理链。

**Phase 1 完整交付清单**：
- ✅ 领域枚举与 Schema
- ✅ 数据库模型（ComplaintTicket / Task / Review / PatrolEvent / AgentScoreSnapshot）
- ✅ Repository 层（5 个仓储）
- ✅ Service 层（orchestrator + ticket + task + review + handoff + 归并等）
- ✅ Agent 角色配置扩展（`role_tag` 等 6 个字段，自动迁移）
- ✅ Complaint Tools（`faq_search` / `policy_search` / `case_sop_search` / `handoff_create`）
- ✅ Handoff 两段式改造（`pending → human`）
- ✅ Chat 主入口接入 orchestrator
- ✅ SSE 事件流（12 种 complaint 事件）
- ✅ Support API（ticket 视角取数）
- ✅ 前端 Store（workbench + support 两层）
- ✅ 用户侧 ComplaintStatusBar（问题标签 + 处理阶段）
- ✅ 客服工作台（列表 + 详情）
- ✅ 测试（14 个测试文件，84 个测试用例全部通过；Planner/Executor 测试已适配 `async` + `anyio`）
- ✅ Phase 2/3 提前实现（巡查任务 + 绩效快照 + 知识缺口分析）
- ✅ **Executor/Planner LLM 升级**：`PlannerService` 接入 `with_structured_output(PlannerDecision)`；`ExecutorService` 绑定 4 个 complaint tools，执行 ReAct 工具调用循环；双服务均有规则引擎降级保障
- ✅ **依赖全量升级**：`langchain>=1.2.15`、`langgraph>=1.1.6`、`langchain-openai>=1.1.12`、`fastapi>=0.135.3`、`qdrant-client>=1.17.1`、`uvicorn>=0.43.0` 等升级至最新稳定版，`uv.lock` 同步更新

**后续建议方向**：
1. 补充 Agent 角色配置管理 UI（`role_tag` 等 6 个字段的可视化配置页）
2. 知识缺口运营闭环（自动化知识库更新建议，减少人工介入）

---

*文档更新时间：2026 年 4 月*
*基于代码实际实现状态分析*
