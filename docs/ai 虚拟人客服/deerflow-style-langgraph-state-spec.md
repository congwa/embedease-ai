# Deer-Flow 式 LangGraph State 详细设计

本文是 `embedease-ai` 全量迁移到 deer-flow 式多 Agent 架构后的状态设计规格。它回答四个核心问题：

1. `LangGraph state` 到底定义哪些字段
2. 哪些字段持久化，哪些字段只在单轮运行时存在
3. 父 Agent 如何把状态传给子 Agent
4. 拖拽流程图中的节点，最终如何映射到 LangGraph 的状态流转

这份文档比总方案更底层，目的是让后续实现时可以直接按字段和边界落代码。

## 0. 本机 deer-flow 参考路径

本规格直接参考你本机上的 deer-flow 仓库：

`/Users/wang/code/github/deer-flow`

本文件涉及的状态设计，主要对照：

- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/subagents/executor.py`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/tools/builtins/task_tool.py`
- `/Users/wang/code/github/deer-flow/doc/02_thread_state.md`
- `/Users/wang/code/github/deer-flow/doc/15_state_flow_diagram.md`

## 1. 设计原则

完全参考 deer-flow 后，状态设计必须满足以下原则：

- `messages` 永远是主状态，所有可被模型感知的历史最终都要归并到这里。
- 业务状态不能混在 prompt 文本里临时拼接后丢失，必须有结构化字段。
- 父子 Agent 不能共享完整消息历史，只能共享必要的运行态和业务快照。
- 累加型字段必须使用 reducer，避免工具和中间件互相覆盖。
- 区分 `persistent state` 和 `ephemeral state`，不要把临时数据长期写进 checkpoint。

## 2. 顶层状态模型

建议新系统的顶层状态命名为 `ComplaintThreadState`，继承 `AgentState`。

```python
from typing import Annotated, NotRequired, TypedDict
from langchain.agents import AgentState


class SandboxState(TypedDict):
    sandbox_id: NotRequired[str | None]


class ThreadDataState(TypedDict):
    workspace_path: NotRequired[str | None]
    uploads_path: NotRequired[str | None]
    outputs_path: NotRequired[str | None]


class ConversationState(TypedDict):
    conversation_id: str
    user_id: str
    channel: NotRequired[str | None]
    language: NotRequired[str | None]
    title: NotRequired[str | None]


class FlowRuntimeState(TypedDict):
    flow_id: str
    flow_version: str
    current_node_id: str
    current_node_type: str
    route_path: list[str]
    current_agent_tag: NotRequired[str | None]


class ComplaintBusinessState(TypedDict):
    primary_issue_tag: NotRequired[str | None]
    secondary_issue_tags: NotRequired[list[str] | None]
    sentiment: NotRequired[str | None]
    severity: NotRequired[str | None]
    unresolved_turns: NotRequired[int | None]
    resolution_status: NotRequired[str | None]
    requires_handoff: NotRequired[bool | None]
    handoff_reason: NotRequired[str | None]
    last_router_reason: NotRequired[str | None]
    collected_slots: NotRequired[dict | None]


class SkillRuntimeState(TypedDict):
    active_skill_ids: NotRequired[list[str] | None]
    active_persona_skill_ids: NotRequired[list[str] | None]
    active_policy_skill_ids: NotRequired[list[str] | None]
    active_tool_skill_ids: NotRequired[list[str] | None]
    active_workflow_skill_ids: NotRequired[list[str] | None]


class ViewedImageData(TypedDict):
    base64: str
    mime_type: str


class ComplaintThreadState(AgentState):
    sandbox: NotRequired[SandboxState | None]
    thread_data: NotRequired[ThreadDataState | None]
    conversation: NotRequired[ConversationState | None]
    flow: NotRequired[FlowRuntimeState | None]
    complaint: NotRequired[ComplaintBusinessState | None]
    skills: NotRequired[SkillRuntimeState | None]
    artifacts: Annotated[list[str], merge_artifacts]
    todos: NotRequired[list | None]
    uploaded_files: NotRequired[list[dict] | None]
    viewed_images: Annotated[dict[str, ViewedImageData], merge_viewed_images]
    debug_trace: Annotated[list[dict], merge_trace_logs]
```

这里的核心变化是：在 deer-flow 的 `ThreadState` 基础上，新增了三块业务层字段：

- `conversation`
- `flow`
- `complaint`

这是为了让系统不只是“能运行 Agent”，而是能稳定表达客诉业务状态。

## 3. 字段分类

### 3.1 持久化字段

这些字段必须进入 checkpointer，因为它们跨轮有效：

- `messages`
- `sandbox`
- `thread_data`
- `conversation`
- `flow`
- `complaint`
- `skills`
- `artifacts`
- `todos`

### 3.2 临时字段

这些字段只服务某一轮模型调用，不能长期残留：

- `uploaded_files`
- `viewed_images`
- 某些 `debug_trace` 片段

其中 `viewed_images` 应延续 deer-flow 做法：在 `after_model` 阶段清空。

## 4. reducer 设计

至少需要三类 reducer：

### 4.1 artifacts reducer

和 deer-flow 一样，用于文件产物累积：

```python
def merge_artifacts(existing: list[str] | None, new: list[str] | None) -> list[str]:
    if existing is None:
        return new or []
    if new is None:
        return existing
    return list(dict.fromkeys(existing + new))
```

### 4.2 viewed_images reducer

保持 deer-flow 语义：空字典代表清空。

### 4.3 debug_trace reducer

建议新增：

```python
def merge_trace_logs(existing: list[dict] | None, new: list[dict] | None) -> list[dict]:
    if existing is None:
        return new or []
    if new is None:
        return existing
    return existing + new
```

它主要给后台审计与调试使用，记录：

- 路由决策
- 节点跳转
- skill 激活
- handoff 触发原因

## 5. runtime.context 定义

在 deer-flow 里，很多不适合进入 `state` 的值，会放在 `runtime.context` 或 `config.metadata`。新系统建议统一如下：

```python
runtime.context = {
  "thread_id": "...",
  "conversation_id": "...",
  "user_id": "...",
  "channel": "web",
  "request_id": "...",
  "trace_id": "...",
  "flow_id": "...",
  "flow_version": "...",
  "current_node_id": "...",
}

runtime.config["metadata"] = {
  "model_name": "...",
  "subagent_enabled": True,
  "agent_template_id": "...",
  "agent_tag": "...",
}
```

### 为什么这些字段不直接进 state

- `request_id`：只在本次请求日志链路里有意义
- `trace_id`：属于 tracing，不属于业务状态
- `model_name`：是运行时配置，不是对话事实
- `subagent_enabled`：是运行时开关，不是用户会话状态

## 6. 父 Agent 的输入状态

Lead Agent 每轮启动时，状态至少应具备：

```python
{
  "messages": [...历史消息..., HumanMessage(content=user_input)],
  "conversation": {
    "conversation_id": "...",
    "user_id": "...",
    "channel": "web"
  },
  "flow": {
    "flow_id": "complaint-default",
    "flow_version": "v3",
    "current_node_id": "router_1",
    "current_node_type": "router",
    "route_path": ["start_1", "router_1"]
  },
  "complaint": {
    "primary_issue_tag": "emotion",
    "sentiment": "negative",
    "severity": "medium",
    "unresolved_turns": 2,
    "requires_handoff": False,
    "collected_slots": {
      "order_id": None,
      "screenshot": False
    }
  },
  "skills": {
    "active_skill_ids": ["persona_router", "policy_handoff_rule"]
  }
}
```

Lead Agent 的责任不是直接回答所有内容，而是：

- 看当前 node
- 决定是否调用 `task`
- 决定是否更新 `complaint` 业务字段
- 决定是否推进 `flow.current_node_id`

## 7. 子 Agent 的输入状态

这里必须严格对齐 deer-flow 的思想：子 Agent 不能继承父的完整 `messages`。

建议子 Agent 初始状态只保留：

```python
{
  "messages": [HumanMessage(content=delegated_prompt)],
  "sandbox": state["sandbox"],
  "thread_data": state["thread_data"],
  "conversation": minimal_conversation_snapshot,
  "complaint": minimal_business_snapshot,
  "skills": subagent_skill_snapshot
}
```

### 7.1 minimal_conversation_snapshot

```python
{
  "conversation_id": "...",
  "user_id": "...",
  "channel": "web"
}
```

### 7.2 minimal_business_snapshot

```python
{
  "primary_issue_tag": "faq",
  "sentiment": "negative",
  "severity": "medium",
  "unresolved_turns": 2,
  "collected_slots": {
    "order_id": "123456"
  }
}
```

### 7.3 为什么不传完整 messages

因为父子 Agent 的职责不同：

- 父 Agent 负责全局编排
- 子 Agent 负责单一标签任务

如果把完整历史透传给子 Agent，问题会变成：

- 子 Agent 被父的上下文污染
- prompt 变长
- 工具执行上下文失焦
- 不同子 Agent 难以保持边界

因此子 Agent 只能拿到“父浓缩后的任务 prompt + 必要业务快照”。

## 8. 父 -> 子 状态传递规则

建议固定以下规则：

### 8.1 允许透传

- `sandbox`
- `thread_data`
- `conversation.conversation_id`
- `conversation.user_id`
- `complaint` 中和当前子任务直接相关的字段
- 子 Agent 绑定的 skill 列表

### 8.2 禁止透传

- 父完整 `messages`
- 父所有中间推理
- 与本子任务无关的其它节点上下文
- 父的所有历史 tool_calls

### 8.3 回传方式

子 Agent 不直接改父的完整 state，而是返回结构化结果，父再决定如何合并：

```python
class SubagentTaskResult(TypedDict):
    task_id: str
    agent_tag: str
    status: str
    summary: str
    business_updates: dict
    suggested_next_node: str | None
    should_handoff: bool
    handoff_reason: str | None
```

父 Agent 收到后再做：

- `messages += ToolMessage(...)`
- `complaint.update(business_updates)`
- `flow.current_node_id = suggested_next_node` 或保持不变

## 9. 流程图节点如何映射到状态

这是你要的拖拽流程图最关键的一层。

### 9.1 StartNode

只负责初始化：

- `flow.current_node_id`
- `flow.route_path`
- `complaint.unresolved_turns = 0`

### 9.2 RouterNode

输入：

- 用户本轮消息
- 最近业务状态
- 当前 flow 节点信息

输出更新：

```python
{
  "complaint": {
    "primary_issue_tag": "emotion",
    "last_router_reason": "检测到强烈不满和催促"
  },
  "flow": {
    "current_node_id": "agent_emotion_1",
    "current_node_type": "agent",
    "route_path": ["start_1", "router_1", "agent_emotion_1"]
  }
}
```

### 9.3 AgentNode

输入：

- 当前业务状态
- 当前节点绑定的 agent template
- skill bindings

执行：

- 调用 `task_tool`
- 创建对应子 Agent

输出更新：

- `messages` 新增 ToolMessage
- `complaint` 根据子 Agent 结果更新
- `flow.current_node_id` 跳到下一个 condition 或 end

### 9.4 ConditionNode

不一定调用模型，优先做规则判断。

例如：

```python
if state["complaint"]["requires_handoff"]:
    goto = "handoff_1"
elif state["complaint"]["resolution_status"] == "resolved":
    goto = "end_1"
else:
    goto = "agent_resolution_1"
```

ConditionNode 最好先规则化，避免什么都靠模型判断。

### 9.5 HandoffNode

输入：

- 当前 complaint 状态
- 子 Agent 回传摘要

输出更新：

```python
{
  "complaint": {
    "requires_handoff": True,
    "handoff_reason": "用户连续三轮未解决且明确要求人工"
  },
  "flow": {
    "current_node_id": "handoff_1",
    "current_node_type": "handoff"
  }
}
```

同时调用 Gateway 的人工接管接口或服务。

## 10. checkpointer 边界

建议保持 deer-flow 思路：

- LangGraph Server 独占对 `ComplaintThreadState` 的 checkpoint 读写
- Gateway 不直接写 LangGraph checkpoint
- Gateway 只写业务数据库

换句话说：

- `state` 属于 Agent runtime
- 业务表属于管理系统

二者通过 `conversation_id / thread_id` 关联，但不要混成一套存储。

## 11. 事件流与状态的关系

建议把 SSE 事件分成两层：

### 11.1 runtime 事件

- `llm.call.start`
- `llm.call.end`
- `task.started`
- `task.running`
- `task.completed`
- `task.failed`

### 11.2 business 事件

- `flow.node.enter`
- `flow.node.leave`
- `agent.routed`
- `skill.activated`
- `support.handoff_requested`
- `support.handoff_started`

这些 business 事件本质都是 `state` 的某个关键字段发生变化后的投影，不应该成为新的状态源。

## 12. 实现顺序建议

如果按状态优先落地，顺序应该是：

1. 先定义 `ComplaintThreadState`
2. 再定义 `runtime.context` 契约
3. 再实现 `lead_agent` 和 `task_tool`
4. 再实现 `SubagentTaskResult` 结构化回传
5. 再实现 `FlowNode -> state transition` 编译器
6. 最后接前端流程图画布

## 13. 对当前项目的直接结论

当前项目的 `ChatContext` 和一体化 `AgentService` 设计太薄，无法支撑 deer-flow 级别的父子 Agent 运行时。你后续重构时，不应该继续在原有上下文对象上补字段，而应该直接切到新的 `ComplaintThreadState + runtime.context + checkpoint + task_tool` 体系。

这是这次重构最该先定死的一层。没有这层，后面的多 Agent、拖拽编排、Skill 绑定都会飘。

配套的子 Agent 业务域定义和扩容规则见：

- `docs/subagent-domain-and-scaling-spec.md`
