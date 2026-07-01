# 子 Agent 领域设计与横向扩展规格

本文专门回答你刚刚追问的三个问题：

1. 子 Agent 本身代表什么问题
2. 如何控制它只解决这类问题
3. 后续如何横向扩充多个子 Agent，而不让系统失控

这份文档默认前提是：系统最终采用 deer-flow 式 `Lead Agent + task_tool + SubagentExecutor + LangGraph state` 架构。

## 0. 本机 deer-flow 参考路径

本文件中的子 Agent 运行方式，默认参考你电脑上的 deer-flow 仓库：

`/Users/wang/code/github/deer-flow`

对照重点：

- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/subagents/config.py`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/subagents/executor.py`
- `/Users/wang/code/github/deer-flow/backend/packages/harness/deerflow/tools/builtins/task_tool.py`
- `/Users/wang/code/github/deer-flow/doc/06_subagent_system_prompt.md`
- `/Users/wang/code/github/deer-flow/doc/08_task_tool.md`
- `/Users/wang/code/github/deer-flow/doc/14_design_tradeoffs.md`

## 1. 子 Agent 在业务上到底是什么

子 Agent 不是“一个模型实例”，也不是“一个 prompt 模板”，而是一个**问题域处理单元**。

它必须同时满足三个条件，才配叫一个独立子 Agent：

1. 它对应一类稳定、可命名的问题域
2. 它有清晰的处理目标和成功标准
3. 它有明确边界，超出边界必须交回父 Agent 或转人工

所以，子 Agent 的本质不是“技能集合”，而是：

`问题域 + 处理目标 + 边界规则 + 技能组合 + 输出合同`

## 2. 子 Agent 不应该怎么拆

错误拆法：

- 按“功能按钮”拆：查询 Agent、安抚 Agent、回复 Agent、总结 Agent
- 按“模型能力”拆：强推理 Agent、强检索 Agent
- 按“技术实现”拆：FAQ Agent、RAG Agent、Tool Agent

这些拆法都太偏技术，不是业务单元。最终会导致：

- 路由不稳定
- 多个 Agent 争抢同一类问题
- 运营无法理解每个 Agent 的职责

## 3. 子 Agent 应该怎么拆

正确拆法是按“客诉问题域”来拆。也就是：用户遇到的是什么问题，就让哪一类 Agent 负责。

建议拆成三层：

### 3.1 L1：问题大类

这是路由入口层，用于父 Agent 粗分流：

- 情绪类
- 规则解释类
- 信息补齐类
- 处理推进类
- 人工升级类

### 3.2 L2：问题域子类

这是实际子 Agent 的主要层级。建议第一版在这一层建 Agent：

- `emotion_deescalation_agent`
- `faq_policy_agent`
- `case_intake_agent`
- `resolution_execution_agent`
- `handoff_orchestrator_agent`

### 3.3 L3：细分专科 Agent

这是后续扩容层，只有当某个问题域明显变复杂时才新增：

- `refund_policy_agent`
- `logistics_delay_agent`
- `product_quality_issue_agent`
- `installation_troubleshooting_agent`
- `billing_dispute_agent`
- `vip_retention_agent`

原则是：

- 先做 L2
- L2 出现明显负载和复杂度，再拆 L3
- 不要一开始把所有子类都建成独立 Agent

## 4. 子 Agent 的标准定义结构

每个子 Agent 必须有一份结构化定义，而不是只存一段 prompt。建议定义为：

```python
class SubagentDomainSpec(TypedDict):
    agent_tag: str
    display_name: str
    problem_domain: str
    business_goal: str
    in_scope: list[str]
    out_of_scope: list[str]
    success_criteria: list[str]
    escalation_rules: list[str]
    required_slots: list[str]
    output_schema_name: str
    skill_bundle_ids: list[str]
    tool_scope_id: str
```

### 各字段含义

- `agent_tag`
  - 路由唯一标识，例如 `emotion_deescalation`
- `problem_domain`
  - 该 Agent 专门负责哪一类问题
- `business_goal`
  - 它解决问题的核心目标，不是技术目标
- `in_scope`
  - 它能处理的场景列表
- `out_of_scope`
  - 它不能碰的场景
- `success_criteria`
  - 什么叫“这类问题已处理完成”
- `escalation_rules`
  - 哪些条件下必须升级
- `required_slots`
  - 解决问题前必须收集的信息
- `skill_bundle_ids`
  - 运行时应绑定哪些 skill

## 5. 五个基础子 Agent 的详细定义

## 5.1 `emotion_deescalation_agent`

### 它代表什么问题

代表“用户当前最主要的问题不是信息缺失，而是情绪失控或强烈不满”。

典型场景：

- 用户持续抱怨
- 语气激烈
- 明显不信任系统
- 反复表达失望、愤怒、催促

### 它的目标

不是立刻解决全部业务问题，而是先把会话拉回可继续沟通的状态。

### 它的成功标准

- 用户情绪明显缓和
- 用户愿意继续提供信息
- 没有进一步升级冲突

### 它不能做什么

- 不能承诺退款金额
- 不能代表公司做最终裁定
- 不能编造处理结果
- 不能无限安抚而不推进问题

### 它应绑定的 Skill

- `persona.empathy_deescalation`
- `policy.no_false_commitment`
- `workflow.acknowledge_then_guide`
- `tool.slot_collection_basic`

### 何时退出

- 情绪稳定，转给 `case_intake_agent` 或 `faq_policy_agent`
- 用户强烈要求人工，转 `handoff_orchestrator_agent`

## 5.2 `faq_policy_agent`

### 它代表什么问题

代表“用户主要是在问规则、政策、流程、时效、是否可以、为什么这样”。

### 它的目标

用标准口径解释清楚规则，减少误解和争议。

### 它的成功标准

- 给出清晰、准确、可追溯的规则解释
- 不超权限承诺
- 用户能理解下一步该做什么

### 它不能做什么

- 不能直接判定个案赔付
- 不能绕过政策边界
- 不能替代人工审核

### 应绑定 Skill

- `persona.professional_policy_explainer`
- `knowledge.faq_policy_scope`
- `policy.compensation_boundary`
- `workflow.policy_answer_then_next_step`

### 何时退出

- 规则解释完成 -> `end`
- 发现是具体个案且信息不足 -> `case_intake_agent`
- 用户不接受规则且升级 -> `emotion_deescalation_agent` 或 `handoff`

## 5.3 `case_intake_agent`

### 它代表什么问题

代表“当前主要阻塞点是信息不完整，系统无法判断下一步”。

### 它的目标

把关键信息采齐，让后续 Agent 可以真正处理问题。

### 应采集的信息

- 订单号
- 时间
- 渠道
- 问题现象
- 已尝试步骤
- 截图/视频
- 联系方式

### 成功标准

- 必填槽位补齐
- 可以进入 `resolution_execution_agent`

### 不能做什么

- 不负责长篇规则解释
- 不负责复杂安抚
- 不负责最终结论

### 应绑定 Skill

- `persona.patient_case_collector`
- `workflow.slot_filling`
- `policy.minimum_required_info`
- `tool.collect_form_fields`

## 5.4 `resolution_execution_agent`

### 它代表什么问题

代表“信息已经足够，现在要根据 SOP、知识库和规则推动解决”。

### 它的目标

输出明确处理动作、时效和下一步。

### 成功标准

- 明确告诉用户现在怎么处理
- 给出时效或等待条件
- 明确责任边界

### 不能做什么

- 不能越权审批赔付
- 不能口头承诺最终处理结果
- 不能忽略高风险升级信号

### 应绑定 Skill

- `persona.resolution_manager`
- `knowledge.sop_resolution_scope`
- `policy.approval_boundary`
- `workflow.resolve_or_escalate`

## 5.5 `handoff_orchestrator_agent`

### 它代表什么问题

代表“这个问题已经不适合继续由 AI 处理，需要交由人工接管”。

### 它的目标

不是继续跟用户讲道理，而是高质量完成交接。

### 成功标准

- 生成结构化交接摘要
- 标明触发转人工的原因
- 标明已收集信息和未完成事项
- 切换会话状态成功

### 应绑定 Skill

- `persona.calm_handoff_operator`
- `workflow.handoff_summary_builder`
- `policy.handoff_trigger_policy`
- `tool.create_handoff_record`

## 6. 如何控制子 Agent 只解决自己的问题

这一层不能只靠 prompt，必须四层同时控制。

## 6.1 第一层：路由控制

父 Agent 只把合适的问题派给合适子 Agent。

也就是说，控制首先发生在“谁收到任务”这一层。

## 6.2 第二层：任务 prompt 控制

父 Agent 派发给子 Agent 的 prompt 不能太泛，必须显式包含：

- 当前问题域是什么
- 这次任务目标是什么
- 哪些事情可以做
- 哪些事情禁止做
- 本次任务完成后应返回什么结构

示例：

```text
你是 emotion_deescalation_agent。

本次任务只处理：用户当前强烈不满情绪。
本次目标：先安抚情绪，并把对话推进到可继续收集信息的状态。

禁止：
1. 承诺退款或赔付结果
2. 编造后台处理进度
3. 长篇解释政策

如果用户明确要求人工，返回 should_handoff=true。
```

## 6.3 第三层：Skill 控制

Skill 不是“锦上添花”，而是边界控制器。

建议把 Skill 分成四类约束：

- `persona skills`
  - 控制语气、人设、表达风格
- `policy skills`
  - 控制什么能说、什么不能承诺
- `workflow skills`
  - 控制处理步骤
- `tool skills`
  - 控制调用哪些工具

### 例子

`emotion_deescalation_agent` 即使想“帮用户直接解决退款”，只要：

- 没有绑定赔付权限 policy skill
- 没有绑定赔付工具 tool skill
- output schema 不允许输出审批结论

它就会被系统三层夹死。

## 6.4 第四层：输出合同控制

每个子 Agent 不能自由发挥输出，而必须返回结构化结果。

例如：

```json
{
  "agent_tag": "emotion_deescalation",
  "status": "completed",
  "summary": "已完成安抚，用户愿意提供订单号",
  "business_updates": {
    "sentiment": "stabilized",
    "resolution_status": "need_info"
  },
  "should_handoff": false,
  "next_recommended_agent": "case_intake_agent"
}
```

父 Agent 只认这个合同，不认随意自由文本。

## 7. Skill 如何组成一个子 Agent

建议给每个子 Agent 用“能力包”而不是散乱 skill。

```text
Subagent Bundle
├─ Persona Bundle
├─ Policy Bundle
├─ Workflow Bundle
├─ Tool Bundle
└─ Knowledge Scope
```

例如：

### `faq_policy_agent` bundle

- Persona:
  - 专业、冷静、规则清晰
- Policy:
  - 不越权、不承诺个案赔付
- Workflow:
  - 先回答规则，再给下一步
- Tool:
  - FAQ 搜索、政策检索
- Knowledge:
  - FAQ / 售后政策 / 服务规则

这样横向增加 Agent 时，很多 bundle 可以复用，而不是每次都从零写 prompt。

## 8. 如何横向扩充多个子 Agent

横向扩容必须遵循“拆域而不是堆人设”。

## 8.1 什么时候应该新增子 Agent

满足以下条件之一才值得拆：

1. 某问题域的知识、流程、风险边界明显独立
2. 当前通用 Agent 处理这类问题经常出错
3. 该类问题的技能组合明显不同
4. 需要单独监控和运营优化

## 8.2 不应该新增子 Agent 的情况

以下情况不要拆 Agent，只需要加 Skill：

- 只是表达风格不同
- 只是多一条政策边界
- 只是多一个检索知识源
- 只是多几个表单字段

换句话说：

- “能力差异”先用 Skill 解决
- “问题域差异”才用 Agent 解决

## 8.3 横向扩容的三种方式

### 方式一：同域扩展，用 Skill 扩展

例如 `resolution_execution_agent` 新增“安装排障 SOP”，不需要新 Agent，只需要新 knowledge/workflow skill。

### 方式二：子域复杂化，拆 L3 专科 Agent

例如退款争议越来越复杂，可以从 `faq_policy_agent` / `resolution_execution_agent` 里拆出：

- `refund_policy_agent`
- `refund_dispute_agent`

### 方式三：按渠道/人群做变体

例如：

- `vip_retention_agent`
- `cross_border_policy_agent`

但这种扩展要非常克制，否则会出现 Agent 爆炸。

## 9. 防止子 Agent 爆炸的治理规则

建议定四条硬规则：

### 9.1 总量限制

第一阶段 L2 + L3 Agent 总数不要超过 8 到 12 个。

### 9.2 命名规则

统一用：

`[domain]_[goal]_agent`

例如：

- `emotion_deescalation_agent`
- `case_intake_agent`
- `refund_dispute_agent`

### 9.3 新增审批条件

每新增一个子 Agent，都必须回答：

1. 它和现有哪个 Agent 的边界不同？
2. 它的 Skill 组合为什么不能直接复用？
3. 它的成功标准是否独立？
4. 它是否有单独监控价值？

答不上来，就不应该新增。

### 9.4 指标监控

每个子 Agent 必须有独立指标：

- 命中率
- 解决率
- 转人工率
- 用户负反馈率
- 平均轮次

没有指标的 Agent，迟早会失控。

## 10. Flow 编排层如何使用这些子 Agent

流程图不是随便把节点连起来，而是基于问题域流转：

### 示例 A：情绪激烈型投诉

```text
Start
 -> Router
 -> emotion_deescalation_agent
 -> Condition(情绪是否稳定)
 -> case_intake_agent
 -> resolution_execution_agent
 -> End
```

### 示例 B：纯规则咨询

```text
Start
 -> Router
 -> faq_policy_agent
 -> Condition(是否接受)
 -> End / handoff_orchestrator_agent
```

### 示例 C：三轮未解决

```text
Start
 -> Router
 -> resolution_execution_agent
 -> Condition(unresolved_turns >= 3)
 -> handoff_orchestrator_agent
```

## 11. 关键结论

子 Agent 代表的不是“一个技术能力”，而是“一个问题域处理责任”。

控制子 Agent 的关键，不是只写 prompt，而是五层一起做：

1. 父 Agent 路由控制
2. 任务 prompt 控制
3. Skill 组合控制
4. Tool scope 控制
5. 结构化输出合同控制

横向扩充子 Agent 的关键，不是多建几个角色，而是严格区分：

- 什么是新问题域
- 什么只是新 skill

如果这条线把住了，后续多 Agent 才会越扩越清晰；把不住，就会越来越乱。
