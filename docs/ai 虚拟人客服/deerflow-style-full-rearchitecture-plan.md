# EmbedeaseAI 全量迁移到 Deer-Flow 式多 Agent 架构方案

本文是新的架构决策文档。结论很明确：`embedease-ai` 不再基于当前“单 FastAPI 后端 + 前端代理聊天流 + 配置式 Supervisor”的架构继续演进，而是整体迁移到与 `deer-flow` 同型的多进程、多 Agent、父子调度体系。

## 0. 本机参考仓库路径

本次重构的直接参考仓库是你本机上的 `deer-flow` 项目，路径固定为：

`/Users/wang/code/github/deer-flow`

后续所有“参考 deer-flow 架构”的说法，默认都是参考这个本地仓库，而不是泛指网络上的任意同名项目。

实现时优先对照以下关键文件：

- `/Users/wang/code/github/deer-flow/backend/langgraph.json`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/tools/builtins/task_tool.py`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/subagents/executor.py`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/subagents/config.py`
- `/Users/wang/code/github/deer-flow/backend/app/gateway/app.py`
- `/Users/wang/code/github/deer-flow/docker/nginx/nginx.conf`
- `/Users/wang/code/github/deer-flow/doc/01_system_overview.md`
- `/Users/wang/code/github/deer-flow/doc/02_thread_state.md`
- `/Users/wang/code/github/deer-flow/doc/06_subagent_system_prompt.md`
- `/Users/wang/code/github/deer-flow/doc/08_task_tool.md`
- `/Users/wang/code/github/deer-flow/doc/15_state_flow_diagram.md`

## 1. 架构决策

目标不是“参考 deer-flow 的一些思路”，而是：

- 进程拓扑模仿 deer-flow
- Agent 运行时模仿 deer-flow
- 父子 Agent 调度方式模仿 deer-flow
- 工具系统与 Skill 注入方式模仿 deer-flow
- 在此之上，再叠加你要的“可拖拽流程图编排器”

这意味着当前项目的很多代码只能保留业务资产，不能保留原有运行方式。

## 2. 为什么当前架构不适合

当前项目的核心问题不是功能不够，而是运行时边界不清：

- `backend/app/main.py` 把聊天运行时、管理 API、调度器、技能、客服、系统配置都塞进同一个 FastAPI 进程。
- `frontend/app/api/v1/chat/route.ts` 用 Next.js 代理 SSE，这只是临时透传，不是 deer-flow 的统一入口设计。
- `docker/nginx/nginx.conf` 目前只是前后端二分发，没有 `LangGraph Server / Gateway API / Frontend` 三层拆分。
- 当前 `Supervisor` 更像“配置化路由”，还不是 deer-flow 那种“Lead Agent + task tool + SubagentExecutor”的运行时。
- 技能系统已存在，但还不是父子 Agent 的一等运行时能力合同。

如果你要完全模仿 deer-flow，就应该接受：现有后端主进程架构基本要拆。

## 3. 目标拓扑

目标拓扑直接对齐 deer-flow：

```text
Nginx
├─ /api/langgraph/*   -> LangGraph Server
├─ /api/models        -> Gateway API
├─ /api/skills        -> Gateway API
├─ /api/flows         -> Gateway API
├─ /api/threads/*     -> Gateway API
├─ /api/handoff/*     -> Gateway API
└─ /*                 -> Frontend
```

### 3.1 LangGraph Server

职责只做三件事：

- 运行 Lead Agent 图
- 维护会话状态与 checkpointer
- 向前端输出 SSE 流

参考 deer-flow，新增 `backend/langgraph.json`，把主图注册为：

- `lead_agent`
- 可选后续增加 `support_agent`

### 3.2 Gateway API

职责只做管理型接口，不直接运行 Agent：

- 技能管理
- FlowDefinition 管理
- AgentTemplate 管理
- 模型配置
- 知识源配置
- 文件上传
- 会话元数据
- 人工接管与客服工作台

现有的 `skills`、`system_config`、`support`、部分 `admin` 和 `quick_setup` 逻辑应迁入 Gateway。

### 3.3 Frontend

前端不再承担聊天代理责任，只调用统一入口。UI 分为两块：

- 用户侧客诉会话界面
- 管理侧编排控制台

## 4. 目标运行时

## 4.1 Lead Agent

Lead Agent 是总编排器，负责：

- 读取用户消息、会话状态、已绑定流程定义
- 判断当前处于哪一个流程节点
- 必要时调用 `task` 工具委派给子 Agent
- 汇总子 Agent 结果
- 决定是否流转到下一个节点或转人工

这部分要尽量对齐 deer-flow 的 `lead_agent` 设计，而不是继续沿用当前简单 Supervisor。

## 4.2 Subagent

Subagent 必须按 deer-flow 的规则重建：

- 每个子 Agent 有独立 `SubagentConfig`
- 有独立系统提示词
- 有独立工具白名单/黑名单
- 不继承完整父会话历史，只接收父下发的任务 prompt
- 不允许递归调用 `task`
- 运行在独立执行器中，结果通过 `ToolMessage` 回流给父 Agent

对于你的客诉场景，第一批内置子 Agent 类型建议是：

- `emotion`
- `faq`
- `case_collect`
- `resolution`
- `handoff`

但实现形态上，它们不应只是 if/else 逻辑，而应是 deer-flow 式可配置 Subagent。

## 4.3 task 工具

必须补齐 deer-flow 的核心机制：

- `task_tool`
- `SubagentExecutor`
- 子 Agent 后台执行与状态注册表
- `task_started / task_running / task_completed / task_failed` SSE 事件
- SubagentLimitMiddleware 或同等硬限制

这部分是从“配置式路由”升级到“真正父子 Agent 系统”的关键。

## 5. 你要的流程图编排器如何接入这套架构

你要的是“像流程图一样拖拽配置整个多 Agent 系统”。这与 deer-flow 不冲突，但它应该是 deer-flow 运行时之上的“设计层”，不是替代运行时。

建议分两层：

### 5.1 设计层：Flow Builder

前端提供可拖拽画布，节点类型包括：

- `StartNode`
- `RouterNode`
- `AgentNode`
- `ConditionNode`
- `CollectFormNode`
- `HandoffNode`
- `EndNode`

运营在画布上配置：

- 当前节点用哪个 Agent 模板
- 该 Agent 绑定哪些 Skill
- 成功条件是什么
- 什么条件转到下个节点
- 什么条件转人工

### 5.2 运行层：Compiler + LangGraph Runtime

画布 JSON 不能直接执行，必须先编译为运行时配置：

- FlowDefinition -> Lead Agent 可识别的节点图
- AgentNode -> SubagentConfig + Skill 绑定
- Edge 条件 -> 路由规则或 Condition 节点规则
- Persona / Policy / Tool Skill -> system prompt 片段 + tool scope + safety policy

也就是说：

- 画布负责“设计”
- Compiler 负责“翻译”
- LangGraph Server 负责“执行”

## 6. Skill 在新架构里的定位

你说得对，子 Agent 的人设、能力边界、可做不可做的上限，都应该由 Skill 驱动，而不是写死在代码里。

建议把 Skill 重新分层：

- `persona skill`
  - 语气、人设、道歉风格、沟通方式
- `policy skill`
  - 赔付上限、升级规则、禁止承诺、敏感词边界
- `tool skill`
  - 能用哪些工具，参数边界是什么
- `workflow skill`
  - 该 Agent 的处理步骤模板
- `knowledge skill`
  - 该 Agent 可以访问哪些 FAQ/SOP/政策知识

最终一个 Agent 不是一段 prompt，而是：

```text
AgentTemplate
+ Persona Skills
+ Policy Skills
+ Tool Skills
+ Workflow Skills
+ Knowledge Scope
```

## 7. 数据模型重建

建议新增以下实体：

- `FlowDefinition`
- `FlowVersion`
- `FlowNode`
- `FlowEdge`
- `AgentTemplate`
- `AgentTemplateSkillBinding`
- `SubagentRuntimeConfig`
- `ConversationFlowState`

现有 `Skill` 和 `AgentSkill` 可以保留，但要升级为更通用的绑定模型。

会话状态建议新增：

- `flow_id`
- `flow_version`
- `current_node_id`
- `current_agent_tag`
- `unresolved_turns`
- `priority_level`
- `handoff_trigger`
- `last_route_reason`
- `resolution_status`

## 8. 仓库目录重组建议

目标目录建议靠近 deer-flow：

```text
backend/
├─ langgraph.json
├─ app/
│  └─ gateway/
│     ├─ app.py
│     ├─ routers/
│     └─ services/
├─ packages/
│  └─ harness/
│     └─ embedease_flow/
│        ├─ agents/
│        │  ├─ lead_agent/
│        │  ├─ subagents/
│        │  ├─ middlewares/
│        │  └─ checkpointer/
│        ├─ tools/
│        ├─ flows/
│        ├─ compiler/
│        └─ runtime/
└─ tests/
```

现有 `backend/app/services/agent/*` 中与业务无关的运行时代码，最终应迁移到 `packages/harness/...`。

## 9. 迁移策略

### Phase 1：分进程

- 拆出 LangGraph Server
- 拆出 Gateway API
- Nginx 改成 deer-flow 式三路分发
- 前端去掉 `/api/v1/chat` 代理模式

### Phase 2：重建 Agent Runtime

- 新建 `lead_agent`
- 新建 `task_tool`
- 新建 `SubagentExecutor`
- 新建 Subagent 配置注册表
- 接入 checkpointer

### Phase 3：迁移业务域

- 删除商品推荐域
- 建立客诉域 Agent 模板
- 建立 FAQ / SOP / 政策 / 转人工知识系统
- 接入客服工作台

### Phase 4：引入 Flow Builder

- 新建 FlowDefinition 数据模型
- 前端画布编辑器
- Flow -> Runtime Compiler
- 节点级 Agent/Skill 配置

### Phase 5：替换旧系统

- 冻结旧 FastAPI 一体化聊天入口
- 迁移旧配置到新 FlowDefinition
- 删除旧商品工具链

## 10. 最终结论

既然你的要求是“完全模仿 deer-flow 架构，而且不怕改造成本”，那正确路线就不是“在现有项目上继续补 Supervisor”，而是：

1. 先把运行时拓扑重建为 deer-flow
2. 再把客诉业务映射到 deer-flow 的 Lead Agent / Subagent / Task Tool 体系
3. 最后把可拖拽流程图做成这套运行时的设计器

一句话说清楚：

`deer-flow` 负责“怎么运行多 Agent”，你的新系统负责“这些 Agent 处理什么客诉问题”，流程图编排器负责“让运营怎样把这些能力拖拽组合起来”。

## 11. 配套细化文档

和本方案配套的状态级技术规格见：

- `docs/deerflow-style-langgraph-state-spec.md`

这份规格已经细化到：

- `LangGraph state` 字段定义
- `runtime.context` 字段定义
- 父子 Agent 的状态透传边界
- `FlowNode` 到状态迁移的映射
- 子 Agent 领域定义与横向扩展规格见 `docs/subagent-domain-and-scaling-spec.md`
