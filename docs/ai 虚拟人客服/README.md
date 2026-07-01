# AI 虚拟人客诉系统总任务计划书

本文档的业务职责，是把 `docs/ai 虚拟人客服` 目录内的所有方案收敛成一份必须逐步完成的总任务计划。它不是阅读指引，也不是可选路线图，而是一份强约束执行清单：写进来的任务都必须做，按顺序完成，直到最终在 `embedease-ai` 中落地一个完整的虚拟人客诉系统。

## 1. 总目标

最终必须完成的结果只有一个：

把 `embedease-ai` 从当前“聊天 + 人工接管 + 基础多 Agent 能力”的系统，改造成一个真正可运行的 `AI 虚拟人客诉系统`。

这个系统最终必须满足以下验收标准：

1. 用户发起问题后，系统会创建问题单，而不是只记录消息。
2. 系统会识别问题标签、风险等级、情绪状态，并进入显式状态机。
3. 系统会由多个虚拟岗位协作处理，而不是一个 Agent 从头做到尾。
4. 系统有审查机制，低质量结果不会直接发给用户。
5. 系统有返工机制，失败处理不会直接中断。
6. 系统有巡查机制，卡住任务能自动发现和恢复。
7. 系统有人工升级链路，AI 不能解决时能稳定转人工。
8. 客服工作台能看到问题状态、责任 Agent、审查结果和接管原因。
9. 调度器能执行巡查、统计、复盘等后台任务。
10. 整个系统能够围绕 Agent、Skill、Flow 持续扩展。

## 2. 执行纪律

后续 AI 或开发者推进本目录内容时，必须遵守以下纪律：

1. 不允许跳步骤。必须按本文档顺序推进。
2. 不允许把“后续再说”留在核心链路中。主链路的关键节点必须一次设计清楚。
3. 不允许再输出新的泛化总方案文档。后续工作应当细化规格、实施清单和代码改造。
4. 不允许把质量控制、返工、巡查只写在 prompt 里，必须落实到状态、数据模型、接口和服务层。
5. 不允许先做外观型能力，例如排行榜、炫酷画布，而跳过 ticket/task/review/patrol 主模型。
6. 不允许脱离当前仓库代码结构重新虚构一套平行系统，必须基于现有 `chat`、`support`、`agent`、`scheduler`、`frontend` 模块演进。

## 3. 主依据文档

本计划书执行时，必须以以下文档为依据：

1. [virtual-customer-complaint-system-full-implementation-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/virtual-customer-complaint-system-full-implementation-plan.md)
   作用：完整实施主线，决定代码结构、状态机、表结构、接口、事件、前后端改造。
2. [phase1-detailed-execution-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-detailed-execution-plan.md)
   作用：Phase 1 执行级施工说明，决定每一步先改什么文件、怎么改、做完如何验证。
3. [phase1-execution-playbook.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-execution-playbook.md)
   作用：Phase 1 施工手册，按数据库、service、orchestrator、接口、前端、测试的顺序拆执行动作。
4. [spec-phase1-database-and-alembic-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-database-and-alembic-plan.md)
   作用：Phase 1 数据库与迁移设计，定义表结构、字段、索引、迁移顺序和兼容策略。
5. [spec-phase1-backend-orchestrator-and-service-flow.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-backend-orchestrator-and-service-flow.md)
   作用：Phase 1 后端主链路规格，定义 chat -> ticket -> planner -> executor -> reviewer -> handoff 的代码执行顺序。
6. [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)
   作用：组织模型主线，决定为什么要有规划者、执行者、审查者、巡查者。
7. [subagent-domain-and-scaling-spec.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/subagent-domain-and-scaling-spec.md)
   作用：决定子 Agent 的问题域拆分、边界和扩容规则。
8. [customer-complaint-multi-agent-revamp-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/customer-complaint-multi-agent-revamp-plan.md)
   作用：保留第一版客诉路由与标签体系背景。

`deerflow-style-full-rearchitecture-plan.md` 和 `deerflow-style-langgraph-state-spec.md` 只作为运行时升级参考，不作为当前第一优先级实施蓝图。

## 4. 必须完成的总任务步骤

以下步骤必须按顺序完成。任何一步未完成，都不能认为虚拟人客诉系统已经完成。

### 第 1 步：统一最终系统定义

必须完成的事项：

1. 明确系统名称统一为“AI 虚拟人客诉系统”。
2. 明确业务对象统一为“问题单驱动”，不再是单聊天驱动。
3. 明确目标场景统一为投诉、催办、规则质疑、售后处理、人工升级，不再是商品推荐。
4. 明确系统中的最小核心对象只有五个：
   - `Conversation`
   - `ComplaintTicket`
   - `ComplaintTask`
   - `ComplaintReview`
   - `ComplaintPatrolEvent`
5. 明确系统中的核心角色只有九个：
   - `front_desk_agent`
   - `service_planner_agent`
   - `emotion_deescalation_agent`
   - `faq_policy_agent`
   - `case_intake_agent`
   - `resolution_execution_agent`
   - `handoff_orchestrator_agent`
   - `quality_reviewer_agent`
   - `operations_patrol_agent`
6. 明确一个硬规则：
   - 一个 `conversation` 默认只允许 `1` 个主活动问题单
   - 用户持续补充、发泄、催办时，默认继续归并到当前问题单
   - 只有系统高置信度判断为“新的独立问题”时，才允许拆出新问题单

完成标准：

- 后续所有设计、文档和代码，都只能围绕这套定义展开。

### 第 2 步：冻结系统状态机

必须完成的事项：

1. 定义会话状态机：
   - `ai`
   - `pending`
   - `human`
   - `closed`
2. 定义问题单状态机：
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
3. 定义任务状态机：
   - `queued`
   - `running`
   - `waiting_review`
   - `done`
   - `failed`
   - `cancelled`
   - `blocked`
4. 定义审查状态机：
   - `pending`
   - `passed`
   - `rejected`
   - `escalated`
5. 定义巡查状态机：
   - `open`
   - `auto_recovered`
   - `escalated`
   - `ignored`
6. 明确所有合法状态流转，不允许代码中出现未定义的跳转。

完成标准：

- 状态机必须可直接映射到后端枚举、数据库字段和前端展示字段。

### 第 2.5 步：冻结问题单归并与拆单规则

必须完成的事项：

1. 明确默认规则：`一个 conversation 同一时刻只允许 1 个主活动问题单`。
2. 明确“主活动问题单”指状态属于以下集合之一的 ticket：
   - `new`
   - `triaged`
   - `planned`
   - `in_progress`
   - `pending_review`
   - `rework_required`
   - `blocked`
   - `handoff_pending`
   - `handed_off`
3. 明确用户在同一问题上继续补充信息、发泄情绪、重复催办、表达不满时，`不得创建新 ticket`，只能追加到当前活动 ticket。
4. 明确只有满足以下条件之一时，才允许创建新 ticket：
   - 当前活动 ticket 已 `resolved` 或 `closed`，用户提出了新的独立问题
   - 用户消息与当前 ticket 的问题域、订单主体、处理目标明显不同，且经过 `front_desk_agent + service_planner_agent` 双重判定为新问题
   - 人工客服或后台运营显式执行“拆单”操作
5. 明确如果用户在旧问题尚未解决时又引入第二个问题，系统默认策略不是立即开第二单，而是：
   - 先将第二问题记录为 `secondary_issue`
   - 挂在当前主 ticket 的扩展字段中
   - 由 planner 判断是继续并单处理，还是触发人工拆单
6. 明确禁止自动因为“用户连续说了很多轮话”而创建多个 ticket。
7. 明确 ticket 创建策略优先级：
   - 优先归并
   - 其次标记 secondary issue
   - 最后才允许拆新单

完成标准：

- 后端在任意时刻都能明确回答“这个会话当前主问题单是哪一个”。
- 前端工作台不会因为用户持续抱怨而出现多个并行主 ticket。
- 数据库不会因为情绪宣泄或重复追问产生大量重复 ticket。

### 第 3 步：冻结角色职责和输入输出合同

必须完成的事项：

1. 为每个 Agent 定义业务职责。
2. 为每个 Agent 定义输入数据。
3. 为每个 Agent 定义输出 schema。
4. 为每个 Agent 定义成功标准。
5. 为每个 Agent 定义边界条件。
6. 为每个 Agent 定义何时交回 planner、何时交人工。

完成标准：

- 每个 Agent 不能只保留 prompt 描述，必须有结构化合同。

### 第 4 步：补齐数据库领域模型

必须完成的事项：

1. 扩展 `Conversation` 表，加入客诉上下文字段。
2. 新增 `ComplaintTicket` 表。
3. 新增 `ComplaintTask` 表。
4. 新增 `ComplaintReview` 表。
5. 新增 `ComplaintPatrolEvent` 表。
6. 新增 `AgentScoreSnapshot` 表。
7. 明确每个表的主键、外键、状态字段、时间字段、JSON 扩展字段。
8. 输出完整 Alembic 迁移设计。

完成标准：

- 后端可以基于数据库直接查询任一会话当前处于什么状态、由谁处理、为什么升级、为什么被驳回、为什么阻塞。

### 第 5 步：改造后端主链路为问题单驱动

必须完成的事项：

1. 修改 [chat.py](/Users/wang/code/my/embedease-ai/backend/app/routers/chat.py)。
2. 在用户消息进入后，先保存消息，再获取或创建 `ComplaintTicket`。
3. 若会话处于人工模式，消息直接进人工链路。
4. 若会话处于 AI 模式，消息必须进入 `ComplaintConversationOrchestrator`。
5. 编排顺序固定为：
   - `front_desk_agent`
   - `service_planner_agent`
   - domain executor
   - `quality_reviewer_agent`
   - `assistant.final` 或 `handoff_pending`
6. 审查未通过时，不允许直接对用户输出最终答案。

完成标准：

- `chat` 主链路必须从“消息驱动回复”升级成“问题单驱动处理”。

### 第 6 步：改造流式编排与事件体系

必须完成的事项：

1. 修改 [chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py)。
2. 保留当前 `assistant.delta`、`tool.start`、`tool.end`、`assistant.final` 机制。
3. 新增 complaint 领域事件：
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
4. 修改 [events.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/events.py) 加入这些事件定义和 payload schema。
5. 保证每个关键状态变化都能通过 SSE 发给前端。

完成标准：

- 前端能通过事件流完整还原“当前问题处理到哪一步了”。

### 第 7 步：改造人工升级链路

必须完成的事项：

1. 修改 [handoff.py](/Users/wang/code/my/embedease-ai/backend/app/services/support/handoff.py)。
2. 不允许再直接 `AI -> HUMAN` 一步切换。
3. 新增 `request_handoff()`，实现 `AI -> PENDING`。
4. 保留 `start_handoff()`，但语义改为 `PENDING -> HUMAN`。
5. 修改 `end_handoff()`，根据结果决定：
   - 回 AI 继续处理
   - 问题已解决
   - 问题关闭
6. 每次升级人工时必须生成：
   - 升级原因
   - 会话摘要
   - 当前已收集槽位
   - 当前风险等级

完成标准：

- 人工接管必须成为客诉闭环的一部分，而不是简单人工聊天开关。

### 第 8 步：补齐 Service / Repository 分层

必须完成的事项：

1. 新增 `backend/app/services/complaint/` 目录。
2. 新增以下服务：
   - `ticket_service.py`
   - `task_service.py`
   - `review_service.py`
   - `handoff_service.py`
   - `patrol_service.py`
   - `score_service.py`
   - `orchestrator.py`
   - `state_machine.py`
3. 新增以下 repository：
   - `complaint_ticket.py`
   - `complaint_task.py`
   - `complaint_review.py`
   - `complaint_patrol_event.py`
   - `agent_score_snapshot.py`
4. 把业务流转逻辑放入 complaint 服务层，不能继续散落在 router 或临时工具中。

完成标准：

- 后端客诉处理逻辑具备独立领域层，而不是粘在聊天服务里。

### 第 9 步：重构 Agent 配置与执行体系

必须完成的事项：

1. 修改 [agent.py](/Users/wang/code/my/embedease-ai/backend/app/models/agent.py)。
2. 修改 [agent.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/agent.py)。
3. 修改 [config.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/config.py)。
4. 修改 [factory.py](/Users/wang/code/my/embedease-ai/backend/app/services/agent/core/factory.py)。
5. 给 Agent 配置补充：
   - `role_tag`
   - `business_domain`
   - `skill_bundle_ids`
   - `knowledge_scope`
   - `review_schema_name`
   - `handoff_rules`
6. 让 Agent 的能力边界通过 Skill 和 role 配置表达，而不是继续只靠 `product/faq/kb/custom`。

完成标准：

- Agent 配置系统能够承载虚拟人岗位，而不是旧商品客服分类。

### 第 10 步：重构知识源与工具系统

必须完成的事项：

1. 下线商品导向工具作为主链路能力。
2. 新增客诉专用工具目录：
   - `faq_search`
   - `policy_search`
   - `case_sop_search`
   - `handoff_create`
3. 为不同 Agent 绑定不同知识范围。
4. 审查 Agent 必须有独立的规则与风险知识视角。
5. 所有执行 Agent 必须有明确工具白名单。

完成标准：

- 工具系统能够支持客诉处理，而不是继续偏商品推荐。

### 第 11 步：改造 Support API 与客服工作台后端接口

必须完成的事项：

1. 修改 [support.py](/Users/wang/code/my/embedease-ai/backend/app/routers/support.py)。
2. 让 `/conversations` 返回 ticket 维度字段，而不只是 handoff 状态。
3. 新增 ticket 查询、指派、解决、重开、升级接口。
4. 修改 [websocket.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/websocket.py)。
5. 扩展 `ConversationStatePayload`，包含：
   - `ticket_status`
   - `primary_issue_tag`
   - `current_agent_tag`
   - `current_node_key`
   - `priority_level`
   - `review_status`
   - `review_score`
   - `block_reason`
6. 新增服务端推送事件：
   - `server.ticket_updated`
   - `server.review_alert`
   - `server.handoff_requested`
   - `server.blocked_alert`

完成标准：

- 客服工作台后端接口必须能完整提供问题单处理信息。

### 第 12 步：改造前端用户侧聊天体验

必须完成的事项：

1. 修改用户聊天页相关状态消费逻辑。
2. 让前端消费新增 complaint SSE 事件。
3. 给用户侧显示：
   - 当前处理阶段
   - 当前问题标签
   - 是否待补充资料
   - 是否已提交人工
   - 当前处理进度
4. 不能让用户只看到“一段 AI 回复”，却不知道当前问题是否真正进入处理流程。

完成标准：

- 用户侧可以感知自己的问题已经被系统正式接单和推进。

### 第 13 步：改造前端客服工作台

必须完成的事项：

1. 修改 [support-store.ts](/Users/wang/code/my/embedease-ai/frontend/stores/support-store.ts)。
2. 增加 ticket 相关状态字段。
3. 修改 [page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/page.tsx)。
4. 修改 [page.tsx](/Users/wang/code/my/embedease-ai/frontend/app/support/[conversationId]/page.tsx)。
5. 在工作台中必须展示：
   - 问题单状态
   - 问题标签
   - 当前责任 Agent
   - 当前处理节点
   - 审查状态与分数
   - 升级原因
   - 阻塞原因
   - 已收集信息
6. 支持按状态、标签、风险等级、阻塞状态筛选问题单。

完成标准：

- 客服工作台必须从“会话消息列表”升级成“问题单处理工作台”。

### 第 14 步：接入 scheduler 巡查能力

必须完成的事项：

1. 基于现有 `scheduler` 框架新增巡查任务。
2. 新增任务：
   - `complaint_patrol_task`
   - `complaint_score_snapshot_task`
   - `complaint_knowledge_gap_task`
   - `complaint_followup_task`
3. 第一阶段至少必须完成 `complaint_patrol_task`。
4. 巡查任务必须扫描：
   - 长时间 `blocked`
   - 长时间 `pending_review`
   - 长时间 `handoff_pending`
   - 返工死循环
5. 巡查任务必须能执行：
   - 自动恢复
   - 自动升级人工
   - 告警记录

完成标准：

- 系统不能因为 AI 执行失败或流程中断而无限挂起。

### 第 15 步：接入绩效与知识运营能力

必须完成的事项：

1. 统计每个 Agent 的首次通过率。
2. 统计平均返工次数。
3. 统计转人工率。
4. 统计审查平均分。
5. 统计处理时长。
6. 汇总高频驳回原因。
7. 汇总高频转人工原因。
8. 汇总知识缺口，反哺 FAQ / policy / SOP。

完成标准：

- 系统必须具备长期优化依据，而不是一次性写完后无法运营。

### 第 16 步：完成端到端验收与上线准备

必须完成的事项：

1. 列出完整测试清单：
   - 状态机测试
   - Router/API 测试
   - Service 层测试
   - Handoff 测试
   - Scheduler 巡查测试
   - 前端状态联动测试
2. 至少覆盖以下关键场景：
   - FAQ 正常解决
   - 情绪安抚后进入信息收集
   - 规则解释后升级处理
   - 审查驳回并返工
   - 连续返工失败自动转人工
   - blocked 会话被巡查恢复
   - 人工接入后完成处理并关闭问题
3. 输出上线检查项：
   - DB 迁移完成
   - SSE 事件兼容
   - WS 事件兼容
   - 前端状态展示正常
   - 支持工作台筛选与接管
   - 巡查任务可执行

完成标准：

- 系统具备上线条件，而不是只有文档和部分代码。

## 5. 当前完成定义

只有当以下条件全部成立时，才能说“虚拟人客诉系统完成”：

1. 核心领域模型已建成。
2. 主状态机已实现并被强校验。
3. AI 客诉主链路已切换为问题单驱动。
4. 审查与返工链路已实现。
5. 转人工链路已实现。
6. 客服工作台已升级为问题单视角。
7. 巡查任务已上线。
8. 绩效统计已可跑通。
9. 关键场景测试已通过。

只要有任一项未完成，都不能把这个项目视为“虚拟人客诉系统已完成”。

## 6. 后续文档输出要求

从本文件开始，后续如果继续在本目录新增文档，只允许补以下内容：

1. `Phase 1` 数据库表结构和 Alembic 迁移设计
2. `Phase 1` 后端模块改造清单
3. `Phase 1` 前端工作台改造清单
4. 状态机精细规格
5. Agent 角色合同规格
6. SSE / WebSocket 协议精细规格
7. 测试与验收清单

不允许再写新的“总愿景文档”。

## 7. 一句话执行命令

后续任何 AI 如果继续推进这个目录，默认执行命令只有一句：

```text
按本 README 的顺序，把 embedease-ai 逐步改造成一个以问题单为核心、具备多角色协作、审查返工、巡查自愈和人工升级能力的 AI 虚拟人客诉系统，直到满足全部完成定义为止。
```
