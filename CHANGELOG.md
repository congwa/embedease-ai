# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Changed

- **事实型长期记忆**：
  - `FactMemoryService` 写入阶段同时更新 SQLite（元数据 + 历史记录）与 Qdrant 向量；检索阶段改为调用 Qdrant `similarity_search_with_score`，并在失败时自动回退至关键词搜索。
  - `update_fact` / `delete_fact` 同步维护 Qdrant 向量数据，确保与 SQLite 状态一致。
  - `Fact` 数据模型移除本地 `embedding` 字段，由 Qdrant 负责托管向量，避免重复存储与手工余弦计算。
- **记忆检索阈值语义** (`backend/app/core/config.py`, `backend/app/services/memory/fact_memory.py`)：将 `MEMORY_FACT_SIMILARITY_THRESHOLD` 明确为“距离阈值（越小越相似）”，检索逻辑改为过滤距离大于阈值的结果，与 Qdrant 的 Distance 语义保持一致。
- **记忆编排中间件** (`backend/app/services/memory/middleware/orchestration.py`)：
  - 新增 `MemoryWriteResult` 结构，统一记录事实/实体/关系写入统计及错误信息。
  - 将记忆写入流程从 `awrap_model_call` 挪至 `aafter_agent` 钩子，仅在整轮 Agent 结束后执行一次，避免多次重复写入并保证抽取使用独立 LLM 调用。
  - 增加 SSE 通知包装器，在记忆抽取开始与完成时通过 `StreamEventType` 向前端发送实时状态（含耗时与写入数量），支持同步/异步两种执行模式。
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
