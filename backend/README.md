# 商品推荐 Agent 后端

基于 LangChain v1.1 + FastAPI + Qdrant 的智能商品推荐系统后端。

## 快速开始

### 1. 安装依赖

```bash
cd backend
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的硅基流动 API Key
```

### 3. 确保 Qdrant 运行中

```bash
# Qdrant 应该在 localhost:6333 运行
docker ps | grep qdrant
```

### 4. 导入商品数据

```bash
uv run python scripts/import_products.py
```

### 5. 启动服务

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 6. 代码检查

```bash
uv run ruff check --fix
```

## API 接口

### 健康检查

```
GET /health
```

### 用户

```
POST /api/v1/users           # 创建匿名用户
GET  /api/v1/users/{user_id} # 获取用户信息
```

### 会话

```
GET    /api/v1/conversations?user_id=xxx  # 获取用户会话列表
POST   /api/v1/conversations              # 创建新会话
GET    /api/v1/conversations/{id}         # 获取会话详情
DELETE /api/v1/conversations/{id}         # 删除会话
```

### 聊天

```
POST /api/v1/chat  # 流式聊天（SSE）
```

## 目录结构

```
backend/
├── app/
│   ├── core/           # 核心配置
│   ├── models/         # SQLAlchemy 模型
│   ├── schemas/        # Pydantic 模型
│   ├── repositories/   # 数据访问层
│   ├── services/       # 业务逻辑层
│   │   └── agent/      # Agent 相关
│   ├── routers/        # API 路由
│   └── utils/          # 工具函数
├── scripts/            # 脚本
├── data/               # 数据文件
└── tests/              # 测试
```

## 技术栈

- **FastAPI**: Web 框架
- **LangChain v1.1**: AI Agent 框架
- **LangGraph**: 状态图管理
- **SQLite**: 数据库
- **Qdrant**: 向量数据库
- **硅基流动**: LLM + Embedding API
