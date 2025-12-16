# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
