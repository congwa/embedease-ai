# Phase 1 执行级实施计划

本文档的业务职责，是把“AI 虚拟人客诉系统”的 Phase 1 改造任务下沉到可执行级别，明确每一步具体怎么做、改哪些文件、先做什么后做什么、每一步的产物是什么、做完如何验证。它服务于开发落地，不再讨论抽象方向。

## 1. Phase 1 目标

Phase 1 的唯一目标是：

把当前 `embedease-ai` 的聊天主链路改造成“问题单驱动的客诉处理闭环”，至少跑通下面这条链：

```text
用户消息
-> 创建/归并问题单
-> 标签识别
-> 任务规划
-> 执行 Agent 处理
-> 审查 Agent 审查
-> 通过后回复用户 / 不通过返工 / 触发人工升级
```

Phase 1 不追求一次做完所有高级能力。Phase 1 完成的标准只有一个：

`同一个会话中的客诉问题，已经不再是“直接 AI 回答”，而是“有 ticket、有 task、有 review、有状态机”的正式处理链。`

## 2. 执行顺序总览

Phase 1 必须按下面顺序执行，不允许跳过：

1. 新增并冻结领域枚举与 schema
2. 扩展数据库模型与迁移
3. 新增 complaint repository
4. 新增 complaint services
5. 改造 handoff 服务
6. 改造 chat 主链路
7. 改造 chat stream 事件
8. 改造 Agent 配置与运行时
9. 新增 complaint tools
10. 改造 support API
11. 改造前端 store
12. 改造用户侧聊天状态展示
13. 改造客服工作台
14. 补测试
15. 联调验收

## 3. 第 1 步：新增领域枚举与 Schema

### 3.1 要做什么

先把所有领域术语定成代码级枚举和 schema，后面数据库、service、前端状态全部基于这些定义走。

### 3.2 改哪些文件

新增：

- `backend/app/schemas/complaint.py`
- `backend/app/schemas/complaint_ticket.py`
- `backend/app/schemas/complaint_task.py`
- `backend/app/schemas/complaint_review.py`
- `backend/app/schemas/complaint_patrol.py`

### 3.3 具体怎么做

1. 在 `complaint.py` 中定义以下枚举：
   - `ConversationMode`
   - `ComplaintStatus`
   - `ComplaintTaskStatus`
   - `ComplaintReviewStatus`
   - `ComplaintPatrolStatus`
   - `IssueContinuity`
2. 在 `complaint_ticket.py` 中定义：
   - `ComplaintTicketCreate`
   - `ComplaintTicketUpdate`
   - `ComplaintTicketResponse`
   - `ActiveTicketResolution`
3. 在 `complaint_task.py` 中定义：
   - `ComplaintTaskCreate`
   - `ComplaintTaskUpdate`
   - `ComplaintTaskResponse`
4. 在 `complaint_review.py` 中定义：
   - `ComplaintReviewCreate`
   - `ComplaintReviewResponse`
   - `ComplaintReviewDecision`
5. 在 `complaint_patrol.py` 中定义：
   - `ComplaintPatrolEventCreate`
   - `ComplaintPatrolEventResponse`

### 3.4 完成产物

- 后续所有模块都可以直接 import complaint 领域类型

### 3.5 完成判定

- 没有任何 service 再使用裸字符串写状态值

## 4. 第 2 步：扩展数据库模型与 Alembic 迁移

### 4.1 要做什么

把“问题单、任务、审查、巡查”落进数据库，否则后面都是内存态。

### 4.2 改哪些文件

修改：

- `backend/app/models/conversation.py`

新增：

- `backend/app/models/complaint_ticket.py`
- `backend/app/models/complaint_task.py`
- `backend/app/models/complaint_review.py`
- `backend/app/models/complaint_patrol_event.py`
- `backend/app/models/agent_score_snapshot.py`

### 4.3 `Conversation` 怎么改

在 [conversation.py](/Users/wang/code/my/embedease-ai/backend/app/models/conversation.py) 中新增字段：

- `conversation_mode`
- `complaint_ticket_id`
- `primary_issue_tag`
- `current_agent_tag`
- `current_node_key`
- `priority_level`
- `last_router_reason`
- `last_review_status`
- `last_review_score`
- `block_reason`

兼容策略：

- `handoff_state` 暂时保留
- 新代码统一优先使用 `conversation_mode`

### 4.4 `ComplaintTicket` 怎么做

建议字段最少包含：

- `id`
- `conversation_id`
- `user_id`
- `status`
- `is_primary_active`
- `parent_ticket_id`
- `superseded_by_ticket_id`
- `issue_fingerprint`
- `primary_issue_tag`
- `secondary_issue_tags`
- `secondary_issues`
- `sentiment`
- `severity`
- `priority_level`
- `current_agent_tag`
- `current_task_id`
- `unresolved_turns`
- `rework_count`
- `requires_handoff`
- `handoff_reason`
- `resolution_summary`
- `collected_slots`
- `created_at`
- `updated_at`
- `resolved_at`
- `closed_at`

### 4.5 `ComplaintTask` 怎么做

建议字段最少包含：

- `id`
- `ticket_id`
- `task_type`
- `assigned_agent_tag`
- `status`
- `goal`
- `success_criteria`
- `input_snapshot`
- `output_payload`
- `failure_reason`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

### 4.6 `ComplaintReview` 怎么做

建议字段最少包含：

- `id`
- `ticket_id`
- `task_id`
- `reviewer_agent_tag`
- `status`
- `score`
- `risk_level`
- `reasons`
- `suggested_next_agent`
- `review_payload`
- `created_at`

### 4.7 `ComplaintPatrolEvent` 怎么做

建议字段最少包含：

- `id`
- `ticket_id`
- `task_id`
- `event_type`
- `status`
- `detected_reason`
- `action_taken`
- `result_payload`
- `created_at`
- `resolved_at`

### 4.8 Alembic 怎么做

1. 新建 migration
2. 先加字段和新表
3. 给 `conversation_mode` 提供回填逻辑：
   - 若 `handoff_state = ai`，则 `conversation_mode = ai`
   - 若 `handoff_state = pending`，则 `conversation_mode = pending`
   - 若 `handoff_state = human`，则 `conversation_mode = human`
4. 新表先不做复杂数据回填

### 4.9 完成判定

- 本地迁移可执行
- ORM 能成功创建和查询 ticket/task/review/patrol 数据

## 5. 第 3 步：新增 Complaint Repository 层

### 5.1 要做什么

把 complaint 领域读写从 router/service 里拆出去。

### 5.2 新增文件

- `backend/app/repositories/complaint_ticket.py`
- `backend/app/repositories/complaint_task.py`
- `backend/app/repositories/complaint_review.py`
- `backend/app/repositories/complaint_patrol_event.py`
- `backend/app/repositories/agent_score_snapshot.py`

### 5.3 具体怎么做

`ComplaintTicketRepository` 至少提供：

- `get_by_id`
- `get_active_by_conversation_id`
- `list_by_conversation_id`
- `create_ticket`
- `update_ticket`
- `set_primary_active`
- `close_ticket`

`ComplaintTaskRepository` 至少提供：

- `create_task`
- `get_latest_by_ticket_id`
- `update_status`
- `complete_task`

`ComplaintReviewRepository` 至少提供：

- `create_review`
- `get_latest_by_ticket_id`

### 5.4 完成判定

- 所有 complaint service 不直接写 SQLAlchemy 业务逻辑细节

## 6. 第 4 步：新增 Complaint Service 层

### 6.1 新增文件

- `backend/app/services/complaint/state_machine.py`
- `backend/app/services/complaint/ticket_service.py`
- `backend/app/services/complaint/task_service.py`
- `backend/app/services/complaint/review_service.py`
- `backend/app/services/complaint/handoff_service.py`
- `backend/app/services/complaint/orchestrator.py`

### 6.2 `state_machine.py` 怎么做

这里不要让状态流转散落在各个 service。

最少定义：

- `can_transition_ticket(from_status, to_status) -> bool`
- `can_transition_task(from_status, to_status) -> bool`
- `can_transition_review(from_status, to_status) -> bool`
- `require_transition(...)`

### 6.3 `ticket_service.py` 怎么做

最重要的方法：

- `get_or_create_active_ticket()`
- `resolve_active_ticket_for_message()`
- `append_message_context_to_ticket()`
- `mark_ticket_handoff_pending()`
- `mark_ticket_resolved()`
- `mark_ticket_closed()`

`resolve_active_ticket_for_message()` 必须实现：

1. 查询当前 conversation 的主活动 ticket
2. 没有则创建
3. 有则判断：
   - `reuse_active_ticket`
   - `record_secondary_issue`
   - `create_new_ticket`

### 6.4 `task_service.py` 怎么做

最重要的方法：

- `create_task_from_plan()`
- `start_task()`
- `complete_task()`
- `mark_task_waiting_review()`
- `mark_task_failed()`

### 6.5 `review_service.py` 怎么做

最重要的方法：

- `build_review_input()`
- `create_pending_review()`
- `apply_review_decision()`

`apply_review_decision()` 必须处理：

- `passed -> task done -> ticket in_progress/resolved`
- `rejected -> ticket rework_required`
- `escalated -> ticket handoff_pending`

### 6.6 `handoff_service.py` 怎么做

这个服务是 complaint 语义下的 handoff，不替代现有 support handoff，而是上层业务编排服务。

最重要的方法：

- `request_handoff_for_ticket()`
- `accept_handoff()`
- `finish_handoff()`

### 6.7 `orchestrator.py` 怎么做

最重要的方法：

- `handle_user_message(...)`

内部固定步骤：

1. 解析 conversation + active ticket
2. 调 `front_desk_agent`
3. 决定 ticket 归并 / secondary issue / 拆单
4. 调 `service_planner_agent`
5. 生成 `ComplaintTask`
6. 调执行 Agent
7. 调 `quality_reviewer_agent`
8. 写 review 决策
9. 输出最终事件

### 6.8 完成判定

- 主业务流已经不需要在 router 中直接写复杂逻辑

## 7. 第 5 步：改造 Handoff 服务

### 7.1 改哪些文件

修改：

- `backend/app/services/support/handoff.py`

### 7.2 具体怎么做

现有 `start_handoff()` 直接把状态写到 `HUMAN`，这必须拆成两段。

必须新增：

- `request_handoff(...)`

语义：

- `conversation_mode = pending`
- `ticket.status = handoff_pending`
- 写入 `handoff_reason`
- 写入 `handoff_summary`

保留但重定义：

- `start_handoff(...)`

语义：

- `pending -> human`

改造：

- `end_handoff(...)`

语义：

- 根据人工处理结果把 ticket 标记为 `resolved` 或交还 AI

### 7.3 完成判定

- 系统不再出现 AI 直接跳 HUMAN 的粗暴切换

## 8. 第 6 步：改造 Chat 主入口

### 8.1 改哪些文件

修改：

- `backend/app/routers/chat.py`

### 8.2 具体怎么做

当前流程是：

- 保存用户消息
- 判断 human mode
- 调 orchestrator.run()

改成：

1. 保存用户消息
2. 加载 conversation mode
3. human mode 走人工链路
4. AI mode 调 `ComplaintConversationOrchestrator.handle_user_message()`
5. orchestrator 返回：
   - `ticket`
   - `task`
   - `review`
   - `assistant_response`
   - `stream_events`

### 8.3 完成判定

- `chat.py` 中已经出现 complaint orchestrator，而不是直接把所有事情丢给旧 agent service

## 9. 第 7 步：改造 Chat Stream 事件

### 9.1 改哪些文件

修改：

- `backend/app/services/chat_stream.py`
- `backend/app/schemas/events.py`

### 9.2 具体怎么做

在现有事件流中插入 complaint 领域事件。

推荐时序：

```text
meta.start
complaint.ticket.created / updated
complaint.task.created
complaint.task.started
assistant.delta ...
complaint.review.requested
complaint.review.completed / rejected
assistant.final 或 complaint.handoff_requested
```

### 9.3 完成判定

- 前端收到事件后，可以画出当前处理阶段

## 10. 第 8 步：改造 Agent 配置与运行时

### 10.1 改哪些文件

修改：

- `backend/app/models/agent.py`
- `backend/app/schemas/agent.py`
- `backend/app/services/agent/core/config.py`
- `backend/app/services/agent/core/factory.py`

### 10.2 具体怎么做

先不废弃旧 `type`，但新增以下字段：

- `role_tag`
- `business_domain`
- `skill_bundle_ids`
- `knowledge_scope`
- `review_schema_name`
- `handoff_rules`

factory 层增加 complaint 角色构建分支：

- `front_desk`
- `planner`
- `executor`
- `reviewer`

### 10.3 完成判定

- complaint 角色可以通过配置加载，而不是写死在 if/else 中

## 11. 第 9 步：新增 Complaint Tools

### 11.1 新增文件

- `backend/app/services/agent/tools/complaint/faq_search.py`
- `backend/app/services/agent/tools/complaint/policy_search.py`
- `backend/app/services/agent/tools/complaint/case_sop_search.py`
- `backend/app/services/agent/tools/complaint/handoff_create.py`

### 11.2 具体怎么做

1. `faq_search`
   - 负责 FAQ 问答
2. `policy_search`
   - 负责规则解释
3. `case_sop_search`
   - 负责处理流程查询
4. `handoff_create`
   - 负责生成转人工摘要对象

### 11.3 完成判定

- 执行 Agent 可以在 complaint 场景下工作，不再依赖商品工具

## 12. 第 10 步：改造 Support API

### 12.1 改哪些文件

修改：

- `backend/app/routers/support.py`
- `backend/app/schemas/support.py`
- `backend/app/schemas/websocket.py`

### 12.2 具体怎么做

新增接口：

- `GET /api/v1/support/conversations/{conversation_id}/active-ticket`
- `GET /api/v1/support/conversations/{conversation_id}/tickets`
- `GET /api/v1/support/tickets/{ticket_id}`
- `POST /api/v1/support/tickets/{ticket_id}/resolve`
- `POST /api/v1/support/tickets/{ticket_id}/reopen`

扩展现有会话列表响应，加入：

- `ticket_status`
- `primary_issue_tag`
- `current_agent_tag`
- `priority_level`
- `review_status`
- `review_score`
- `block_reason`

### 12.3 完成判定

- 客服端已经能以问题单视角取数

## 13. 第 11 步：改造前端 Store

### 13.1 改哪些文件

修改：

- `frontend/stores/support-store.ts`

### 13.2 具体怎么做

新增状态字段：

- `ticketStatus`
- `primaryIssueTag`
- `currentAgentTag`
- `currentNodeKey`
- `priorityLevel`
- `reviewStatus`
- `reviewScore`
- `blockReason`
- `secondaryIssues`

新增 action：

- `updateTicketState()`
- `setReviewState()`
- `setBlockedState()`

### 13.3 完成判定

- 前端不再只能维护 handoff 状态

## 14. 第 12 步：改造用户侧聊天页

### 14.1 怎么做

用户侧先做最小展示，不做复杂 UI。

最少展示：

- 当前问题标签
- 当前处理阶段
- 是否待补充资料
- 是否已提交人工

### 14.2 完成判定

- 用户知道问题在被正式处理，而不是只看到一段 AI 文本

## 15. 第 13 步：改造客服工作台

### 15.1 改哪些文件

修改：

- `frontend/app/support/page.tsx`
- `frontend/app/support/[conversationId]/page.tsx`

### 15.2 具体怎么做

会话列表页增加：

- 状态筛选
- 标签筛选
- 风险等级展示
- blocked 标记

详情页增加：

- 当前主 ticket 卡片
- 当前 task 卡片
- review 卡片
- collected slots 卡片
- handoff 摘要卡片

### 15.3 完成判定

- 客服打开会话时，能第一眼看到“这单是什么问题、处理到哪一步、为什么转人工”

## 16. 第 14 步：补测试

### 16.1 新增测试目录建议

- `backend/tests/services/complaint/`
- `backend/tests/routers/support/`
- `backend/tests/routers/chat/`

### 16.2 必测场景

1. 无活动 ticket 时新建 ticket
2. 有活动 ticket 时归并消息
3. 新问题高置信度拆单
4. review 通过
5. review 驳回返工
6. review 连续驳回后转人工
7. pending -> human
8. human -> resolved

### 16.3 完成判定

- complaint 主链路的关键状态转换都有测试保护

## 17. 第 15 步：联调验收

### 17.1 联调顺序

1. 后端 API 自测
2. SSE 事件联调
3. WebSocket 状态联调
4. 前端工作台联调
5. 人工升级联调

### 17.2 验收用例

1. 用户投诉订单延迟并持续发泄，系统只保留一个主 ticket
2. 用户补充截图和订单号，继续归并到同一 ticket
3. AI 解释规则后进入 review，通过后回复
4. AI 回复被驳回，进入 rework
5. 连续返工失败，自动进入 handoff_pending
6. 客服接入后解决问题并关闭 ticket

### 17.3 完成判定

- 整条主闭环可在真实页面中从头跑到尾

## 18. Phase 1 完成定义

当以下条件全部满足时，Phase 1 才算完成：

1. 数据库中已有 ticket/task/review 主模型
2. 一个会话默认只维护一个主活动 ticket
3. chat 主链路已切换到 complaint orchestrator
4. 审查通过/驳回逻辑已落地
5. handoff_pending -> human 链路已落地
6. 前端可看到问题处理状态
7. 客服工作台可看到 ticket 维度信息
8. 关键测试已通过

只要缺任何一项，都不能进入“Phase 1 已完成”的状态。
