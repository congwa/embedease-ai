# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.10] - 2026-01-04

### 2026-01-04 16:00 (UTC+08:00)

#### Added

- **工具调用追踪与消息元数据** (`backend/app/services/chat_stream.py`, `backend/app/models/message.py`, `backend/app/services/conversation.py`): 将 LangGraph 工具调用与模型 usage metadata 全量落库，暴露 `tool_calls` 表与 `message.extra_metadata`，方便历史回放、Token 统计与仪表盘分析。
- **消息送达 / 已读与在线状态** (`backend/app/models/message.py`, `backend/app/services/conversation.py`, `backend/app/routers/chat.py`): 记录消息送达、已读时间与当前在线用户/客服 ID，支持客服面板实时掌握多端状态。
- **客服双通道与嵌入式聊天 WebSocket** (`backend/app/services/chat_stream.py`, `backend/app/services/support/*`, `frontend/components/features/embed/*`): 嵌入式组件改为 WebSocket 长连推送，并允许在任意会话中一键切换人工客服；手动/自动交接均通过同一双通道广播。
- **管理后台基础路由** (`backend/app/routers/admin.py`): 提供统一的后台入口，为后续运营面板/统计视图铺路。

#### Changed

- **客服介入通知机制重构** (`backend/app/services/support/handoff.py`, `backend/app/services/websocket/*`): 从 SSE + 客户端轮询改为服务端 WebSocket 广播，移除客服端主动推送，保证所有状态更新按服务器时间线下发。
- **事件类型系统升级** (`backend/app/schemas/events.py`, `backend/app/services/agent/streams/response_handler.py`): 将 Agent 事件按生命周期重新分层，新增工具调用分组（Cluster）以便时间线展示，同时保留 start/end 精准配对。
- **爬虫数据库拆分与 WAL** (`backend/app/core/crawler_database.py`, `backend/app/models/crawler/*.py`): 将爬虫数据迁移至独立 SQLite 文件，默认启用 WAL、分离页面处理事务，避免影响主业务数据库并提升并发能力。
- **日志格式与转义** (`backend/app/core/logging.py`): 优化 loguru formatter，自动转义特殊字符，防止彩色输出被错误解析。

#### Fixed

- **WebSocket 连接稳定性** (`backend/app/services/websocket/manager.py`): 修复并发下的连接泄露与状态同步问题，避免客服端卡死或状态错乱。

#### Docs

- **客服配置指南** (`README.md`, `docs/support.md`): 补充企业微信 / Webhook 通知、人工介入开关与新 WebSocket 事件说明。

## [0.1.9] - 2025-12-24

### 2025-12-24 21:09 (UTC+08:00)

#### Added

- 新增爬虫模块配置与数据模型，支持自动发现商品并导入
- 新增 `scheduler` 模块，提供 TaskRegistry/TaskScheduler/TaskRunner 结构，支持单站点多任务调度
- 新增 `CrawlSiteTask` 及 `/scheduler/*` API，文档化扩展方式（`backend/app/scheduler/README.md`）
- 支持通过 `CRAWLER_SITES_JSON` 在配置文件中定义站点，应用启动时自动导入并注册定时任务
- 新增 `normalize_domain` / `generate_site_id` 工具与站点初始化器，保证不同子域名可作为独立站点
- `/crawler/sites` API 增加域名查重、ID 自动生成及系统站点删除保护
- **Agent 工具稳健性配置** (`backend/.env.example`, `backend/app/core/config.py`): 新增工具重试与调用次数限制配置（`AGENT_TOOL_RETRY_*`, `AGENT_TOOL_LIMIT_*`），并补全 TODO 规划开关及自定义提示/描述字段。
- **中间件扩展** (`backend/app/services/agent/agent.py`, `backend/app/services/agent/middleware/todo_broadcast.py`): 条件注入 `ToolRetryMiddleware`、`ToolCallLimitMiddleware`、`TodoListMiddleware`，并新增 `TodoBroadcastMiddleware` 在 todos 变更时向前端推送 SSE。
- **SSE 事件类型** (`backend/app/schemas/events.py`): 新增 `assistant.todos` 事件与 TODO payload 定义。
- **前端待办渲染** (`frontend/hooks/use-timeline-reducer.ts`, `frontend/types/chat.ts`, `frontend/components/features/chat/TimelineTodosItem.tsx`, `frontend/components/prompt-kit/todo-list.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 时间线 reducer 支持 `assistant.todos`，新增 TodoList 组件与时间线项渲染，展示待办清单及状态。

#### Changed

- **TODO 历史保留** (`frontend/hooks/use-timeline-reducer.ts`): `assistant.todos` 事件不再查找并更新现有 item，而是每次推送都插入新的 TodoList，保留大模型在同一轮对话中的多次规划记录。

### 2025-12-24 18:05 (UTC+08:00)

#### Added

- **分类导航工具集** (`backend/app/services/agent/tools/list_all_categories.py`, `get_category_overview.py`, `list_products_by_category.py`): 新增「列出所有分类」「获取分类概览」「按分类列出商品」三款工具，支持查询类目规模、价格区间、热门关键词与代表商品，回答"有哪些分类 / 某分类有啥"的问题更加精准。
- **语义推荐工具集** (`find_similar_products.py`, `list_featured_products.py`, `list_products_by_attribute.py`): 新增「查找相似商品」「列出精选商品」「按属性关键词筛选商品」三款工具，结合向量检索与价格/标签/描述信息，为用户提供替代商品、主题推荐与特性过滤能力。
- **探索与链接工具** (`suggest_related_categories.py`, `get_product_purchase_links.py`): 新增「推荐相关分类」「获取商品购买链接」两款工具，可在无匹配结果时扩展联想、并直接返回可跳转的商品 URL。
- **Agent 工具注册** (`backend/app/services/agent/tools/__init__.py`, `backend/app/services/agent/agent.py`): 将上述 8 个工具全部注册进 Agent，配合既有搜索/对比/引导能力，共 13 个职能单一的工具可被模型自由组合，形成"分类概览 → 商品筛选 → 相似/精选推荐 → 购买链接"完整链路。

#### Changed

- **工具参数单一性校验** (`search_products.py`, `list_products_by_category.py`, `get_category_overview.py`, `find_similar_products.py`, `list_products_by_attribute.py`, `suggest_related_categories.py`): 在 6 个工具中增加运行时参数校验，检测逗号、顿号、换行等分隔符，防止模型一次性传入多个品类/分类/关键词导致检索失败。当检测到多值参数时，工具立即返回结构化错误提示，引导模型拆分为多次调用，确保每次工具调用保持单一职责，提升检索准确率。

## [0.1.8] - 2025-12-23

### 2025-12-23 17:33 (UTC+08:00)

#### Added

- **推理模型多态基座** (`backend/app/core/chat_models/base.py`, `backend/app/core/chat_models/__init__.py`): 新增 `ReasoningChunk` 数据结构与 `BaseReasoningChatModel.extract_reasoning()` 统一入口，Agent 通过多态接口即可获取推理增量，彻底移除对 `additional_kwargs["reasoning_content"]` 的依赖。
- **SiliconFlow 推理实现文档化** (`backend/app/core/chat_models/providers/reasoning_content.py`, `backend/app/core/chat_models/README.md`): 以 `SiliconFlowReasoningChatModel` 封装 `reasoning_content` 字段的提取流程，并补充多态架构设计/扩展指南，方便后续按平台扩展。
- **推理模型注册表** (`backend/app/core/chat_models/registry.py`): 引入 `REASONING_MODEL_REGISTRY`，集中声明 provider → 模型实现的映射，新增平台只需注册即可被自动选择。
- **右下角浮窗聊天组件** (`frontend/components/features/embed/FloatingChatWidget.tsx`, `frontend/components/features/embed/EmbedChatContent.tsx`, `frontend/app/layout.tsx`): 在开发体验页默认渲染可折叠的浮动聊天窗口，支持单会话清空按钮和最小化，方便快速演示。
- **嵌入式脚本打包管线** (`frontend/embed/entry.tsx`, `frontend/embed/EmbedWidget.tsx`, `frontend/embed/embed.css`, `frontend/embed/vite.config.ts`, `frontend/embed/demo.html`): 新增纯 JS Widget 入口与 UI，实现 `window.EmbedAiChat.init()` API，并通过 Vite 打包为单文件 `embed-ai-chat.js`，可直接在第三方站点以 `<script>` 内嵌。
- **构建脚本与依赖** (`frontend/package.json`): 添加 `pnpm build:embed` 命令及 `vite`、`@vitejs/plugin-react`、`terser` 依赖，确保嵌入脚本能够独立打包。
- **README 演示入口** (`README.md`): 在文档顶部加入 `docs/agent0.mp4` 演示视频按钮，访客打开仓库即可直接观看。
- **记忆专用模型配置** (`backend/app/core/config.py`, `backend/.env.example`, `backend/app/core/llm.py`, `backend/app/services/memory/fact_memory.py`, `backend/app/services/memory/graph_memory.py`): 引入 `MEMORY_MODEL/MEMORY_PROVIDER/MEMORY_API_KEY/MEMORY_BASE_URL` 配置与 `get_memory_model()`，记忆抽取可选用独立模型，避免与主聊天模型抢配额。

#### Changed

- **Agent 推理事件发送** (`backend/app/services/agent/agent.py`): SSE 推理增量改为调用 `model.extract_reasoning()`，兼容不同 provider 的推理字段并保留逐字符播报统计。
- **版本号** (`backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`): bump 至 0.1.8，确保前后端版本保持一致。

#### Removed

- **OpenAI 推理实现与旧单测** (`backend/app/core/chat_models/providers/openai.py`, `backend/tests/test_reasoning_content_injection.py`): 删除旧的 OpenAI 专用逻辑与对应单测，为多态实现压缩冗余代码。

## [0.1.7] - 2025-12-22

### 2025-12-23 10:16 (UTC+08:00)

#### Added

- **上下文压缩配置与事件** (`backend/.env.example`, `backend/app/core/config.py`, `backend/app/schemas/events.py`): 默认开启 `SummarizationMiddleware`，新增触发阈值/保留条数/裁剪 token 配置，并定义 `context.summarized` SSE 事件 payload（包含压缩前后消息与 token 数）。
- **SummarizationBroadcastMiddleware** (`backend/app/services/agent/middleware/summarization_broadcast.py`): 封装 LangChain `SummarizationMiddleware`，捕获压缩结果并向前端推送 SSE，复用当前 token 计数器估算压缩收益。
- **前端上下文压缩可视化** (`frontend/types/chat.ts`, `frontend/hooks/use-timeline-reducer.ts`, `frontend/components/features/chat/timeline/TimelineContextSummarizedItem.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 新增 `context.summarized` 事件类型、时间线 item 以及 UI 卡片，展示压缩前后消息/Token 变化。
- **Agent 工具稳健性配置** (`backend/.env.example`, `backend/app/core/config.py`): 新增工具重试与调用次数限制配置（`AGENT_TOOL_RETRY_*`, `AGENT_TOOL_LIMIT_*`），并补全 TODO 规划开关及自定义提示/描述字段。
- **中间件扩展** (`backend/app/services/agent/agent.py`, `backend/app/services/agent/middleware/todo_broadcast.py`): 条件注入 `ToolRetryMiddleware`、`ToolCallLimitMiddleware`、`TodoListMiddleware`，并新增 `TodoBroadcastMiddleware` 在 todos 变更时向前端推送 SSE。
- **SSE 事件类型** (`backend/app/schemas/events.py`): 新增 `assistant.todos` 事件与 TODO payload 定义。
- **前端待办渲染** (`frontend/hooks/use-timeline-reducer.ts`, `frontend/types/chat.ts`, `frontend/components/features/chat/TimelineTodosItem.tsx`, `frontend/components/prompt-kit/todo-list.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 时间线 reducer 支持 `assistant.todos`，新增 TodoList 组件与时间线项渲染，展示待办清单及状态。

#### Changed

- **Agent 中间件声明式构建** (`backend/app/services/agent/agent.py`): 以 `MiddlewareSpec` 数据类集中声明中间件顺序/启用条件/工厂函数，并在注释表格中列出执行顺序，替代原先分散的 `insert/append` 逻辑。
- **System Prompt 升级** (`backend/app/services/agent/agent.py`): 三种模式的 system prompt 精简为核心原则 + 输出格式，不再列举具体工具或流程。
- **工具文档统一** (`backend/app/services/agent/tools/*.py`): `compare_products`、`get_product_details`、`filter_by_price`、`guide_user` docstring 统一使用“商品搜索能力/价格筛选能力”描述，示例与 Note 不再出现英文工具名。
- **Strict 模式执行逻辑** (`backend/app/services/agent/middleware/strict_mode.py`): 依据 ToolPolicy 判断最小工具调用次数、允许直接回答与回退提示，替代 prompt 层强制逻辑。
- **依赖版本** (`backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`): bump 至 0.1.8 并同步锁定文件。

#### Removed

- **意图识别层** (`backend/app/services/agent/middleware/intent_recognition.py`, `backend/app/services/agent/intent_analyzer.py`, `backend/app/schemas/intent.py`): 删除规则/LLM 双重意图识别及工具过滤逻辑，改由策略层与模型自主判断。

### 2025-12-22 17:06 (UTC+08:00)

#### Added

- **Agent 工具稳健性配置** (`backend/.env.example`, `backend/app/core/config.py`): 新增工具重试与调用次数限制配置（`AGENT_TOOL_RETRY_*`, `AGENT_TOOL_LIMIT_*`），并补全 TODO 规划开关及自定义提示/描述字段。
- **中间件扩展** (`backend/app/services/agent/agent.py`, `backend/app/services/agent/middleware/todo_broadcast.py`): 条件注入 `ToolRetryMiddleware`、`ToolCallLimitMiddleware`、`TodoListMiddleware`，并新增 `TodoBroadcastMiddleware` 在 todos 变更时向前端推送 SSE。
- **SSE 事件类型** (`backend/app/schemas/events.py`): 新增 `assistant.todos` 事件与 TODO payload 定义。
- **前端待办渲染** (`frontend/hooks/use-timeline-reducer.ts`, `frontend/types/chat.ts`, `frontend/components/features/chat/TimelineTodosItem.tsx`, `frontend/components/prompt-kit/todo-list.tsx`, `frontend/components/features/chat/ChatContent.tsx`, `frontend/components/features/chat/timeline/index.ts`): 时间线 reducer 支持 `assistant.todos`，新增 TodoList 组件与时间线项渲染，展示待办清单及状态。

### Overview

- System prompt 与工具说明全面改为“能力描述”，彻底移除英文工具名曝光，配合策略层实现纯中文提示体验。
- strict/natural/free 模式的约束由 `ToolPolicy` 与中间件驱动，提示词仅描述角色原则。

### Added

- **ToolPolicy 配置层** (`backend/app/services/agent/policy.py`): 定义 natural/free/strict 策略（最小工具调用、允许直接回答、回退提示等），供 StrictModeMiddleware 使用。
- **Agent 工具执行配置** (`backend/app/core/config.py`, `backend/.env.example`): 新增 `AGENT_SERIALIZE_TOOLS` 配置项，支持控制工具调用是否串行执行（避免并发问题）。
- **串行工具执行中间件** (`backend/app/services/agent/middleware/sequential_tools.py`): 新增 `SequentialToolExecutionMiddleware`，当模型返回多个工具调用时强制按顺序执行。
- **中间件集成** (`backend/app/services/agent/agent.py`): 根据配置条件性地添加串行工具执行中间件到Agent流程。

### Changed

- **System Prompt 升级** (`backend/app/services/agent/agent.py`): 三种模式的 system prompt 精简为核心原则 + 输出格式，不再列举具体工具或流程。
- **工具文档统一** (`backend/app/services/agent/tools/*.py`): `compare_products`、`get_product_details`、`filter_by_price`、`guide_user` docstring 统一使用“商品搜索能力/价格筛选能力”描述，示例与 Note 不再出现英文工具名。
- **Strict 模式执行逻辑** (`backend/app/services/agent/middleware/strict_mode.py`): 依据 ToolPolicy 判断最小工具调用次数、允许直接回答与回退提示，替代 prompt 层强制逻辑。
- **依赖版本** (`backend/pyproject.toml`, `backend/uv.lock`, `frontend/package.json`): bump 至 0.1.7 并同步锁定文件。

### Removed

- **意图识别层** (`backend/app/services/agent/middleware/intent_recognition.py`, `backend/app/services/agent/intent_analyzer.py`, `backend/app/schemas/intent.py`): 删除规则/LLM 双重意图识别及工具过滤逻辑，改由策略层与模型自主判断。

## [0.1.6] - 2025-12-19

### Overview

本版本聚焦于「记忆系统 MVP」，完善了三类记忆能力及其编排能力：

1. **LangGraph Store（长期画像）**：用于跨会话维度存储用户偏好、预算范围、任务进度等结构化信息，为 Agent 提供稳定的上下文基线。
2. **Fact Memory（事实型记忆）**：自动从对话中提取事实，去重后写入 SQLite（元数据）与独立 Qdrant 集合 `memory_facts`（向量），支持回放与高相似度召回。
3. **Graph Memory（图谱记忆）**：以 JSONL 形式记录实体-关系-观察，适合描述“用户与商品/计划/家庭成员之间”的结构化链接。
4. **Memory Orchestration Middleware**：在请求开始阶段注入画像 + 事实 + 图谱，在请求结束后异步写入记忆，实现闭环流水线。

### Added

- **记忆向量存储模块**：新增 `vector_store.py`，负责初始化/缓存 Qdrant 客户端，自动创建独立集合 `memory_facts`，并对嵌入模型进行统一管理。
- **记忆配置扩展**：`.env.example` 与 `Settings` 增加 `MEMORY_FACT_COLLECTION`、`MEMORY_FACT_SIMILARITY_THRESHOLD` 等参数，允许针对不同环境调整集合名称与过滤阈值。
- **文档补全**：`backend/app/services/memory/README.md` 新增“多层混合记忆 + 中间件编排”说明，详细描述 LangGraph Store、Fact Memory（SQLite + Qdrant）、Graph Memory、Orchestration 中间件的职责与交互流程。
- **记忆抽取 SSE 事件** (`backend/app/schemas/events.py`, `backend/app/services/memory/middleware/orchestration.py`)：新增 `memory.extraction.start/complete` 事件类型及 payload，在记忆抽取开始/完成时向前端推送进度与统计信息，便于实时展示记忆写入状态。
- **用户画像服务** (`backend/app/services/memory/profile_service.py`)：
  - 新增 `ProfileService` 统一管理画像的读写与更新，支持从事实/图谱自动提取结构化画像信息。
  - 规则引擎支持自动提取：预算区间（`budget_min/max`）、品类偏好（`favorite_categories`）、品牌偏好（`custom_data.brand_preferences`）、语气偏好（`tone_preference`）、任务进度（`task_progress`）。
  - 新增 `ProfileUpdateSource` 枚举区分更新来源（fact/graph/user_input/system），支持来源优先级冲突解决。
- **画像更新 SSE 事件** (`backend/app/schemas/events.py`)：新增 `memory.profile.updated` 事件类型及 `MemoryProfileUpdatedPayload`，在画像更新时向前端推送更新字段列表和来源。
- **用户画像 API** (`backend/app/routers/users.py`)：
  - `GET /api/v1/users/{user_id}/profile`: 获取用户画像
  - `POST /api/v1/users/{user_id}/profile`: 更新用户画像（用户显式设置）
  - `DELETE /api/v1/users/{user_id}/profile`: 删除用户画像

### Changed

- **事实型长期记忆**：
  - `FactMemoryService` 写入阶段同时更新 SQLite（元数据 + 历史记录）与 Qdrant 向量；检索阶段改为调用 Qdrant `similarity_search_with_score`，并在失败时自动回退至关键词搜索。
  - `update_fact` / `delete_fact` 同步维护 Qdrant 向量数据，确保与 SQLite 状态一致。
  - `Fact` 数据模型移除本地 `embedding` 字段，由 Qdrant 负责托管向量，避免重复存储与手工余弦计算。
- **记忆检索阈值语义** (`backend/app/core/config.py`, `backend/app/services/memory/fact_memory.py`)：将 `MEMORY_FACT_SIMILARITY_THRESHOLD` 明确为“距离阈值（越小越相似）”，检索逻辑改为过滤距离大于阈值的结果，与 Qdrant 的 Distance 语义保持一致。
- **记忆编排中间件** (`backend/app/services/memory/middleware/orchestration.py`)：
  - 新增 `MemoryWriteResult` 结构，统一记录事实/实体/关系/画像写入统计及错误信息。
  - 将记忆写入流程从 `awrap_model_call` 挪至 `aafter_agent` 钩子，仅在整轮 Agent 结束后执行一次，避免多次重复写入并保证抽取使用独立 LLM 调用。
  - 增加 SSE 通知包装器，在记忆抽取开始与完成时通过 `StreamEventType` 向前端发送实时状态（含耗时与写入数量），支持同步/异步两种执行模式。
  - `_process_memory_write` 在事实/图谱抽取后自动调用 `ProfileService` 更新用户画像，并通过 SSE 推送 `memory.profile.updated` 事件。
- **事实记忆服务** (`backend/app/services/memory/fact_memory.py`)：新增 `get_recent_facts()` 方法，支持获取用户最近添加的事实用于画像更新。
- **记忆编排说明**：README 中的数据流图、工作流示例更新为“注入记忆 → Agent 推理 → 异步写入 SQLite + Qdrant”的完整闭环，并补充回退机制、并发安全策略。

## [0.1.5] - 2025-12-19

### 2025-12-19 11:45 (UTC+08:00)

- **系统提示词结合库状态（商品库画像注入）** (`backend/scripts/import_products.py`, `backend/app/services/catalog_profile.py`, `backend/app/services/agent/agent.py`):
  - 导入时对商品数据做源头标准化，并生成商品库画像（Top 类目/价位范围）与短提示词（<=100 字）
  - 新增 `app_metadata` KV 表用于持久化存储 `catalog_profile.stats` / `catalog_profile.prompt_short` / `catalog_profile.fingerprint`
  - Agent 初始化时读取画像提示词并拼接到 system prompt（带 TTL 缓存），fingerprint 变化时清空所有 mode 的 agent 缓存触发重建
  - 新增配置项：`CATALOG_PROFILE_ENABLED` / `CATALOG_PROFILE_TTL_SECONDS` / `CATALOG_PROFILE_TOP_CATEGORIES`（并补充 `.env.example`）
  - 新增单测：`tests/test_catalog_profile.py`

### 2025-12-19 10:50 (UTC+08:00)

#### ⏱️ 时间线渲染重构 (Timeline-based Chat Rendering)

实现 **Cursor/Windsurf 风格的时序时间线渲染**，SSE 事件按到达顺序逐条显示，同一个 span 的 start/end 更新同一张卡片。

##### 🔧 后端改动 (Backend Changes)

- **事件 payload 增强** (`backend/app/schemas/events.py`):
  - `ToolStartPayload` / `ToolEndPayload` 新增 `tool_call_id` 字段，支持前端配对 start/end 事件
  - `ToolEndPayload` 新增 `status` 字段（`success` / `error` / `empty`）

- **工具 tool_call_id 注入** (`backend/app/services/agent/tools/*.py`):
  - 5 个工具（`search_products` / `get_product_details` / `filter_by_price` / `compare_products` / `guide_user`）均生成并传递 `tool_call_id`



##### ✨ 前端改动 (Frontend Changes)

- **Timeline Reducer** (`frontend/hooks/use-timeline-reducer.ts`):
  - 新增纯函数 reducer，处理 7 种 `TimelineItem` 类型
  - 支持按 `id` 快速定位更新（O(1)）
  - 推理/正文增量自动归属当前运行的 LLM 调用

- **Timeline 组件** (`frontend/components/features/chat/timeline/`):
  - `TimelineLlmCallItem`: 模型调用状态卡片（思考中/完成/失败）
  - `TimelineToolCallItem`: 工具执行状态卡片
  - `TimelineReasoningItem`: 推理内容（流式，可折叠）
  - `TimelineContentItem`: 正文内容（流式）
  - `TimelineProductsItem`: 商品卡片网格
  - `TimelineUserMessageItem`: 用户消息气泡
  - `TimelineErrorItem`: 错误提示条

- **新版 Hook 与组件** (`frontend/hooks/use-chat-v2.ts`, `frontend/components/features/chat/ChatContentV2.tsx`):
  - 使用 reducer 管理 timeline 状态
  - 渲染 timeline items 而非消息列表

##### 📡 时间线 Item 类型 (TimelineItem Types)

| 类型 | 说明 |
|------|------|
| `user.message` | 用户消息气泡 |
| `llm.call` | 模型调用状态卡片（start 插入、end 更新） |
| `assistant.reasoning` | 推理内容（流式，归属当前 LLM call） |
| `assistant.content` | 正文内容（流式） |
| `tool.call` | 工具执行状态卡片（start 插入、end 更新） |
| `assistant.products` | 商品卡片网格 |
| `error` | 错误条 |

##### 🎯 事件流示例 (Event Flow Example)

```
09:10:01 llm.call.start      → 插入「模型思考中」卡片
09:10:02 reasoning.delta     → 在卡片下方显示推理内容
09:10:10 llm.call.end        → 更新卡片为「思考完成 · 9000ms」
09:10:11 tool.start          → 插入「商品搜索中」卡片
09:10:12 tool.end            → 更新卡片为「搜索完成 · 5项 · 1234ms」
09:10:13 llm.call.start      → 插入新的「模型思考中」卡片
...
```

---

## [0.1.4] - 2025-12-17

### 2025-12-18 16:59 (UTC+08:00)

#### 🧭 新增聊天模式 natural/free/strict (Chat Modes)

- **配置驱动默认模式** (`backend/app/core/config.py`, `backend/.env.example`):
  - 新增 `CHAT_MODE` 配置项（`natural` / `free` / `strict`），用于控制默认聊天模式
  - `.env.example` 增加 `CHAT_MODE=natural` 示例与说明

- **请求级别覆盖默认模式** (`backend/app/schemas/chat.py`):
  - `ChatRequest` 新增 `mode` 字段（可选），支持按请求切换模式
  - 增加 `effective_mode`：请求优先，否则回退到 `settings.CHAT_MODE`

- **模式透传到运行时上下文** (`backend/app/services/streaming/context.py`, `backend/app/services/chat_stream.py`, `backend/app/routers/chat.py`):
  - `ChatContext` 新增 `mode` 字段，使 middleware/tools 可读取当前模式
  - `ChatStreamOrchestrator` 接收 `mode` 并注入到 `ChatContext`

- **Agent 按模式选择 Prompt/Middleware** (`backend/app/services/agent/agent.py`):
  - 新增三份 system prompt：`NATURAL_SYSTEM_PROMPT` / `FREE_SYSTEM_PROMPT` / `STRICT_SYSTEM_PROMPT`
  - Agent 实例按 mode 缓存（同一进程内不同模式互不影响）
  - `free` 模式禁用意图识别工具过滤（避免强制引导回商品话题）

- **strict 模式强约束与受控失败** (`backend/app/services/agent/middleware/strict_mode.py`, `backend/app/services/chat_stream.py`):
  - 新增 `StrictModeMiddleware`：strict 模式下若模型未发起工具调用则替换为“受控失败”提示
  - Orchestrator 增加 strict 兜底：若全程未出现 `tool.end`，落库前用受控失败消息替换内容（最终保险）

### 2025-12-18 16:22 (UTC+08:00)

#### 🐛 修复 products 污染导致空卡片 (Fix Empty ProductCard Rendering)

- **后端 products 解析修复** (`backend/app/services/agent/agent.py`):
  - ToolMessage 解析 products 时使用临时变量，避免 normalize 失败时污染 `products_data`
  - 防止 `assistant.final` 携带非商品对象（如 `{"products": [], "message": ...}`）导致前端渲染空 `ProductCard` / `product.id` 缺失日志

### 2025-12-18 15:43 (UTC+08:00)

#### 🎨 前端 SSE 展示重构 (Frontend SSE Display Refactor)

- **消息结构升级** (`frontend/hooks/use-chat.ts`):
  - `timeline` 简化为仅保留消息项（不再插入工具/LLM 卡片）
  - 将 `llm`（思考中/完成/耗时/错误）、`toolsSummary`（工具执行摘要）、`trace`（运行轨迹）写入到 `ChatMessage`
  - `llm.call.start` 到达时自动插入空的 reasoning segment，确保推理折叠标题立即出现并承载状态

- **UI 展示重构** (`frontend/components/features/chat/ChatContent.tsx`):
  - 推理折叠标题右侧常驻：运行轨迹入口 + LLM 状态 + 工具摘要
  - 运行轨迹使用 `Steps` 面板展示（LLM / Tool / Products / Error 全部可追溯）
  - 移除正文区域 “思考中...” 占位，避免主消息流被过程事件打断

### 2025-12-18 12:35 (UTC+08:00)

#### 🧠 推理内容与流式兼容 (Reasoning & Streaming Compatibility)

##### ✨ 核心改进 (Core Improvements)

- **推理内容统一归一化**: 同时兼容 LangChain OpenAI 的两条 streaming 路径（Chat Completions vs Responses API），统一将推理内容写入 `AIMessageChunk.additional_kwargs["reasoning_content"]`
- **向后兼容增强**: 兼容 LangChain v0 compat 格式（`additional_kwargs["reasoning"]` 为 dict），自动提取并转换为 `reasoning_content` 字符串

##### 🔧 技术实现 (Technical Changes)

- **推理内容归一化中枢** (`backend/app/core/chat_models/base.py`):
  - 覆盖 `_convert_chunk_to_generation_chunk`：对 Chat Completions streaming 的 raw dict chunk 注入 `reasoning_content`
  - 覆盖 `_stream_responses` / `_astream_responses`：对 Responses API streaming 的产物做后处理注入，避免路径 B 绕过注入点
  - 提供可选覆盖钩子 `_extract_reasoning_content`：允许平台特定提取逻辑扩展，但默认同时支持 `reasoning` / `reasoning_content`
  - 补充特别详细的数据结构说明：解释两条路径的原始/中间/最终结构与前因后果，降低维护成本

- **去冗余且保留兼容** (`backend/app/core/chat_models/providers/*.py`):
  - `OpenAIReasoningChatModel` 与 `ReasoningContentChatModel` 保留类名与导入路径，但提取逻辑统一委托给基类默认实现，减少重复代码

##### 🧩 SSE 事件职责拆分与清晰化 (SSE Middleware Responsibility)

- **职责拆分**: `LoggingMiddleware` 仅负责 logger 记录，不再发送 `llm.call.start/end` SSE 事件；对应 SSE 事件由 `SSEMiddleware` 统一负责
- **文件命名澄清**: 将 LLM 调用级别 SSE 中间件实现明确为 `llm_call_sse.py`，并更新引用与文档（删除旧 `sse_events.py`）

##### ✅ 测试 (Tests)

- 新增并恢复单测：
  - `tests/test_reasoning_content_injection.py`: 覆盖 Chat Completions（`reasoning`/`reasoning_content`）、Responses content blocks、v0 compat dict 解析与不覆写行为
  - `tests/test_llm_call_sse_middleware.py`: 覆盖 SSEMiddleware 成功/异常路径的 start/end 事件
  - 更新 `tests/test_llm_logging_middleware.py`: 断言 LoggingMiddleware 不 emit SSE 事件

### 2025-12-17 18:00 (UTC+08:00)

#### 🔧 日志与序列化优化 (Logging & Serialization Improvements)

##### ✨ 核心改进 (Core Improvements)

- **ChatContext 重构**: 将 `ChatContext` 从 `@dataclass` 重构为 Pydantic `BaseModel`，解决 Pydantic 序列化警告
- **日志记录增强**: 优化工具调用日志记录，确保 `tool_calls.items` 完整显示，避免深层嵌套被截断
- **工具函数签名优化**: 使用 `Annotated` 类型注解改进工具函数参数，提升代码清晰度和类型安全

##### 🔧 技术实现 (Technical Changes)

- **ChatContext 重构** (`backend/app/services/streaming/context.py`):
  - 从 `@dataclass(frozen=True, slots=True)` 改为 Pydantic `BaseModel`
  - 使用 `Field(exclude=True, repr=False)` 排除 `emitter` 字段的序列化
  - 配置 `ConfigDict` 支持 `arbitrary_types_allowed=True` 和 `frozen=True`
  - 解决 LangChain 内部序列化 `ModelRequest`/`ToolRuntime` 时的 Pydantic 警告

- **日志记录优化** (`backend/app/core/logging.py`, `backend/app/services/agent/middleware/logging.py`):
  - 移除 `ChatContext` 的特殊处理逻辑，直接使用 Pydantic 的 `model_dump()` 方法
  - 增强 `_summarize_tool_calls` 函数，添加 `args_preview` 显示参数预览
  - 新增 `_ensure_serializable` 函数，确保对象完全序列化为基本类型
  - 调整 `_safe_for_logging` 函数，增加深度限制并特殊处理 `tool_calls.items`
  - 在日志记录前完全序列化 `response_data`，避免嵌套结构被截断

- **工具函数改进** (`backend/app/services/agent/tools/`):
  - 所有工具函数使用 `Annotated` 类型注解替代简单类型
  - 简化工具启动和结束事件的记录逻辑
  - 删除不必要的输入模式类，精简代码库
  - 增强错误处理和日志记录

##### 🐛 Bug 修复 (Bug Fixes)

- 修复 `tool_calls.items` 在日志中显示为 `['...']` 的问题
- 修复 Pydantic 序列化警告：`PydanticSerializationUnexpectedValue(Expected 'none' - serialized value may not be as expected [field_name='context'])`

##### 📝 代码质量 (Code Quality)

- 改进类型注解，提升代码可读性和 IDE 支持
- 统一日志记录格式，确保关键信息完整显示
- 优化序列化逻辑，避免深层嵌套导致的日志截断

---

## [0.1.3] - 2025-12-17

### 🔄 多 LLM 提供商支持 (Multi-Provider Support)

#### ✨ 核心改进 (Core Improvements)

- **多提供商架构**: 重构配置系统，支持 OpenAI、Anthropic、DeepSeek、SiliconFlow 等多个 LLM 提供商
- **统一配置接口**: 使用通用的 `LLM_*` 配置变量替代平台特定的 `SILICONFLOW_*` 变量
- **灵活混合配置**: 支持为 LLM、Embeddings、Rerank 使用不同的提供商，优化成本和性能
- **自动迁移工具**: 提供 `migrate_env.py` 脚本，自动迁移旧配置到新格式

#### 🔧 技术实现 (Technical Changes)

- **配置层重构** (`backend/app/core/config.py`):
  - 新增 `LLM_PROVIDER`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_CHAT_MODEL`
  - 新增 `EMBEDDING_PROVIDER`、`RERANK_PROVIDER` 支持独立配置
  - 添加 `effective_*` 属性方法，自动回退到主配置
  
- **Chat Models 重构** (`backend/app/core/chat_models/`):
  - 重命名 `providers/siliconflow.py` → `providers/reasoning_content.py`
  - 按推理字段类型分类而非平台名称
  - 更新注册机制，支持多平台自动匹配

- **核心模块更新**:
  - `backend/app/core/llm.py`: 支持多提供商初始化
  - `backend/app/core/rerank.py`: 通用化 Rerank 客户端
  - `backend/app/core/models_dev.py`: 支持动态 provider_id

#### 📝 配置变更 (Configuration Changes)

**旧配置格式**:
```bash
SILICONFLOW_API_KEY=sk-xxx
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_CHAT_MODEL=moonshotai/Kimi-K2-Instruct
```

**新配置格式**:
```bash
LLM_PROVIDER=siliconflow
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_CHAT_MODEL=moonshotai/Kimi-K2-Instruct
```

#### 🛠️ 迁移指南 (Migration Guide)

1. **自动迁移** (推荐):
   ```bash
   cd backend
   python migrate_env.py
   ```

2. **手动迁移**:
   - 将所有 `SILICONFLOW_*` 变量重命名为对应的通用变量
   - 添加 `LLM_PROVIDER=siliconflow`
   - 参考 `backend/.env.example` 查看完整配置

#### 📚 文档更新 (Documentation)

- 更新 `README.md` 添加多提供商配置说明和示例
- 更新 `backend/app/core/chat_models/README.md` 反映新架构
- 创建 `backend/.env.example` 提供配置模板

#### ⚠️ 破坏性变更 (Breaking Changes)

- 所有 `SILICONFLOW_*` 环境变量已废弃，需要迁移到新的通用变量
- 旧配置文件不兼容，必须使用迁移脚本或手动更新

#### 🎯 优势 (Benefits)

- **灵活性**: 轻松切换不同 LLM 提供商
- **成本优化**: 为不同功能选择性价比最高的提供商
- **可扩展性**: 添加新提供商只需最小改动
- **供应商独立**: 不被单一供应商锁定

---

## [0.1.3] - 2025-12-16

### 🚀 检索与推荐能力增强 (Retrieval Improvements)

- **增强检索链路**: 新增混合检索策略（向量检索 + 关键词过滤 + 相关性重排序）
- **Rerank 重排序**: 对接 Rerank API，失败自动回退本地打分；新增配置项 `RERANK_*`

### 🧠 意图识别与工具选择 (Intent & Tooling)

- **意图识别中间件**: 基于规则识别意图，动态过滤可用工具，并注入意图上下文提示
- **结构化意图模型**: 新增 `IntentAnalysis` / `IntentType` / `INTENT_TO_TOOLS`
- **工具体系模块化**: 原 `tools.py` 拆分为 `tools/` 包（`search_products` / `get_product_details` / `compare_products` / `filter_by_price`）并补充说明文档

### 🛑 流式对话可中断 (Streaming Abort)

- **前端支持停止生成**: `AbortController` + UI “停止”按钮；中断后移除未完成的 assistant 消息
- **后端中断检测**: 通过 `request.is_disconnected()` / `CancelledError` 及时停止生成，且不落库不完整消息
- **数据库会话稳定性**: 取消/异常路径 rollback 更稳健，避免二次异常

### 🔧 工程与可观测性 (Engineering)

- **日志稳定性增强**: 复杂对象安全序列化，修复 loguru enqueue/pickle 问题；异常栈转义；日志 file 路径显示为相对路径

#### ⚠️ 行为变更 (Behavior Changes)

- 客户端主动中断后，后端不会保存未完成的 assistant 消息（前端已同步适配）

## [0.1.2] - 2025-12-16

### 🔧 技术改进 (Technical Improvements)

- **版本管理脚本优化**: 修复 `version.sh` 脚本语法问题，替换为更稳定的 Python 版本管理脚本 `update_version.py`
- **构建系统改进**: 优化版本自动更新流程，提高发布效率

## [0.1.1] - 2025-12-16

### 🚀 架构重构：SSE事件系统职责分离

#### ✨ 核心改进 (Core Improvements)

- **统一流式事件协议**: 新增 `StreamEvent` envelope，支持版本化扩展
- **职责分离架构**: Agent业务逻辑、事件编排、SSE传输完全解耦
- **Context事件注入**: 工具和中间件可实时emit事件，实现多源事件合流
- **类型安全提升**: 事件类型枚举化，减少魔法字符串，提高可维护性

#### 🔧 技术实现 (Technical Changes)

- **新增模块**:
  - `backend/app/schemas/events.py`: 事件类型枚举与payload类型定义
  - `backend/app/schemas/stream.py`: 统一流式事件协议
  - `backend/app/services/streaming/`: SSE编解码与Context注入
  - `backend/app/services/chat_stream.py`: 聊天流编排核心

- **重构模块**:
  - `backend/app/services/agent/`: 输出domain events而非SSE格式
  - `backend/app/routers/chat.py`: 简化路由层职责
  - `frontend/types/chat.ts`: 协议类型升级，支持判别联合
  - `frontend/hooks/use-chat.ts`: 适配新事件渲染逻辑

#### 📡 事件协议升级 (Event Protocol)

- **新增事件类型**:
  - `meta.start`: 流开始，提供message_id对齐
  - `assistant.delta`: 文本增量
  - `assistant.reasoning.delta`: 推理内容增量
  - `assistant.products`: 商品数据
  - `assistant.final`: 最终完整状态
  - `tool.start/end`: 工具执行状态
  - `llm.call.start/end`: LLM调用状态

- **协议特性**:
  - 统一envelope: `v/id/seq/ts/conversation_id/message_id/type/payload`
  - 版本化支持: `v`字段预留协议升级空间
  - 类型安全: 前端TypeScript判别联合自动推导payload结构

#### 🏗️ 架构优势 (Architecture Benefits)

- **可扩展性**: 新增事件类型只需在枚举中添加，无需改动传输层
- **职责清晰**: Agent专注业务，编排层专注聚合，传输层专注SSE
- **实时性**: 工具执行状态可实时推送到前端，提升用户体验
- **一致性**: 前端显示与后端存储使用相同message_id

#### ⚠️ 破坏性变更 (Breaking Changes)

- 事件协议升级，前端需同步更新类型定义
- 部分内部API签名调整（向后兼容）

---

## [0.1.0] - 2025-12-12

### 🎉 初始版本发布

#### 📥 数据嵌入角度 (Data Embedding)

- **商品向量化存储**
  - 商品描述智能分块处理 (RecursiveCharacterTextSplitter)
  - Qdrant 向量数据库
  - 支持商品元数据关联 (名称、价格、URL等)

- **嵌入流程**
  ```
  JSON商品数据 → 文本分块 → 向量嵌入 → Qdrant存储
      ↓            ↓          ↓          ↓
   商品描述 → chunk_size=1000 → 嵌入模型 → collection=products
  ```

#### 🔍 查询意图角度 (Query Intent)

- **智能推荐流程**
  ```
  用户查询 → Agent推理 → 工具调用 → 向量相似度 → 商品推荐 → 流式回复
     ↓         ↓         ↓         ↓            ↓         ↓
  "降噪耳机" → 意图识别 → search_products → k=5检索 → 生成回复 → SSE推送
  ```

#### ✨ 核心功能 (Features)

- **对话系统**: 匿名用户 + 会话历史 + 流式回复
- **推荐引擎**: 向量检索 + 智能排序 + 商品卡片展示
- **技术栈**: FastAPI + Next.js + LangChain + Qdrant

#### 🏗️ 架构设计 (Architecture)

- **后端**: Python 3.13 + FastAPI + LangGraph + SQLite
- **前端**: Next.js 15 + React + TypeScript + Tailwind
- **AI**: LangChain v1.1 + Qdrant

---
