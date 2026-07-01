# Phase 1 执行级施工手册

本文档的业务职责，是把“AI 虚拟人客诉系统”第一阶段从总规划进一步细化成可直接执行的施工步骤。它不再回答“要不要做”，而是回答“每一步具体怎么做、改哪些文件、先后顺序是什么、做完如何验证”。

适用范围：

- 当前仓库 `embedease-ai`
- 当前架构 `chat + support + agent + scheduler + frontend`
- 当前目标：先把“单会话单主问题单”的客诉主链路做通

## 1. Phase 1 的唯一目标

Phase 1 完成后，系统必须实现下面这个最小闭环：

```text
用户发消息
-> 创建或归并到主活动问题单
-> front_desk 判断问题和风险
-> planner 选择责任岗位
-> executor 输出处理结果
-> reviewer 审查
-> 通过则对用户回复
-> 不通过则返工或转人工
```

Phase 1 先不做：

- 自动巡查自愈
- 绩效榜
- 复杂拖拽编排器
- 大规模并行多 Agent

## 2. Phase 1 施工顺序

Phase 1 必须严格按以下顺序做。

1. 先补数据库和模型
2. 再补 repository / service
3. 再补 orchestrator 主链路
4. 再补事件和接口
5. 再补前端展示
6. 最后补测试和验收

不能跳过底层表结构直接先改 UI。

## 3. 第一步：补齐数据库表和模型

### 3.1 要做什么

先把“问题单驱动”落到数据库，不然后面的所有编排都是空的。

### 3.2 必须新增或修改的模型

必须改这些文件：

- `backend/app/models/conversation.py`
- `backend/app/models/__init__.py`

必须新增这些文件：

- `backend/app/models/complaint_ticket.py`
- `backend/app/models/complaint_task.py`
- `backend/app/models/complaint_review.py`
- `backend/app/models/complaint_patrol_event.py`
- `backend/app/models/agent_score_snapshot.py`

### 3.3 `Conversation` 要怎么改

在现有字段基础上新增：

- `current_ticket_id`
- `conversation_mode` 或复用 `handoff_state` 但统一语义
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

实现要求：

- 这些字段必须是“当前快照”，方便前端列表和客服工作台快速读取
- 历史明细不要只靠 `Conversation` 保存，明细要进入 ticket/task/review 表

### 3.4 `ComplaintTicket` 要怎么设计

必须包含：

- 主键 `id`
- 外键 `conversation_id`
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
- `version`
- `created_at` / `updated_at` / `closed_at`

实现要求：

- 一个 `conversation` 默认只允许一个活动 ticket
- `timeline` 记录关键动作摘要，不替代 message 表

### 3.5 `ComplaintTask` 要怎么设计

必须包含：

- `ticket_id`
- `task_type`
- `agent_tag`
- `status`
- `input_payload`
- `output_payload`
- `review_required`
- `review_status`
- `retry_count`
- `started_at` / `finished_at`

任务类型第一阶段固定为：

- `triage`
- `plan`
- `emotion`
- `faq`
- `case_collect`
- `resolution`
- `handoff`
- `review`

### 3.6 `ComplaintReview` 要怎么设计

必须包含：

- `ticket_id`
- `task_id`
- `reviewer_agent_tag`
- `status`
- `score`
- `risk_level`
- `reasons`
- `suggested_next_agent`
- `created_at`

### 3.7 Alembic 迁移怎么做

必须做：

1. 新建迁移脚本
2. 创建新表
3. 给 `conversations` 增加新字段
4. 补索引：
   - `conversation_id + status`
   - `ticket_id + status`
   - `handoff_state`
   - `current_ticket_id`
5. 写清楚数据兼容策略

### 3.8 这一步做完怎么验证

验证标准：

1. 数据库可以创建一条 conversation 和一条活动 ticket
2. 可以插入 task 和 review
3. `Conversation.current_ticket_id` 能正确指向主活动单
4. 多轮消息不会自动生成多个 ticket

## 4. 第二步：补 repository 和 service 层

### 4.1 要做什么

把数据库访问从 chat/router 中抽出来，形成客诉领域 service。

### 4.2 必须新增的 repository

- `backend/app/repositories/complaint_ticket.py`
- `backend/app/repositories/complaint_task.py`
- `backend/app/repositories/complaint_review.py`
- `backend/app/repositories/complaint_patrol_event.py`

### 4.3 必须新增的 service

- `backend/app/services/complaint/ticket_service.py`
- `backend/app/services/complaint/task_service.py`
- `backend/app/services/complaint/review_service.py`
- `backend/app/services/complaint/ticket_merge_service.py`

### 4.4 `TicketMergeService` 怎么做

必须提供：

- `get_active_ticket(conversation_id)`
- `should_merge_into_current_ticket(ticket, user_message)`
- `attach_secondary_issue(ticket, issue_payload)`
- `create_new_ticket(...)`
- `get_or_create_active_ticket(...)`

强规则：

- 默认先查活动 ticket
- 有活动 ticket 时默认先归并
- 只有明确新问题才新建 ticket

### 4.5 `TicketService` 怎么做

必须提供：

- `create_ticket()`
- `update_ticket_status()`
- `update_ticket_snapshot()`
- `increment_unresolved_turns()`
- `mark_handoff_pending()`
- `close_ticket()`

### 4.6 `TaskService` 怎么做

必须提供：

- `create_task()`
- `start_task()`
- `complete_task()`
- `fail_task()`
- `block_task()`

### 4.7 `ReviewService` 怎么做

必须提供：

- `request_review()`
- `complete_review()`
- `reject_review()`
- `should_escalate_after_reject()`

### 4.8 这一步做完怎么验证

验证标准：

1. 可以通过 service 创建 ticket/task/review
2. 可以对活动 ticket 执行归并
3. 可以把第二问题记录为 `secondary_issue`
4. 可以在 review reject 后触发 rework 计数

## 5. 第三步：补 complaint orchestrator 主链路

### 5.1 要做什么

把当前 `chat.py -> ChatStreamOrchestrator -> agent_service` 的直连路径，改造成 complaint 主链路。

### 5.2 必须新增的文件

- `backend/app/services/complaint/orchestrator.py`
- `backend/app/services/complaint/planner_service.py`
- `backend/app/services/complaint/executor_service.py`

### 5.3 `ComplaintConversationOrchestrator` 怎么做

入口方法建议固定为：

```python
async def handle_user_message(
    conversation_id: str,
    user_id: str,
    message_id: str,
    user_message: str,
    context: ChatContext | None = None,
) -> ComplaintRunResult:
    ...
```

内部顺序必须固定：

1. 调用 `TicketMergeService.get_or_create_active_ticket`
2. 生成或更新 ticket 快照
3. 创建 `triage` task
4. 调用 `front_desk_agent`
5. 更新 ticket 基础标签/情绪/风险
6. 创建 `plan` task
7. 调用 `service_planner_agent`
8. 根据 planner 结果创建 executor task
9. 调用 executor
10. 创建 review task
11. 调用 reviewer
12. 根据 reviewer 结果：
   - `passed` -> 输出给用户
   - `rejected` -> rework
   - `escalated` -> handoff_pending

### 5.4 planner 怎么做

`ComplaintPlannerService` 第一阶段必须只解决三件事：

1. 当前应该由哪个 executor 接手
2. 是否继续处理当前 ticket
3. 是否需要 handoff

它暂时不要承担复杂并行调度。

### 5.5 executor 怎么做

`ExecutorService` 第一阶段只负责统一执行下面几类岗位：

- `emotion_deescalation_agent`
- `faq_policy_agent`
- `case_intake_agent`
- `resolution_execution_agent`
- `handoff_orchestrator_agent`

### 5.6 这一步做完怎么验证

验证标准：

1. 用户发一条消息后，系统能产出 ticket、task、review 三层记录
2. 能根据分类走不同 executor
3. reviewer reject 后不会直接输出 assistant.final
4. handoff 条件满足时，ticket 状态会进入 `handoff_pending`

## 6. 第四步：改造 `chat.py` 和 `chat_stream.py`

### 6.1 `chat.py` 怎么改

必须修改 [chat.py](/Users/wang/code/my/embedease-ai/backend/app/routers/chat.py)：

1. 保留“先保存 user message”的逻辑
2. 人工模式分支保留
3. AI 模式下不再直接走通用 `agent_service.chat_emit`
4. 改为调用 `ComplaintConversationOrchestrator`

### 6.2 `chat_stream.py` 怎么改

必须修改 [chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py)：

1. 保留原有 token 流式输出机制
2. 增加 complaint 领域状态事件透传
3. 在最终落库 assistant 消息前，确认 review 已通过
4. 如果 review 未通过，不落库外发 assistant 正文

### 6.3 要新增哪些 SSE 事件

第一阶段必须新增：

- `complaint.ticket.created`
- `complaint.ticket.merged`
- `complaint.ticket.updated`
- `complaint.task.created`
- `complaint.task.started`
- `complaint.task.completed`
- `complaint.review.pending`
- `complaint.review.passed`
- `complaint.review.rejected`
- `complaint.handoff_requested`

### 6.4 这一步做完怎么验证

验证标准：

1. 前端能收到 ticket/task/review 事件
2. 同一问题多轮对话时能收到 `ticket.merged`
3. 被驳回时看不到错误外发内容

## 7. 第五步：改造人工升级链路

### 7.1 要做什么

把当前简单 handoff 改造成客诉链路的一部分。

### 7.2 `handoff.py` 必须怎么改

必须修改 [handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py)：

1. 增加 `request_handoff()`
2. `request_handoff()` 只做 `AI -> PENDING`
3. `start_handoff()` 改成 `PENDING -> HUMAN`
4. `end_handoff()` 允许指定 ticket 处理结果
5. handoff 时必须写入 ticket 摘要和接管原因

### 7.3 `support.py` 必须怎么改

必须修改 [support.py](/Users/wang/code/my/embedease-ai/backend/app/routers/support.py)：

1. 查询会话状态时返回 ticket 快照
2. 会话列表返回当前 ticket 摘要
3. handoff API 返回 ticket 状态变化

### 7.4 这一步做完怎么验证

验证标准：

1. AI 请求转人工后，会话状态进入 `pending`
2. 客服接入后会话进入 `human`
3. 工作台能看到接管原因和摘要

## 8. 第六步：扩展 Agent 配置与能力合同

### 8.1 要做什么

把当前 `product/faq/kb/custom` 体系向客诉岗位迁移。

### 8.2 必须修改的文件

- `backend/app/models/agent.py`
- `backend/app/schemas/agent.py`
- `backend/app/services/agent/core/config.py`
- `backend/app/services/agent/core/factory.py`

### 8.3 第一阶段怎么做最稳妥

先不要删除所有旧类型，先新增 complaint 场景类型或 tag：

- `front_desk`
- `planner`
- `emotion`
- `faq_policy`
- `case_intake`
- `resolution`
- `handoff`
- `reviewer`
- `patrol`

### 8.4 必须补什么配置

每个 complaint agent 至少补：

- `business_goal`
- `in_scope`
- `out_of_scope`
- `success_criteria`
- `handoff_rules`
- `tool_scope`

### 8.5 这一步做完怎么验证

验证标准：

1. 配置层能区分各岗位 agent
2. planner 能基于配置选择 executor
3. reviewer/patrol 有独立配置入口

## 9. 第七步：补 complaint 工具与知识范围

### 9.1 要做什么

把商品导向工具收缩，补客诉工具。

### 9.2 第一阶段必须有的工具

- `faq_search`
- `policy_search`
- `case_sop_search`
- `collect_case_slot`
- `create_handoff_summary`

### 9.3 必须修改的文件

- `backend/app/services/agent/tools/registry.py`
- 新增 `backend/app/services/agent/tools/complaint/*`

### 9.4 这一步做完怎么验证

验证标准：

1. FAQ/Policy/Resolution agent 工具范围不同
2. emotion agent 不会看到赔付决策类工具
3. handoff agent 可以生成接管摘要

## 10. 第八步：改造前端用户侧聊天界面

### 10.1 要做什么

用户侧要从“普通聊天”变成“问题处理可见”。

### 10.2 必须改的区域

- `frontend/app/chat/*`
- 对应聊天组件和 store

### 10.3 必须展示什么

- 当前问题状态
- 当前处理岗位
- 是否等待审查
- 是否等待人工接入
- 当前 ticket 是否被归并处理

### 10.4 这一步做完怎么验证

验证标准：

1. 用户能看到当前正在处理哪个问题状态
2. 被转人工时能看到等待接入提示
3. 同一 ticket 多轮沟通时不会让用户误以为系统在新开多个问题

## 11. 第九步：改造客服工作台

### 11.1 要做什么

把当前只按 `handoff_state` 展示的工作台，升级成 ticket 驱动。

### 11.2 必须改的文件

- `frontend/app/support/page.tsx`
- `frontend/app/support/[conversationId]/page.tsx`
- `frontend/stores/support-store.ts`

### 11.3 工作台必须新增展示字段

- 当前主 ticket ID
- ticket 状态
- primary issue tag
- current agent tag
- risk level
- handoff reason
- review status
- review score
- unresolved turns
- secondary issues

### 11.4 工作台必须新增操作

- 接管
- 结束接管
- 标记已解决
- 标记需拆单
- 查看 review 驳回原因

### 11.5 这一步做完怎么验证

验证标准：

1. 客服端能明确看到当前主问题单
2. 能区分“AI 处理中”“等待人工”“人工处理中”
3. 能看到为何转人工、为何驳回

## 12. 第十步：补 support API 和详情查询

### 12.1 要做什么

support API 必须返回 ticket 级信息，而不是只返回 handoff 状态。

### 12.2 必须改的后端文件

- `backend/app/routers/support.py`
- `backend/app/schemas/support.py`

### 12.3 必须新增的返回内容

- `current_ticket`
- `ticket_status`
- `primary_issue_tag`
- `current_agent_tag`
- `review_status`
- `review_score`
- `handoff_summary`

### 12.4 这一步做完怎么验证

验证标准：

1. support 列表接口可以直接驱动工作台列表
2. support 详情接口可以直接驱动单会话详情页

## 13. 第十一步：补测试

### 13.1 要做什么

Phase 1 必须有测试，不允许只改实现不补测试。

### 13.2 必须新增的测试类型

- ticket merge/split 单元测试
- ticket/task/review service 单元测试
- handoff 状态流转测试
- chat complaint orchestrator 集成测试
- support API 测试

### 13.3 必测场景

1. 同一问题多轮发泄，不新建 ticket
2. 已解决后提出新问题，创建新 ticket
3. 审查驳回后进入 rework
4. 连续驳回后进入 handoff_pending
5. 人工接入后 ticket 状态同步变化

## 14. 第十二步：Phase 1 验收

只有同时满足以下条件，Phase 1 才算完成：

1. 同一会话默认只有一个主活动 ticket
2. 用户持续抱怨/补充信息不会炸出多个重复 ticket
3. 后端主链路已经是 ticket 驱动
4. executor 输出前有 reviewer 审查
5. 审查失败会返工或升级人工
6. support 工作台能看到 ticket 级状态
7. handoff 链路已经纳入 ticket 状态机
8. 关键场景有自动化测试

如果以上任意一项未完成，就不能进入 Phase 2。

