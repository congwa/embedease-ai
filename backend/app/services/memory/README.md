# 记忆系统

embedeaseai-agent 的记忆系统实现，包含 LangGraph Store、事实型长期记忆、图谱记忆和记忆编排中间件。

## 架构概览

```
memory/
├── __init__.py          # 模块导出
├── models.py            # 数据模型（Entity, Relation, Fact, UserProfile）
├── prompts.py           # LLM 提示词模板（事实抽取、行动判定、图谱抽取）
├── store.py             # LangGraph Store（跨会话用户画像存储）
├── profile_service.py   # 用户画像服务（规则引擎 + 统一读写）
├── fact_memory.py       # 事实型长期记忆服务（SQLite + Qdrant）
├── graph_memory.py      # 图谱记忆（Python 原生实现）
├── vector_store.py      # 记忆专用 Qdrant 集合管理
└── middleware/
    ├── __init__.py
    └── orchestration.py # 记忆编排中间件
```

整体设计遵循“**多层混合记忆 + 中间件编排**”：

1. **LangGraph Store**：存储长期用户画像、任务进度等结构化数据，提供 namespace + key/value 语义。
2. **Fact Memory**：对对话提炼出的事实进行哈希去重后，元数据写入 SQLite，向量写入独立的 Qdrant 集合 `memory_facts`，检索阶段直接利用 Qdrant 的 `similarity_search_with_score`，失败时回退到关键词匹配。
3. **Graph Memory**：以 JSONL 为底层存储，实现实体/关系/观察的 CRUD，用于结构化记录人与物之间的关系。
4. **Memory Orchestration Middleware**：在 LangChain Agent 中居于最前，负责记忆检索注入 + 对话结束后的异步写入（事实与图谱）。

下文分别介绍各组件的功能点与使用方式。

## 功能模块

### 1. LangGraph Store（长期记忆基座）

跨会话的用户画像/状态仓库，存放用户偏好、任务进度等。

```python
from app.services.memory import get_user_profile_store

store = await get_user_profile_store()

# 设置用户画像
await store.set_user_profile("user_123", {
    "nickname": "小明",
    "budget_min": 1000,
    "budget_max": 5000,
    "favorite_categories": ["手机", "电脑"],
})

# 获取用户画像
profile = await store.get_user_profile("user_123")

# 更新偏好
await store.update_user_profile("user_123", {"tone_preference": "友好"})

# 通用 key-value 存储
await store.put(("users", "user_123", "tasks"), "task_001", {"status": "in_progress"})
item = await store.get(("users", "user_123", "tasks"), "task_001")
```

**配置项：**
- `MEMORY_STORE_ENABLED`: 是否启用（默认 true）
- `MEMORY_STORE_DB_PATH`: SQLite 存储路径

### 2. 事实型长期记忆

LLM 事实抽取 → 哈希去重 → **SQLite 元数据 + Qdrant 向量检索**。

```python
from app.services.memory import get_fact_memory_service

service = await get_fact_memory_service()

# 从对话抽取事实
messages = [
    {"role": "user", "content": "我预算 3000 左右，想买个轻薄本"},
    {"role": "assistant", "content": "好的，我帮您推荐几款..."},
]
facts = await service.extract_facts("user_123", messages)
# facts: ["用户预算约 3000 元", "用户需要轻薄本"]

# 手动添加事实
await service.add_fact("user_123", "用户对苹果产品过敏")

# 搜索相关事实（由 Qdrant 完成向量计算）
results = await service.search_facts("user_123", "预算")

# 完整处理流程（抽取 + 去重 + 存储）
added_count = await service.process_conversation("user_123", messages)
```

**配置项：**
- `MEMORY_FACT_ENABLED`: 是否启用（默认 true）
- `MEMORY_FACT_DB_PATH`: SQLite 元数据/历史记录存储路径
- `MEMORY_FACT_COLLECTION`: Qdrant 集合名（默认 `memory_facts`，自动创建）
- `MEMORY_FACT_SIMILARITY_THRESHOLD`: 相似度阈值（默认 0.5，用于过滤 Qdrant score）
- `MEMORY_FACT_MAX_RESULTS`: 搜索最大返回数（默认 10）
- `MEMORY_FACT_EXTRACTION_MODEL`: 事实抽取模型（默认使用主模型）

**架构说明：**
- **SQLite**：负责存储事实正文、哈希值、创建/更新时间以及 `fact_history`；可用于审计和手动编辑。
- **Qdrant**：通过 `vector_store.py` 维护的独立集合；写入/更新/删除事实时同步操作 Qdrant，检索阶段直接调用 `similarity_search_with_score`，性能与扩展性更好。
- **回退机制**：若 Qdrant 不可用或调用超时，服务会自动退化为 SQLite 关键词匹配，至少保证基本召回能力。
- **并发安全**：`FactMemoryService` 内部使用 `asyncio.Lock` 保证同一实例在写入阶段的线程安全；向量写入/删除通过 `asyncio.to_thread` 异步执行，避免阻塞事件循环。

**工作流概览：**

1. **抽取阶段**：`extract_facts()` 读取最近对话，使用 LLM + `FACT_EXTRACTION_PROMPT` 提取结构化事实列表。
2. **判定阶段**：`decide_action()` 将新事实与 Qdrant 检索结果对比，由 LLM 决定是新增、更新还是删除。
3. **写入阶段**：`add_fact()` / `update_fact()` / `delete_fact()` 同时操作 SQLite（元数据）与 Qdrant（向量），并记录历史表。
4. **检索阶段**：`search_facts()` 通过 Qdrant 检索得到最相关的事实，再回到 SQLite 获取元数据，最终返回 `Fact` 数据对象。

### 3. 图谱记忆

实体/关系/观察的结构化知识图谱，JSONL 持久化。

```python
from app.services.memory import get_graph_manager, Entity, Relation

manager = await get_graph_manager()

# 创建实体
await manager.create_entities([
    Entity(name="用户A", entity_type="PERSON", observations=["喜欢科技产品"]),
    Entity(name="iPhone 15", entity_type="PRODUCT", observations=["苹果旗舰"]),
])

# 创建关系
await manager.create_relations([
    Relation(from_entity="用户A", to_entity="iPhone 15", relation_type="PREFERS"),
])

# 添加观察
await manager.add_observations([
    {"entity_name": "用户A", "contents": ["预算 5000 左右"]}
])

# 搜索节点
graph = await manager.search_nodes("科技")

# 获取用户相关图谱
user_graph = await manager.get_user_graph("user_123")

# 从对话自动抽取并保存
entities, relations = await manager.extract_and_save("user_123", messages)
```

**配置项：**
- `MEMORY_GRAPH_ENABLED`: 是否启用（默认 true）
- `MEMORY_GRAPH_FILE_PATH`: JSONL 存储路径

### 4. 用户画像服务（ProfileService）

从事实和图谱中自动提取结构化画像信息，统一管理画像的读写与更新。

```python
from app.services.memory import get_profile_service, ProfileUpdateSource

service = await get_profile_service()

# 获取用户画像
profile = await service.get_profile("user_123")

# 用户显式更新画像
result = await service.update_profile(
    "user_123",
    {"budget_max": 5000, "tone_preference": "友好"},
    source=ProfileUpdateSource.USER_INPUT
)

# 从事实更新画像（自动提取预算、品类等）
result = await service.update_from_facts("user_123", facts)

# 从图谱更新画像（自动提取偏好关系、任务进度）
result = await service.update_from_graph("user_123", graph)
```

**规则引擎支持的自动提取：**
- **预算区间**：从"预算3000""3000-5000""不超过5000"等文本提取 `budget_min/max`
- **品类偏好**：识别手机、电脑、耳机等品类关键词 → `favorite_categories`
- **品牌偏好**：识别苹果、华为、小米等品牌 → `custom_data.brand_preferences`
- **语气偏好**：识别友好、专业、简洁等关键词 → `tone_preference`
- **任务进度**：从图谱实体中提取任务状态 → `task_progress`

**API 接口：**
- `GET /api/v1/users/{user_id}/profile`: 获取用户画像
- `POST /api/v1/users/{user_id}/profile`: 更新用户画像
- `DELETE /api/v1/users/{user_id}/profile`: 删除用户画像

### 5. 记忆编排中间件

自动在 Agent 调用时注入记忆上下文，并在对话结束后异步写入记忆和更新画像。

**三阶段处理：**
1. **awrap_model_call**: 检索记忆（画像 + 事实 + 图谱）并注入到 system prompt
2. **aafter_agent**: Agent 完成后异步触发事实抽取、图谱抽取和画像更新
3. **SSE 通知**: 记忆抽取开始/完成、画像更新事件推送给前端

**SSE 事件类型：**
- `memory.extraction.start`: 记忆抽取开始
- `memory.extraction.complete`: 记忆抽取完成（含事实/实体/关系数量）
- `memory.profile.updated`: 用户画像更新（含更新的字段列表）

**配置项：**
- `MEMORY_ENABLED`: 总开关（默认 true）
- `MEMORY_ORCHESTRATION_ENABLED`: 编排中间件开关（默认 true）
- `MEMORY_ASYNC_WRITE`: 是否异步写入（默认 true）

## 配置示例

```bash
# .env

# === 总开关 ===
MEMORY_ENABLED=true

# === LangGraph Store ===
MEMORY_STORE_ENABLED=true
MEMORY_STORE_DB_PATH=./data/memory_store.db

# === 事实型记忆 ===
MEMORY_FACT_ENABLED=true
MEMORY_FACT_DB_PATH=./data/facts.db
MEMORY_FACT_SIMILARITY_THRESHOLD=0.85
MEMORY_FACT_MAX_RESULTS=10

# === 图谱记忆 ===
MEMORY_GRAPH_ENABLED=true
MEMORY_GRAPH_FILE_PATH=./data/knowledge_graph.jsonl

# === 记忆编排 ===
MEMORY_ORCHESTRATION_ENABLED=true
MEMORY_ASYNC_WRITE=true
```

## 数据流
```
用户输入
    │
    ▼
┌─────────────────────────────────────┐
│   MemoryOrchestrationMiddleware     │
│   ┌─────────────────────────────┐   │
│   │ 1. 读取 Store 用户画像       │   │
│   │ 2. Qdrant 检索事实记忆       │   │
│   │ 3. 搜索相关图谱节点          │   │
│   │ 4. 注入到 System Prompt     │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│          Agent 推理                 │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│   MemoryOrchestrationMiddleware     │
│   ┌─────────────────────────────┐   │
│   │ 5. 异步触发事实抽取          │   │
│   │ 6. 异步触发图谱抽取          │   │
│   │ 7. 写入 SQLite + Qdrant      │   │
│   │ 8. ProfileService 更新画像   │   │
│   │ 9. SSE 通知前端              │   │
│   └─────────────────────────────┘   │
└─────────────────────────────────────┘
    │
    ▼
响应输出
```

## 画像更新闭环

```
事实抽取                     图谱抽取
    │                           │
    ▼                           ▼
┌─────────────────┐    ┌─────────────────┐
│ 规则引擎提取    │    │ 关系/实体提取    │
│ - 预算区间      │    │ - 偏好关系      │
│ - 品类/品牌     │    │ - 任务进度      │
│ - 语气偏好      │    │                 │
└────────┬────────┘    └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
           ┌───────────────────┐
           │  ProfileService   │
           │  update_profile() │
           └─────────┬─────────┘
                     │
                     ▼
           ┌───────────────────┐
           │  UserProfileStore │
           │  (SQLite)         │
           └─────────┬─────────┘
                     │
                     ▼
           ┌───────────────────┐
           │  SSE 通知前端     │
           │  memory.profile   │
           │  .updated         │
           └───────────────────┘
```

## 注意事项

1. **性能**: 记忆检索在模型调用前执行，会增加少量延迟；写入采用异步模式，不阻塞响应
2. **隐私**: 所有记忆按 user_id 隔离，支持按用户导出/删除
3. **存储**: 默认使用 SQLite + JSONL，后续可扩展到向量数据库
4. **回收**: 建议定期清理过期记忆（可通过 fact_history 表追踪变更）
