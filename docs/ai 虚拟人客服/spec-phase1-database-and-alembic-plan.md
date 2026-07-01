# Phase 1 数据库与 Alembic 迁移设计

本文档的业务职责，是把 AI 虚拟人客诉系统 Phase 1 需要落地的数据库结构写成可执行的设计规格，供后续直接实现 SQLAlchemy Model、Repository、Alembic migration 与数据兼容逻辑。它不讨论抽象方向，只定义字段、关系、索引、迁移顺序和回填规则。

## 1. 本文档解决什么问题

当前系统只有：

- `conversations`
- `messages`
- `tool_calls`
- `agents`

这不足以支撑客诉系统，因为缺少：

- 问题单
- 任务
- 审查记录
- 巡查记录
- Agent 绩效快照

因此 Phase 1 必须把以下对象落库：

1. `Conversation` 扩展为客诉入口快照
2. `ComplaintTicket` 作为主业务对象
3. `ComplaintTask` 作为执行单元
4. `ComplaintReview` 作为质量审查记录
5. `ComplaintPatrolEvent` 作为巡查与恢复记录
6. `AgentScoreSnapshot` 作为后续运营分析基础

## 2. 设计原则

所有表设计必须遵守以下原则：

1. 一个 `conversation` 默认只允许一个主活动 ticket。
2. `Conversation` 存“当前快照”，`Ticket/Task/Review/Patrol` 存“历史明细”。
3. 状态字段必须可索引，不能只放在 JSON 里。
4. 对前端列表页高频使用的字段，必须直接挂在 `Conversation` 或 `ComplaintTicket` 上。
5. 复杂扩展信息允许用 JSON，但核心状态、关系、时间、责任 Agent 不能只放 JSON。
6. 第一期要兼容旧数据，不能破坏现有聊天和人工接管基础能力。

## 3. 需要新增和修改的表

Phase 1 必须完成以下表改造：

1. 修改 `conversations`
2. 新增 `complaint_tickets`
3. 新增 `complaint_tasks`
4. 新增 `complaint_reviews`
5. 新增 `complaint_patrol_events`
6. 新增 `agent_score_snapshots`

## 4. `conversations` 表改造

对应模型文件：

- [conversation.py](/Users/wang/code/my/embedease-ai/backend/app/models/conversation.py)

### 4.1 保留字段

以下字段继续保留：

- `id`
- `user_id`
- `title`
- `created_at`
- `updated_at`
- `handoff_state`
- `handoff_operator`
- `handoff_reason`
- `handoff_at`
- `last_notification_at`
- 在线状态字段
- `greeting_sent`
- `agent_id`

### 4.2 新增字段

必须新增：

```python
current_ticket_id: Mapped[str | None]
conversation_mode: Mapped[str]
complaint_status: Mapped[str | None]
primary_issue_tag: Mapped[str | None]
current_agent_tag: Mapped[str | None]
current_node_key: Mapped[str | None]
priority_level: Mapped[str | None]
risk_level: Mapped[str | None]
unresolved_turns: Mapped[int]
review_status: Mapped[str | None]
review_score: Mapped[int | None]
block_reason: Mapped[str | None]
secondary_issues: Mapped[list[dict] | None]
ticket_snapshot: Mapped[dict | None]
```

### 4.3 字段含义

- `current_ticket_id`
  - 当前会话主活动问题单 ID
- `conversation_mode`
  - 对话通道状态：`ai/pending/human/closed`
- `complaint_status`
  - 当前主 ticket 的状态快照
- `primary_issue_tag`
  - 当前主 ticket 的主问题标签
- `current_agent_tag`
  - 当前正在处理该 ticket 的 AI 岗位
- `current_node_key`
  - 当前流程节点，例如 `triage`, `review`, `handoff_pending`
- `priority_level`
  - 优先级，例如 `low/medium/high/urgent`
- `risk_level`
  - 风险级别，例如 `low/medium/high/critical`
- `unresolved_turns`
  - 当前 ticket 下连续未解决轮次
- `review_status`
  - 最近一次审查结果快照
- `review_score`
  - 最近一次审查分数快照
- `block_reason`
  - 当前阻塞原因
- `secondary_issues`
  - 当前主 ticket 下记录的次级问题列表
- `ticket_snapshot`
  - 给前端和工作台用的快照信息

### 4.4 默认值设计

建议默认值：

- `conversation_mode = "ai"`
- `unresolved_turns = 0`
- `secondary_issues = null`
- `ticket_snapshot = null`

### 4.5 索引设计

建议新增索引：

- `ix_conversations_current_ticket_id`
- `ix_conversations_conversation_mode`
- `ix_conversations_complaint_status`
- `ix_conversations_primary_issue_tag`
- `ix_conversations_priority_level`
- `ix_conversations_risk_level`

### 4.6 兼容策略

Phase 1 期间保留 `handoff_state`，但新代码规则如下：

1. 写入时双写：
   - `conversation_mode`
   - `handoff_state`
2. 读取时优先：
   - `conversation_mode`
   - 若为空再回退到 `handoff_state`

## 5. `complaint_tickets` 表设计

对应新增模型：

- `backend/app/models/complaint_ticket.py`

### 5.1 表职责

`complaint_tickets` 是整个客诉系统的主业务表。

一条 ticket 代表：

- 一个当前正在处理或历史已处理的客户问题单

### 5.2 必须字段

```python
id: str
conversation_id: str
user_id: str
status: str
is_primary_active: bool
parent_ticket_id: str | None
superseded_by_ticket_id: str | None
issue_fingerprint: str | None
primary_issue_tag: str | None
secondary_issue_tags: list[str] | None
secondary_issues: list[dict] | None
sentiment: str | None
severity: str | None
priority_level: str | None
risk_level: str | None
current_agent_tag: str | None
current_task_id: str | None
current_node_key: str | None
unresolved_turns: int
rework_count: int
handoff_required: bool
handoff_reason: str | None
handoff_summary: dict | None
resolved_summary: str | None
slot_data: dict | None
timeline: list[dict] | None
version: int
created_at: datetime
updated_at: datetime
resolved_at: datetime | None
closed_at: datetime | None
```

### 5.3 字段解释

- `status`
  - 取值来自 `ComplaintStatus`
- `is_primary_active`
  - 当前是否为该会话的主活动问题单
- `parent_ticket_id`
  - 若当前 ticket 来自拆单或衍生问题，可追溯来源
- `superseded_by_ticket_id`
  - 若当前 ticket 被新问题单替代，记录替代关系
- `issue_fingerprint`
  - 问题语义指纹，用于后续“归并还是拆单”判断
- `secondary_issue_tags`
  - 当前 ticket 中记录的次级问题标签
- `secondary_issues`
  - 当前 ticket 中记录的次级问题详情
- `slot_data`
  - 已采集的业务槽位，例如订单号、时间、图片、渠道
- `timeline`
  - 关键业务事件时间线，不替代 messages
- `version`
  - 乐观锁版本号，避免并发更新覆盖

### 5.4 外键关系

- `conversation_id -> conversations.id`
- `user_id -> users.id`
- `parent_ticket_id -> complaint_tickets.id`
- `superseded_by_ticket_id -> complaint_tickets.id`

`current_task_id` 第一阶段建议不做硬外键，避免循环依赖；后续通过 service 维护。

### 5.5 索引设计

必须新增：

- `ix_complaint_tickets_conversation_id`
- `ix_complaint_tickets_user_id`
- `ix_complaint_tickets_status`
- `ix_complaint_tickets_is_primary_active`
- `ix_complaint_tickets_primary_issue_tag`
- `ix_complaint_tickets_current_agent_tag`
- `ix_complaint_tickets_priority_level`
- `ix_complaint_tickets_risk_level`
- 组合索引：`(conversation_id, is_primary_active)`
- 组合索引：`(conversation_id, status)`

### 5.6 唯一性约束

第一阶段建议不做数据库层“只能有一个 active ticket”的复杂 partial unique constraint。

原因：

- SQLite 兼容成本高
- 迁移复杂度高

第一阶段改为：

- 用 service 层强约束
- 用 `(conversation_id, is_primary_active)` 组合索引加快校验
- 在创建新主 ticket 前强制把旧主 ticket 改为非主活动

## 6. `complaint_tasks` 表设计

对应新增模型：

- `backend/app/models/complaint_task.py`

### 6.1 表职责

记录 ticket 在处理过程中的每一个可执行工作项。

### 6.2 必须字段

```python
id: str
ticket_id: str
task_type: str
agent_tag: str
status: str
goal: str | None
success_criteria: list[str] | None
input_payload: dict | None
output_payload: dict | None
review_required: bool
review_status: str | None
failure_reason: str | None
retry_count: int
started_at: datetime | None
finished_at: datetime | None
created_at: datetime
updated_at: datetime
```

### 6.3 字段解释

- `task_type`
  - 第一阶段固定值之一：
    - `triage`
    - `plan`
    - `emotion`
    - `faq`
    - `case_collect`
    - `resolution`
    - `handoff`
    - `review`
- `agent_tag`
  - 当前任务责任岗位
- `review_required`
  - 该任务是否必须走 reviewer
- `review_status`
  - 当前任务关联的审查结果快照

### 6.4 外键和索引

- `ticket_id -> complaint_tickets.id`

索引：

- `ix_complaint_tasks_ticket_id`
- `ix_complaint_tasks_status`
- `ix_complaint_tasks_task_type`
- `ix_complaint_tasks_agent_tag`
- 组合索引：`(ticket_id, status)`
- 组合索引：`(ticket_id, created_at)`

## 7. `complaint_reviews` 表设计

对应新增模型：

- `backend/app/models/complaint_review.py`

### 7.1 表职责

记录对执行结果的审查。

### 7.2 必须字段

```python
id: str
ticket_id: str
task_id: str
reviewer_agent_tag: str
status: str
score: int | None
risk_level: str | None
reasons: list[str] | None
suggested_next_agent: str | None
review_payload: dict | None
created_at: datetime
```

### 7.3 外键与索引

- `ticket_id -> complaint_tickets.id`
- `task_id -> complaint_tasks.id`

索引：

- `ix_complaint_reviews_ticket_id`
- `ix_complaint_reviews_task_id`
- `ix_complaint_reviews_status`
- `ix_complaint_reviews_reviewer_agent_tag`

## 8. `complaint_patrol_events` 表设计

对应新增模型：

- `backend/app/models/complaint_patrol_event.py`

### 8.1 表职责

记录巡查发现、自动恢复、升级人工等运维动作。

### 8.2 必须字段

```python
id: str
ticket_id: str
task_id: str | None
event_type: str
status: str
detected_reason: str | None
action_taken: str | None
result_payload: dict | None
created_at: datetime
resolved_at: datetime | None
```

### 8.3 索引

- `ix_complaint_patrol_events_ticket_id`
- `ix_complaint_patrol_events_status`
- `ix_complaint_patrol_events_event_type`

## 9. `agent_score_snapshots` 表设计

对应新增模型：

- `backend/app/models/agent_score_snapshot.py`

### 9.1 表职责

为后续 Phase 2/3 的绩效统计保留表结构。

Phase 1 不要求填充完整数据，但建议先把表建好。

### 9.2 必须字段

```python
id: str
agent_tag: str
window_type: str
window_start: datetime
window_end: datetime
pass_rate: float | None
handoff_rate: float | None
avg_review_score: float | None
avg_resolution_time_ms: int | None
rework_rate: float | None
violation_rate: float | None
payload: dict | None
created_at: datetime
```

## 10. 推荐 SQLAlchemy 模型组织方式

### 10.1 新增文件

必须新增：

- `backend/app/models/complaint_ticket.py`
- `backend/app/models/complaint_task.py`
- `backend/app/models/complaint_review.py`
- `backend/app/models/complaint_patrol_event.py`
- `backend/app/models/agent_score_snapshot.py`

### 10.2 修改 `models/__init__.py`

把新模型导出，确保 Alembic 和 ORM 能发现。

## 11. Alembic 迁移顺序

迁移顺序必须固定为：

### 11.1 第一步：给 `conversations` 增字段

新增：

- `current_ticket_id`
- `conversation_mode`
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
- `secondary_issues`
- `ticket_snapshot`

### 11.2 第二步：创建 `complaint_tickets`

### 11.3 第三步：创建 `complaint_tasks`

### 11.4 第四步：创建 `complaint_reviews`

### 11.5 第五步：创建 `complaint_patrol_events`

### 11.6 第六步：创建 `agent_score_snapshots`

### 11.7 第七步：补索引

先建表后补索引，方便排查迁移错误。

## 12. 数据回填策略

Phase 1 不需要复杂历史数据修复，但必须做以下回填：

### 12.1 回填 `conversation_mode`

规则：

- `handoff_state = "ai"` -> `conversation_mode = "ai"`
- `handoff_state = "pending"` -> `conversation_mode = "pending"`
- `handoff_state = "human"` -> `conversation_mode = "human"`
- 其他异常值 -> `conversation_mode = "ai"`

### 12.2 回填 `unresolved_turns`

统一初始化为 `0`。

### 12.3 其他新字段

统一初始化为：

- `null`
- 或业务默认值

不对历史 conversation 强行创建 ticket。

原因：

- 历史消息未必能可靠映射问题单
- Phase 1 优先保证新链路正确

## 13. 并发与一致性规则

### 13.1 主 ticket 规则

每次创建新主 ticket 时，必须：

1. 先查当前活动 ticket
2. 若存在，先把旧 ticket 的 `is_primary_active` 置为 `False`
3. 再创建新 ticket
4. 再回写 `Conversation.current_ticket_id`

### 13.2 版本号规则

`complaint_tickets.version` 每次更新必须 `+1`。

用途：

- 避免并发更新互相覆盖
- 为后续乐观锁扩展预留

## 14. 与现有前端的字段映射

前端第一阶段需要直接消费以下字段：

### 14.1 会话列表页

- `conversation.id`
- `conversation.current_ticket_id`
- `conversation.complaint_status`
- `conversation.primary_issue_tag`
- `conversation.current_agent_tag`
- `conversation.priority_level`
- `conversation.risk_level`
- `conversation.review_status`
- `conversation.review_score`
- `conversation.block_reason`

### 14.2 详情页

- `ticket.status`
- `ticket.primary_issue_tag`
- `ticket.secondary_issues`
- `ticket.slot_data`
- `ticket.handoff_reason`
- `task.agent_tag`
- `review.score`
- `review.reasons`

## 15. 推荐 migration 文件命名

建议迁移命名为：

`xxxxxx_add_complaint_ticket_task_review_patrol_tables.py`

不要拆成太多碎 migration。Phase 1 先做一版完整迁移，减少状态不一致。

## 16. 完成判定

这份数据库设计落地完成的标准是：

1. 新模型已写入 `backend/app/models/`
2. Alembic 迁移可执行
3. `Conversation` 已能指向当前主 ticket
4. 新 ticket/task/review 表可正常增删查改
5. 同一会话多轮消息场景下，数据库层可以稳定表达“当前主活动问题单是哪一个”

未达到这五条，不能进入下一步业务编排实现。
