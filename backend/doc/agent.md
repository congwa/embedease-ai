# Agent 架构设计

本文档详细描述 Yuxi-Know 的多 Agent 架构设计，包括现有架构分析、Supervisor 编排方案及实现规划。

## 目录

1. [现有架构分析](#1-现有架构分析)
2. [Supervisor 编排方案](#2-supervisor-编排方案)
3. [数据模型设计](#3-数据模型设计)
4. [后端实现方案](#4-后端实现方案)
5. [前端集成方案](#5-前端集成方案)
6. [配置与迁移](#6-配置与迁移)

---

## 1. 现有架构分析

### 1.1 Agent 类型定义

当前系统支持 4 种 Agent 类型（`app/models/agent.py`）：

| 类型 | 枚举值 | 职责 | 默认工具 |
|------|--------|------|----------|
| **Product** | `product` | 商品搜索、推荐、比较 | search, query, compare, filter, category, featured, purchase, guide |
| **FAQ** | `faq` | FAQ 问答，匹配预设问答对 | faq_search |
| **KB** | `kb` | 知识库检索，文档问答 | kb_search, kb_query |
| **Custom** | `custom` | 自定义场景，灵活配置 | 用户自定义 |

### 1.2 核心代码结构

```
app/services/agent/
├── core/
│   ├── factory.py      # build_agent(): 从 AgentConfig 构建 LangGraph Agent
│   ├── service.py      # AgentService: Agent 实例管理、缓存
│   ├── config.py       # AgentConfigLoader: 从 DB 加载配置
│   └── policy.py       # 模式策略定义
├── tools/
│   └── registry.py     # get_tools_for_agent(): 按配置过滤工具
├── middleware/
│   └── registry.py     # build_middlewares_for_agent(): 构建中间件链
└── bootstrap.py        # Agent 初始化
```

### 1.3 当前执行流程

```
┌─────────────────┐
│  用户消息       │
└────────┬────────┘
         ▼
┌─────────────────┐
│  ChatStreamOrchestrator
│  (chat_stream.py)
└────────┬────────┘
         ▼
┌─────────────────┐
│  AgentService.get_agent()
│  - 加载 AgentConfig
│  - 获取 Checkpointer
│  - build_agent()
└────────┬────────┘
         ▼
┌─────────────────┐
│  build_agent()
│  (factory.py)
│  - get_chat_model()
│  - get_tools_for_agent()
│  - build_middlewares_for_agent()
│  - create_agent()
└────────┬────────┘
         ▼
┌─────────────────┐
│  CompiledStateGraph
│  (LangGraph Agent)
└────────┬────────┘
         ▼
┌─────────────────┐
│  SSE 事件流     │
└─────────────────┘
```

### 1.4 配置继承链

```
全局 settings (.env)
    ↓ fallback
类型默认 (configurators.py)
    ↓ fallback
Agent 配置 (agents 表)
    ↓ override
Mode 覆盖 (agent_mode_overrides 表)
```

---

## 2. Supervisor 编排方案

### 2.1 设计目标

| 目标 | 说明 |
|------|------|
| **可选启用** | Supervisor 模式通过后台配置开关，不影响现有单 Agent 模式 |
| **动态路由** | 根据用户意图自动选择最合适的子 Agent |
| **配置驱动** | 路由策略通过后台配置，无需修改代码 |
| **透明集成** | SSE 事件流、会话历史、中间件等现有功能无缝兼容 |

### 2.2 架构对比

#### 模式一：单 Agent 模式（现有）

```
用户 → Agent (product/faq/kb/custom) → 响应
```

- 用户在前端选择具体 Agent
- 每个 Agent 独立处理请求

#### 模式二：Supervisor 模式（新增）

```
用户 → Supervisor → 意图识别 → 子 Agent 调度 → 响应汇总 → 用户
                          ↓
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          Product       FAQ         KB
```

- 用户统一入口，无需选择 Agent
- Supervisor 自动分析意图并路由
- 支持多 Agent 协作完成复杂任务

### 2.3 路由策略设计

Supervisor 根据以下维度判断路由目标：

| 策略类型 | 触发条件 | 示例 |
|----------|----------|------|
| **关键词匹配** | 用户消息包含特定关键词 | "退换货" → FAQ Agent |
| **意图分类** | LLM 意图识别结果 | "推荐一款耳机" → Product Agent |
| **上下文延续** | 当前对话已有子 Agent 处理 | 继续使用上一个 Agent |
| **默认兜底** | 无法匹配时 | 使用默认 Agent 或直接回复 |

#### 路由策略配置示例

```json
{
  "routing_policy": {
    "type": "hybrid",
    "rules": [
      {
        "condition": {"type": "keyword", "keywords": ["退货", "换货", "售后"]},
        "target": "faq_agent",
        "priority": 100
      },
      {
        "condition": {"type": "intent", "intents": ["product_search", "product_compare"]},
        "target": "product_agent",
        "priority": 90
      },
      {
        "condition": {"type": "intent", "intents": ["knowledge_query"]},
        "target": "kb_agent",
        "priority": 80
      }
    ],
    "default_agent": "product_agent",
    "allow_multi_agent": false
  }
}
```

---

## 3. 数据模型设计

### 3.1 Agent 表扩展

在现有 `agents` 表基础上新增字段：

```python
class Agent(Base, TimestampMixin):
    # ... 现有字段 ...
    
    # ========== Supervisor 相关（新增） ==========
    
    # 是否为 Supervisor 类型
    is_supervisor: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    
    # 子 Agent 配置（JSON，仅 is_supervisor=True 时有效）
    # 格式: [{"agent_id": "xxx", "name": "商品助手", "routing_hints": [...]}]
    sub_agents: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    
    # 路由策略配置（JSON）
    routing_policy: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Supervisor 专用提示词（意图分类指令）
    supervisor_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
```

### 3.2 Supervisor 配置 Schema

```python
class SubAgentConfig(BaseModel):
    """子 Agent 配置"""
    agent_id: str
    name: str
    description: str | None = None
    routing_hints: list[str] = []  # 路由提示词
    priority: int = 0              # 优先级

class RoutingRule(BaseModel):
    """路由规则"""
    condition: dict                # 触发条件
    target: str                    # 目标 Agent ID
    priority: int = 0              # 规则优先级

class RoutingPolicy(BaseModel):
    """路由策略"""
    type: Literal["keyword", "intent", "hybrid"] = "hybrid"
    rules: list[RoutingRule] = []
    default_agent: str | None = None
    allow_multi_agent: bool = False  # 是否允许多 Agent 协作

class SupervisorConfig(BaseModel):
    """Supervisor 配置"""
    sub_agents: list[SubAgentConfig]
    routing_policy: RoutingPolicy
    supervisor_prompt: str | None = None
```

---

## 4. 后端实现方案

### 4.1 Factory 层扩展

修改 `app/services/agent/core/factory.py`：

```python
async def build_agent(
    config: AgentConfig,
    checkpointer: BaseCheckpointSaver,
    use_structured_output: bool = False,
) -> CompiledStateGraph:
    """从配置构建 Agent 实例"""
    
    # 判断是否为 Supervisor 模式
    if config.is_supervisor and config.sub_agents:
        return await build_supervisor_agent(config, checkpointer)
    
    # 现有逻辑：构建单 Agent
    return await build_single_agent(config, checkpointer, use_structured_output)


async def build_supervisor_agent(
    config: AgentConfig,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    """构建 Supervisor Agent
    
    使用 LangGraph 的 langgraph-supervisor 或自定义 StateGraph 实现。
    """
    from langgraph_supervisor import create_supervisor
    
    # 1. 构建子 Agent 列表
    sub_agents = []
    for sub_config in config.sub_agents:
        sub_agent_config = await load_sub_agent_config(sub_config["agent_id"])
        agent = await build_single_agent(sub_agent_config, checkpointer)
        sub_agents.append({
            "name": sub_config["name"],
            "agent": agent,
            "description": sub_config.get("description", ""),
        })
    
    # 2. 构建 Supervisor
    model = get_chat_model()
    supervisor_prompt = config.supervisor_prompt or DEFAULT_SUPERVISOR_PROMPT
    
    supervisor = create_supervisor(
        agents=sub_agents,
        model=model,
        prompt=supervisor_prompt,
    ).compile(checkpointer=checkpointer)
    
    return supervisor
```

### 4.2 意图识别器

新增 `app/services/agent/core/intent.py`：

```python
class IntentClassifier:
    """意图分类器"""
    
    def __init__(self, routing_policy: RoutingPolicy):
        self.policy = routing_policy
    
    async def classify(self, message: str, context: dict) -> str:
        """分类用户意图，返回目标 Agent ID"""
        
        # 1. 关键词匹配（优先级最高）
        for rule in self._get_keyword_rules():
            if self._match_keywords(message, rule.condition["keywords"]):
                return rule.target
        
        # 2. LLM 意图识别
        if self.policy.type in ["intent", "hybrid"]:
            intent = await self._llm_classify(message, context)
            target = self._match_intent(intent)
            if target:
                return target
        
        # 3. 默认兜底
        return self.policy.default_agent
```

### 4.3 Service 层适配

`app/services/agent/core/service.py` 无需修改，`build_agent` 内部自动判断是否 Supervisor。

### 4.4 SSE 事件扩展

在 `app/schemas/events.py` 中新增事件类型：

```python
class StreamEventType(StrEnum):
    # ... 现有事件 ...
    
    # Supervisor 相关事件
    AGENT_ROUTED = "agent.routed"      # Agent 路由决策
    AGENT_HANDOFF = "agent.handoff"    # Agent 切换
    AGENT_COMPLETE = "agent.complete"  # 子 Agent 完成

class AgentRoutedPayload(TypedDict):
    """Agent 路由事件 payload"""
    source_agent: str          # 来源 Agent（Supervisor）
    target_agent: str          # 目标 Agent
    target_agent_name: str     # 目标 Agent 名称
    reason: str                # 路由原因
```

---

## 5. 前端集成方案

### 5.1 后台配置页面

新增 Supervisor 配置页面：

```
/admin/agents/[agentId]/supervisor
├── 基础设置
│   ├── 是否启用 Supervisor 模式
│   └── Supervisor 提示词
├── 子 Agent 管理
│   ├── 添加子 Agent（从现有 Agent 选择）
│   ├── 配置路由提示词
│   └── 调整优先级
└── 路由策略
    ├── 策略类型（关键词/意图/混合）
    ├── 规则列表
    └── 默认 Agent
```

### 5.2 聊天界面展示

当使用 Supervisor 时，前端可根据 SSE 事件展示路由状态：

```typescript
// 监听 agent.routed 事件
case "agent.routed":
  showNotification(`正在由 ${payload.target_agent_name} 处理...`);
  break;

// 监听 agent.handoff 事件  
case "agent.handoff":
  showBadge(payload.target_agent_name);
  break;
```

### 5.3 Agent 切换器（仅后台调试）

**后台调试界面** (`/admin/chat`) 提供 Agent 切换器，方便开发测试：

| 选项 | 说明 |
|------|------|
| **智能助手** | Supervisor 模式，自动路由 |
| **商品助手** | 直接使用 Product Agent |
| **FAQ 助手** | 直接使用 FAQ Agent |
| **知识库助手** | 直接使用 KB Agent |

### 5.4 嵌入小窗口模式

嵌入式聊天窗口（Embed Widget）**不提供** Agent 切换器，完全由后台配置控制：

```
┌─────────────────────────────────────────────────────────────┐
│                     后台 Agent 配置                          │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │ 默认 Agent      │    │ Supervisor 开关  │                │
│  │ (is_default)    │    │ (is_supervisor)  │                │
│  └────────┬────────┘    └────────┬─────────┘                │
│           │                      │                          │
│           └──────────┬───────────┘                          │
│                      ▼                                      │
│           ┌─────────────────────┐                           │
│           │  嵌入小窗口使用      │                           │
│           │  后台配置的默认Agent │                           │
│           └─────────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

#### 配置方式

1. **单 Agent 模式**：设置某个 Agent 为 `is_default=true`，嵌入窗口直接使用该 Agent
2. **Supervisor 模式**：设置 Supervisor Agent 为默认，嵌入窗口自动使用 Supervisor 路由

#### Agent 配置表新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `is_supervisor` | bool | 是否为 Supervisor 类型 |
| `sub_agents` | JSON | 子 Agent 配置列表 |
| `routing_policy` | JSON | 路由策略配置 |
| `supervisor_prompt` | Text | Supervisor 专用提示词 |

---

## 6. 配置与迁移

### 6.1 环境变量

```bash
# Supervisor 全局开关（默认关闭）
SUPERVISOR_ENABLED=false

# 默认 Supervisor Agent ID（留空则使用默认 Agent）
SUPERVISOR_DEFAULT_AGENT_ID=

# 意图分类超时（秒）
SUPERVISOR_INTENT_TIMEOUT=3.0

# 是否允许多 Agent 协作
SUPERVISOR_ALLOW_MULTI_AGENT=false
```

### 6.2 兼容性保证

| 场景 | 行为 |
|------|------|
| `SUPERVISOR_ENABLED=false` | 完全使用现有逻辑，无任何变化 |
| Agent 未配置 `is_supervisor` | 作为普通 Agent 使用 |
| Supervisor 无子 Agent | 回退到默认 Agent |

---

## 7. 设置流程

### 7.1 快速设置（Quick Setup）

适用于首次部署或快速体验，通过向导式界面完成配置。

#### 流程步骤

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: 选择 Agent 类型                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Product │ │   FAQ   │ │   KB    │ │ Custom  │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: 基础配置                                            │
│  - Agent 名称                                                │
│  - Agent 描述                                                │
│  - 默认模式 (natural/free/strict)                           │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: 知识源配置（可选）                                   │
│  - FAQ: 上传 FAQ 文件或手动添加                              │
│  - KB: 选择向量库集合                                        │
│  - Product: 自动绑定商品库                                   │
└─────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: 完成                                                │
│  - 设为默认 Agent（嵌入窗口使用）                            │
│  - 预览效果                                                  │
│  - 获取嵌入代码                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 快速设置 API

```bash
# 获取可用的 Agent 类型及其默认配置
GET /api/v1/quick-setup/agent-types

# 创建 Agent（使用类型默认配置）
POST /api/v1/quick-setup/create
{
  "type": "product",
  "name": "商品推荐助手",
  "is_default": true
}
```

### 7.2 管理端详细设置

适用于需要精细控制的场景，通过管理后台进行完整配置。

#### 7.2.1 Agent 基础设置

路径：`/admin/agents/[agentId]`

| 配置项 | 说明 | 示例值 |
|--------|------|--------|
| 名称 | Agent 显示名称 | "商品推荐助手" |
| 描述 | Agent 功能描述 | "帮助用户搜索和推荐商品" |
| 类型 | Agent 类型（创建后不可修改） | product/faq/kb/custom |
| 默认模式 | 回答策略 | natural/free/strict |
| 是否默认 | 嵌入窗口使用此 Agent | true/false |
| 状态 | 启用/禁用 | enabled/disabled |

#### 7.2.2 系统提示词配置

路径：`/admin/agents/[agentId]/memory`

```markdown
## 系统提示词模板

你是一个专业的{agent_type}助手。

### 角色定义
- 主要职责：{description}
- 回答风格：专业、友好、简洁

### 行为约束
- 只基于工具返回的真实数据回答
- 不确定时主动询问用户
- 推荐时说明理由

### 可用工具
{tools_description}
```

#### 7.2.3 工具配置

路径：`/admin/agents/[agentId]/tools`

| 配置项 | 说明 |
|--------|------|
| 工具类别 | 启用的工具类别（search/compare/filter 等） |
| 工具白名单 | 精细到单个工具的启用/禁用 |
| 工具策略 | 最小调用次数、允许直接回答、兜底工具等 |

#### 7.2.4 中间件配置

路径：`/admin/agents/[agentId]/middleware`

| 中间件 | 配置项 | 默认值 |
|--------|--------|--------|
| **滑动窗口** | 启用、策略、最大消息数/Token | 禁用 |
| **上下文压缩** | 启用、触发阈值、保留策略、摘要模型 | 50条触发 |
| **噪音过滤** | 启用、最大字符数、头尾保留 | 2000字符 |
| **TODO 规划** | 启用、系统提示、工具描述 | 启用 |
| **工具重试** | 启用、最大重试次数、退避因子 | 2次 |
| **工具限制** | 启用、线程限制、单次限制 | 100/20 |

#### 7.2.5 Supervisor 配置（可选）

路径：`/admin/agents/[agentId]/supervisor`

| 配置项 | 说明 |
|--------|------|
| 启用 Supervisor | 是否作为 Supervisor Agent |
| 子 Agent 列表 | 添加/移除子 Agent，配置优先级 |
| 路由策略 | 关键词规则、意图规则、默认 Agent |
| Supervisor 提示词 | 意图分类和路由决策指令 |

**子 Agent 配置示例：**

```json
{
  "sub_agents": [
    {
      "agent_id": "agent-product-001",
      "name": "商品助手",
      "routing_hints": ["商品", "推荐", "比较", "价格"],
      "priority": 100
    },
    {
      "agent_id": "agent-faq-001", 
      "name": "FAQ 助手",
      "routing_hints": ["退货", "售后", "发货", "支付"],
      "priority": 90
    },
    {
      "agent_id": "agent-kb-001",
      "name": "知识库助手",
      "routing_hints": ["政策", "规则", "说明"],
      "priority": 80
    }
  ]
}
```

**路由策略配置示例：**

```json
{
  "routing_policy": {
    "type": "hybrid",
    "rules": [
      {
        "condition": {"type": "keyword", "keywords": ["退货", "换货"]},
        "target": "agent-faq-001",
        "priority": 100
      },
      {
        "condition": {"type": "intent", "intents": ["product_query"]},
        "target": "agent-product-001",
        "priority": 90
      }
    ],
    "default_agent": "agent-product-001"
  }
}
```

### 7.3 嵌入代码获取

完成配置后，在管理端获取嵌入代码：

路径：`/admin/embed`

```html
<!-- 嵌入式聊天窗口 -->
<script src="https://your-domain.com/embed.js"></script>
<script>
  YuxiChat.init({
    // 使用后台配置的默认 Agent
    // 无需指定 agentId，自动使用 is_default=true 的 Agent
  });
</script>
```

### 7.4 配置优先级

```
环境变量 (.env)
    ↓ 被覆盖
类型默认配置 (configurators.py)
    ↓ 被覆盖
Agent 配置 (数据库 agents 表)
    ↓ 被覆盖
Mode 覆盖配置 (数据库 agent_mode_overrides 表)
```

---