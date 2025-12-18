# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [0.1.4] - 2025-12-17

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
