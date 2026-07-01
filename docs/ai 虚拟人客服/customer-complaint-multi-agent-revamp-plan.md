# 客诉多 Agent 系统改造方案

本文用于指导 `embedease-ai` 从“商品咨询/推荐系统”改造成“客户问题解决与客诉沟通系统”。目标不是继续卖货，而是围绕用户问题分类、情绪安抚、FAQ 解答、问题推进、升级转人工，形成一套完整的客诉处理闭环。

## 1. 从 deer-flow 借鉴什么，不照搬什么

我阅读了 `deer-flow` 的父子 Agent 调度设计，核心结论有四点：

1. 父 Agent 只负责编排，不负责细节执行。
2. 子 Agent 必须有独立 prompt、独立工具范围、独立超时，不共享完整历史。
3. 子 Agent 不能无限递归再调子 Agent，必须有硬限制。
4. 调度规则不能只靠 prompt，还要有代码层兜底。

但本项目当前场景不是“复杂研究并行拆任务”，而是“根据客诉标签把会话交给最合适的处理角色”。因此不建议第一阶段直接照搬 `deer-flow` 的 `task_tool + SubagentExecutor + 线程池` 体系。更合适的路线是：

- 先复用当前已有的 `Supervisor + SubAgent + Handoff` 骨架。
- 把 Supervisor 改造成“标签路由器”。
- 把子 Agent 改造成“问题标签处理器”。
- 等第一版稳定后，再考虑引入 deer-flow 式的独立子会话执行器。

## 2. 目标业务形态

系统的新定位：

- 用户进来不是咨询商品，而是反馈问题、投诉、催办、质疑、要求解释或要求人工。
- 父 Agent 先识别“当前问题标签”。
- 标签决定交给哪个子 Agent。
- 子 Agent 负责该标签下的处理目标，而不是泛化聊天。
- 多轮未解决、强负面情绪、明确要求人工、涉及赔付/法律/舆情风险时，直接转人工。

建议第一版固定 5 类标签 Agent：

- `emotion_agent`：情绪安抚、道歉、缓和冲突，不承诺未确认事项。
- `faq_agent`：处理标准 FAQ、流程说明、规则解释。
- `case_collect_agent`：收集订单号、时间、渠道、截图、故障现象等关键信息。
- `resolution_agent`：根据知识库/SOP 给出处理步骤、时效、下一步动作。
- `handoff_agent`：触发人工介入，输出转人工原因和摘要。

后续可扩展：

- `refund_agent`
- `logistics_agent`
- `technical_issue_agent`
- `vip_retention_agent`

## 3. 调度机制设计

### 3.1 父 Agent 职责

父 Agent 不再扮演“商品总助手”，而是 `Complaint Supervisor`：

- 读取当前用户消息 + 最近会话摘要 + 当前已路由标签 + 未解决轮次。
- 输出一个主标签 `primary_tag`。
- 判断是否需要直接转人工。
- 生成路由理由，便于后台审计。

建议第一版坚持“单主标签路由”，不要一开始就做多 Agent 并行。客诉沟通比研究任务更强调口径统一，过早并行会让回复风格分裂。

### 3.2 子 Agent 职责

每个子 Agent 绑定一个标签和处理目标：

- `emotion_agent` 的成功标准：用户情绪被接住，进入可继续沟通状态。
- `faq_agent` 的成功标准：用标准口径回答清楚，不乱承诺。
- `case_collect_agent` 的成功标准：把后续处理所需信息采集完整。
- `resolution_agent` 的成功标准：给出明确下一步、时效、责任边界。
- `handoff_agent` 的成功标准：生成可供人工接手的摘要并切换状态。

借鉴 deer-flow，这些子 Agent 应具备：

- 独立系统提示词。
- 独立工具白名单。
- 禁止子 Agent 再次路由其它子 Agent。
- 输出标准化结果，避免父 Agent 难以判断是否已解决。

### 3.3 转人工规则

建议把“转人工”从文案动作升级为显式状态机规则。满足任一条件直接触发：

- 用户明确要求人工。
- 同一问题连续 2 到 3 轮仍未解决。
- 负向情绪强烈，如辱骂、威胁投诉、曝光、法律追责。
- 涉及赔付、退款审批、特殊补偿、敏感舆情。
- 系统判断答案置信度低，或知识库缺失。

## 4. 对当前项目的具体改造

### 4.1 后端

保留并重用：

- `backend/app/services/agent/core/factory.py`
- `backend/app/services/agent/core/intent.py`
- `backend/app/services/support/handoff.py`
- `backend/app/routers/support.py`
- `backend/app/services/system_config.py` 里的 Supervisor 全局配置能力

重点改造：

1. 把 `AgentTypeEnum` 从 `product/faq/kb/custom` 改成客诉领域标签或可扩展 tag。
2. 把 `quick_setup` 里的商品推荐配置器全部替换成客诉模板配置器。
3. 删除或冻结 `backend/app/services/agent/tools/product/*` 与 `retrieval/product.py`。
4. 把知识工具重构为：
   - `faq_search`
   - `policy_search`
   - `case_sop_search`
   - `handoff_create`
5. 给会话表新增客诉字段：
   - `current_tag`
   - `complaint_status`
   - `unresolved_turns`
   - `last_router_reason`
   - `priority_level`
   - `handoff_trigger`
6. 在流式事件中新增：
   - `agent.routed`
   - `agent.reclassified`
   - `support.handoff_requested`

推荐新增一个明确的“路由决策对象”，避免只返回字符串：

```json
{
  "primary_tag": "emotion",
  "should_handoff": false,
  "reason": "用户当前核心诉求是表达不满，需先安抚再收集信息",
  "confidence": 0.86
}
```

### 4.2 前端

需要从“商品咨询 UI”切到“客诉处理 UI”：

- 去掉商品卡片、商品推荐、购买入口、商品对比入口。
- 将聊天时间线改成“问题处理进度时间线”。
- 增加当前标签展示，如“情绪安抚中 / FAQ 解答中 / 已转人工”。
- 增加“转人工状态提示”和“人工已接入”提示。
- 后台把 `Supervisor 配置` 页改成 `标签路由配置` 页。
- 客服工作台保留，但要强化“待接管原因”“会话摘要”“已采集信息”。

### 4.3 数据与知识层

原来的商品知识库要下线，替换为客诉知识源：

- FAQ 标准问答
- 售后政策/服务规则
- 处理 SOP
- 赔付与升级规则
- 历史工单总结

建议把知识按“标签可见性”管理，例如：

- `emotion_agent` 不看复杂政策，只看安抚话术边界。
- `faq_agent` 看 FAQ 和政策规则。
- `resolution_agent` 看 SOP 与处理时效。
- `handoff_agent` 只负责摘要与接管信息整理。

## 5. 推荐实施路径

### Phase 1：去商品化

- 下线商品工具、商品文案、商品路由、商品前端组件。
- 保留现有 Supervisor、Support、Conversation 基础设施。
- 先把系统定位改对。

### Phase 2：建立标签路由 MVP

- 上线父 Agent 标签路由。
- 建立 `emotion/faq/case_collect/resolution/handoff` 五类子 Agent。
- 增加未解决轮次和转人工阈值。
- 前端展示当前处理标签和状态。

### Phase 3：标准化输出与审计

- 给父 Agent 路由输出加结构化 schema。
- 给子 Agent 输出加“是否完成本标签目标”的字段。
- 后台记录每次路由原因、置信度、转人工触发条件。

### Phase 4：再评估是否引入 deer-flow 式执行器

当出现以下需求时，再考虑引入 deer-flow 那套独立子会话机制：

- 一个客诉需要多个子 Agent 串并行协作。
- 需要子 Agent 独立事件流和更强的隔离执行。
- 需要对子 Agent 工具权限、超时、上下文做更细粒度控制。

## 6. 我的建议

最佳路线不是“把 deer-flow 直接搬进来”，而是“借它的设计原则，升级你现有的 Supervisor 骨架”。因为你当前项目已经具备：

- 子 Agent 配置
- Supervisor 全局配置
- 意图路由
- 人工 handoff
- 客服工作台

真正缺的是“业务模型重定义”。这次改造的关键不是多加几个 Agent，而是把全系统从“推荐商品”切换成“解决客户问题”。一旦业务对象、标签体系、升级规则、知识源和前端状态都改对，后续再把调度内核升级成 deer-flow 风格，会顺很多。

## 7. 你要的目标架构：可拖拽编排 + Agent/Skill 可配置

如果你的目标是“像流程图一样拖拽配置父子 Agent、子 Skill、条件分支和转人工”，那系统架构不应该再以“单个 Agent 配置页”为中心，而要升级为“编排画布 + 配置面板”的双层模型。

### 7.1 核心思想

父 Agent 不再只是一个 prompt，而是一个可视化流程编排器中的“路由节点”。子 Agent 也不是死写在代码里的枚举，而是画布上的节点实例。Skill 不只是附属说明，而是 Agent 的能力合同：

- `persona skills`：定义人设、语气、边界、禁忌承诺。
- `tool skills`：定义能调用哪些工具。
- `policy skills`：定义业务规则、权限上限、赔付边界、升级条件。
- `workflow skills`：定义当前 Agent 收到什么输入后应走什么处理步骤。

也就是说：

- Agent 决定“谁来处理”
- Skill 决定“它能怎么处理”
- Flow 决定“处理完之后去哪儿”

### 7.2 推荐的数据模型

建议新增三个核心实体，而不是只靠现有 `Agent + Skill` 勉强承载：

1. `FlowDefinition`
   - 表示一张流程图
   - 包含版本、发布状态、适用渠道、默认入口节点

2. `FlowNode`
   - 节点类型：`router / agent / condition / handoff / end / form_collect`
   - 保存画布坐标、节点配置、引用的 agent 模板或 skill 组合

3. `FlowEdge`
   - 表示节点之间的连线
   - 保存条件表达式，如 `intent=emotion`、`unresolved_turns>=3`、`user_requests_human=true`

现有 `Skill` 继续保留，但要进一步细分使用方式：

- Skill 是可复用能力模块
- Node/Agent 只是引用 Skill 的组合

### 7.3 Agent 配置模型

建议把 Agent 从“一个大 prompt”拆成以下配置：

- `base_profile`
  - 名称、角色、职责描述
- `skill_bindings`
  - 绑定哪些 skill，优先级如何
- `tool_scope`
  - 允许哪些工具，禁止哪些工具
- `output_schema`
  - 输出必须包含哪些业务字段
- `handoff_policy`
  - 何时必须升级

这样子 Agent 的“人设”不是写死在代码里，而是由多个 Skill 叠加出来：

- 安抚型 persona skill
- 售后政策 skill
- 技术排障 skill
- 转人工边界 skill

### 7.4 画布节点设计

推荐第一版支持以下节点：

- `StartNode`
  - 会话入口
- `IntentRouterNode`
  - 识别标签，决定下一跳
- `AgentNode`
  - 执行某个子 Agent
- `ConditionNode`
  - 判断是否已解决、是否高风险、是否转人工
- `CollectInfoNode`
  - 结构化收集订单号、截图、联系方式
- `HandoffNode`
  - 生成摘要并切换到人工
- `EndNode`
  - 结束或等待用户下一轮输入

一个典型流程会是：

`Start -> IntentRouter -> EmotionAgent -> Condition(是否仍激烈) -> Handoff`

或：

`Start -> IntentRouter -> FAQAgent -> Condition(是否解决) -> End / ResolutionAgent / Handoff`

### 7.5 前端交互形态

前端建议采用标准节点编辑器，而不是继续堆表单页。推荐组件形态：

- 左侧：节点与 Skill 素材栏
- 中间：流程画布
- 右侧：当前节点配置面板
- 底部或侧边：运行预览、路由日志、版本发布

你现在项目里已有技能管理页，但还没有流程画布。第一版可以引入 React Flow 一类节点画布库，实现：

- 拖拽创建节点
- 连线配置条件
- 点击节点编辑绑定 Agent/Skill
- 保存为 JSON 流程定义

### 7.6 后端运行时如何执行

运行时不要直接“看前端怎么画就怎么跑”，而是把画布 JSON 编译成一份可执行流程：

- 入口载入 `FlowDefinition`
- 根据当前节点类型执行对应逻辑
- `RouterNode` 产出标签
- `AgentNode` 加载绑定的 skill 列表，合成 system prompt 和工具白名单
- `ConditionNode` 根据结构化状态决定下一条 edge
- `HandoffNode` 调用现有 `HandoffService`

也就是说，运行时本质是一个“状态机 + Agent 执行器”，而不是前端直接控制流程。

### 7.7 为什么这比“纯 Supervisor 配置”更适合你

因为你的目标已经不是“让 AI 选一个最合适的子 Agent”这么简单，而是：

- 让运营能通过拖拽编排业务流程
- 让每个 Agent 的能力边界可配置
- 让 skill 成为能力和人设的最小复用单元
- 让升级、转人工、收集信息、解决问题都成为流程图上的显式节点

这时候最合理的产品形态就是：

`流程图编排层 > Agent 层 > Skill 层 > Tool/Knowledge 层`

而不是反过来。

## 8. 实施建议调整

如果要走你现在说的这个方向，Phase 2 之后建议拆成两条并行建设线：

### 8.1 编排平台线

- 新增 FlowDefinition / FlowNode / FlowEdge 数据模型
- 新增流程发布、版本管理、灰度切换
- 新增画布编辑器页面

### 8.2 Agent 能力平台线

- Skill 按 persona/tool/policy/workflow 重新建模
- Agent 改为“模板 + Skill 绑定”
- 运行时支持动态合成 prompt、工具边界、升级规则

最终你要的不是“几个客服 Agent”，而是一套“可编排的客诉处理操作系统”。
