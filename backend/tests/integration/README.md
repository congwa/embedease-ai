# 集成测试文档

本目录包含提示词系统的集成测试，通过真实 AI 调用验证提示词在实际场景下的效果。

> **前置条件**：需在 `.env` 中配置 `LLM_API_KEY` 和 `LLM_PROVIDER`，否则测试自动跳过。

---

## 目录结构

```
integration/
├── prompts/
│   ├── conftest.py              # 测试配置和 fixtures
│   ├── test_agent_prompts.py    # Agent 提示词测试
│   ├── test_crawler_prompts.py  # 爬虫提示词测试
│   ├── test_memory_prompts.py   # 记忆系统提示词测试
│   └── test_skill_prompts.py    # 技能生成提示词测试
└── README.md
```

---

## 测试配置 (`conftest.py`)

### 标记说明

| 标记 | 说明 |
|------|------|
| `@requires_api` | 需要真实 API 配置，未配置时跳过 |
| `@integration` | 集成测试标记 |
| `@slow` | 慢速测试标记（涉及 AI 调用） |

### Fixtures

| Fixture | 用途 |
|---------|------|
| `llm_model` | 获取真实 LLM 模型实例 |
| `sample_conversation` | 示例对话数据（用户询问键盘推荐） |
| `sample_html_content` | 示例商品页面 HTML（HHKB 键盘） |
| `sample_skill_description` | 示例技能描述 |

### 辅助函数

- `invoke_llm(model, system_prompt, user_message)` - 调用 LLM 的封装函数

---

## Agent 提示词测试 (`test_agent_prompts.py`)

测试各类 Agent 系统提示词在真实 AI 调用下的表现。

### 测试用例详解

#### 1. `test_product_prompt_generates_recommendation`

**测试内容**：商品推荐提示词 (`agent.product`)

**输入**：
- System: 商品推荐助手提示词
- User: "我想买一款适合程序员用的机械键盘，预算500左右"

**验证**：
- 响应长度 > 50 字符
- 包含推荐相关关键词（推荐、建议、键盘、程序员等）

**保证**：AI 能生成专业友好的商品推荐回复

---

#### 2. `test_faq_prompt_answers_question`

**测试内容**：FAQ 问答提示词 (`agent.faq`)

**输入**：
- System: FAQ 助手提示词
- User: "如何退换货？"

**验证**：
- 响应长度 > 20 字符
- 包含引导关键词（退、换、客服、联系等）

**保证**：AI 能直接回答或引导用户解决常见问题

---

#### 3. `test_kb_prompt_references_data`

**测试内容**：知识库提示词 (`agent.kb`)

**输入**：
- System: 知识库助手提示词
- User: "公司的年假政策是什么？"

**验证**：
- 响应长度 > 20 字符
- 包含检索相关词（检索、查询、知识库、无法确认等）

**保证**：AI 在无数据时明确表示需要检索或无法回答

---

#### 4. `test_custom_prompt_is_helpful`

**测试内容**：自定义通用提示词 (`agent.custom`)

**输入**：
- System: 自定义助手提示词
- User: "帮我写一首关于编程的小诗"

**验证**：
- 响应长度 > 30 字符
- 包含相关内容（编程、代码、程序、诗等）

**保证**：AI 保持有帮助的通用助手行为

---

#### 5. `test_strict_mode_suffix_effect`

**测试内容**：严格模式后缀 (`agent.mode.strict`)

**输入**：
- System: 商品提示词 + 严格模式后缀
- User: "推荐一款手机"

**验证**：
- 响应长度 > 20 字符
- 包含数据依赖相关词（数据、检索、工具、需要等）或正常回复

**保证**：严格模式能约束 AI 基于数据回答或表明需要更多信息

---

#### 6. `test_free_mode_suffix_effect`

**测试内容**：自由模式后缀 (`agent.mode.free`)

**输入**：
- System: 自定义提示词 + 自由模式后缀
- User: "今天天气怎么样？"

**验证**：
- 响应长度 > 20 字符
- 包含友好交流词（天气、今天、您、我、帮等）

**保证**：自由模式允许 AI 进行自由对话

---

## 爬虫提示词测试 (`test_crawler_prompts.py`)

测试爬虫数据提取提示词的 AI 调用效果。

### 测试用例详解

#### 1. `test_product_extraction_returns_json`

**测试内容**：商品信息提取 (`crawler.product_extraction`)

**输入**：
- System: 商品提取提示词
- User: HHKB 键盘商品页面 HTML

**验证**：
- 返回有效 JSON
- `is_product_page` 为 `true`
- `product` 对象包含 `title/name/price` 字段
- 正确提取品牌信息（HHKB、键盘、2580、静电容等）

**保证**：AI 能从商品页面 HTML 准确提取商品信息

**期望输出结构**：
```json
{
  "is_product_page": true,
  "product": {
    "title": "HHKB Professional HYBRID Type-S 静电容键盘",
    "price": "2580.00",
    ...
  }
}
```

---

#### 2. `test_non_product_page_detection`

**测试内容**：非商品页面检测 (`crawler.product_extraction`)

**输入**：
- System: 商品提取提示词
- User: 博客文章 HTML（机械键盘选购指南）

**验证**：
- 返回有效 JSON
- `is_product_page` 为 `false`

**保证**：AI 能正确识别非商品页面，避免误提取

**期望输出结构**：
```json
{
  "is_product_page": false
}
```

---

#### 3. `test_content_extraction_general`

**测试内容**：通用内容提取 (`crawler.content_extraction`)

**输入**：
- System: 通用内容提取提示词
- User: 文章 HTML（2024年机械键盘选购指南）

**验证**：
- 返回有效 JSON
- 提取内容包含关键词（机械键盘、选购、轴体、预算等）

**保证**：AI 能提取文章等通用内容的结构化信息

---

## 记忆系统提示词测试 (`test_memory_prompts.py`)

测试用户记忆管理相关提示词的 AI 调用效果。

### 测试用例详解

#### 1. `test_fact_extraction_returns_json`

**测试内容**：事实抽取 (`memory.fact_extraction`)

**输入**：
- System: 事实抽取提示词
- User: 示例对话（用户询问键盘推荐）

**验证**：
- 返回有效 JSON
- `facts` 为数组
- 抽取的事实包含关键信息（程序员、键盘、500、预算等）

**保证**：AI 能从对话中准确提取用户相关事实

**期望输出结构**：
```json
{
  "facts": [
    "用户想买机械键盘",
    "用户是程序员",
    "用户预算500元左右",
    "用户需要长时间打字"
  ]
}
```

---

#### 2. `test_memory_action_decision`

**测试内容**：记忆操作决策 (`memory.action_decision`)

**输入**：
- System: 操作决策提示词
- User: 新事实"预算从500调整为800" + 现有记忆列表

**验证**：
- 返回有效 JSON
- `action` 为 `ADD/UPDATE/DELETE/NONE` 之一
- 若为 `UPDATE`，包含 `target_id`

**保证**：AI 能正确决定对记忆执行的操作类型

**期望输出结构**：
```json
{
  "action": "UPDATE",
  "target_id": "mem_002",
  "reason": "用户预算已更新"
}
```

---

#### 3. `test_graph_extraction_entities_and_relations`

**测试内容**：知识图谱抽取 (`memory.graph_extraction`)

**输入**：
- System: 图谱抽取提示词
- User: 示例对话

**验证**：
- 返回有效 JSON
- `entities` 为数组，每个实体包含 `name` 和 `entity_type`
- `relations` 为数组

**保证**：AI 能从对话中提取实体和关系用于构建知识图谱

**期望输出结构**：
```json
{
  "entities": [
    { "name": "用户", "entity_type": "person" },
    { "name": "机械键盘", "entity_type": "product" }
  ],
  "relations": [
    { "source": "用户", "relation": "想买", "target": "机械键盘" }
  ]
}
```

---

#### 4. `test_fact_extraction_empty_conversation`

**测试内容**：空对话事实抽取 (`memory.fact_extraction`)

**输入**：
- System: 事实抽取提示词
- User: 简单问候对话（你好/有什么可以帮您）

**验证**：
- 返回有效 JSON
- `facts` 为数组（通常为空或很少）

**保证**：简单问候不会产生无意义的事实记录

---

## 技能生成提示词测试 (`test_skill_prompts.py`)

测试技能（Skill）生成和优化提示词的 AI 调用效果。

### 测试用例详解

#### 1. `test_skill_generate_returns_valid_json`

**测试内容**：技能生成 (`skill.generate`)

**输入**：
- System: 技能生成提示词（包含描述、分类、适用Agent、示例）
- User: "请根据上述描述生成技能定义"

**验证**：
- 返回有效 JSON
- 包含必需字段：`name`, `description`, `category`, `content`, `trigger_keywords`
- `name` 长度 ≤ 20 字符
- `trigger_keywords` 为数组且 ≥ 3 个
- `content` 长度 > 20 字符

**保证**：AI 能根据描述生成结构完整的技能定义

**期望输出结构**：
```json
{
  "name": "价格筛选",
  "description": "根据价格区间筛选商品并按性价比排序",
  "category": "prompt",
  "content": "当用户询问特定价格区间的商品时，筛选符合条件的商品...",
  "trigger_keywords": ["价格", "多少钱", "预算", "价位", "便宜"]
}
```

---

#### 2. `test_skill_refine_improves_skill`

**测试内容**：技能优化 (`skill.refine`)

**输入**：
- System: 技能优化提示词（包含原技能JSON + 改进反馈）
- User: "请根据反馈优化技能"

**原技能**：
```json
{
  "name": "价格筛选",
  "description": "筛选价格",
  "category": "prompt",
  "content": "帮用户筛选价格",
  "trigger_keywords": ["价格", "多少钱"]
}
```

**反馈**：描述太简单，trigger_keywords 不够丰富，content 需要更详细

**验证**：
- 返回有效 JSON
- 优化后 `description` 长度 > 原长度
- 优化后 `trigger_keywords` 数量 > 原数量
- 优化后 `content` 长度 > 原长度

**保证**：AI 能根据反馈有效改进技能定义

---

#### 3. `test_skill_generate_with_examples`

**测试内容**：带示例的技能生成 (`skill.generate`)

**输入**：
- System: 技能生成提示词（包含对话示例）
- User: "请根据上述描述和示例生成技能定义"

**示例对话**：
```
用户: 500块以内有什么好的键盘？
助手: 让我帮您筛选500元以下的键盘...

用户: 推荐一些200-300价位的鼠标
助手: 这个价位有几款不错的鼠标...
```

**验证**：
- 返回有效 JSON
- `trigger_keywords` 包含价格相关词（价格、价位、多少钱、块、元等）

**保证**：AI 能参考示例生成更精准的触发关键词

---

## 运行测试

### 运行所有集成测试

```bash
pytest backend/tests/integration/ -v -m integration
```

### 运行特定模块

```bash
# Agent 提示词测试
pytest backend/tests/integration/prompts/test_agent_prompts.py -v

# 爬虫提示词测试
pytest backend/tests/integration/prompts/test_crawler_prompts.py -v

# 记忆系统测试
pytest backend/tests/integration/prompts/test_memory_prompts.py -v

# 技能生成测试
pytest backend/tests/integration/prompts/test_skill_prompts.py -v
```

### 跳过慢速测试

```bash
pytest backend/tests/integration/ -v -m "integration and not slow"
```

---

## 质量保证总结

| 模块 | 测试数量 | 保证的核心能力 |
|------|---------|---------------|
| Agent | 6 | 不同场景下 AI 响应符合预期风格和约束 |
| Crawler | 3 | 准确识别页面类型并提取结构化数据 |
| Memory | 4 | 正确提取用户信息并做出合理的记忆操作决策 |
| Skill | 3 | 生成结构完整且可改进的技能定义 |
| 聊天流 | 5 | 完整对话流程、事件序列、错误处理 |
| SSE 事件 | 8 | 事件结构正确、编码标准、版本控制 |
| 工具调用 | 9 | 工具执行、错误处理、多步骤任务 |

**总计 38 个集成测试用例**，覆盖提示词系统和聊天流的核心功能。

---

## 聊天流集成测试

详见 [chat/README.md](./chat/README.md)，包含：
- **聊天流基础测试** - 完整对话流程验证
- **SSE 事件结构测试** - 事件格式和编码验证
- **工具调用测试** - 各类工具的调用和执行验证
