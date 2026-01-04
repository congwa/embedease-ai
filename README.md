# 商品推荐 Agent（Look & Run in 5 Minutes）

[演示动图](http://qiniu.biomed168.com/agent0.gif)

![演示动图](http://qiniu.biomed168.com/agent0.gif)

## 1. TL;DR

| 我是谁 | 我能做什么 | 怎么跑起来 |
| :---- | :--------- | :--------- |
| 基于 **LangChain v1.1 + LangGraph** 的「商品推荐 Agent」一体化工程（后端 FastAPI，前端 Next.js 15） | 多 LLM Provider 推理、记忆系统、上下文压缩、SSE 时间线、Todo & 商品卡片混合流式展示 | 准备 `.env` → `uv sync && uvicorn`（后端）+ `pnpm dev`（前端）→ 打开 `http://localhost:3000` |

---

## 2. 它到底能做什么？（用人话讲清楚）

1. **像客服一样陪聊**：你问“帮我找 3000 元以内的轻薄本”，它会先跟你澄清需求，再把候选商品列表流式打出来，并解释为什么推荐它们。
2. **自动判断是否真的要查资料**：在“随便聊聊”和“务必给事实依据”之间自由切换——`natural` 更随和、`strict` 会强制调用工具，尽量不给“我猜是…”.
3. **自己总结上一轮聊了啥**：对话里超过阈值就自动压缩上下文，把重点用卡片推到前端，防止模型忘记关键要求。
4. **记住用户偏好**：同一个用户 ID 多轮对话后，会存下预算、品类、品牌、语气等画像，下次开场就能 “记得你上次说想买苹果生态”的感觉。
5. **同步 Todo / 推理过程**：当 Agent 决定“先去查库存再比较价格”时，前端时间线会蹦出 TODO 卡；推理文本与最终回答分开，让你知道它现在在想什么。
6. **随时切换模型/成本**：一个 `.env` 就能决定用 OpenAI 还是国产模型，还能把 embedding/rerank 指到另一家服务，满足“老板要省钱”或“我要最强模型”的不同需求。
7. **可追溯的工具调用与消息状态**：LangGraph state dump 到数据库，tool start/end、usage metadata、送达/已读、在线状态通通持久化，历史页、Dashboard、客服面板都能直接复用。

> 一句话：它不仅会回话，还会自己组织步骤、记录偏好、把过程摊在阳光下，适合作为商品导购 / 复杂比较任务的基础工程。

## 3. 功能速览（后端 × 前端）

| 模块 | 能力点 | 说明 |
| --- | --- | --- |
| **LLM/推理** | 多 Provider & 多态推理模型 | 统一 `ReasoningChunk`，按 provider（OpenAI / SiliconFlow / DeepSeek…）自动选择实现 |
| **对话模式** | `natural / free / strict` | 通过 `ToolPolicy` + 中间件约束工具调用次数、允许直答或失败兜底 |
| **流式体验** | SSE + WebSocket 时间线、推理/正文拆流 | `llm.call.*`、`assistant.reasoning.delta`、`assistant.todos` 等事件驱动前端时序卡片，嵌入式组件改用 WebSocket 长连 |
| **工具链路可视化** | LangGraph state dump + `tool_calls` 表 | AI/Tool 消息含完整参数、输入/输出、耗时、状态，便于历史回放、Token 统计、Dashboard |
| **中间件编排** | Summarization / Todo / Sequential Tools | 配置驱动注入，支持上下文压缩广播、待办推送、串行工具执行 |
| **客服协作** | 双端在线状态 + 人工介入 | 记录消息送达/已读/在线状态，客服切换走统一 WebSocket 广播，支持企业微信/Webhook 通知 |
| **记忆系统** | 用户画像 + 事实 + 图谱 + Orchestration | LangGraph Store / SQLite / Qdrant 多层记忆，附带 SSE 进度事件 |
| **商品体验** | 商品向量检索 + 卡片展示 | 标配 `search_products` 工具、Qdrant 检索、前端商品网格 |
| **配置/诊断** | `.env` 全量示例、结构化日志、Swagger | `backend/.env.example` 覆盖所有开关，`/docs` 自动文档，日志支持 simple/detailed/json |

---

## 3. 架构长什么样？

```
┌──────────┐    SSE / REST    ┌─────────────┐    LLM / 向量 / KV
│ Frontend │ ◀──────────────▶ │   Backend   │ ◀─────────────────┐
│ Next.js  │    Timeline UI   │ FastAPI +   │                   │
│ Timeline │                  │ LangChain   │    ┌──────────┐   │
└──────────┘                  │ LangGraph   │    │ OpenAI   │   │
      ▲                       │ Agent + SSE │    │ DeepSeek │   │
      │                       └─────────────┘    │ Silicon… │   │
      │                             ▲            └──────────┘   │
      │                             │            ┌──────────┐   │
      │                      SQLite / Qdrant ◀── │  Qdrant  │ ◀─┘
      └────────── 用户 ↔️ 商品 ↔️ 中间件 ↔️ 记忆 ↔️ 推理 ↔️ SSE ──────────┘
```

---

## 4. 5 分钟跑通（真的就三步）

> **前置依赖**：Node ≥ 18、Python 3.13（项目使用 `uv`）、Qdrant（本地或远端）、LLM API Key

```bash
# ① Clone & 安装依赖
git clone https://github.com/你的账号/embedAi-agent.git
cd embedAi-agent

cd backend && uv sync        # 后端依赖
cd ../frontend && pnpm install  # 前端依赖

# ② 配环境
cd ../backend
cp .env.example .env          # 每个开关旁都写了注释，照填即可
# 最少需要 LLM_PROVIDER / LLM_API_KEY，若本地跑 Qdrant 记得确保 6333 端口在线

uv run python scripts/import_products.py  # ③ 导入商品样例

# ③ 启动
uv run uvicorn app.main:app --reload --port 8000    # 后端
cd ../frontend && pnpm dev                          # 前端
```

浏览器打开 **http://localhost:3000**，就能看到时间线式的对话 + 商品推荐界面。

---

## 5. 后端配置清单（最常用的几个）

| 配置 | 作用 | 示例 |
| --- | --- | --- |
| `LLM_PROVIDER` / `LLM_API_KEY` / `LLM_BASE_URL` | 指定推理 Model 来源 | `siliconflow` / `https://api.siliconflow.cn/v1` |
| `LLM_CHAT_MODEL` / `EMBEDDING_MODEL` | 主模型 + 向量模型 | `moonshotai/Kimi-K2-Thinking` / `Qwen/Qwen3-Embedding-8B` |
| `CHAT_MODE` | 默认对话模式 | `natural` / `free` / `strict` |
| `SUMMARIZATION_*` | 上下文压缩触发阈值/保留条数 | 默认在 `.env.example` 已写明 |
| `AGENT_TOOL_RETRY_*` / `AGENT_TOOL_LIMIT_*` | 工具重试与调用上限 | 防止模型疯狂调工具 |
| `MEMORY_*` | 事实/图谱/画像配置 | 控制 SQLite / Qdrant 存储位置、阈值 |

> 完整注释版请看 `backend/.env.example`，照抄即可。

---

## 6. 能力详情（想深入一点的同学看这里）

### 6.1 Agent 管线亮点

1. **多态推理模型**：`BaseReasoningChatModel` + `ReasoningChunk`，SSE 只依赖统一接口，换 provider 不动业务层。
2. **中间件矩阵**：
   - `SummarizationMiddleware` + `SummarizationBroadcastMiddleware`：压缩上下文并推送 `context.summarized` 事件。
   - `ToolRetry / ToolCallLimit / SequentialToolExecution`：从配置控制稳定性。
   - `TodoBroadcastMiddleware`：在工具调用里生成 TODO，前端以卡片渲染。
3. **记忆编排**：`Memory Orchestration Middleware` 串联画像、事实、图谱读写，全程 SSE 报告抽取进度。
4. **SSE 事件族**：`llm.call.start/end`、`assistant.reasoning.delta`、`tool.start/end`、`context.summarized`、`assistant.todos` … 与前端时间线一一对应。

### 6.2 前端体验

- **时间线式 Chat**：每个 LLM Call、推理段、正文段、工具卡、商品卡、Todos 都是独立组件，按事件插入/更新。
- **状态同步**：`use-timeline-reducer` 把 SSE 事件归并为统一 `TimelineItem`，支持倒回和补写。
- **UI 技术栈**：Next.js App Router、Tailwind、shadcn/ui、自定义 Prompt Kit 组件，PC/移动两端可用。
- **一键配置**：`.env.local` 只需要 `NEXT_PUBLIC_API_URL`，默认指向 `http://localhost:8000`。

---

## 7. 目录地图（看到名字就知道去哪改）

```
embedAi-agent/
├── backend/
│   ├── app/
│   │   ├── core/              # 配置、LLM 抽象、Reasoning 多态
│   │   ├── services/
│   │   │   ├── agent/         # Agent 主流程 & 中间件
│   │   │   └── memory/        # 画像/事实/图谱服务
│   │   ├── routers/           # FastAPI 路由 (chat/users/conversations/health)
│   │   ├── schemas/           # Pydantic Schema & SSE Payload
│   │   └── repositories/      # SQLite 访问层
│   ├── scripts/               # 商品导入、迁移脚本
│   ├── data/                  # 本地 SQLite、样例数据
│   └── tests/                 # 单测（覆盖 SSE、推理、工具等）
├── frontend/
│   ├── app/                   # Next.js 页面 & API 路由
│   ├── components/
│   │   ├── features/chat      # 时间线 UI
│   │   └── prompt-kit         # Prompt / Todo 复用组件
│   ├── hooks/                 # use-chat、use-timeline 等核心 Hook
│   └── lib/                   # API 封装、工具函数
└── docker-compose.yml         # 本地依赖（Qdrant 等）一键拉起
```

---

## 8. 常用命令 & 调试入口

| 场景 | 命令 |
| --- | --- |
| 后端开发 | `uv run uvicorn app.main:app --reload --port 8000` |
| 导入商品 | `uv run python scripts/import_products.py` |
| 后端测试 | `uv run pytest` 或 `make test`（按需） |
| 前端开发 | `pnpm dev` |
| 嵌入脚本打包 | `cd frontend && pnpm build:embed`（产物见 `frontend/dist/embed/embed-ai-chat.js`） |
| Lint / Format | `uv run ruff check .` / `pnpm lint`（或见各子目录 README） |
| API 文档 | `http://localhost:8000/docs` |

---

## 9. 嵌入任意网站（使用 `build:embed` 产物）

1. **构建脚本**
   ```bash
   cd frontend
   pnpm build:embed
   ```
   该命令会使用 `vite` + `embed/vite.config.ts` 将小组件打成单文件（IIFE），输出到 `frontend/dist/embed/embed-ai-chat.js`，并自动内联样式，方便直接托管到任意静态存储或 CDN。

2. **部署产物**
   - 将 `dist/embed/embed-ai-chat.js` 上传到你的静态资源服务（OSS、S3、Vercel、Cloudflare Pages 等）。
   - 若需要多环境配置，可按域名区分不同脚本地址。

3. **在外部站点引用**
   - **自动初始化（推荐）**
     ```html
     <script
       src="https://your-cdn.com/embed-ai-chat.js"
       data-auto-init
       data-api-base-url="https://your-backend.com"
       data-position="bottom-right"
       data-title="商品推荐助手">
     </script>
     ```
     `data-*` 属性会在脚本加载后自动触发 `window.EmbedAiChat.init`，并将配置传入。可选参数包括 `api-base-url`、`position`（`bottom-right`/`bottom-left`）、`primary-color`、`title`、`placeholder`。

   - **手动初始化**
     ```html
     <script src="https://your-cdn.com/embed-ai-chat.js"></script>
     <script>
       window.EmbedAiChat.init({
         apiBaseUrl: "https://your-backend.com",
         position: "bottom-right",
         title: "商品推荐助手",
         placeholder: "输入消息..."
       });
       // window.EmbedAiChat.destroy(); // 需要销毁时调用
     </script>
     ```

4. **后端与跨域**
   - 确保后端 `.env` 中的 `CORS_ALLOW_ORIGINS`（或相关配置）包含外部站点域名。
   - 生产环境记得开启 HTTPS、鉴权与速率限制，避免被滥用。

> Demo 可参考 `frontend/embed/demo.html`，它展示了打包产物如何在独立页面被引用。

---

## 9. 下一步你可以

1. **切换 provider**：只改 `.env`，马上体验不同模型的推理差异。
2. **扩展工具**：在 `backend/app/services/agent/tools/` 新增商品工具，它会自动出现在推理流程中。
3. **自定义前端展示**：Timeline 组件天然支持插槽，新增卡片类型很轻松。
4. **部署生产**：把 SQLite 换成 Postgres，把 Qdrant 换成托管服务，再加上 API Key 管理即可上线。

---

> 有问题？直接翻 `backend/README.md` 和 `frontend/README.md` 获取更细的命令行指南。这里只负责让你“先懂再说”。
