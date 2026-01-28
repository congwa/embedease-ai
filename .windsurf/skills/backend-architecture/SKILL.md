---
name: backend-architecture
description: |
  后端代码架构上下文。此技能在每次对话开始时自动触发，提供项目后端的模块化架构概览。
  包含：核心模块、业务服务、数据模型、API路由、调度器等组件的介绍。
  触发条件：alwaysApply: true（始终应用）
alwaysApply: true
---

# EmbedEase AI 后端架构

基于 **FastAPI + LangChain v1.2 + LangGraph** 的多智能体商品推荐系统。

## 目录结构

```
backend/
├── app/
│   ├── core/           # 核心模块（配置、数据库、LLM、日志、Chat Models）
│   ├── models/         # SQLAlchemy 数据模型
│   ├── prompts/        # 提示词管理系统
│   ├── repositories/   # 数据访问层
│   ├── routers/        # FastAPI 路由
│   ├── schemas/        # Pydantic Schema
│   ├── services/       # 业务逻辑层
│   ├── scheduler/      # 定时任务调度
│   ├── utils/          # 工具函数
│   └── main.py         # 应用入口
├── tests/              # 测试用例
└── data/               # 静态数据
```

## 核心模块 (app/core/)

| 模块 | 文件 | 职责 |
|------|------|------|
| **配置** | `config.py` | Pydantic Settings，环境变量管理 |
| **数据库** | `database.py` | SQLAlchemy 异步引擎、会话管理 |
| **爬虫数据库** | `crawler_database.py` | 爬虫专用数据库连接 |
| **Chat Models** | `chat_models/` | 多态架构 Chat 模型（推理内容提取） |
| **LLM** | `llm.py` | ChatOpenAI/Embeddings 初始化 |
| **Embedding** | `embedding.py` | 向量嵌入模型 |
| **Rerank** | `rerank.py` | 重排序模型 |
| **日志** | `logging.py` | Loguru 结构化日志 |
| **健康检查** | `health.py`, `health_checks.py` | 依赖健康状态 |
| **错误处理** | `errors.py`, `error_reporter.py` | 统一异常类和错误报告 |
| **依赖注入** | `dependencies.py` | FastAPI 依赖（DB Session 等）|
| **路径管理** | `paths.py` | 文件路径常量 |

### Chat Models 多态架构 (`core/chat_models/`)

```
chat_models/
├── base.py             # ReasoningChunk 结构 + BaseReasoningChatModel 抽象基类
├── registry.py         # 模型创建工厂，按 provider 选择实现
└── providers/
    └── reasoning_content.py  # SiliconFlow 推理内容实现
```

## 提示词系统 (app/prompts/)

统一管理所有提示词，支持默认值 + 数据库覆盖：

```
prompts/
├── registry.py         # PromptRegistry - 提示词注册表
├── schemas.py          # Pydantic Schema
└── defaults/           # 默认提示词
    ├── agent.py        # Agent 提示词
    ├── crawler.py      # 爬虫提示词
    ├── memory.py       # 记忆提示词
    └── skill.py        # 技能提示词
```

| 类 | 职责 |
|-----|------|
| `PromptRegistry` | 提示词 CRUD、优先级（数据库 > 默认）、reset |

## 数据模型 (app/models/)

| 模型 | 文件 | 说明 |
|------|------|------|
| `Agent` | `agent.py` | 智能体配置、FAQEntry、KnowledgeConfig |
| `Conversation` | `conversation.py` | 会话、HandoffState |
| `Message` | `message.py` | 消息 |
| `User` | `user.py` | 用户 |
| `Product` | `product.py` | 商品 |
| `CrawlSite/CrawlPage/CrawlTask` | `crawler.py` | 爬虫站点、页面、任务 |
| `Prompt` | `prompt.py` | 提示词模板 |
| `ToolCall` | `tool_call.py` | 工具调用记录 |
| `AppMetadata` | `app_metadata.py` | 键值存储（系统配置）|
| `Skill/AgentSkill` | `skill.py` | 技能定义、Agent-技能关联 |

## 业务服务 (app/services/)

### Agent 服务 (`services/agent/`)

多智能体系统核心：

```
agent/
├── core/               # 核心服务
│   ├── service.py      # AgentService 主入口
│   ├── factory.py      # Agent 工厂
│   ├── config.py       # Agent 配置管理
│   ├── intent.py       # 意图识别
│   └── policy.py       # 路由策略
├── middleware/         # 中间件（声明式注册，按 order 执行）
│   ├── registry.py           # 中间件注册表
│   ├── sliding_window.py     # 滑动窗口裁剪
│   ├── summarization_broadcast.py # 上下文压缩摘要
│   ├── todo_broadcast.py     # TODO 规划广播
│   ├── sequential_tools.py   # 工具串行执行
│   ├── noise_filter.py       # 工具输出噪音过滤
│   ├── response_sanitization.py # 响应内容安全过滤
│   ├── llm_call_sse.py       # LLM 调用事件推送
│   ├── logging.py            # 日志记录
│   └── strict_mode.py        # 严格模式检查
├── retrieval/          # 检索服务（已迁移到 knowledge/）
├── streams/            # 流式响应
├── tools/              # 工具定义（声明式注册）
│   ├── registry.py     # 工具注册表
│   ├── product/        # 商品工具（12+）
│   ├── knowledge/      # 知识库工具
│   └── common/         # 通用工具
└── bootstrap.py        # 默认 Agent 初始化
```

#### 中间件执行顺序

| Order | 名称 | 说明 |
|-------|------|------|
| 10 | MemoryOrchestration | 记忆注入 + 异步写入 |
| 20 | ResponseSanitization | 响应内容安全过滤 |
| 30 | SSE | LLM 调用事件推送 |
| 40 | TodoBroadcast | 任务规划广播 |
| 50 | SequentialToolExecution | 工具串行执行 |
| 55 | NoiseFilter | 工具输出噪音过滤 |
| 60 | Logging | 日志记录 |
| 85 | SlidingWindow | 滑动窗口裁剪 |
| 90 | Summarization | 上下文压缩摘要 |
| 100 | StrictMode | 严格模式检查 |

#### 商品工具列表

| 工具 | 说明 |
|------|------|
| `search_products` | 搜索商品 |
| `get_product_details` | 获取商品详情 |
| `compare_products` | 对比商品 |
| `filter_by_price` | 价格筛选 |
| `list_all_categories` | 列出所有类目 |
| `get_category_overview` | 类目概览 |
| `list_products_by_category` | 按类目列商品 |
| `find_similar_products` | 查找相似商品 |
| `list_featured_products` | 精选商品 |
| `list_products_by_attribute` | 按属性筛选 |
| `suggest_related_categories` | 推荐相关类目 |
| `get_product_purchase_links` | 获取购买链接 |
| `guide_user` | 引导用户 |

### 记忆系统 (`services/memory/`)

长期记忆 + 用户画像：

```
memory/
├── store.py            # UserProfileStore - LangGraph Store 基座
├── profile_service.py  # ProfileService - 用户画像服务
├── fact_memory.py      # FactMemoryService - 事实型长期记忆
├── graph_memory.py     # KnowledgeGraphManager - 图谱记忆
├── vector_store.py     # Qdrant 向量存储
├── models.py           # Entity, Fact, Relation, UserProfile
├── prompts.py          # 记忆提示词
└── middleware/         # 记忆编排中间件
```

| 类 | 职责 |
|-----|------|
| `UserProfileStore` | LangGraph Store，跨会话画像存储 |
| `ProfileService` | 从事实/图谱自动提取画像信息 |
| `FactMemoryService` | LLM 抽取 + Qdrant 向量检索 |
| `KnowledgeGraphManager` | 实体/关系结构化存储 |

### 技能服务 (`services/skill/`)

Agent 可扩展技能系统：

```
skill/
├── service.py      # SkillService - CRUD、Agent 关联、技能匹配
├── generator.py    # SkillGenerator - AI 智能生成技能
├── registry.py     # SkillRegistry - 运行时缓存
├── injector.py     # SkillInjector - 技能注入到 Agent
└── system_skills.py # 系统内置技能定义
```

### 知识库服务 (`services/knowledge/`)

```
knowledge/
├── factory.py          # 检索器工厂
├── kb_retriever.py     # 知识库检索
├── faq_retriever.py    # FAQ 检索
└── faq_service.py      # FAQ CRUD
```

### 客服支持 (`services/support/`)

```
support/
├── gateway.py          # 客服网关
├── handoff.py          # 人工客服转接
├── heat_score.py       # 热度评分
└── notification/       # 通知渠道
    ├── base.py         # 通知基类
    ├── dispatcher.py   # 通知分发器
    └── channels/       # 具体渠道实现
```

### 其他服务

| 服务 | 目录/文件 | 职责 |
|------|-----------|------|
| **会话** | `conversation.py` | 会话 CRUD、消息管理 |
| **聊天流** | `chat_stream.py` | SSE 流式响应 |
| **流式响应** | `streaming/` | SSE 上下文、事件发射器 |
| **爬虫** | `crawler/` | 网站爬取、页面解析、站点初始化 |
| **OCR** | `ocr/` | 多引擎支持（RapidOCR、PaddleX、MinerU）|
| **存储** | `storage/` | MinIO 对象存储 |
| **WebSocket** | `websocket/` | 实时通信、心跳、消息路由 |
| **快速配置** | `quick_setup/` | 配置向导、状态管理、检查清单 |
| **商品画像** | `catalog_profile.py` | 商品分类画像 |
| **系统配置** | `system_config.py` | LLM/Embedding/Rerank 动态配置 |

## 数据访问层 (app/repositories/)

| 仓库 | 文件 | 职责 |
|------|------|------|
| `ConversationRepository` | `conversation.py` | 会话 CRUD |
| `MessageRepository` | `message.py` | 消息 CRUD |
| `ProductRepository` | `product.py` | 商品 CRUD |
| `CrawlerRepository` | `crawler.py` | 爬虫站点/页面 CRUD |
| `ToolCallRepository` | `tool_call.py` | 工具调用记录 |
| `UserRepository` | `user.py` | 用户 CRUD |

## API 路由 (app/routers/)

| 路由 | 前缀 | 说明 |
|------|------|------|
| `admin.py` | `/api/v1/admin` | 后台管理 |
| `system_config.py` | `/api/v1/admin/system-config` | 系统配置 |
| `skills.py` | `/api/v1/admin/skills` | 技能管理、AI 生成 |
| `prompts.py` | `/api/v1/admin/prompts` | 提示词管理 |
| `chat.py` | `/api/v1/chat` | 聊天 API |
| `conversations.py` | `/api/v1/conversations` | 会话管理 |
| `agents.py` | `/api/v1/agents` | Agent CRUD |
| `crawler.py` | `/api/v1/crawler` | 爬虫管理 |
| `ocr.py` | `/api/v1/ocr` | OCR 服务 |
| `support.py` | `/api/v1/support` | 客服支持 |
| `users.py` | `/api/v1/users` | 用户管理 |
| `upload.py` | `/api/v1/upload` | 文件上传 |
| `quick_setup.py` | `/api/v1/quick-setup` | 快速配置向导 |
| `health.py` | `/api/v1/health` | 健康检查 |
| `system.py` | `/api/v1/system` | 系统信息 |
| `ws.py` | `/ws` | WebSocket |

## 调度器 (app/scheduler/)

APScheduler 定时任务：

```
scheduler/
├── scheduler.py        # 任务调度器
├── registry.py         # 任务注册
├── runner.py           # 任务执行器
├── state/              # 任务状态管理
├── tasks/              # 任务定义
│   ├── base.py         # 任务基类
│   └── crawl_site.py   # 爬虫定时任务
└── routers/            # 调度器 API
```

## 事件类型 (app/schemas/events.py)

细粒度事件分类：

| 类别 | 事件 | 说明 |
|------|------|------|
| **流级别** | `meta.start` | 流开始 |
| | `assistant.final` | 最终态 |
| | `error` | 错误事件 |
| **LLM 边界** | `llm.call.start` | LLM 调用开始 |
| | `llm.call.end` | LLM 调用结束 |
| **LLM 内部** | `assistant.reasoning.delta` | 推理内容增量 |
| | `assistant.delta` | 文本增量 |
| **工具调用** | `tool.start` | 工具开始 |
| | `tool.end` | 工具结束 |
| **数据事件** | `assistant.products` | 商品数据 |
| | `assistant.todos` | TODO 规划更新 |
| | `context.summarized` | 上下文压缩完成 |
| | `context.trimmed` | 滑动窗口裁剪 |
| **后处理** | `memory.extraction.start` | 记忆抽取开始 |
| | `memory.extraction.complete` | 记忆抽取完成 |
| | `memory.profile.updated` | 用户画像更新 |
| **客服** | `support.handoff_started` | 客服介入开始 |
| | `support.handoff_ended` | 客服介入结束 |
| | `support.human_message` | 人工客服消息 |
| **技能** | `skill.activated` | 技能被激活 |
| | `skill.loaded` | 技能被加载 |
| **多 Agent** | `agent.routed` | Agent 路由决策 |
| | `agent.handoff` | Agent 切换 |

## 数据流

```
用户请求 → FastAPI Router → Service → Repository → Database
                ↓
           Agent 服务 → 中间件链 → LangGraph → LLM
                ↓
           工具调用 → 检索服务 → Qdrant/知识库
                ↓
           SSE 流式响应 → 事件推送
                ↓
           记忆抽取 → 用户画像更新
```

## 配置优先级

- **系统配置**（LLM_API_KEY 等）：**数据库 > 环境变量**
- **提示词**：**数据库 > 默认值**

通过 `SystemConfigService` 和 `PromptRegistry` 管理动态配置。

## 测试

```bash
# 运行所有测试
uv run pytest

# 运行特定模块测试
uv run pytest tests/services/test_system_config.py -v

# 运行技能系统测试
uv run pytest tests/schemas/test_skill.py tests/services/test_skill.py tests/routers/test_skills.py -v
```
