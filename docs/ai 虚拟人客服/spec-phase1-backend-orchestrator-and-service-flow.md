# Phase 1 后端编排与 Service 流程规格

本文档的业务职责，是把 AI 虚拟人客诉系统 Phase 1 的后端主链路写成可直接落代码的流程规格。它重点解决的问题是：收到一条用户消息后，后端到底按什么顺序调用哪些 service、如何归并 ticket、如何创建 task、如何做 review、如何决定回复用户还是转人工，以及这些结果如何通过 SSE 和 Support API 暴露出去。

## 1. 本文档覆盖范围

本规格只覆盖 Phase 1 的后端主链路，不覆盖：

- 前端 UI 细节
- 调度器巡查任务细节
- 绩效统计细节
- deer-flow 式深度子会话执行器

本规格重点覆盖：

1. `chat.py`
2. `chat_stream.py`
3. `ComplaintConversationOrchestrator`
4. `TicketMergeService`
5. `TicketService`
6. `TaskService`
7. `ReviewService`
8. `ComplaintHandoffService`
9. `support.py`

## 2. Phase 1 后端主链路目标

收到一条用户消息后，系统必须按下面的逻辑运行：

```text
保存 user message
-> 找到或创建当前主活动 ticket
-> 判断这条消息是继续同一问题还是引入新问题
-> 更新 ticket 快照
-> front_desk 识别问题和风险
-> planner 生成当前处理任务
-> executor 执行处理
-> reviewer 审查输出
-> 通过: 对外回复并推进状态
-> 驳回: 返工或转人工
```

整个过程必须保证一个核心原则：

`主链路围绕 current active ticket 运转，而不是围绕 message 直接回复。`

## 3. 目标代码结构

Phase 1 后端新增或改造后的主链路应组织为：

```text
backend/app/routers/chat.py
  -> ComplaintConversationOrchestrator
     -> TicketMergeService
     -> TicketService
     -> PlannerService
     -> ExecutorService
     -> ReviewService
     -> ComplaintHandoffService
     -> ChatStreamOrchestrator
```

对应推荐新增目录：

```text
backend/app/services/complaint/
  orchestrator.py
  ticket_merge_service.py
  ticket_service.py
  task_service.py
  review_service.py
  planner_service.py
  executor_service.py
  handoff_service.py
  state_machine.py
```

## 4. 入口流程：`chat.py`

对应文件：

- [chat.py](/Users/wang/code/my/embedease-ai/backend/app/routers/chat.py)

### 4.1 当前问题

当前 `chat.py` 主流程是：

1. 保存用户消息
2. 判断 `handoff_state`
3. AI 模式直接进入通用流式生成

这意味着：

- 没有 ticket
- 没有 task
- 没有 review
- 没有“归并还是拆单”逻辑

### 4.2 目标流程

`chat.py` 必须调整为：

1. 保存用户消息
2. 查询 `conversation_mode`
3. 如果 `human` 模式，直接进入人工消息转发逻辑
4. 如果 `ai` 或 `pending`，进入 `ComplaintConversationOrchestrator`
5. 由 orchestrator 返回标准运行结果
6. 再由 `ChatStreamOrchestrator` 输出事件流

### 4.3 建议伪代码

```python
async def chat(...):
    save_user_message(...)

    conversation = await conversation_service.get_conversation(...)

    if conversation.conversation_mode == "human":
        return human_mode_stream(...)

    complaint_orchestrator = ComplaintConversationOrchestrator(...)

    run_result = await complaint_orchestrator.prepare_run(
        conversation_id=...,
        user_id=...,
        user_message_id=...,
        user_message=...,
    )

    stream = ComplaintChatStreamOrchestrator(
        run_result=run_result,
        ...
    )
    return StreamingResponse(stream.run())
```

### 4.4 强约束

`chat.py` 自己不负责：

- 判定是否拆单
- 选择 executor
- 决定是否 review 通过
- 决定是否 handoff

这些必须全部下沉到 complaint service 层。

## 5. 票据归并入口：`TicketMergeService`

对应新增文件：

- `backend/app/services/complaint/ticket_merge_service.py`

### 5.1 这个 service 的职责

这是整个系统最关键的入口 service，负责回答：

`这条用户消息，应该归并到当前 ticket，还是引入 secondary issue，还是创建新 ticket？`

### 5.2 必须提供的方法

```python
async def get_active_ticket(conversation_id: str) -> ComplaintTicket | None

async def resolve_ticket_for_message(
    conversation_id: str,
    user_message: str,
    conversation_snapshot: dict,
) -> ActiveTicketResolution

async def create_initial_ticket(...)

async def attach_secondary_issue(...)

async def split_to_new_ticket(...)
```

### 5.3 `resolve_ticket_for_message()` 输出合同

必须统一返回：

```json
{
  "decision": "reuse_active_ticket",
  "ticket_id": "tk_123",
  "previous_ticket_id": null,
  "reason": "用户仍在围绕同一订单延迟问题持续表达不满",
  "issue_continuity": "same_issue",
  "confidence": 0.93
}
```

允许的 `decision`：

- `create_initial_ticket`
- `reuse_active_ticket`
- `record_secondary_issue`
- `create_new_ticket`

### 5.4 决策顺序

必须固定为：

1. 查当前会话是否存在主活动 ticket
2. 若不存在，直接创建初始 ticket
3. 若存在，默认先走 `reuse_active_ticket`
4. 只有在高置信度新问题下，才允许 `create_new_ticket`
5. 若不确定，但识别到第二问题，先 `record_secondary_issue`

### 5.5 Phase 1 的保守策略

`uncertain` 一律不拆单。

实现要求：

- `uncertain` -> `record_secondary_issue` 或 `reuse_active_ticket`
- 不允许因为模型犹豫就新建 ticket

## 6. Ticket 快照更新：`TicketService`

对应新增文件：

- `backend/app/services/complaint/ticket_service.py`

### 6.1 职责

负责 ticket 的状态推进和快照同步。

### 6.2 必须提供的方法

```python
async def create_ticket(...)
async def update_snapshot(...)
async def update_classification(...)
async def set_current_agent(...)
async def set_current_node(...)
async def increment_unresolved_turns(...)
async def reset_unresolved_turns(...)
async def mark_pending_review(...)
async def mark_rework_required(...)
async def mark_handoff_pending(...)
async def mark_resolved(...)
async def mark_closed(...)
```

### 6.3 关键规则

1. 每次 ticket 状态变化，都必须同步更新 `Conversation` 快照字段。
2. `Conversation.current_ticket_id` 必须始终指向当前主活动 ticket。
3. `mark_handoff_pending()` 时必须同步：
   - `ticket.status = handoff_pending`
   - `conversation.conversation_mode = pending`

### 6.4 快照字段同步原则

每次更新 ticket 后，必须同步这些字段到 `Conversation`：

- `complaint_status`
- `primary_issue_tag`
- `current_agent_tag`
- `current_node_key`
- `priority_level`
- `risk_level`
- `unresolved_turns`
- `review_status`
- `review_score`
- `block_reason`

## 7. 任务创建与推进：`TaskService`

对应新增文件：

- `backend/app/services/complaint/task_service.py`

### 7.1 职责

把 planner 决策和 executor 行为持久化成任务。

### 7.2 必须提供的方法

```python
async def create_task(...)
async def start_task(task_id: str)
async def complete_task(task_id: str, output_payload: dict)
async def fail_task(task_id: str, reason: str)
async def block_task(task_id: str, reason: str)
async def mark_waiting_review(task_id: str)
```

### 7.3 Phase 1 的任务类型

必须固定为：

- `triage`
- `plan`
- `emotion`
- `faq`
- `case_collect`
- `resolution`
- `handoff`
- `review`

### 7.4 任务创建规则

每一轮用户消息，至少会出现：

1. `triage` task
2. `plan` task
3. 一个 executor task
4. 一个 `review` task

允许优化为：

- `triage` 和 `plan` 只保留结构化记录，不强制全部独立显示在前端

但数据库层仍建议完整保留。

## 8. 规划者：`PlannerService`

对应新增文件：

- `backend/app/services/complaint/planner_service.py`

### 8.1 职责

根据当前 ticket 快照和 front_desk 输出，决定当前应该由谁处理。

### 8.2 必须输出的字段

```json
{
  "assigned_agent_tag": "case_intake_agent",
  "task_type": "case_collect",
  "goal": "收集订单号、截图和故障时间",
  "success_criteria": [
    "订单号已提供",
    "至少有一张截图"
  ],
  "should_handoff": false,
  "next_node_key": "case_collect"
}
```

### 8.3 Phase 1 规划规则

必须先简化，不做复杂并行：

1. 一轮只分配一个主 executor
2. 优先保持口径统一
3. 只有高风险或连续失败时才转人工

### 8.4 规划优先级

第一阶段推荐优先级：

1. 高风险或明确人工请求 -> `handoff_orchestrator_agent`
2. 情绪失控 -> `emotion_deescalation_agent`
3. 信息不足 -> `case_intake_agent`
4. 规则解释 -> `faq_policy_agent`
5. 已具备信息且可推进 -> `resolution_execution_agent`

## 9. 执行者：`ExecutorService`

对应新增文件：

- `backend/app/services/complaint/executor_service.py`

### 9.1 职责

统一执行 planner 分派的 executor agent。

### 9.2 必须支持的 executor

- `emotion_deescalation_agent`
- `faq_policy_agent`
- `case_intake_agent`
- `resolution_execution_agent`
- `handoff_orchestrator_agent`

### 9.3 输入格式

必须传入：

- `ticket snapshot`
- `last user message`
- `relevant message summary`
- `collected slots`
- `goal`
- `success_criteria`

### 9.4 输出格式

必须统一成：

```json
{
  "content": "回复用户的候选文本",
  "task_completed": true,
  "collected_slots": {
    "order_id": "123456"
  },
  "handoff_recommended": false,
  "handoff_reason": null,
  "next_hint": "可进入处理推进"
}
```

## 10. 审查者：`ReviewService`

对应新增文件：

- `backend/app/services/complaint/review_service.py`

### 10.1 职责

统一把 executor 输出送入 reviewer，决定能不能对外回复。

### 10.2 必须提供的方法

```python
async def create_pending_review(...)
async def run_review(...)
async def apply_review_result(...)
```

### 10.3 reviewer 输入

必须至少包含：

- `ticket snapshot`
- `task output`
- `policy context`
- `current risk level`
- `handoff rules`

### 10.4 reviewer 输出

必须统一成：

```json
{
  "status": "passed",
  "score": 88,
  "risk_level": "low",
  "reasons": [],
  "suggested_next_agent": null,
  "should_handoff": false
}
```

或者：

```json
{
  "status": "rejected",
  "score": 63,
  "risk_level": "medium",
  "reasons": [
    "缺少订单号，不能给出处理承诺",
    "回复里存在越权赔付表述"
  ],
  "suggested_next_agent": "case_intake_agent",
  "should_handoff": false
}
```

### 10.5 驳回规则

`apply_review_result()` 必须处理：

1. `passed`
   - task -> `done`
   - ticket -> `in_progress` 或 `resolved`
2. `rejected`
   - task -> `failed`
   - ticket -> `rework_required`
   - `rework_count + 1`
3. `escalated`
   - ticket -> `handoff_pending`

### 10.6 强约束

review 未通过时：

- 不允许发 `assistant.final` 正文
- 只允许发状态事件

## 11. 人工升级：`ComplaintHandoffService`

对应新增文件：

- `backend/app/services/complaint/handoff_service.py`

### 11.1 职责

把业务上的 handoff 语义和底层 `support/handoff.py` 连接起来。

### 11.2 必须提供的方法

```python
async def request_handoff_for_ticket(...)
async def accept_handoff(...)
async def finish_handoff(...)
```

### 11.3 `request_handoff_for_ticket()` 必须做什么

1. 更新 ticket 为 `handoff_pending`
2. 生成 `handoff_summary`
3. 写入 `handoff_reason`
4. 调用底层 support handoff，把 conversation 切到 `pending`
5. 发出：
   - `complaint.handoff_requested`
   - `server.handoff_requested`

### 11.4 `accept_handoff()` 必须做什么

1. 把 conversation 从 `pending` 切到 `human`
2. ticket 变成 `handed_off`
3. 记录 `handoff_operator`

### 11.5 `finish_handoff()` 必须做什么

1. 接收人工总结
2. 根据人工操作决定：
   - `resolved`
   - `closed`
   - 或重新交回 AI
3. 写回 ticket 和 conversation 快照

## 12. orchestrator 总体流程

对应新增文件：

- `backend/app/services/complaint/orchestrator.py`

### 12.1 推荐入口方法

```python
async def prepare_run(
    conversation_id: str,
    user_id: str,
    user_message_id: str,
    user_message: str,
) -> ComplaintRunContext:
    ...
```

### 12.2 `prepare_run()` 固定流程

必须固定为：

1. 读取 conversation 快照
2. 调 `TicketMergeService.resolve_ticket_for_message`
3. 获取或创建主活动 ticket
4. 创建 `triage` task
5. 调 `front_desk_agent`
6. 更新 ticket 标签、情绪、风险、continuity
7. 创建 `plan` task
8. 调 `PlannerService`
9. 决定 executor
10. 创建 executor task
11. 生成 run context

### 12.3 `execute_run()` 固定流程

必须固定为：

1. 执行 executor
2. 更新 task output
3. 创建 review task
4. 调 reviewer
5. 应用 review 结果
6. 如果需要 handoff，走 `ComplaintHandoffService`
7. 组装最终 stream events

### 12.4 返回对象

`ComplaintRunContext` 必须至少包含：

- `conversation`
- `ticket`
- `planner_result`
- `executor_task`
- `stream_events`
- `assistant_candidate_content`
- `review_result`
- `handoff_result`

## 13. `chat_stream.py` 的 complaint 扩展规则

对应文件：

- [chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py)

### 13.1 必须新增的事件顺序

推荐顺序：

```text
meta.start
complaint.ticket.created / merged / updated
complaint.task.created (triage)
complaint.task.completed (triage)
complaint.task.created (plan)
complaint.task.completed (plan)
complaint.task.created (executor)
assistant.delta ...
complaint.task.completed (executor)
complaint.review.pending
complaint.review.passed / rejected
assistant.final 或 complaint.handoff_requested
```

### 13.2 assistant.final 发出的唯一条件

只有同时满足以下条件，才允许发：

1. `review.status == passed`
2. `ticket.status != handoff_pending`
3. `assistant_candidate_content` 非空

## 14. `support.py` 的 complaint 扩展规则

对应文件：

- [support.py](/Users/wang/code/my/embedease-ai/backend/app/routers/support.py)

### 14.1 会话列表接口必须增加

- `current_ticket_id`
- `complaint_status`
- `primary_issue_tag`
- `current_agent_tag`
- `priority_level`
- `risk_level`
- `review_status`
- `review_score`
- `block_reason`

### 14.2 会话详情接口必须增加

- `current_ticket`
- `recent_tasks`
- `latest_review`
- `secondary_issues`
- `handoff_summary`

### 14.3 人工接入接口必须联动 complaint 服务

不能只改 `Conversation.handoff_state`，还必须联动 ticket 状态。

## 15. 异常分支处理

### 15.1 planner 失败

处理规则：

- ticket 标记为 `blocked`
- 写 `block_reason = planner_failed`
- 不直接给用户编造答案

### 15.2 executor 失败

处理规则：

- task -> `failed`
- ticket -> `blocked` 或 `handoff_pending`
- 依据风险和失败类型决定

### 15.3 reviewer 失败

处理规则：

- 默认走保守策略
- 若无法完成审查，则直接 `handoff_pending`

### 15.4 ticket 归并判断失败

处理规则：

- 默认归并到当前主 ticket
- 并标记 `issue_continuity = uncertain`

## 16. Phase 1 完成判定

当以下条件全部满足时，这份后端流程规格才算被正确实现：

1. `chat.py` 已经接入 complaint orchestrator
2. Ticket merge / secondary issue / split 规则已落地
3. 每轮消息至少产生 triage / plan / executor / review 这四类处理记录
4. review 未通过时不会直接对用户输出候选答案
5. handoff_pending -> human 链路已与 ticket 状态机打通
6. support API 能返回 ticket 级处理信息

缺任何一项，都说明 Phase 1 主链路还没真正完成。
