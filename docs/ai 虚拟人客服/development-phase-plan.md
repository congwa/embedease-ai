# AI 虚拟人客诉系统阶段开发计划

本文档的业务职责，是把 `docs/ai 虚拟人客服` 目录中已经沉淀的规划，整理成一份从“现在开始如何开发”的阶段性执行计划。它重点回答三个问题：

1. 第一阶段先开发什么
2. 第二阶段再开发什么
3. 每个阶段分别参考哪些文档

这份文档不是重复总规划，而是把当前已经写好的文档变成实际开发顺序。

## 1. 开发总原则

开发必须按阶段推进，不能跳阶段。

顺序固定为：

1. 先做 Phase 1：客诉主链路落地
2. 再做 Phase 2：巡查、调度、自愈
3. 最后做 Phase 3：绩效、运营、流程化扩展

原因很明确：

- 没有主 ticket、task、review 主链路，后面的巡查和绩效没有对象可管
- 没有 ticket 驱动的 support API 和前端状态，后面的后台能力都是空的
- 没有稳定状态机，不能先上复杂流程编排和高级运营能力

## 2. 第一阶段开发计划

### 2.1 第一阶段目标

第一阶段的唯一目标是：

把当前系统从“聊天 + 人工接管”升级成“单会话单主问题单驱动的客诉主链路系统”。

第一阶段完成后，系统必须具备：

- 用户消息进入后会创建或归并到主问题单
- 系统能识别问题标签、风险、情绪
- 系统能通过 planner 选择执行岗位
- executor 输出后必须经过 reviewer
- 审查失败会返工或转人工
- support 工作台能看到 ticket 状态

### 2.2 第一阶段开发顺序

第一阶段必须按下面顺序开发：

1. 数据库与模型层
2. repository 与 service 层
3. orchestrator 主链路
4. chat / chat_stream 改造
5. handoff 链路改造
6. support API 改造
7. 前端用户侧状态展示
8. 前端客服工作台改造
9. 测试与验收

### 2.3 第一阶段具体开发内容

#### 1. 数据库与模型层

要开发的内容：

- 扩展 `Conversation`
- 新增 `ComplaintTicket`
- 新增 `ComplaintTask`
- 新增 `ComplaintReview`
- 新增 `ComplaintPatrolEvent`
- 新增 `AgentScoreSnapshot`
- 设计 Alembic 迁移

重点实现：

- `current_ticket_id`
- ticket 状态机字段
- 单会话单主活动 ticket 约束
- `secondary_issue` 扩展字段

参考文档：

- [README.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/README.md)
- [virtual-customer-complaint-system-full-implementation-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/virtual-customer-complaint-system-full-implementation-plan.md)
- [phase1-execution-playbook.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-execution-playbook.md)
- [spec-phase1-database-and-alembic-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-database-and-alembic-plan.md)

#### 2. repository 与 service 层

要开发的内容：

- `ComplaintTicketRepository`
- `ComplaintTaskRepository`
- `ComplaintReviewRepository`
- `TicketMergeService`
- `TicketService`
- `TaskService`
- `ReviewService`

重点实现：

- 获取主活动 ticket
- merge / split 规则
- `secondary_issue` 记录
- review reject / rework 逻辑

参考文档：

- [phase1-execution-playbook.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-execution-playbook.md)
- [spec-phase1-backend-orchestrator-and-service-flow.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-backend-orchestrator-and-service-flow.md)
- [spec-phase1-test-and-acceptance-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-test-and-acceptance-plan.md)

#### 3. orchestrator 主链路

要开发的内容：

- `ComplaintConversationOrchestrator`
- `ComplaintPlannerService`
- `ComplaintExecutorService`
- `ComplaintHandoffService`

重点实现：

- user message -> ticket merge/create
- triage -> plan -> execute -> review
- review reject -> rework
- review escalate -> handoff pending

参考文档：

- [virtual-customer-complaint-system-full-implementation-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/virtual-customer-complaint-system-full-implementation-plan.md)
- [phase1-detailed-execution-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-detailed-execution-plan.md)
- [phase1-execution-playbook.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-execution-playbook.md)
- [spec-phase1-backend-orchestrator-and-service-flow.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-backend-orchestrator-and-service-flow.md)

#### 4. chat / chat_stream 改造

要开发的内容：

- 改造 `backend/app/routers/chat.py`
- 改造 `backend/app/services/chat_stream.py`
- 增加 complaint SSE 事件

重点实现：

- AI 模式走 complaint orchestrator
- assistant.final 前必须经过 review gate
- 同步 `ticket.created / ticket.merged / review.rejected / handoff_requested`

参考文档：

- [spec-phase1-backend-orchestrator-and-service-flow.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-backend-orchestrator-and-service-flow.md)
- [spec-phase1-support-api-and-frontend-state-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-support-api-and-frontend-state-plan.md)

#### 5. handoff 链路改造

要开发的内容：

- 改造 `backend/app/services/support/handoff.py`
- 改造 `backend/app/routers/support.py`

重点实现：

- `AI -> PENDING -> HUMAN`
- handoff reason / summary
- ticket 状态同步到 support 工作台

参考文档：

- [virtual-customer-complaint-system-full-implementation-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/virtual-customer-complaint-system-full-implementation-plan.md)
- [spec-phase1-backend-orchestrator-and-service-flow.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-backend-orchestrator-and-service-flow.md)
- [spec-phase1-support-api-and-frontend-state-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-support-api-and-frontend-state-plan.md)

#### 6. support API 改造

要开发的内容：

- 扩展 support schema
- support 列表返回 ticket 快照
- support 详情返回 review / handoff / risk / primary_issue_tag

参考文档：

- [spec-phase1-support-api-and-frontend-state-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-support-api-and-frontend-state-plan.md)

#### 7. 用户侧前端状态展示

要开发的内容：

- 用户聊天页展示当前 ticket 状态
- 展示“继续归并处理”“发现次要问题”“等待人工接入”等提示

参考文档：

- [spec-phase1-support-api-and-frontend-state-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-support-api-and-frontend-state-plan.md)

#### 8. 客服工作台改造

要开发的内容：

- 工作台列表展示 ticket 状态
- 详情页展示 current ticket / review summary / handoff summary
- support-store 增加 ticket 状态字段

参考文档：

- [spec-phase1-support-api-and-frontend-state-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-support-api-and-frontend-state-plan.md)

#### 9. 测试与验收

要开发的内容：

- ticket merge 专项测试
- review reject 测试
- handoff pending 测试
- support API 测试
- chat complaint flow 集成测试

参考文档：

- [spec-phase1-test-and-acceptance-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-test-and-acceptance-plan.md)

### 2.4 第一阶段完成标准

满足以下全部条件，第一阶段才算完成：

1. 同一会话默认只有一个主活动 ticket
2. 用户持续抱怨/补充不会产生多个重复 ticket
3. 主链路已经变成 ticket -> task -> review 驱动
4. review gate 已生效
5. handoff 已纳入状态机
6. support 工作台能看到 ticket 级状态
7. 测试全部通过

## 3. 第二阶段开发计划

### 3.1 第二阶段目标

第二阶段的目标是：

让系统从“能处理”升级成“不会轻易卡死”。

也就是补齐：

- 巡查
- 调度
- 自愈
- 阻塞恢复

### 3.2 第二阶段开发顺序

第二阶段必须按下面顺序开发：

1. 巡查事件模型落地
2. scheduler 接入 complaint 巡查任务
3. 阻塞识别规则落地
4. 自动恢复和升级逻辑
5. 工作台巡查视图
6. 巡查场景测试

### 3.3 第二阶段具体开发内容

#### 1. 巡查事件模型落地

要开发的内容：

- 完善 `ComplaintPatrolEvent`
- 明确 `open / auto_recovered / escalated / ignored`

参考文档：

- [virtual-customer-complaint-system-full-implementation-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/virtual-customer-complaint-system-full-implementation-plan.md)
- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)

#### 2. scheduler 接入 complaint 巡查任务

要开发的内容：

- 在 `backend/app/scheduler/*` 中新增 complaint 巡查 task
- 扫描 `blocked / pending_review 超时 / handoff_pending 超时`

参考文档：

- [phase1-execution-playbook.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-execution-playbook.md)
- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)

#### 3. 阻塞识别规则落地

要开发的内容：

- 定义卡住 ticket 的判定条件
- 定义超时 review 的判定条件
- 定义 handoff 长时间未接入的判定条件

参考文档：

- [virtual-customer-complaint-system-full-implementation-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/virtual-customer-complaint-system-full-implementation-plan.md)

#### 4. 自动恢复和升级逻辑

要开发的内容：

- `operations_patrol_agent`
- 自动重试一次
- 自动转人工
- 记录 patrol result

参考文档：

- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)
- [subagent-domain-and-scaling-spec.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/subagent-domain-and-scaling-spec.md)

#### 5. 工作台巡查视图

要开发的内容：

- 增加巡查事件列表
- 增加阻塞会话视图
- 增加恢复结果视图

参考文档：

- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)

#### 6. 巡查场景测试

要开发的内容：

- blocked 自动恢复测试
- handoff_pending 超时升级测试
- review 超时巡查测试

参考文档：

- [spec-phase1-test-and-acceptance-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-test-and-acceptance-plan.md)

### 3.4 第二阶段完成标准

满足以下全部条件，第二阶段才算完成：

1. scheduler 能定时扫描 complaint ticket
2. blocked ticket 能被识别
3. 异常 ticket 能自动恢复或升级
4. 工作台能看到 patrol 结果
5. 巡查测试通过

## 4. 第三阶段开发计划

### 4.1 第三阶段目标

第三阶段的目标是：

让系统从“能稳定运行”升级成“可持续优化和运营扩展”。

重点包括：

- 绩效统计
- 知识缺口分析
- Flow / Skill / Agent 效果对比
- 后续流程化配置能力

### 4.2 第三阶段开发顺序

第三阶段必须按下面顺序开发：

1. 绩效快照模型与统计任务
2. review / handoff 数据运营分析
3. knowledge gap 分析
4. Flow / Skill / Agent 对比报表
5. 后续流程编排准备

### 4.3 第三阶段具体开发内容

#### 1. 绩效快照模型与统计任务

要开发的内容：

- 完善 `AgentScoreSnapshot`
- 定时统计 review pass rate / reject rate / handoff rate

参考文档：

- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)

#### 2. review / handoff 运营分析

要开发的内容：

- 驳回原因排行
- 转人工原因排行
- 高风险问题分布

参考文档：

- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)

#### 3. knowledge gap 分析

要开发的内容：

- 高频失败问题聚合
- FAQ 缺口
- SOP 缺口

参考文档：

- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)

#### 4. Flow / Skill / Agent 对比报表

要开发的内容：

- 不同 Agent 效果对比
- 不同 Skill bundle 效果对比
- 不同 Flow 版本效果对比

参考文档：

- [openmoss-style-virtual-customer-service-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/openmoss-style-virtual-customer-service-plan.md)
- [subagent-domain-and-scaling-spec.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/subagent-domain-and-scaling-spec.md)

#### 5. 后续流程编排准备

要开发的内容：

- 整理 FlowDefinition / FlowVersion / FlowNode / FlowEdge 需求
- 为未来可视化编排做数据结构准备

参考文档：

- [deerflow-style-full-rearchitecture-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/deerflow-style-full-rearchitecture-plan.md)
- [deerflow-style-langgraph-state-spec.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/deerflow-style-langgraph-state-spec.md)

### 4.4 第三阶段完成标准

满足以下全部条件，第三阶段才算完成：

1. 可以统计各类 Agent 绩效指标
2. 可以分析 review / handoff 原因
3. 可以识别知识缺口
4. 可以为后续 Flow / Skill / Agent 配置化扩展做准备

## 5. 建议开发节奏

从现在开始，建议按下面节奏推进：

1. 先把第一阶段完整做完，不要并行开发第二阶段
2. 第一阶段完成并验收后，再做第二阶段巡查调度
3. 第二阶段稳定后，再进入第三阶段运营与扩展

最重要的原则是：

`先把 ticket 主链路做对，再做系统自动化和运营化。`

