# 🚀 新用户快速上手指南

欢迎使用 EmbedeaseAI！本指南将帮助你在 **5 分钟内**完成项目配置并运行。

## 📋 前置要求

### 必需
- ✅ **Docker** 和 **Docker Compose**（推荐使用 Docker Desktop）
- ✅ **LLM API Key**（任选其一）：
  - [SiliconFlow](https://siliconflow.cn)（推荐，国内快速便宜）
  - [OpenAI](https://platform.openai.com)
  - [DeepSeek](https://platform.deepseek.com)
  - 其他兼容 OpenAI API 格式的服务

### 可选
- Node.js 18+ 和 pnpm（仅本地开发需要）
- Python 3.13+ 和 uv（仅本地开发需要）

---

## 🎯 快速开始（推荐）

### 步骤 1：克隆项目

```bash
git clone https://github.com/你的账号/embedease-ai.git
cd embedease-ai
```

### 步骤 2：配置后端环境变量

```bash
cd backend
cp .env.example .env
```

**编辑 `backend/.env` 文件，只需配置以下 4 项：**

```bash
# 1. LLM 提供商（选择一个）
LLM_PROVIDER=siliconflow  # 或 openai、deepseek

# 2. API Key（必填）
LLM_API_KEY=sk-your-api-key-here

# 3. API 地址
LLM_BASE_URL=https://api.siliconflow.cn/v1

# 4. 模型名称
LLM_CHAT_MODEL=moonshotai/Kimi-K2-Thinking
```

> 💡 **提示**：其他配置项都有合理的默认值，可以稍后再调整。

### 步骤 3：配置 JSON 目录（可选，按需使用）

**⚠️ 重要说明**：`.env.json` 目录是**可选的**，仅在需要以下功能时才需要配置：

#### 何时需要配置 `.env.json` 目录？

| 功能 | 是否需要 | 说明 |
|------|---------|------|
| **基础对话功能** | ❌ 不需要 | 使用 `.env` 默认配置即可 |
| **覆盖模型能力** | ✅ 需要 | 当 models.dev 数据不准确时 |
| **配置爬虫站点** | ✅ 需要 | 启用网站爬虫功能时 |
| **自定义 Agent** | ✅ 需要 | 需要预置多个 Agent 时 |
| **多域名 CORS** | ✅ 需要 | 需要配置多个跨域源时 |

#### 如何配置？

**步骤 1：创建目录**
```bash
# 在 backend 目录下
mkdir .env.json
```

**步骤 2：按需复制配置文件**

**⚠️ 不要直接复制整个目录！** 示例文件中的值仅供参考，不能直接使用。

```bash
# 仅在需要时复制对应的文件

# 1. 如果需要覆盖模型能力配置
cp .env.json.example/MODEL_PROFILES_JSON.json .env.json/
# 然后编辑 .env.json/MODEL_PROFILES_JSON.json，填写你的模型配置

# 2. 如果需要配置爬虫
cp .env.json.example/CRAWLER_SITES_JSON.json .env.json/
# 然后编辑 .env.json/CRAWLER_SITES_JSON.json，填写你的站点信息

# 3. 如果需要预置 Agent
cp .env.json.example/DEFAULT_AGENTS_JSON.json .env.json/
# 然后编辑 .env.json/DEFAULT_AGENTS_JSON.json，配置你的 Agent

# 4. 如果需要配置多个 CORS 源
cp .env.json.example/CORS_ORIGINS.json .env.json/
# 然后编辑 .env.json/CORS_ORIGINS.json，添加你的域名
```

**步骤 3：启用目录加载**

在 `backend/.env` 中添加：
```bash
ENV_JSON_DIR=.env.json
```

**💡 提示**：
- 如果不配置 `.env.json` 目录，系统会使用 `.env` 中的配置或默认值
- 每个 JSON 文件都有详细的 README 说明，复制后请查看对应的 `.README.md` 文件
- 详细说明请查看 [backend/.env.json.example/README.md](backend/.env.json.example/README.md)

### 步骤 4：启动服务

```bash
# 回到项目根目录
cd ..

# 启动 Qdrant 向量数据库和 MinIO（开发环境）
docker compose up -d
```

**等待服务启动**（约 30 秒），然后验证：

```bash
# 检查 Qdrant 是否运行
curl http://localhost:6333/healthz
# 应该返回：{"title":"healthz","version":"1.x.x"}

# 检查 MinIO 是否运行
curl http://localhost:9000/minio/health/live
# 应该返回：200 OK
```

### 步骤 5：启动后端服务

```bash
cd backend

# 安装依赖（首次运行）
uv sync

# 导入示例商品数据
uv run python scripts/import_products.py

# 启动后端
uv run uvicorn app.main:app --reload --port 8000
```

**验证后端**：访问 http://localhost:8000/docs 查看 API 文档

### 步骤 6：启动前端服务

**新开一个终端**：

```bash
cd frontend

# 安装依赖（首次运行）
pnpm install

# 启动前端
pnpm dev
```

### 步骤 7：开始使用

访问以下地址：

| 地址 | 用途 |
|------|------|
| http://localhost:3000 | 💬 对话界面 |
| http://localhost:3000/admin/quick-setup | 🎯 一站式引导（推荐首次使用） |
| http://localhost:3000/admin | ⚙️ 管理后台 |
| http://localhost:8000/docs | 📄 API 文档 |

---

## ⚡ 必需配置项（仅 4 项，必须填写）

---

### 1. LLM 配置（必填）

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `LLM_PROVIDER` | LLM 服务商 | `siliconflow` |
| `LLM_API_KEY` | API 密钥 | `sk-xxxxx` |
| `LLM_BASE_URL` | API 地址 | `https://api.siliconflow.cn/v1` |
| `LLM_CHAT_MODEL` | 聊天模型 | `moonshotai/Kimi-K2-Thinking` |

#### 推荐配置方案

**方案一：SiliconFlow（推荐国内用户）**
```bash
LLM_PROVIDER=siliconflow
LLM_API_KEY=sk-your-siliconflow-key
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_CHAT_MODEL=moonshotai/Kimi-K2-Thinking
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
```

**方案二：OpenAI**
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-openai-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_CHAT_MODEL=gpt-4
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSION=3072
```

**方案三：DeepSeek**
```bash
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_CHAT_MODEL=deepseek-chat
EMBEDDING_MODEL=deepseek-embedding
EMBEDDING_DIMENSION=1536
```

### 2. 数据库配置（使用默认值即可）

默认使用 SQLite，零配置：

```bash
DATABASE_BACKEND=sqlite
DATABASE_PATH=./data/app.db
```

如需使用 PostgreSQL（生产环境推荐）：

```bash
DATABASE_BACKEND=postgres
# 启动 PostgreSQL: docker compose --profile postgres up -d
```

### 3. 向量数据库配置（使用默认值即可）

```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

---

---

---

## 🎨 可选配置项（都有默认值，可稍后调整）

---

**以下所有配置都有合理的默认值，新用户无需修改即可运行。**

根据实际需求，可以稍后调整：

### 记忆系统

```bash
MEMORY_ENABLED=true  # 启用记忆系统
```

### Agent 中间件

```bash
AGENT_TODO_ENABLED=true              # TODO 规划
AGENT_SUMMARIZATION_ENABLED=true     # 上下文压缩
AGENT_TOOL_RETRY_ENABLED=true        # 工具重试
AGENT_TOOL_LIMIT_ENABLED=true        # 工具调用限制
```

### 网站爬虫

```bash
CRAWLER_ENABLED=false  # 默认关闭，需要时启用
```

### 图片上传

```bash
MINIO_ENABLED=false  # 默认关闭，需要时启用
# 启用后需要启动 MinIO: docker compose up -d minio
```

---

## 📂 配置文件结构

```
backend/
├── .env                    # 主配置文件（必需，包含敏感信息）
├── .env.example            # 配置示例（Git 管理）
├── .env.json/              # JSON 配置目录（可选但推荐）
│   ├── MODEL_PROFILES_JSON.json      # 模型能力配置
│   ├── CRAWLER_SITES_JSON.json       # 爬虫站点配置
│   ├── DEFAULT_AGENTS_JSON.json      # Agent 配置
│   └── CORS_ORIGINS.json             # CORS 配置
└── .env.json.example/      # JSON 配置示例
    └── README.md           # 详细说明
```

### 配置优先级

```
.env 环境变量 > .env.json 目录文件 > 默认值
```

---

## ✅ 验证配置

### 1. 检查服务状态

```bash
# 检查 Docker 服务
docker compose ps

# 应该看到 qdrant 和 minio 运行中
```

### 2. 检查后端健康

```bash
curl http://localhost:8000/health
```

应该返回：
```json
{
  "status": "healthy",
  "qdrant": "connected",
  "database": "connected"
}
```

### 3. 测试对话功能

访问 http://localhost:3000，尝试发送消息：
- "帮我推荐一款耳机"
- "3000 元以内的笔记本"

---

## 🎯 下一步

### 1. 配置 Agent（推荐使用一站式引导）

访问 http://localhost:3000/admin/quick-setup

系统会引导你：
1. 选择 Agent 类型（商品推荐/FAQ/知识库）
2. 配置数据源（导入商品/添加 FAQ/上传文档）
3. 设置开场白和推荐问题

### 2. 导入商品数据

**方式一：使用示例数据**
```bash
cd backend
uv run python scripts/import_products.py
```

**方式二：批量导入**
- 访问管理后台 → 商品管理 → 批量导入
- 上传 CSV/JSON 文件

**方式三：配置爬虫**
- 访问管理后台 → 爬虫管理
- 添加站点并配置爬取规则

### 3. 嵌入到你的网站

```bash
# 构建嵌入组件
cd frontend
pnpm build:embed
```

然后在你的网站中引入：
```html
<script
  src="https://your-cdn.com/embedeaseai-chat.js"
  data-auto-init
  data-api-base-url="https://your-backend.com">
</script>
```

---

## 🐛 常见问题

### Q1: 启动后端时报错 "Qdrant connection failed"

**原因**：Qdrant 服务未启动

**解决**：
```bash
docker compose up -d qdrant
# 等待 30 秒后重试
```

### Q2: LLM 调用失败

**原因**：API Key 无效或网络问题

**解决**：
1. 检查 `LLM_API_KEY` 是否正确
2. 检查 `LLM_BASE_URL` 是否可访问
3. 查看后端日志获取详细错误

### Q3: 前端无法连接后端

**原因**：CORS 配置问题

**解决**：
在 `backend/.env` 中添加：
```bash
CORS_ORIGINS=http://localhost:3000
```

### Q4: 找不到商品

**原因**：未导入商品数据

**解决**：
```bash
cd backend
uv run python scripts/import_products.py
```

### Q5: 配置文件修改后不生效

**原因**：未重启服务

**解决**：
```bash
# 重启后端
Ctrl+C 停止，然后重新运行 uvicorn

# 重启前端
Ctrl+C 停止，然后重新运行 pnpm dev
```

---

## 📚 进阶配置

### 使用 PostgreSQL（生产环境推荐）

```bash
# 1. 启动 PostgreSQL
docker compose --profile postgres up -d

# 2. 修改 backend/.env
DATABASE_BACKEND=postgres

# 3. 重启后端服务
```

### 启用企业微信通知

```bash
# 在 backend/.env 中配置
WEWORK_CORP_ID=your-corp-id
WEWORK_AGENT_ID=your-agent-id
WEWORK_AGENT_SECRET=your-secret
WEWORK_NOTIFY_USERS=@all
```

### 配置多个 Agent

访问管理后台 → Agent 管理 → 创建 Agent

或编辑 `backend/.env.json/DEFAULT_AGENTS_JSON.json`

---

## 📖 更多文档

- [完整配置说明](backend/.env.example) - 所有配置项的详细说明
- [JSON 配置指南](backend/.env.json.example/README.md) - JSON 配置文件使用方法
- [API 文档](http://localhost:8000/docs) - 后端 API 接口文档
- [项目 README](README.md) - 项目完整介绍

---

## 💡 提示

1. **配置文件不要提交到 Git**
   - `.env` 包含敏感信息，已在 `.gitignore` 中
   - `.env.json/` 目录也已忽略

2. **使用 .env.json 目录**
   - 复杂 JSON 配置建议使用文件而非环境变量
   - 支持注释和格式化，更易维护

3. **查看日志排查问题**
   ```bash
   # 后端日志
   tail -f backend/logs/app.log
   
   # Docker 日志
   docker compose logs -f
   ```

4. **定期备份数据**
   ```bash
   # 备份数据库和向量库
   ./scripts/backup.sh
   ```

---

## 🎉 开始使用

配置完成后，访问 http://localhost:3000/admin/quick-setup 开始配置你的第一个 Agent！

如有问题，请查看 [常见问题](#-常见问题) 或提交 Issue。
