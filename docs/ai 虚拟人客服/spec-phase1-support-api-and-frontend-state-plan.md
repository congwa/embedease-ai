# Phase 1 Support API 与前端状态方案

本文档的业务职责，是把 Phase 1 的接口层和前端状态层固定下来，确保“AI 虚拟人客诉系统”在用户端和客服工作台上都能基于同一套 ticket 驱动状态工作。它重点回答三个问题：

1. 后端 `support API` 和 `chat SSE` 必须返回什么
2. WebSocket 推送必须同步什么 ticket 状态
3. 前端 store 和页面必须保存和展示什么字段

本文件是以下文档的直接落地补充：

- [virtual-customer-complaint-system-full-implementation-plan.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/virtual-customer-complaint-system-full-implementation-plan.md)
- [phase1-execution-playbook.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/phase1-execution-playbook.md)
- [spec-phase1-backend-orchestrator-and-service-flow.md](/Users/wang/code/my/embedease-ai/docs/ai%20虚拟人客服/spec-phase1-backend-orchestrator-and-service-flow.md)

## 1. Phase 1 接口层目标

Phase 1 完成后，前端必须能够在不额外拼凑业务语义的情况下，直接从后端拿到这些状态：

- 当前 conversation 是否在 `ai / pending / human`
- 当前主活动 `ticket` 是哪一张
- 当前主 ticket 的 `status`
- 当前问题的 `primary_issue_tag`
- 当前责任岗位 `current_agent_tag`
- 是否处于 `pending_review`
- 最近一次 review 是否 `passed / rejected / escalated`
- 是否已经 `handoff_pending`
- 为什么转人工
- 用户当前这轮消息是归并进旧问题，还是触发了 secondary issue

如果前端仍然只能拿到 `handoff_state + messages`，则 Phase 1 不算完成。

## 2. Support API 必须扩展的响应结构

当前 [support.py](/Users/wang/code/my/embedease-ai/backend/app/routers/support.py) 和 [support.py schema](/Users/wang/code/my/embedease-ai/backend/app/schemas/support.py) 只返回 `handoff_state` 和基础会话信息。Phase 1 必须升级为 ticket 驱动返回。

### 2.1 必须新增的核心响应对象

建议新增这些 schema：

- `TicketSummarySchema`
- `ReviewSummarySchema`
- `ConversationTicketStateSchema`
- `ConversationSupportDetailSchema`

### 2.2 `TicketSummarySchema` 必须包含的字段

```json
{
  "id": "ticket_xxx",
  "status": "in_progress",
  "primary_issue_tag": "emotion",
  "secondary_issue_tags": ["policy"],
  "current_agent_tag": "emotion_deescalation_agent",
  "priority_level": "high",
  "risk_level": "medium",
  "unresolved_turns": 3,
  "handoff_required": false,
  "handoff_reason": "",
  "merged_from_latest_message": true,
  "secondary_issue_detected": false,
  "updated_at": "2026-03-30T18:30:00+08:00"
}
```

说明：

- `merged_from_latest_message` 用于告诉前端“用户刚才这轮话是并入当前单，不是新开单”
- `secondary_issue_detected` 用于告诉客服“用户开始引入次要问题了”

### 2.3 `ReviewSummarySchema` 必须包含的字段

```json
{
  "status": "rejected",
  "score": 71,
  "risk_level": "medium",
  "reasons": [
    "缺少订单号，无法推进",
    "当前回复承诺边界过大"
  ],
  "suggested_next_agent": "case_intake_agent",
  "created_at": "2026-03-30T18:30:20+08:00"
}
```

### 2.4 `ConversationStateResponse` 必须升级

当前 `ConversationStateResponse` 只返回：

- `conversation_id`
- `handoff_state`
- `handoff_operator`
- `handoff_reason`

Phase 1 必须升级为至少返回：

- `conversation_id`
- `conversation_mode`
- `handoff_state`
- `handoff_operator`
- `handoff_reason`
- `current_ticket`
- `review_summary`
- `user_online`
- `peer_last_online_at`

### 2.5 `ConversationListItem` 必须升级

客服工作台列表项必须新增：

- `current_ticket_id`
- `ticket_status`
- `primary_issue_tag`
- `current_agent_tag`
- `risk_level`
- `review_status`
- `review_score`
- `handoff_reason`
- `secondary_issue_detected`

这样列表页才能直接做：

- “高风险”筛选
- “等待人工”排序
- “审查驳回”标记
- “次要问题插入”提醒

## 3. Chat SSE 必须发出的 ticket 事件

当前 [chat_stream.py](/Users/wang/code/my/embedease-ai/backend/app/services/chat_stream.py) 主要发 token 流和工具事件。Phase 1 必须把 ticket 生命周期同步给前端。

### 3.1 必须新增的 SSE 事件类型

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

### 3.2 关键事件 payload 要求

#### `complaint.ticket.created`

```json
{
  "ticket": {
    "id": "ticket_xxx",
    "status": "new",
    "primary_issue_tag": "emotion",
    "current_agent_tag": "front_desk_agent"
  }
}
```

#### `complaint.ticket.merged`

```json
{
  "ticket_id": "ticket_xxx",
  "merged_message_id": "msg_xxx",
  "reason": "用户继续围绕同一问题发泄和催办",
  "unresolved_turns": 4
}
```

#### `complaint.secondary_issue.detected`

```json
{
  "ticket_id": "ticket_xxx",
  "secondary_issue": {
    "issue_tag": "refund_policy",
    "reason": "用户在催办物流问题时引入退款诉求"
  }
}
```

#### `complaint.review.rejected`

```json
{
  "ticket_id": "ticket_xxx",
  "review": {
    "status": "rejected",
    "score": 68,
    "reasons": ["缺少关键槽位"],
    "suggested_next_agent": "case_intake_agent"
  }
}
```

#### `complaint.handoff_requested`

```json
{
  "ticket_id": "ticket_xxx",
  "conversation_mode": "pending",
  "handoff_reason": "用户明确要求人工且连续两次 review 不通过",
  "handoff_summary": "已收集订单号和问题现象，用户情绪强烈"
}
```

## 4. WebSocket 协议必须补的 ticket 状态推送

当前 [websocket.py](/Users/wang/code/my/embedease-ai/backend/app/schemas/websocket.py) 主要围绕消息和 handoff 推送。Phase 1 必须让客服端在不刷新页面的情况下感知 ticket 状态变化。

### 4.1 `SERVER_CONVERSATION_STATE` 必须升级

当前 `ConversationStatePayload` 必须扩展为：

```json
{
  "conversation_id": "conv_xxx",
  "handoff_state": "pending",
  "operator": null,
  "user_online": true,
  "peer_last_online_at": "2026-03-30T18:31:00+08:00",
  "unread_count": 2,
  "current_ticket": {
    "id": "ticket_xxx",
    "status": "handoff_pending",
    "primary_issue_tag": "emotion",
    "current_agent_tag": "handoff_orchestrator_agent",
    "risk_level": "high",
    "unresolved_turns": 5,
    "secondary_issue_detected": true
  },
  "review_summary": {
    "status": "escalated",
    "score": 55,
    "risk_level": "high"
  }
}
```

### 4.2 建议新增的 Server Action

第一阶段建议新增：

- `server.ticket_updated`
- `server.review_updated`

用途：

- 避免所有 ticket 变化都只能靠 `server.conversation_state` 全量刷新
- 提高工作台局部刷新效率

### 4.3 `server.ticket_updated` payload

```json
{
  "ticket": {
    "id": "ticket_xxx",
    "status": "pending_review",
    "primary_issue_tag": "faq_policy",
    "current_agent_tag": "quality_reviewer_agent",
    "risk_level": "medium",
    "secondary_issue_detected": false
  }
}
```

### 4.4 `server.review_updated` payload

```json
{
  "ticket_id": "ticket_xxx",
  "review": {
    "status": "passed",
    "score": 92,
    "risk_level": "low"
  }
}
```

## 5. 前端 store 必须如何升级

当前 [support-store.ts](/Users/wang/code/my/embedease-ai/frontend/stores/support-store.ts) 只有 `handoffState / operator / userOnline / messages`。这不够支撑 ticket 驱动工作台。

### 5.1 `SupportState` 必须新增字段

必须新增：

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

### 5.2 必须新增 actions

- `updateTicketState(ticket)`
- `updateReviewState(review)`
- `markTicketMerged(payload)`
- `markSecondaryIssue(payload)`

### 5.3 更新策略

固定规则：

1. 初次进入页面先走 REST 拉全量状态
2. 后续由 WebSocket / SSE 做增量更新
3. 如果同一 ticket 收到 `merged` 事件，不新建本地 ticket，只更新摘要和轮次
4. 如果收到 `secondary_issue.detected`，只更新警告标志，不自动切主 ticket

## 6. 用户聊天页必须怎么展示

用户侧页面必须把“问题处理过程”暴露出来，但不能做成客服后台。

### 6.1 必须展示的状态

- 当前问题状态：如“处理中”“待人工接入”“人工处理中”
- 当前处理岗位：如“情绪安抚中”“处理中”“规则解释中”
- 最近状态变化提示：如“已归并到当前问题单继续处理”

### 6.2 必须展示的特殊提示

#### 同单归并提示

当收到 `complaint.ticket.merged` 时，前端应展示轻提示：

- “已继续在当前问题单中补充处理”

#### 次要问题提示

当收到 `complaint.secondary_issue.detected` 时，前端应展示：

- “检测到您提出了新的相关诉求，系统会在当前问题处理中一并评估”

不能直接告诉用户“已新建第二个工单”，因为第一阶段默认不自动拆单。

#### 人工接入提示

当收到 `complaint.handoff_requested` 时，前端必须从“AI 回复流”切换到“等待人工接入状态展示”。

## 7. 客服工作台必须怎么展示

客服工作台必须围绕“当前主 ticket”展开。

### 7.1 会话列表必须展示

- 标题
- 用户在线状态
- handoff 状态
- ticket 状态
- primary issue tag
- 当前责任 agent
- risk level
- review 状态
- 最新消息摘要
- 是否出现 `secondary issue`

### 7.2 单会话详情页必须展示

- 消息时间线
- 当前主 ticket 卡片
- 当前状态流程节点
- 最近一次 review 结果
- handoff 原因
- handoff 摘要
- secondary issue 区域

### 7.3 单会话详情页必须支持的动作

- 接管会话
- 结束接管
- 标记问题已解决
- 标记需人工拆单
- 查看 review 驳回原因

### 7.4 Phase 1 禁止的前端行为

- 不要在工作台里默认展示多个并行活动 ticket
- 不要自动因为 secondary issue 就切换当前主 ticket
- 不要只根据 handoff_state 来判断整个业务状态

## 8. 后端接口与前端页面映射

### 8.1 REST 接口映射

- `GET /api/v1/support/handoff/{conversation_id}`
  - 作用：拉当前会话 ticket 快照和 handoff 状态
- `GET /api/v1/support/conversations`
  - 作用：拉客服工作台列表
- `POST /api/v1/support/handoff/{conversation_id}`
  - 作用：客服接入
- `POST /api/v1/support/handoff/{conversation_id}/close`
  - 作用：客服结束接入

### 8.2 WebSocket 映射

- `server.conversation_state`
  - 更新全局会话状态
- `server.ticket_updated`
  - 更新当前主 ticket 状态
- `server.review_updated`
  - 更新 review 区域
- `server.message`
  - 更新消息时间线

### 8.3 SSE 映射

- 用户侧聊天页消费 complaint 事件
- 工作台主要用 REST + WS
- 不建议工作台直接复用聊天 SSE 作为唯一状态来源

## 9. 完成判定

只有满足以下条件，这份接口与前端状态方案才算落实：

1. `support API` 返回 ticket 级字段
2. WebSocket 能推送 ticket/review 状态变化
3. 用户聊天页能区分“当前问题继续处理中”与“等待人工接入”
4. 客服工作台能围绕主活动 ticket 展示状态
5. 同一问题多轮发泄时，前端不会误以为系统自动新开多个 ticket
6. 出现 secondary issue 时，前端能展示提醒但不乱切主问题

