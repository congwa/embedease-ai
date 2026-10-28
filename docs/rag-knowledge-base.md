# 托管 RAG：文档、索引与引用

本功能仅包含后端及 Python Agent SDK。前端管理页面、引用组件及 TypeScript SDK 尚未实现。

## 数据如何保存

```text
原文件 / 粘贴文本 → 独立私有 MinIO 桶
                         ↓
                     解析规范化全文
                         ↓
SQL：Document → DocumentRevision → DocumentChunk
                         ↓
Qdrant：分块向量 + 正文 + config/document/revision/chunk ID
                         ↓
Agent 检索 → SQL 校验当前版本 → 回答 [S1] → MessageCitation
                                                ↓
                                签名读取文章最新全文 / 原文件
```

业务采用最新知识快照：每篇文章只允许当前生效构建参与检索。更新先构建新内容，确认完整后切换，再删除文章所有旧构建的向量；**旧向量删除并核对数量为零之前，任务不能返回 ready**。清理失败重试只继续清理，不能重新生成正在服务的分块。

SQL 的 revision ID 是内部构建批次，用于任务恢复和安全切换，不是让业务同时检索多个历史版本。SQL 是当前发布构建及文章启停状态的事实来源。原文件保留原始字节，解析全文便于定位；向量不能还原原文。分块偏移是 Python Unicode 字符索引，满足 `full_text[start_offset:end_offset] == content`。JavaScript 的 UTF-16 字符串索引与此不同，含 emoji 等字符时应先使用 `Array.from(text)` 再按偏移定位。

新增表由现有数据库初始化流程创建：`rag_sources`、`knowledge_documents`、`knowledge_revisions`、`knowledge_chunks`、`knowledge_jobs`、`knowledge_message_citations`。无需修改旧知识源表。只显式启用的 vector 知识源进入托管路径；旧 FAQ、商品及非托管知识库保持原路径。

## 配置与启动

沿用已有 `MINIO_*`、`QDRANT_*`、`EMBEDDING_*` 配置。新增环境变量：

| 配置 | 默认值 | 说明 |
|---|---|---|
| `KNOWLEDGE_ADMIN_KEY` | 空 | 管理密钥；空值关闭管理入口，建议随机生成至少 32 字符 |
| `KNOWLEDGE_SIGNING_KEY` | 空 | 引用签名密钥，空值回退管理密钥；实际使用的签名密钥至少 32 字符 |
| `KNOWLEDGE_BUCKET` | `knowledge-documents` | 独立私有桶；禁止与图片桶相同，已有桶若存在策略则拒绝使用 |
| `KNOWLEDGE_RAG_ENABLED` | `true` | 托管 RAG 总开关，关闭后拒绝新管理和托管检索，不回退旧集合 |
| `KNOWLEDGE_WORKER_ENABLED` | `true` | 控制入库、清理及巡检任务，不影响已发布内容的检索 |
| `KNOWLEDGE_MAX_FILE_BYTES` | `20971520` | 单文件 20 MiB |
| `KNOWLEDGE_MAX_TEXT_CHARS` | `2000000` | 解析后全文字符上限 |
| `KNOWLEDGE_MAX_CHUNKS` | `10000` | 每版本分块上限 |
| `KNOWLEDGE_DOCX_MAX_UNPACKED_BYTES` | `104857600` | DOCX 解压总量上限 |
| `KNOWLEDGE_PARSE_TIMEOUT` | `120` | 子进程解析超时秒数 |
| `KNOWLEDGE_CONTEXT_CHARS` | `8000` | 本轮知识库工具正文预算；不会截断入选分块 |
| `KNOWLEDGE_CITATION_TTL` | `3600` | 引用凭证有效期秒数 |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `800` / `100` | 按字符计数，重叠必须小于块长 |

本地依赖安装使用 `cd backend && uv sync --locked`，启动仍使用仓库的 Uvicorn 命令。增加的解析依赖为 pypdf 和 python-docx，版本由 `uv.lock` 固定。

MinIO 使用服务端受控的独立桶，原文不生成公开存储 URL。默认每 5 秒领取一个任务，每实例串行执行，多个实例通过数据库租约协调。任务运行期间不持有长 SQL 写事务。后台解析需要运行环境允许创建 Python 子进程。

## 管理接口

以下所有接口前缀为 `/api/v1/admin/knowledge-configs/{config_id}`，需要 `X-Knowledge-Admin-Key`。

| 方法及路径 | 请求 / 作用 |
|---|---|
| `POST /rag/enable` | 显式开启托管模式；旧 collection 非空时返回 409，不自动迁移 |
| `POST /documents/upload` | multipart：`file`、可选 `title`、`independent=false` |
| `POST /documents/text` | JSON：`title`、`text`、`markdown=false`、`independent=false` |
| `GET /documents` | `offset=0&limit=50&include_deleted=false`；返回文章、当前版本、最新版本状态 |
| `GET /documents/{id}` | 文章及所有版本元信息；不包含全文和对象键 |
| `PATCH /documents/{id}` | JSON：可选 `title`、`enabled`；禁止 null |
| `POST /documents/{id}/revisions` | multipart：`file` 与 `text` 二选一，可选 `markdown`；替换正文生成新版本 |
| `POST /documents/{id}/reindex` | 读取当前发布版本原文件（首版失败则读取最新原文件），按当前全局配置建立新版本 |
| `GET /documents/{id}/content` | 可选 `revision_id`；返回规范化全文 |
| `GET /documents/{id}/chunks` | 可选 `revision_id`、`offset`、`limit`；返回按顺序分块及精确偏移 |
| `GET /documents/{id}/original` | 可选 `revision_id`；以附件返回原始文件 |
| `DELETE /documents/{id}` | 立即标记删除、撤销在途任务，异步清理外部资源 |
| `GET /jobs/{job_id}` | 返回阶段、进度、失败次数、下次可执行时间及安全错误摘要 |
| `POST /jobs/{job_id}/retry` | 只允许重试文章最新的失败版本；不抢占其他任务 |
| `POST /search` | JSON：`query`；返回分块、评分、文章版本与定位信息 |

新增文档和版本返回 `202`：

```json
{
  "document_id": "uuid",
  "revision_id": "uuid",
  "job_id": "uuid",
  "status": "queued"
}
```

`202` 仅表示已保存并排队，需轮询任务。相同知识源内，最新版本的原文件字节、格式及处理配置相同时复用已有文档/任务；`independent=true` 显式创建独立文章。更新正文必须使用 revisions 接口，不能靠重复上传隐式替换文章。

```sh
# 使用外部注入的管理密钥，不把密钥写进前端代码或仓库。
export API_BASE=http://127.0.0.1:8000
export CONFIG_ID=your-vector-config-id

curl -X POST "$API_BASE/api/v1/admin/knowledge-configs/$CONFIG_ID/rag/enable" \
  -H "X-Knowledge-Admin-Key: $KNOWLEDGE_ADMIN_KEY"

curl -X POST "$API_BASE/api/v1/admin/knowledge-configs/$CONFIG_ID/documents/upload" \
  -H "X-Knowledge-Admin-Key: $KNOWLEDGE_ADMIN_KEY" \
  -F 'file=@./policy.pdf' -F 'title=退货政策'

curl -X POST "$API_BASE/api/v1/admin/knowledge-configs/$CONFIG_ID/search" \
  -H "X-Knowledge-Admin-Key: $KNOWLEDGE_ADMIN_KEY" \
  -H 'Content-Type: application/json' -d '{"query":"退货期限是多少天？"}'
```

现有知识源 PATCH/DELETE 对托管模式同样要求密钥。不能通过旧 PATCH 直接修改 type、collection、index 或模型。删除知识源前，必须完成其所有文章的清理。

错误使用 `{"detail":"可理解的错误"}`：401 表示缺少/错误管理密钥或无效/过期凭证，403 表示引用绑定不匹配，404 表示资源不存在或不属于该知识源，409 表示状态冲突/模型配置不匹配，410 表示原文已删除，413 表示上传超限，422 表示不支持的输入，503 表示服务或配置不可用。外部服务暂时故障也可能产生通用 500；入库阶段的详细状态以 jobs 查询为准。

## 解析与发布规则

- TXT/Markdown 只接受 UTF-8（包括 BOM），Markdown 代码围栏内的井号不作为标题。
- PDF 逐页提取文字，不跨页分块；加密或扫描 PDF 明确失败。DOCX 按正文段落、表格顺序提取，按 Heading 样式划分章节，不提供虚构页码。复杂排版、嵌入对象及图片不会成为可检索文字。
- 先按标题/页划分结构单元，再在单元内递归分块，重叠不会跨章节或跨 PDF 页。
- 每版保存解析器版本、分块配置、文件哈希、模型/维度/端点指纹。向量 ID 由版本和序号确定，任务重复执行不会创建重复 point。
- 每批最多 32 块，验证返回数量、维度、有限值及非零向量，确认 Qdrant 数量后才发布。
- 新内容构建失败时继续使用当前生效内容。新内容构建成功后切换 SQL 指针，在同一个入库任务内删除所有较旧构建的向量并确认数量为零，再把任务标为 ready。SQL 及私有文件中的构建记录保留用于管理诊断；业务引用不再回放旧正文。
- 检索强制过滤知识源和当前已发布版本，再回查 SQL 排除删除/停用/过期版本，之后执行可选 rerank。分数是相似度，不是正确概率。
- 模型维度或端点改变后拒绝混用旧索引。管理者通过每篇文章的 reindex 接口显式采用当前全局模型，逐篇重建；所有可检索文章完成前，知识源查询明确拒绝混用。首版失败文章也可用 reindex 采用当前配置，或对同配置失败任务使用 retry。

任务状态：`queued → parsing → chunking → embedding → publishing → ready`，临时失败进入 `retry_wait`，永久失败为 `failed`。自动入库重试最多 3 次，间隔 10/30/120 秒；格式错误不会自动重试。执行租约 180 秒，每 30 秒续租；进程退出后过期租约可被重新领取，旧 token 无权发布。`available_at` 为 Unix 秒数。清理任务使用 `running` 阶段，持续重试直到成功。

删除先让文章退出检索，再清理所有版本原文件、全文、分块和向量。保留轻量版本元信息、删除墓碑和历史引用摘要，便于对账；后台每小时再次对账已删除文章，清理迟到的外部写入。没有版本归属且超过 24 小时的暂存对象才会被删除。正常文章的旧构建原文件和全文不自动过期，仅作为后台诊断记录保留，不参与检索。

## Agent 引用与历史

KB Agent 仍通过 `knowledge_config_id` 绑定知识源。工具在每轮 ChatContext 中维护来源注册表，编号为 S1、S2 等；结构化来源放入工具 artifact。系统提供的资料说明要求模型使用 `[S1]` 标记。最终仅接受匹配本轮真实检索来源的标记，不根据模型自行生成的 URL 签发访问权限。

新增流式事件，在 `assistant.final` 前发送：

```json
{
  "type": "assistant.citations",
  "payload": {
    "items": [{
      "citation_id": "uuid",
      "label": "S1",
      "document_id": "uuid",
      "revision_id": "uuid",
      "chunk_id": "uuid",
      "title": "退货政策",
      "excerpt": "摘要文字",
      "page": 2,
      "heading_path": [],
      "start_offset": 800,
      "end_offset": 1450,
      "source_url": "/api/v1/knowledge/citations/uuid?token=short-lived-signature"
    }]
  }
}
```

- 管理密钥不进入 source_url。引用凭证绑定真实会话、消息及引用记录，有效期默认一小时，是持有即授权的链接；凭证内原构建 ID 用于核对引用记录，不表示允许业务回放旧正文。
- `GET source_url` 总是读取文章当前最新生效全文；`original_url` 同样下载请求时的当前原文件。文章未变化时提供引用段落位置；文章已变化时返回 `source_updated=true` 和提示，并将旧 `chunk_id`、`excerpt`、`page`、`start_offset`、`end_offset` 设为 null，避免把旧位置套在新正文上。
- 历史消息保存的回答文字不自动改写。`extra_metadata.citations` 内部记录实际引用快照；历史接口读取时重新签名并按最新原文修正展示字段。文章已更新时，提醒历史回答可能过时，链接仍打开最新原文。SDK 和 Legacy 均已接入。
- 原文删除后引用读取返回 410，历史摘要保留；停用只禁止新检索，不撤销历史阅读。
- Uvicorn 引用访问日志脱敏，响应使用 no-store/no-referrer。反向代理、APM 和前端也必须避免记录 token 完整 URL。
- 现有聊天/历史接口尚无完整账号鉴权，本功能不承诺用户级或租户级隔离。新管理接口具有应用层密钥边界；历史读取沿用现有权限模型。
- 引用验证证明“标记对应检索来源”，不证明每句话都被该段落支持。未被模型实际标注的召回结果不会作为回答引用输出。

## 本地验收与运行边界

可复跑直接功能验收（会调用配置中的真实 Embedding 和聊天 API，产生正常 API 用量）：

```sh
cd backend
PYTHONPATH=. uv run python scripts/verify_rag.py --live
```

脚本使用临时 SQLite/Checkpointer、随机知识源和独立私有 MinIO 桶，不修改原有业务数据库。Qdrant 验收数据按随机知识源过滤清理，不删除共享集合；临时桶与对象最终删除。异常中断时可能留下验收桶，应按验收命名 `rag-qa-*` 人工核对后清理。脚本仅面向本地验收，不是生产运维命令。

2026-10-20 本地真实验收已完成：

| 验证 | 结果 |
|---|---|
| TXT/Markdown/PDF/DOCX/粘贴文本入库，分块偏移与原文件哈希 | 通过 |
| 真实 Embedding + Qdrant 的文末检索、知识源隔离 | 通过 |
| 真实 Agent 在 SDK/Legacy 下回答、引用事件、持久化及历史重新签名 | 通过 |
| 错误密钥、伪造凭证、过期凭证、跨文章版本访问 | 通过 |
| 新内容切换、构建失败保留当前内容、停用和删除 | 通过 |
| 旧向量物理删除并核对为零后任务才成功；清理故障恢复不重新 Embedding | 通过 |
| 历史引用打开最新正文；更新后清空旧摘要和旧坐标 | 通过 |
| 租约过期重新领取、旧执行令牌拒绝发布 | 数据库故障场景注入通过 |
| 网络/Qdrant 中断后的重试及恢复 | 适配器故障注入通过，未重启共享服务 |
| 相关现有回归测试 | 105 项通过 |
| PostgreSQL | 建表 SQL 编译通过；未进行真实 PostgreSQL、多实例进程并发验收 |

本机 Qdrant 服务版本为 1.15.5，客户端为 1.17.1，存在版本兼容警告；上述实际查询和写入成功，但未替用户升级共享服务。运行中的 Agent 也有原有 context 序列化警告，不影响本轮已核对的事件和持久化结果。扫描件、解析超时和各类超限输入的拒绝另由直接边界检查核对，不宣称做过大批量性能压测。

本次不新增或修改任何 `tests/` 文件。接口通过 ASGI 实际调用服务链路，未部署生产或实现前端点击交互。

## 发布及回滚

上线前备份业务数据库，记录新私有桶及 `kb_managed_v1_*` collection。先配置密钥和运行依赖，再启动应用建立新增表；显式开启空 vector 知识源，导入一份文件完成问答及引用检查后再批量导入。

回滚先将 `KNOWLEDGE_WORKER_ENABLED=false` 停止任务，再关闭 `KNOWLEDGE_RAG_ENABLED`；保留 SQL、原文件及索引，以便恢复当前知识服务。回滚到不认识托管表的旧程序时，同时恢复知识源/Agent 配置备份，不能假设旧 collection 包含新导入的文章。不得在回滚时删除共享 FAQ、商品集合或图片桶。

本次没有执行生产发布，也没有把管理密钥写入本地真实环境文件。
