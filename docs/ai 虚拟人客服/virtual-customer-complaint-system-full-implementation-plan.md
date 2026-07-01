# EmbedeaseAI AI 虚拟人客诉系统完整实施规划

本文档的业务职责，是把 `embedease-ai` 从当前“聊天 + 人工接管”的支持系统，升级成“面向客诉闭环处理的多角色虚拟人客服系统”的完整实施蓝图。它不是概念性路线图，而是基于当前代码结构，明确状态流转、模块拆分、表结构扩展、接口协议、事件体系和实施顺序，供后续开发直接落地。

## 1. 文档结论

当前仓库已经具备多 Agent、流式事件、人工接入、客服工作台、定时任务的基础骨架，但还没有把“客诉问题单、处理任务、审查返工、巡查自愈、绩效统计”建成一等运行时对象。

因此这次改造的核心，不是再加几个 prompt，而是做五件事：

1. 把 `conversation + message` 扩展成 `conversation + complaint ticket + task + review + patrol`
2. 把当前 `handoff_state(ai/pending/human)` 升级成完整客诉状态机
3. 把当前 `Supervisor` 路由升级成“规划者 + 执行者 + 审查者 + 巡查者”的运行框架
4. 把 SSE / WebSocket / Support Workbench 全部切到“问题处理状态可见”
5. 把 scheduler 从“单纯定时任务框架”升级成“客诉巡查与运营任务调度器”

## 2. 当前代码基线

本规划基于以下现有模块判断，不做脱离仓库现实的设计。

### 2.1 后端现状

- 聊天主入口：[chat.py](/Users/wang/code/my/embedease-ai/backend/app/routers/chat.py)
- 流式编排层：[chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py)
- 会话/消息服务：[conversation.py](/Users/wang/code/my/embedease-ai/backend/app/services/conversation.py)
- Agent 运行时骨架：
  - [service.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/service.py)
  - [factory.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/factory.py)
  - [config.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/config.py)
- 客服接管服务：[handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py)
- 客服接口：[support.py](/Users/wang/code/my/embedease-ai/backend/app/routers/support.py)
- 会话模型：[conversation.py](/Users/wang/code/my/embedease-ai/backend/app/models/conversation.py)
- 消息模型：[message.py](/Users/wang/code/my/embedease-ai/backend/app/models/message.py)
- SSE 事件定义：[events.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/events.py)
- WebSocket 协议：[websocket.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/websocket.py)
- 调度器基础：
  - [models.py](/Users/wang/code/my/embedease-ai/backend/app/scheduler/state/models.py)
  - [base.py](/Users/wang/code/my/embedease-ai/backend/app/scheduler/tasks/base.py)

### 2.2 前端现状

- 用户聊天页入口：[page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/chat/page.tsx)
- 聊天代理接口：[route.ts](/Users/wang/code/my/embedease-ai/frontend/app/api/v1/chat/route.ts)
- 客服工作台页：[page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/page.tsx)
- 单会话客服页：[page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/[conversationId]/page.tsx)
- 客服端状态仓库：[support-store.ts](/Users/wang/code/my/embedease-ai/frontend/stores/support-store.ts)

### 2.3 当前系统真实边界

当前系统已经支持：

- 用户消息持久化
- AI 流式回复
- 工具调用追踪
- 人工客服介入与退出
- WebSocket 推送人工消息
- 客服工作台按 `handoff_state` 筛选会话
- Agent 配置与知识源配置
- 基础 scheduler 任务执行框架

当前系统还不支持：

- 客诉问题分类状态
- 问题单级别状态机
- 多角色执行任务编排
- 审查/返工循环
- 巡查/阻塞恢复
- Agent 绩效和知识缺口运营

## 3. 当前架构存在的问题

### 3.1 状态过薄

[conversation.py](/Users/wang/code/my/embedease-ai/backend/app/models/conversation.py) 只有 `handoff_state` 和在线状态，无法表达：

- 当前问题标签
- 当前处理节点
- 问题严重度
- 是否处于返工
- 是否阻塞
- 是否等待审查
- 为什么转人工

### 3.2 消息即流程

[chat.py](/Users/wang/code/my/embedease-ai/backend/app/routers/chat.py) 和 [chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py) 当前仍以“收到用户消息 -> 生成回复 -> 落库 assistant 消息”为主，不存在“先建任务、再执行、再审查、再对外回复”的中间运行层。

### 3.3 人工接管过于简单

[handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py) 只实现了：

- `AI -> HUMAN`
- `HUMAN -> AI`

没有实现：

- `AI -> PENDING -> HUMAN`
- 升级原因结构化记录
- 接管摘要
- 人工完成后的问题单归档

### 3.4 前端只能展示“人工/AI”

[support-store.ts](/Users/wang/code/my/embedease-ai/frontend/stores/support-store.ts) 当前核心状态只有：

- `handoffState`
- `operator`
- `userOnline`
- `messages`

客服工作台无法看到：

- 当前负责 Agent
- 当前问题标签
- 当前处理节点
- 审查是否通过
- 阻塞原因
- 风险等级

## 4. 改造目标架构

目标架构分为四层。

### 4.1 交互层

- 用户聊天界面
- 客服工作台
- 运营配置后台

### 4.2 应用编排层

- `ComplaintConversationOrchestrator`
- `ComplaintPlannerService`
- `ComplaintReviewService`
- `ComplaintHandoffService`

### 4.3 Agent 运行层

- `front_desk_agent`
- `service_planner_agent`
- `emotion_deescalation_agent`
- `faq_policy_agent`
- `case_intake_agent`
- `resolution_execution_agent`
- `handoff_orchestrator_agent`
- `quality_reviewer_agent`
- `operations_patrol_agent`

### 4.4 领域模型层

- `Conversation`
- `ComplaintTicket`
- `ComplaintTask`
- `ComplaintReview`
- `ComplaintPatrolEvent`
- `AgentScoreSnapshot`

## 5. 目标运行时主链路

### 5.1 用户实时消息处理链

```text
POST /api/v1/chat
-> 保存 user message
-> 获取/创建 complaint ticket
-> front_desk 识别问题标签与风险
-> service_planner 生成当前任务
-> 执行 agent 完成任务
-> quality_reviewer 审查输出
-> 审查通过: 输出 assistant.final 并落库
-> 审查拒绝: 进入 rework 或 handoff_pending
```

### 5.2 人工升级链

```text
执行/审查阶段触发 handoff
-> ticket.status = handoff_pending
-> conversation.handoff_state = pending
-> 生成 handoff summary
-> 推送 support.handoff_requested / server.conversation_state
-> 客服接入后 conversation.handoff_state = human
-> ticket.status = handed_off
```

### 5.3 巡查自愈链

```text
scheduler 触发 patrol task
-> 扫描 blocked/长时间 pending_review/长时间 handoff_pending
-> 写入 patrol event
-> 自动重试 / 自动升级 / 自动告警
-> 更新 ticket/task 状态
```

### 5.4 单会话问题单归并链

这里必须明确一个关键规则：用户在一个会话里持续表达不满、补充细节、重复催办时，默认不是不断新建 ticket，而是持续归并到当前活动问题单。

默认处理链如下：

```text
POST /api/v1/chat
-> 保存 user message
-> 查询当前 conversation 是否存在 active ticket
-> 若存在 active ticket: 先判断是“同一问题继续沟通”还是“新问题”
-> 同一问题: 写入当前 ticket，增加 timeline / unresolved_turns
-> 新问题: 关闭或挂起旧 ticket，再新建 ticket
```

这条规则是主链路强约束。否则用户一句一句补充信息、发泄情绪、重复催促时，系统会在一个会话里产生大量重复问题单，后端状态机会失控，前端工作台也无法判断当前到底在处理哪一个问题。

## 6. 客诉领域状态机

这里必须把“会话状态”和“问题单状态”拆开。

### 6.1 会话状态

会话状态保留在 `Conversation`，只表达对话通道层状态：

- `ai`
- `pending`
- `human`
- `closed`

建议新增枚举：

```python
class ConversationMode(StrEnum):
    AI = "ai"
    PENDING = "pending"
    HUMAN = "human"
    CLOSED = "closed"
```

### 6.2 问题单状态

问题单状态表达业务处理进度：

- `new`
- `triaged`
- `planned`
- `in_progress`
- `pending_review`
- `rework_required`
- `blocked`
- `handoff_pending`
- `handed_off`
- `resolved`
- `closed`

建议新增枚举：

```python
class ComplaintStatus(StrEnum):
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
```

### 6.3 任务状态

任务状态表达执行单元的运行情况：

- `queued`
- `running`
- `waiting_review`
- `done`
- `failed`
- `cancelled`
- `blocked`

### 6.4 审查状态

- `pending`
- `passed`
- `rejected`
- `escalated`

### 6.5 巡查状态

- `open`
- `auto_recovered`
- `escalated`
- `ignored`

### 6.6 问题单归并状态规则

这里不是新的状态枚举，而是 ticket 生命周期的强约束规则：

1. 一个 `conversation` 在任一时刻默认只允许存在 `1` 个主活动 ticket。
2. 主活动 ticket 指状态属于以下集合之一：
   - `new`
   - `triaged`
   - `planned`
   - `in_progress`
   - `pending_review`
   - `rework_required`
   - `blocked`
   - `handoff_pending`
   - `handed_off`
3. 只有当旧 ticket 进入以下状态后，才允许无冲突地创建新 ticket：
   - `resolved`
   - `closed`
4. 如果旧 ticket 仍是活动状态，但用户明确提出另一个独立问题，系统允许“拆新 ticket”，但必须把旧 ticket 置为：
   - `blocked`
   - 或继续保持活动并标记为非当前主 ticket
5. 第一阶段实现时，不允许一个 conversation 同时并行推进多个主活动 ticket。

第一阶段的硬规则必须是：

`一个会话只维护一个当前主问题单，除非系统明确判断用户提出了新的独立问题。`

## 7. 关键状态流转定义

## 7.0 问题单归并与拆单规则

这个规则必须在系统第一阶段就冻结，否则 ticket 数量会失控，planner、handoff、patrol、workbench 全部会变复杂。

### 7.0.1 默认规则

默认采用：

`一个 conversation 同一时刻只允许 1 个主活动问题单。`

这里的“主活动问题单”指状态属于以下集合之一的 ticket：

- `new`
- `triaged`
- `planned`
- `in_progress`
- `pending_review`
- `rework_required`
- `blocked`
- `handoff_pending`
- `handed_off`

也就是说，只要当前会话里已经存在一个还没真正结束的问题单，用户继续说话时，系统默认都应该先归并到这个 ticket，而不是新建 ticket。

### 7.0.2 不创建新 ticket 的场景

以下情况必须归并到当前活动 ticket：

- 用户继续补充订单号、截图、时间、渠道等信息
- 用户继续发泄情绪、表达不满、重复投诉
- 用户催进度、追问结果、反复确认同一规则
- 用户围绕同一个处理目标继续追问，例如“什么时候处理完”“为什么还没退款”“你们到底怎么解决”
- 用户在人工等待期间继续发送情绪性消息

这些消息会改变：

- `sentiment`
- `severity`
- `unresolved_turns`
- `latest_user_goal`
- `secondary_issue_notes`

但不会改变“当前主 ticket 还是这一单”的判断。

### 7.0.3 允许创建新 ticket 的场景

只有满足以下条件之一时，才允许创建新 ticket：

1. 当前主 ticket 已 `resolved` 或 `closed`，用户提出一个新的独立问题。
2. 当前消息与现有主 ticket 在以下至少两项上明显不同，并且经过 `front_desk_agent + service_planner_agent` 双重判定：
   - 订单主体不同
   - 问题域不同
   - 处理目标不同
   - 责任归属不同
   - 所需处理 SOP 不同
3. 人工客服或后台运营显式执行“拆单”操作。

### 7.0.4 旧问题未完结时出现第二问题的处理规则

这是最容易失控的场景。

规则如下：

1. 默认不自动新建第二个主 ticket。
2. 先把新问题写入当前主 ticket 的 `secondary_issues` 或等价扩展字段。
3. 由 `service_planner_agent` 判断：
   - 是否可以并单处理
   - 是否需要等待主问题结束后再开新单
   - 是否风险过高，必须人工拆单
4. 只有当 planner 输出 `should_split_ticket = true`，或者人工明确操作拆单时，才真正创建第二张 ticket。

### 7.0.5 推荐实现规则

建议后端增加一个统一判定函数，例如：

```python
async def get_or_create_active_ticket(
    conversation_id: str,
    user_message: str,
    message_context: dict,
) -> ComplaintTicket:
    ...
```

处理顺序必须固定为：

1. 先查当前会话是否已有活动 ticket
2. 如果没有，创建新 ticket
3. 如果有，先归并并更新 ticket 快照
4. 再由 `front_desk_agent` 判断是否出现 secondary issue
5. 再由 `service_planner_agent` 判断是否需要拆单
6. 只有 planner/人工明确批准后，才创建新 ticket

### 7.0.6 对前后端的直接影响

后端必须保证：

- 一个会话随时能查到唯一主活动 ticket
- 用户连续发多轮情绪消息不会制造多个重复 ticket
- handoff、review、patrol 都围绕主活动 ticket 进行

前端必须保证：

- 用户侧默认只展示“当前问题处理进度”
- 客服工作台默认聚焦“当前主 ticket”
- 如果存在 `secondary_issues`，只作为辅助信息展示，而不是默认展开多个并行主问题

### 7.1 正常 AI 解决流

```text
conversation.mode = ai
ticket.status = new

new -> triaged
triaged -> planned
planned -> in_progress
in_progress -> pending_review
pending_review -> resolved
resolved -> closed
```

### 7.2 审查返工流

```text
in_progress -> pending_review
pending_review -> rework_required
rework_required -> planned
planned -> in_progress
```

约束：

- 单 ticket 默认最多允许 2 次返工
- 连续 2 次驳回自动转 `handoff_pending`

### 7.3 升级人工流

```text
new/triaged/planned/in_progress/pending_review
-> handoff_pending
-> handed_off
-> resolved
-> closed
```

约束：

- `ticket.status = handoff_pending` 时，`conversation.mode` 必须同步为 `pending`
- 客服真正接入时，`conversation.mode = human`

### 7.4 阻塞恢复流

```text
in_progress -> blocked
blocked -> planned
blocked -> handoff_pending
blocked -> closed
```

约束：

- 只有 `operations_patrol_agent` 或后台人工操作可以把 `blocked` 改回可执行状态

### 7.5 同一问题持续聊天流

这是客服场景里最容易出错的一类状态流转，必须单独定义。

典型用户行为：

- 继续补充订单号、截图、时间
- 重复表达不满
- 追问进度
- 换一种说法重复同一诉求
- 在等待期间反复催促

这些行为默认都应归并到当前活动 ticket，而不是创建新 ticket。

标准流转：

```text
active ticket exists
-> new user message arrives
-> router 判断 issue_continuity = same_issue
-> current ticket.updated_at 刷新
-> unresolved_turns +1 或按规则重置
-> planner 重新评估下一步
-> 继续在当前 ticket 上推进
```

### 7.6 新问题拆单流

只有满足“新问题”判定规则时，才允许拆出新的 ticket。

标准流转：

```text
active ticket exists
-> new user message arrives
-> router 判断 issue_continuity = new_issue
-> old ticket 标记为 resolved / blocked / superseded
-> create new ticket
-> new ticket.status = new
-> 新 ticket 成为当前主 ticket
```

为了防止误拆单，第一阶段必须把新问题判定门槛设高。

## 8. 角色与职责映射

### 8.1 `front_desk_agent`

职责：

- 分析用户输入
- 给出 `primary_issue_tag`
- 给出 `sentiment`
- 给出 `severity`
- 判断是否立即人工升级

输入：

- 当前用户消息
- 最近对话摘要
- 最近一次 ticket 快照

输出：

```json
{
  "primary_issue_tag": "emotion",
  "secondary_tags": ["policy"],
  "sentiment": "negative",
  "severity": "medium",
  "should_handoff": false,
  "reason": "用户当前主要在表达不满，并询问规则",
  "issue_continuity": "same_issue"
}
```

这里新增一个强制字段：

- `issue_continuity`
  - `same_issue`
  - `new_issue`
  - `uncertain`

它的职责不是做最终拆单，而是给 `ticket_service` 提供归并或拆单判断依据。

### 8.2 `service_planner_agent`

职责：

- 根据 ticket 状态和标签选择执行 Agent
- 生成当前任务
- 明确成功标准和升级条件

输出：

```json
{
  "task_type": "emotion_deescalation",
  "assigned_agent_tag": "emotion_deescalation_agent",
  "goal": "先安抚情绪并引导用户提供订单号",
  "success_criteria": [
    "用户愿意继续沟通",
    "至少补齐一个关键槽位"
  ],
  "fallback_action": "handoff_pending"
}
```

### 8.3 执行 Agent

执行 Agent 只做一个问题域，不负责全局路由。

第一阶段固定：

- `emotion_deescalation_agent`
- `faq_policy_agent`
- `case_intake_agent`
- `resolution_execution_agent`
- `handoff_orchestrator_agent`

### 8.4 `quality_reviewer_agent`

职责：

- 审查执行结果
- 输出分数、风险、返工建议、是否允许对外发送

### 8.5 `operations_patrol_agent`

职责：

- 巡查长时间不推进 ticket
- 发现异常循环
- 自动恢复或升级人工

## 9. 数据模型设计

## 9.1 Conversation 表扩展

修改文件：[conversation.py](/Users/wang/code/my/embedease-ai/backend/app/models/conversation.py)

建议新增字段：

```python
complaint_ticket_id: Mapped[str | None]
conversation_mode: Mapped[str]  # ai/pending/human/closed
primary_issue_tag: Mapped[str | None]
current_agent_tag: Mapped[str | None]
current_node_key: Mapped[str | None]
priority_level: Mapped[str | None]
last_router_reason: Mapped[str | None]
last_review_status: Mapped[str | None]
last_review_score: Mapped[int | None]
block_reason: Mapped[str | None]
```

说明：

- `handoff_state` 可以保留一版兼容，但新代码统一改读 `conversation_mode`
- `current_agent_id` 现在表示人工客服在线标识，不适合复用为 AI 责任 Agent

### 9.2 新增 `ComplaintTicket`

建议新增文件：

- `backend/app/models/complaint_ticket.py`
- `backend/app/schemas/complaint_ticket.py`
- `backend/app/repositories/complaint_ticket.py`

建议字段：

```python
id
conversation_id
user_id
status
is_primary_active
parent_ticket_id
superseded_by_ticket_id
issue_fingerprint
primary_issue_tag
secondary_issue_tags
sentiment
severity
priority_level
current_agent_tag
current_task_id
unresolved_turns
rework_count
requires_handoff
handoff_reason
resolution_summary
collected_slots
created_at
updated_at
resolved_at
closed_at
```

新增字段含义：

- `is_primary_active`
  - 当前是否为该 conversation 的主活动问题单
- `parent_ticket_id`
  - 若当前 ticket 来自旧问题单衍生，可建立关联
- `superseded_by_ticket_id`
  - 若当前 ticket 被新 ticket 替代，用于链路追踪
- `issue_fingerprint`
  - 问题语义指纹，用于判断后续消息是否仍属于同一问题

### 9.3 新增 `ComplaintTask`

建议新增文件：

- `backend/app/models/complaint_task.py`
- `backend/app/schemas/complaint_task.py`
- `backend/app/repositories/complaint_task.py`

建议字段：

```python
id
ticket_id
task_type
assigned_agent_tag
status
input_snapshot
output_payload
goal
success_criteria
failure_reason
started_at
finished_at
created_at
updated_at
```

### 9.4 新增 `ComplaintReview`

建议字段：

```python
id
ticket_id
task_id
reviewer_agent_tag
status
score
risk_level
reasons
suggested_next_agent
review_payload
created_at
```

### 9.5 新增 `ComplaintPatrolEvent`

建议字段：

```python
id
ticket_id
task_id
event_type
status
detected_reason
action_taken
result_payload
created_at
resolved_at
```

### 9.6 新增 `AgentScoreSnapshot`

建议字段：

```python
id
agent_tag
window_type
window_start
window_end
pass_rate
handoff_rate
avg_review_score
avg_resolution_time_ms
rework_rate
violation_rate
payload
created_at
```

## 10. Repository 与 Service 层改造

### 10.1 保留并扩展现有服务

[conversation.py](/Users/wang/code/my/embedease-ai/backend/app/services/conversation.py) 保留消息落库职责，不再承担客诉业务编排。

[handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py) 保留人工接入状态管理，但要升级成 `ComplaintHandoffService`。

### 10.2 新增领域服务

建议新增：

- `backend/app/services/complaint/ticket_service.py`
- `backend/app/services/complaint/task_service.py`
- `backend/app/services/complaint/review_service.py`
- `backend/app/services/complaint/patrol_service.py`
- `backend/app/services/complaint/orchestrator.py`

职责划分：

- `ticket_service`
  - 创建/更新 ticket
  - 判断归并到当前 ticket 还是拆出新 ticket
  - 维护 ticket 状态机
- `task_service`
  - 创建与推进任务
  - 记录执行输入输出
- `review_service`
  - 执行审查规则
  - 记录审查结果
- `patrol_service`
  - 巡查超时和阻塞
  - 写 patrol event
- `orchestrator`
  - 串联 front desk -> planner -> executor -> reviewer -> handoff

## 11. Chat 主链路代码改造

修改文件：[chat.py](/Users/wang/code/my/embedease-ai/backend/app/routers/chat.py)

当前流程：

```text
save user message
-> if human mode: 直接发给客服
-> else: chat_stream orchestrator.run()
```

目标流程：

```text
save user message
-> load conversation + ticket
-> if conversation_mode == human: 转客服
-> complaint orchestrator.run()
-> stream structured complaint events
-> save assistant response / task / review / ticket state
```

建议新增步骤：

1. 查询或创建 `ComplaintTicket`
2. 若存在活动 ticket，调用 `ticket_service.resolve_active_ticket_for_message()`
3. 根据结果决定：
   - 归并到当前 ticket
   - 创建新 ticket
   - 切换当前主 ticket
2. 判断 `conversation_mode`
3. 调用 `ComplaintConversationOrchestrator`
4. 在 orchestrator 内部调用：
   - `front_desk_agent`
   - `service_planner_agent`
   - domain executor
   - `quality_reviewer_agent`
5. 审查通过后才发出 `assistant.final`

建议新增一个明确的归并判断返回对象：

```json
{
  "decision": "reuse_active_ticket",
  "ticket_id": "tk_123",
  "previous_ticket_id": null,
  "reason": "用户仍在围绕订单延迟和补偿问题继续表达不满",
  "confidence": 0.91
}
```

以及新问题拆单时：

```json
{
  "decision": "create_new_ticket",
  "ticket_id": "tk_456",
  "previous_ticket_id": "tk_123",
  "reason": "用户已转向全新的安装故障问题，与旧物流投诉不属于同一处理链",
  "confidence": 0.88
}
```

## 12. 流式编排层改造

修改文件：[chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py)

当前职责：

- 发 `meta.start`
- 转发 assistant/tool 事件
- 聚合最终回复
- 落库 assistant message

目标职责：

- 增加 complaint 领域事件透传
- 在最终回复前写入 task/review/ticket 状态
- 支持“审查未通过不对外发完整回答”

建议新增事件类型：

- `complaint.ticket.created`
- `complaint.ticket.updated`
- `complaint.task.created`
- `complaint.task.started`
- `complaint.task.completed`
- `complaint.review.requested`
- `complaint.review.completed`
- `complaint.review.rejected`
- `complaint.blocked`
- `complaint.handoff_requested`

## 13. SSE 事件协议扩展

修改文件：[events.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/events.py)

建议新增枚举：

```python
class ComplaintEventType(StrEnum):
    COMPLAINT_TICKET_CREATED = "complaint.ticket.created"
    COMPLAINT_TICKET_UPDATED = "complaint.ticket.updated"
    COMPLAINT_TASK_CREATED = "complaint.task.created"
    COMPLAINT_TASK_STARTED = "complaint.task.started"
    COMPLAINT_TASK_COMPLETED = "complaint.task.completed"
    COMPLAINT_REVIEW_REQUESTED = "complaint.review.requested"
    COMPLAINT_REVIEW_COMPLETED = "complaint.review.completed"
    COMPLAINT_REVIEW_REJECTED = "complaint.review.rejected"
    COMPLAINT_BLOCKED = "complaint.blocked"
    COMPLAINT_HANDOFF_REQUESTED = "complaint.handoff_requested"
```

建议 payload 示例：

```json
{
  "type": "complaint.ticket.updated",
  "payload": {
    "ticket_id": "tk_123",
    "status": "pending_review",
    "primary_issue_tag": "faq_policy",
    "current_agent_tag": "faq_policy_agent",
    "priority_level": "medium"
  }
}
```

## 14. WebSocket 协议扩展

修改文件：[websocket.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/websocket.py)

当前 `SERVER_CONVERSATION_STATE` 只适合表达人工接入状态。

建议扩展 payload：

```python
class ConversationStatePayload(BaseModel):
    conversation_id: str
    handoff_state: str
    ticket_status: str | None = None
    primary_issue_tag: str | None = None
    current_agent_tag: str | None = None
    current_node_key: str | None = None
    priority_level: str | None = None
    review_status: str | None = None
    review_score: int | None = None
    block_reason: str | None = None
    operator: str | None = None
    user_online: bool = False
    peer_last_online_at: str | None = None
    unread_count: int = 0
```

建议新增 server push：

- `server.ticket_updated`
- `server.review_alert`
- `server.handoff_requested`
- `server.blocked_alert`

## 15. Agent 配置体系改造

当前模型：

- [agent.py](/Users/wang/code/my/embedease-ai/backend/app/models/agent.py)
- [agent.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/agent.py)
- [config.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/config.py)

当前 `AgentType` 仍然是：

- `product`
- `faq`
- `kb`
- `custom`

这不适合客诉系统。

### 15.1 第一阶段兼容策略

不要立刻删除旧类型，先新增 `role_tag` 和 `business_domain`：

```python
role_tag: Mapped[str | None]  # front_desk / planner / emotion / faq_policy ...
business_domain: Mapped[str | None]  # complaint_support
skill_bundle_ids: Mapped[list[str] | None]
review_schema_name: Mapped[str | None]
handoff_rules: Mapped[dict[str, Any] | None]
```

### 15.2 第二阶段正式迁移

把 `AgentType` 迁移为：

- `front_desk`
- `planner`
- `executor`
- `reviewer`
- `patrol`
- `custom`

### 15.3 Config Loader 改造

[config.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/config.py) 要能加载：

- `role_tag`
- `skill_bundle_ids`
- `review_schema_name`
- `knowledge_scope`
- `handoff_rules`

## 16. Agent Factory 改造

修改文件：[factory.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/factory.py)

目标：

- 保留单 Agent 构建能力
- 新增 complaint roles 构建能力
- 新增 reviewer/patrol 专用输出 schema

建议新增：

```python
async def build_complaint_role_agent(...)
async def build_reviewer_agent(...)
async def build_patrol_agent(...)
```

建议不要在第一阶段直接引入太复杂的 deer-flow task executor，而是先在 orchestration service 层串起来。

## 17. Knowledge 与 Tool 体系改造

当前工具更偏商品与通用知识检索。客诉系统第一阶段建议只保留四类工具：

- `faq_search`
- `policy_search`
- `case_sop_search`
- `handoff_create`

建议新增目录：

- `backend/app/services/agent/tools/complaint/faq_search.py`
- `backend/app/services/agent/tools/complaint/policy_search.py`
- `backend/app/services/agent/tools/complaint/case_sop_search.py`
- `backend/app/services/agent/tools/complaint/handoff_create.py`

知识源建议按角色可见范围控制：

- `emotion_deescalation_agent`
  - 只看情绪安抚话术边界
- `faq_policy_agent`
  - 看 FAQ + 政策
- `case_intake_agent`
  - 看槽位采集规则
- `resolution_execution_agent`
  - 看 SOP + 时效
- `quality_reviewer_agent`
  - 看政策、风险边界、审查标准

## 18. 人工接管服务改造

修改文件：[handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py)

当前状态机注释是：

```text
AI -> PENDING -> HUMAN -> AI
AI -> HUMAN -> AI
```

但实际 `start_handoff()` 直接把状态写成 `human`。

这需要修正为两步：

### 18.1 AI 触发升级

新增方法：

```python
async def request_handoff(...)
```

职责：

- `conversation_mode = pending`
- `ticket.status = handoff_pending`
- 保存 `handoff_reason`
- 保存 `handoff_summary`
- 发通知给客服工作台

### 18.2 客服真正接入

保留 `start_handoff()`，但语义改为：

- `pending -> human`
- 记录 `handoff_operator`

### 18.3 客服结束服务

`end_handoff()` 改为：

- 若问题已解决：`ticket.status = resolved`
- 若需继续 AI 跟进：`ticket.status = planned`，`conversation_mode = ai`
- 保存人工总结并回写 ticket

## 19. Support API 规划

修改文件：[support.py](/Users/wang/code/my/embedease-ai/backend/app/routers/support.py)

建议新增接口：

- `GET /api/v1/support/tickets`
  - 按 ticket 状态、风险、标签筛选
- `GET /api/v1/support/tickets/{ticket_id}`
  - 查询 ticket + tasks + reviews + patrols
- `POST /api/v1/support/tickets/{ticket_id}/assign`
  - 人工指派
- `POST /api/v1/support/tickets/{ticket_id}/resolve`
  - 标记已解决
- `POST /api/v1/support/tickets/{ticket_id}/reopen`
  - 重新打开
- `POST /api/v1/support/handoff/{conversation_id}/request`
  - AI 或用户请求人工

现有 `/conversations` 接口也应返回 ticket 维度字段。

此外必须新增或补充：

- `GET /api/v1/support/conversations/{conversation_id}/active-ticket`
  - 查询当前会话正在处理的主问题单
- `GET /api/v1/support/conversations/{conversation_id}/tickets`
  - 查询该会话下所有历史 ticket 链

这样客服进入会话时，可以明确区分：

- 当前主问题单
- 历史已解决问题单
- 被新问题替代的问题单

## 20. Scheduler 任务规划

当前 scheduler 已有统一任务抽象：

- [models.py](/Users/wang/code/my/embedease-ai/backend/app/scheduler/state/models.py)
- [base.py](/Users/wang/code/my/embedease-ai/backend/app/scheduler/tasks/base.py)

这非常适合作为巡查与运营任务入口。

建议新增任务：

- `complaint_patrol_task`
  - 巡查 blocked/pending_review/handoff_pending 超时
- `complaint_score_snapshot_task`
  - 每日计算 Agent 绩效
- `complaint_knowledge_gap_task`
  - 汇总高频驳回和高频转人工原因
- `complaint_followup_task`
  - 对高风险 ticket 做回访提醒

建议新增目录：

- `backend/app/scheduler/tasks/complaint_patrol.py`
- `backend/app/scheduler/tasks/complaint_score_snapshot.py`
- `backend/app/scheduler/tasks/complaint_knowledge_gap.py`
- `backend/app/scheduler/tasks/complaint_followup.py`

## 21. 前端用户侧改造

### 21.1 用户聊天页

当前入口：[page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/chat/page.tsx)

用户侧需要新增可见状态：

- 当前处理阶段
- 当前问题标签
- 是否已提交人工处理
- 是否等待补充资料
- 下一步动作

建议增加状态条：

```text
已识别问题 -> 处理中 -> 审查中 -> 已解决
```

### 21.2 SSE 前端处理

当前前端代理只透传 SSE：

[route.ts](/Users/wang/code/my/embedease-ai/frontend/app/api/v1/chat/route.ts)

这可以保留，但前端消费层必须识别新增 complaint 事件并写入状态仓库。

## 22. 前端客服工作台改造

### 22.1 `support-store` 扩展

修改文件：[support-store.ts](/Users/wang/code/my/embedease-ai/frontend/stores/support-store.ts)

建议新增状态：

```ts
ticketStatus: string | null
primaryIssueTag: string | null
currentAgentTag: string | null
currentNodeKey: string | null
priorityLevel: string | null
reviewStatus: string | null
reviewScore: number | null
blockReason: string | null
```

### 22.2 会话详情页扩展

修改文件：[page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/[conversationId]/page.tsx)

建议新增展示区块：

- 问题标签卡片
- 当前节点卡片
- 审查结果卡片
- 收集到的槽位信息
- 转人工原因与摘要
- 巡查告警历史

### 22.3 工作台列表页扩展

修改文件：[page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/page.tsx)

建议新增筛选维度：

- ticket 状态
- 问题标签
- 风险等级
- 是否阻塞
- 是否待人工接入

## 23. 推荐代码目录调整

建议新增如下目录，不破坏现有结构：

```text
backend/app/models/
  complaint_ticket.py
  complaint_task.py
  complaint_review.py
  complaint_patrol_event.py
  agent_score_snapshot.py

backend/app/repositories/
  complaint_ticket.py
  complaint_task.py
  complaint_review.py
  complaint_patrol_event.py
  agent_score_snapshot.py

backend/app/schemas/
  complaint.py
  complaint_ticket.py
  complaint_task.py
  complaint_review.py
  complaint_patrol.py

backend/app/services/complaint/
  orchestrator.py
  ticket_service.py
  task_service.py
  review_service.py
  handoff_service.py
  patrol_service.py
  score_service.py
  state_machine.py

backend/app/services/agent/tools/complaint/
  faq_search.py
  policy_search.py
  case_sop_search.py
  handoff_create.py
```

## 24. Phase 1 必做清单

Phase 1 目标是：让客诉系统形成“识别 -> 执行 -> 审查 -> 升级/解决”的主闭环。

必须做：

- 新增 `ComplaintTicket`
- 新增 `ComplaintTask`
- 新增 `ComplaintReview`
- 给 chat 主链路接入 complaint orchestrator
- 实现 `front_desk_agent`
- 实现 `service_planner_agent`
- 实现 5 个执行 Agent
- 实现 `quality_reviewer_agent`
- 扩展 SSE 事件
- 扩展 Support Workbench 状态展示
- 把 handoff 改成 `pending -> human`

不要做：

- 不要一开始做复杂拖拽 Flow Builder
- 不要一开始做大量并行子 Agent
- 不要一开始做排行榜 UI
- 不要先做跨租户通用组织引擎

## 25. Phase 2 必做清单

Phase 2 目标是：具备“不会卡死”的运维保障。

必须做：

- 新增 `ComplaintPatrolEvent`
- 新增 `complaint_patrol_task`
- 支持 blocked 自动恢复
- 支持 pending_review 超时升级
- 支持 handoff_pending 超时告警

## 26. Phase 3 必做清单

Phase 3 目标是：具备持续优化和运营分析能力。

必须做：

- 新增 `AgentScoreSnapshot`
- 新增分数统计任务
- 新增驳回原因分析
- 新增知识缺口任务

## 27. 迁移顺序建议

最稳妥的迁移顺序：

1. 新增 complaint 数据模型，不改老接口语义
2. 在 `chat.py` 中插入 complaint orchestrator
3. 扩展 `events.py` 和前端状态消费
4. 升级 `handoff.py` 为 pending/human 两段式
5. 扩展客服工作台
6. 接入 scheduler 巡查任务
7. 最后再做绩效和配置后台

## 28. 风险与约束

### 28.1 兼容风险

当前前端很多地方仍直接依赖 `handoff_state`。迁移时必须保留兼容字段至少一个阶段。

### 28.2 复杂度风险

如果同时改表结构、聊天主链路、前端状态仓库和工作台 UI，回归范围很大。建议先完成后端双写和事件兼容，再切 UI。

### 28.3 模型稳定性风险

审查、路由、升级都不能只靠 prompt，需要：

- 结构化输出 schema
- 状态机校验
- 最大返工次数限制
- 明确的兜底 handoff

### 28.4 错误拆单风险

如果没有清晰的“同一问题继续沟通”和“新问题拆单”规则，系统会出现两类严重问题：

1. 用户连续发泄不满时，系统不断创建重复 ticket，导致问题被拆碎。
2. 用户已经提出新问题，系统却继续塞进旧 ticket，导致状态污染和处理错误。

因此第一阶段必须采用保守策略：

- 默认归并到当前活动 ticket
- 只有高置信度新问题才拆新 ticket
- `uncertain` 一律先归并，再由 planner 或人工决定是否拆单

## 29. 最终建议

这次改造不应该继续沿着“AI 回复 + 人工兜底”的思路微调，而要明确进入“问题单驱动”的客诉系统阶段。

对当前仓库最重要的落点是：

1. 把 `Conversation` 从聊天容器升级成客诉入口
2. 把 `ComplaintTicket` 变成主业务对象
3. 把 `ComplaintTask/Review/Patrol` 变成真实运行记录
4. 把 `chat.py + chat_stream.py` 变成客诉编排主链路
5. 把 `support` 工作台从“接消息”升级成“处理问题单”

只有这样，OpenMOSS 那种“像公司一样运转”的思路，才能在 `embedease-ai` 里落成真正可开发、可观测、可运维、可运营的系统。
