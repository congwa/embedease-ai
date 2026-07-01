# Phase 1 逐文件开发任务单

本文档的业务职责，是把 [README.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/README.md) 和 [development-phase-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/development-phase-plan.md) 中的第一阶段目标，进一步拆成“逐文件开发任务单”。

它不再回答“做哪一块”，而是回答：

- 第一阶段具体先改哪个文件
- 每个文件新增什么类、什么字段、什么方法
- 每一步依赖什么前置改动
- 每一步做完怎么确认已经完成

这是第一阶段的直接开发顺序，必须按顺序执行。

## 1. 执行规则

第一阶段开发必须遵守以下规则：

1. 先建模型，再建 repository/service，再接入 orchestrator，再改接口和前端。
2. 任何时候都不能跳过“单会话单主活动 ticket”规则。
3. 没有完成上一步，不要开始下一步。
4. 每一步改完都要能单独验证。

## 2. 第一步：补模型层文件

### 2.1 修改 [conversation.py](/Users/wang/code/my/embedease-ai/backend/app/models/conversation.py)

必须新增字段：

- `current_ticket_id`
- `conversation_mode`
- `primary_issue_tag`
- `current_agent_tag`
- `complaint_status`
- `priority_level`
- `risk_level`
- `unresolved_turns`
- `review_status`
- `review_score`
- `block_reason`
- `secondary_issues`

必须补的业务注释：

- 说明这些字段为什么是“会话快照”而不是历史明细

完成判断：

- `Conversation` 能表达当前主活动 ticket 的状态快照

### 2.2 新增 [complaint_ticket.py](/Users/wang/code/my/embedease-ai/backend/app/models/complaint_ticket.py)

必须新增：

- `ComplaintStatus` 枚举
- `ComplaintTicket` 模型

必须包含字段：

- `id`
- `conversation_id`
- `status`
- `primary_issue_tag`
- `secondary_issue_tags`
- `sentiment`
- `severity`
- `priority_level`
- `risk_level`
- `current_agent_tag`
- `current_task_id`
- `handoff_required`
- `handoff_reason`
- `resolved_summary`
- `slot_data`
- `timeline`
- `rework_count`
- `issue_fingerprint`
- `is_primary_active`
- `created_at`
- `updated_at`
- `closed_at`

完成判断：

- ticket 模型可以独立表达一个问题单的完整生命周期

### 2.3 新增 [complaint_task.py](/Users/wang/code/my/embedease-ai/backend/app/models/complaint_task.py)

必须新增：

- `ComplaintTaskStatus` 枚举
- `ComplaintTask` 模型

必须包含字段：

- `ticket_id`
- `task_type`
- `agent_tag`
- `status`
- `input_payload`
- `output_payload`
- `review_required`
- `review_status`
- `retry_count`
- `started_at`
- `finished_at`

完成判断：

- 可以为任意 ticket 挂多个有顺序的处理任务

### 2.4 新增 [complaint_review.py](/Users/wang/code/my/embedease-ai/backend/app/models/complaint_review.py)

必须新增：

- `ComplaintReviewStatus` 枚举
- `ComplaintReview` 模型

必须包含字段：

- `ticket_id`
- `task_id`
- `reviewer_agent_tag`
- `status`
- `score`
- `risk_level`
- `reasons`
- `suggested_next_agent`
- `created_at`

完成判断：

- review 结果可以单独审计，而不是只写在日志里

### 2.5 新增 [complaint_patrol_event.py](/Users/wang/code/my/embedease-ai/backend/app/models/complaint_patrol_event.py)

虽然 Phase 1 先不做巡查逻辑，但模型必须先落位。

必须新增：

- `ComplaintPatrolStatus` 枚举
- `ComplaintPatrolEvent` 模型

完成判断：

- 第二阶段接巡查时不需要再回头改模型结构

### 2.6 新增 [agent_score_snapshot.py](/Users/wang/code/my/embedease-ai/backend/app/models/agent_score_snapshot.py)

虽然 Phase 1 不做绩效统计逻辑，但表结构应预留。

完成判断：

- 第三阶段接统计任务时不需要重改一遍基础数据模型

### 2.7 修改 [__init__.py](/Users/wang/code/my/embedease-ai/backend/app/models/__init__.py)

必须把新模型导出。

完成判断：

- 新模型能被 metadata 和后续 repository 正常引用

## 3. 第二步：补 repository 层文件

### 3.1 新增 [complaint_ticket.py](/Users/wang/code/my/embedease-ai/backend/app/repositories/complaint_ticket.py)

必须实现：

- `get_by_id()`
- `get_active_by_conversation_id()`
- `create_ticket()`
- `update_ticket()`
- `close_ticket()`
- `list_by_conversation_id()`

重点要求：

- `get_active_by_conversation_id()` 必须是后续 merge 规则的唯一数据入口

### 3.2 新增 [complaint_task.py](/Users/wang/code/my/embedease-ai/backend/app/repositories/complaint_task.py)

必须实现：

- `create_task()`
- `get_latest_by_ticket_id()`
- `list_by_ticket_id()`
- `update_status()`

### 3.3 新增 [complaint_review.py](/Users/wang/code/my/embedease-ai/backend/app/repositories/complaint_review.py)

必须实现：

- `create_review()`
- `get_latest_by_ticket_id()`
- `list_by_ticket_id()`

### 3.4 新增 [complaint_patrol_event.py](/Users/wang/code/my/embedease-ai/backend/app/repositories/complaint_patrol_event.py)

先补基础 CRUD，不急着接业务。

完成判断：

- 所有 complaint 领域对象都能通过 repository 读写

## 4. 第三步：补 service 层文件

### 4.1 新增目录 [complaint](/Users/wang/code/my/embedease-ai/backend/app/services/complaint)

必须新增：

- `__init__.py`
- `ticket_service.py`
- `task_service.py`
- `review_service.py`
- `ticket_merge_service.py`
- `planner_service.py`
- `executor_service.py`
- `handoff_service.py`
- `orchestrator.py`

### 4.2 新增 [ticket_merge_service.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/ticket_merge_service.py)

必须实现方法：

- `get_or_create_active_ticket()`
- `should_merge_into_current_ticket()`
- `attach_secondary_issue()`
- `should_split_ticket()`

重点要求：

- 默认先 merge
- 发现第二问题先记 `secondary_issue`
- 只有明确是新问题才 split

### 4.3 新增 [ticket_service.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/ticket_service.py)

必须实现方法：

- `create_ticket()`
- `update_ticket_snapshot()`
- `update_status()`
- `mark_handoff_pending()`
- `mark_resolved()`
- `increment_unresolved_turns()`

### 4.4 新增 [task_service.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/task_service.py)

必须实现方法：

- `create_triage_task()`
- `create_plan_task()`
- `create_executor_task()`
- `create_review_task()`
- `start_task()`
- `complete_task()`
- `block_task()`

### 4.5 新增 [review_service.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/review_service.py)

必须实现方法：

- `run_review()`
- `apply_review_result()`
- `should_escalate_after_reject()`

### 4.6 新增 [planner_service.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/planner_service.py)

必须实现方法：

- `plan_for_ticket()`

输出必须包括：

- `target_agent_tag`
- `task_type`
- `should_handoff`
- `reason`

### 4.7 新增 [executor_service.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/executor_service.py)

必须实现方法：

- `run_executor()`

支持执行：

- `emotion_deescalation_agent`
- `faq_policy_agent`
- `case_intake_agent`
- `resolution_execution_agent`
- `handoff_orchestrator_agent`

### 4.8 新增 [handoff_service.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/handoff_service.py)

必须实现方法：

- `request_handoff()`
- `start_handoff()`
- `finish_handoff()`

重点要求：

- 这个 service 是 complaint 业务 handoff，不是替代现有 support handoff 的底层实现
- 它要调用现有 [handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py)

### 4.9 新增 [orchestrator.py](/Users/wang/code/my/embedease-ai/backend/app/services/complaint/orchestrator.py)

必须实现：

- `ComplaintConversationOrchestrator`
- `handle_user_message()`

固定顺序：

1. merge/create ticket
2. triage
3. plan
4. execute
5. review
6. reply or handoff

完成判断：

- complaint 领域服务已经能在不依赖 router 的情况下串起主流程

## 5. 第四步：改后端 schema 层文件

### 5.1 修改 [events.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/events.py)

必须新增 complaint 事件：

- `complaint.ticket.created`
- `complaint.ticket.merged`
- `complaint.ticket.updated`
- `complaint.secondary_issue.detected`
- `complaint.task.started`
- `complaint.task.completed`
- `complaint.review.pending`
- `complaint.review.passed`
- `complaint.review.rejected`
- `complaint.handoff_requested`

### 5.2 修改 [support.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/support.py)

必须新增：

- `TicketSummarySchema`
- `ReviewSummarySchema`
- 扩展 `ConversationStateResponse`
- 扩展 `ConversationListItem`

### 5.3 修改 [websocket.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/websocket.py)

必须新增：

- `server.ticket_updated`
- `server.review_updated`
- 扩展 `ConversationStatePayload`

完成判断：

- schema 已能表达 ticket 级状态

## 6. 第五步：改 router 和流式主链路文件

### 6.1 修改 [chat.py](/Users/wang/code/my/embedease-ai/backend/app/routers/chat.py)

必须改动：

- AI 模式下不再直接走旧的通用 agent 对话路径
- 接入 `ComplaintConversationOrchestrator`
- 人工模式保持现有分支

### 6.2 修改 [chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py)

必须改动：

- 增加 complaint 事件透传
- assistant.final 落库前检查 review 结果

### 6.3 修改 [support.py](/Users/wang/code/my/embedease-ai/backend/app/routers/support.py)

必须改动：

- 列表接口返回 ticket 快照
- 详情接口返回 current ticket 和 review summary
- handoff 接口返回 complaint 状态变化

完成判断：

- 主链路和 support API 都已 ticket 驱动

## 7. 第六步：改现有 support handoff 文件

### 7.1 修改 [handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py)

必须改动：

- 增加 `AI -> PENDING -> HUMAN` 的底层支持
- start / end handoff 时同步 complaint ticket 状态

重点要求：

- 不能破坏现有客服能力
- 但必须把 handoff 变成 ticket 状态机的一部分

完成判断：

- handoff 已经和 complaint ticket 同步

## 8. 第七步：改 Agent 配置相关文件

### 8.1 修改 [agent.py](/Users/wang/code/my/embedease-ai/backend/app/models/agent.py)

必须改动：

- 增补 complaint 场景下的 agent type 或 tag 支持

### 8.2 修改 [agent.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/agent.py)

必须改动：

- 支持 complaint agent 的配置字段

### 8.3 修改 [config.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/config.py)

必须改动：

- complaint agent 的默认 prompt / tool_categories / policy

### 8.4 修改 [factory.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/factory.py)

必须改动：

- 支持 complaint 角色的 agent 构建

完成判断：

- planner / executor / reviewer 等 complaint 岗位都能通过配置层运行

## 9. 第八步：改前端状态和页面文件

### 9.1 修改 [support-store.ts](/Users/wang/code/my/embedease-ai/frontend/stores/support-store.ts)

必须新增字段：

- `conversationMode`
- `currentTicketId`
- `ticketStatus`
- `primaryIssueTag`
- `currentAgentTag`
- `priorityLevel`
- `riskLevel`
- `unresolvedTurns`
- `reviewStatus`
- `reviewScore`
- `reviewReasons`
- `secondaryIssueDetected`
- `handoffSummary`

### 9.2 修改 [page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/page.tsx)

必须改动：

- 列表页展示 ticket 状态、risk、review 状态

### 9.3 修改 [page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/[conversationId]/page.tsx)

必须改动：

- 详情页展示 current ticket、review summary、handoff summary、secondary issue

### 9.4 修改用户聊天相关页面和 store

必须改动：

- 展示 ticket 处理状态
- 展示 merged / secondary issue / waiting human 提示

完成判断：

- 用户侧和客服侧都能看到 ticket 驱动状态

## 10. 第九步：补测试文件

### 10.1 必须新增的测试

- `test_complaint_ticket_model.py`
- `test_ticket_merge_service.py`
- `test_review_service.py`
- `test_support_ticket_state_api.py`
- `test_complaint_flow.py`

### 10.2 必测场景

- 同一问题持续发泄不新建 ticket
- 新问题出现创建新 ticket
- secondary issue 记录成功
- review reject 不外发最终内容
- handoff pending -> human 状态同步

完成判断：

- 第一阶段关键场景都有自动化测试覆盖

## 11. 开发完成的判定标准

第一阶段逐文件任务全部完成后，必须满足：

1. 后端已有 complaint 领域模型、repository、service、orchestrator
2. router 和 stream 已接入 complaint 主链路
3. support API 已 ticket 化
4. 前端 store 和页面已能表达 ticket 状态
5. 测试通过

只有全部满足，才算第一阶段代码改造准备完成，可以进入实际编码实施或逐步提交。

