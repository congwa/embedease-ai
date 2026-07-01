# Phase 1 测试与验收计划

本文档的业务职责，是为“AI 虚拟人客诉系统” Phase 1 提供统一测试标准和验收口径。它不讨论实现方案，而是明确：哪些测试必须写、哪些场景必须覆盖、什么状态才算 Phase 1 真正完成。

本文件直接服务于以下文档：

- [phase1-execution-playbook.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-execution-playbook.md)
- [spec-phase1-database-and-alembic-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-database-and-alembic-plan.md)
- [spec-phase1-backend-orchestrator-and-service-flow.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-backend-orchestrator-and-service-flow.md)
- [spec-phase1-support-api-and-frontend-state-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-support-api-and-frontend-state-plan.md)

## 1. 测试目标

Phase 1 的测试目标只有一个：

证明系统已经从“消息驱动聊天”升级成“单会话单主问题单驱动的客诉处理系统”，并且这个主链路在关键异常场景下不会失控。

必须验证的核心事实：

1. 同一问题多轮沟通不会炸出多个主 ticket
2. 新问题出现时系统能正确识别归并、挂次要问题或拆单
3. planner / executor / reviewer 主链路真实生效
4. review 拦截真实生效，低质量内容不会直接出给用户
5. handoff 已纳入 ticket 状态机
6. support API 和前端工作台能正确看到 ticket 状态

## 2. 测试分层

Phase 1 的测试必须分四层，不允许只写集成测试，也不允许只写单元测试。

### 2.1 模型与 repository 层测试

目标：

- 验证数据库结构、状态枚举、索引依赖、基础查询逻辑

必须覆盖：

- `Conversation.current_ticket_id` 更新
- 活动 ticket 查询
- ticket/task/review 关联查询
- 状态字段持久化

### 2.2 service 层测试

目标：

- 验证领域服务逻辑是对的，不依赖 HTTP 或前端

必须覆盖：

- `TicketMergeService`
- `TicketService`
- `TaskService`
- `ReviewService`
- `ComplaintHandoffService`

### 2.3 router / API 层测试

目标：

- 验证 API 返回结构和状态同步正确

必须覆盖：

- `/api/v1/chat`
- `/api/v1/support/handoff/{conversation_id}`
- `/api/v1/support/conversations`

### 2.4 集成链路测试

目标：

- 验证从用户发消息到 ticket/review/handoff 的完整业务链路

必须覆盖：

- 单 ticket 正常处理
- review reject 返工
- handoff pending
- 人工接入

## 3. 必须新增的测试文件

建议新增以下测试文件，文件名和职责固定：

- `backend/tests/models/test_complaint_ticket_model.py`
- `backend/tests/repositories/test_complaint_ticket_repository.py`
- `backend/tests/services/test_ticket_merge_service.py`
- `backend/tests/services/test_ticket_service.py`
- `backend/tests/services/test_review_service.py`
- `backend/tests/services/support/test_complaint_handoff_service.py`
- `backend/tests/routers/test_support_ticket_state_api.py`
- `backend/tests/integration/chat/test_complaint_flow.py`

如果代码落地时模块拆分不同，测试文件名可以微调，但上述职责必须完整覆盖。

## 4. 必测业务场景

以下场景全部必须测。缺一个都不能算 Phase 1 完成。

### 场景 1：首次发起问题创建主 ticket

输入：

- 用户首次发送投诉消息

期望：

- 创建 `Conversation`
- 创建 `ComplaintTicket`
- `Conversation.current_ticket_id` 指向该 ticket
- `ticket.status` 进入 `new -> triaged -> planned`

### 场景 2：同一问题持续发泄，不创建新 ticket

输入：

- 用户连续三轮表达不满、催办、重复追问

期望：

- 系统仍只有一个活动 ticket
- `unresolved_turns` 增加
- 触发 `complaint.ticket.merged`
- 不会新增第二个主 ticket

### 场景 3：补充信息归并到当前 ticket

输入：

- 用户后续补充订单号、截图、时间、渠道

期望：

- 当前 ticket 的 `slot_data` 更新
- 不新建 ticket
- `timeline` 增加补充记录

### 场景 4：旧问题未完结时引入第二问题

输入：

- 用户先投诉物流延迟
- 随后又提出退款诉求

期望：

- 默认不立即创建第二个主 ticket
- 在当前 ticket 上记录 `secondary_issue`
- 触发 `complaint.secondary_issue.detected`

### 场景 5：已解决后出现新问题，创建新 ticket

输入：

- 当前 ticket 已 `resolved` 或 `closed`
- 用户提出新的独立问题

期望：

- 创建新的 ticket
- `Conversation.current_ticket_id` 指向新 ticket

### 场景 6：review 通过后才能外发最终回复

输入：

- executor 正常输出
- reviewer 返回 `passed`

期望：

- `assistant.final` 正常输出
- assistant message 落库
- review 状态为 `passed`

### 场景 7：review 驳回，禁止外发低质量内容

输入：

- executor 输出不完整
- reviewer 返回 `rejected`

期望：

- 不直接外发 assistant 最终内容
- ticket 进入 `rework_required` 或回到 `planned`
- review 记录保存 `reasons`

### 场景 8：连续驳回后升级人工

输入：

- 连续两次 review reject

期望：

- ticket 进入 `handoff_pending`
- conversation 进入 `pending`
- 生成 handoff reason 和 summary

### 场景 9：人工接入后状态同步

输入：

- 客服调用接管 API

期望：

- `handoff_state = human`
- ticket 进入 `handed_off`
- support API 返回接管信息
- WebSocket 推送会话状态更新

### 场景 10：工作台详情返回 ticket 级状态

输入：

- 请求 support 会话详情

期望：

- 响应包含 `current_ticket`
- 包含 `review_summary`
- 包含 `primary_issue_tag`、`current_agent_tag`、`risk_level`

## 5. Ticket Merge 规则专项测试

这是 Phase 1 的最高优先级专项测试。

必须覆盖以下判定：

1. 相同订单、相同目标、相同问题域 -> 必须归并
2. 相同订单、不同情绪表达 -> 必须归并
3. 相同订单、同问题但加入额外次要诉求 -> 主单归并 + 记录 secondary issue
4. 不同订单、不同问题域、不同处理目标 -> 允许拆单
5. 当前 ticket 已关闭，新问题出现 -> 必须新建

## 6. SSE / WebSocket 协议专项测试

必须验证这些事件真实可用：

- `complaint.ticket.created`
- `complaint.ticket.merged`
- `complaint.secondary_issue.detected`
- `complaint.review.rejected`
- `complaint.handoff_requested`
- `server.conversation_state`
- `server.ticket_updated`
- `server.review_updated`

验证要求：

1. 事件 payload 字段完整
2. 前端可识别关键字段
3. 状态变化顺序正确

## 7. 前端验收场景

前端至少要手工或自动验证以下场景：

### 用户侧

1. 首次发起问题后，页面显示“处理中”状态
2. 同一问题继续发泄时，页面提示“继续在当前问题单中处理”
3. 检测到次要问题时，页面提示“系统会一并评估”
4. 转人工时，页面切到“等待人工接入”

### 客服工作台

1. 列表页能看到主 ticket 状态
2. 列表页能看到 risk level 和 review 状态
3. 详情页能看到 handoff reason 和 review reasons
4. 接管后状态立即同步

## 8. Phase 1 验收门槛

Phase 1 只有同时满足以下门槛，才能算完成：

1. 所有关键领域模型已经落库
2. 主链路已经基于 ticket 驱动
3. 同一问题不会生成多个主活动 ticket
4. secondary issue 规则已经落地
5. review gate 已经生效
6. handoff 已纳入 ticket 状态机
7. support API 返回 ticket 级状态
8. 前端能展示 ticket 级状态
9. 关键测试场景全部通过

如果其中任一项未满足，Phase 1 不能进入 Phase 2。

## 9. 建议执行命令

当实现进入代码阶段后，建议至少执行以下验证：

```bash
cd backend && uv run pytest backend/tests/services/test_ticket_merge_service.py
cd backend && uv run pytest backend/tests/routers/test_support_ticket_state_api.py
cd backend && uv run pytest backend/tests/integration/chat/test_complaint_flow.py
cd backend && uv run pytest
```

如果仓库测试目录最终结构不同，可以调整路径，但“专项测试 + 路由测试 + 集成测试 + 全量回归”这四层验证不能省略。

