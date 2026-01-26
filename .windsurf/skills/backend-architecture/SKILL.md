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
│   ├── core/           # 核心模块（配置、数据库、LLM、日志）
│   ├── models/         # SQLAlchemy 数据模型
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
| **LLM** | `llm.py` | ChatOpenAI/Embeddings 初始化 |
| **日志** | `logging.py` | Loguru 结构化日志 |
| **健康检查** | `health.py`, `health_checks.py` | 依赖健康状态 |
| **错误处理** | `errors.py` | 统一异常类和错误响应 |
| **依赖注入** | `dependencies.py` | FastAPI 依赖（DB Session 等）|

## 数据模型 (app/models/)

| 模型 | 文件 | 说明 |
|------|------|------|
| `Agent` | `agent.py` | 智能体配置 |
| `Conversation` | `conversation.py` | 会话 |
| `Message` | `message.py` | 消息 |
| `User` | `user.py` | 用户 |
| `KnowledgeBase/Document` | `knowledge.py` | 知识库 |
| `FAQItem` | `faq.py` | FAQ 条目 |
| `AppMetadata` | `app_metadata.py` | 键值存储（系统配置）|

## 业务服务 (app/services/)

### Agent 服务 (`services/agent/`)

多智能体系统核心：

```
agent/
├── core/           # 核心服务
│   ├── service.py      # AgentService 主入口
│   ├── graph.py        # LangGraph 图构建
│   ├── config.py       # Agent 配置管理
│   ├── intent.py       # 意图识别
│   └── policy.py       # 路由策略
├── middleware/     # 中间件
│   ├── llm_monitor.py  # LLM 调用监控
│   ├── strict_mode.py  # 严格模式
│   └── memory_inject.py # 记忆注入
├── retrieval/      # 检索服务
│   ├── product.py      # 商品向量检索
│   ├── knowledge.py    # 知识库检索
│   └── faq.py          # FAQ 检索
├── streams/        # 流式响应
│   ├── response_handler.py # 响应处理
│   └── sse_builder.py      # SSE 构建
├── tools/          # 工具定义
│   ├── product/        # 商品工具
│   ├── knowledge/      # 知识库工具
│   └── common/         # 通用工具
└── bootstrap.py    # 默认 Agent 初始化
```

### 其他服务

| 服务 | 目录/文件 | 职责 |
|------|-----------|------|
| **会话** | `conversation.py` | 会话 CRUD、消息管理 |
| **聊天流** | `chat_stream.py` | SSE 流式响应 |
| **记忆** | `memory/` | 用户记忆存储（短期/长期）|
| **知识库** | `knowledge/` | 知识库管理、文档解析 |
| **爬虫** | `crawler/` | 网站内容爬取 |
| **OCR** | `ocr/` | 图片文字识别 |
| **存储** | `storage/` | MinIO 对象存储 |
| **WebSocket** | `websocket/` | 实时通信 |
| **客服** | `support/` | 人工客服转接 |
| **系统配置** | `system_config.py` | LLM/Embedding/Rerank 动态配置 |

## API 路由 (app/routers/)

| 路由 | 前缀 | 说明 |
|------|------|------|
| `admin.py` | `/api/v1/admin` | 后台管理 |
| `system_config.py` | `/api/v1/admin/system-config` | 系统配置 |
| `chat.py` | `/api/v1/chat` | 聊天 API |
| `conversations.py` | `/api/v1/conversations` | 会话管理 |
| `agents/` | `/api/v1/agents` | Agent CRUD |
| `quick_setup.py` | `/api/v1/quick-setup` | 快速配置向导 |
| `health.py` | `/api/v1/health` | 健康检查 |
| `ws.py` | `/ws` | WebSocket |

## 调度器 (app/scheduler/)

APScheduler 定时任务：

| 模块 | 文件 | 职责 |
|------|------|------|
| **调度器** | `scheduler.py` | 任务调度器 |
| **注册表** | `registry.py` | 任务注册 |
| **任务** | `tasks.py` | 爬虫定时任务 |

## 数据流

```
用户请求 → FastAPI Router → Service → Repository → Database
                ↓
           Agent 服务 → LangGraph → LLM
                ↓
           工具调用 → 检索服务 → Qdrant/知识库
                ↓
           SSE 流式响应
```

## 配置优先级

系统配置（LLM_API_KEY 等）优先级：**数据库 > 环境变量**

通过 `SystemConfigService` 管理动态配置，支持后台管理界面修改。

## 测试

```bash
# 运行所有测试
uv run pytest

# 运行特定模块测试
uv run pytest tests/services/test_system_config.py -v
```
