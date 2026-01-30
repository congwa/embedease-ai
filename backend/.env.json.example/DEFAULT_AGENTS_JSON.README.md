# DEFAULT_AGENTS_JSON.json 配置说明

## 文件作用

定义系统中的默认 Agent 配置，包括商品推荐助手、FAQ 客服助手、知识库助手等不同类型的智能助手。

## 配置格式

```json
[
  {
    "id": "agent-唯一标识",
    "name": "Agent名称",
    "description": "Agent描述",
    "type": "product|faq|kb",
    "is_default": true/false,
    "middleware_flags": { ... },
    "tool_policy": { ... },
    "tool_categories": [ ... ],
    "knowledge_config": { ... }
  }
]
```

## 字段说明

### 基础配置

| 字段 | 类型 | 说明 | 必填 | 示例 |
|------|------|------|------|------|
| `id` | string | Agent 唯一标识符 | ✅ | `"agent-product-default"` |
| `name` | string | Agent 显示名称 | ✅ | `"商品推荐助手"` |
| `description` | string | Agent 功能描述 | ✅ | `"智能商品推荐"` |
| `type` | string | Agent 类型：`product`/`faq`/`kb` | ✅ | `"product"` |
| `is_default` | boolean | 是否为默认 Agent | ✅ | `true` |

### 中间件配置

```json
"middleware_flags": {
  "todo_enabled": true,           // 启用 TODO 规划中间件
  "memory_enabled": true,          // 启用记忆中间件
  "summarization_enabled": true,   // 启用对话摘要
  "tool_retry_enabled": true,      // 启用工具重试
  "tool_limit_enabled": true       // 启用工具调用限制
}
```

### 工具策略配置

```json
"tool_policy": {
  "min_tool_calls": 0,              // 最小工具调用次数
  "allow_direct_answer": true,      // 是否允许直接回答
  "fallback_tool": "search_products" // 降级工具
}
```

### 工具分类

```json
"tool_categories": [
  "search",    // 搜索工具
  "query",     // 查询工具
  "compare",   // 比较工具
  "filter",    // 筛选工具
  "category",  // 分类工具
  "featured",  // 精选工具
  "purchase",  // 购买工具
  "guide"      // 指南工具
]
```

### 知识库配置

```json
"knowledge_config": {
  "id": "kb-faq-default",
  "name": "FAQ 知识库",
  "type": "faq|vector",
  "collection_name": "faq_entries",
  "top_k": 5,
  "rerank_enabled": false,
  "similarity_threshold": 0.7
}
```

## 完整示例

### 示例一：商品推荐助手

```json
{
  "id": "agent-product-default",
  "name": "商品推荐助手",
  "description": "智能商品推荐，帮助用户发现和选择合适的商品",
  "type": "product",
  "is_default": true,
  "middleware_flags": {
    "todo_enabled": true,
    "memory_enabled": true,
    "summarization_enabled": true,
    "tool_retry_enabled": true,
    "tool_limit_enabled": true
  },
  "tool_policy": {
    "min_tool_calls": 0,
    "allow_direct_answer": true
  },
  "tool_categories": [
    "search",
    "query",
    "compare",
    "filter",
    "category",
    "featured",
    "purchase",
    "guide"
  ]
}
```

### 示例二：FAQ 客服助手

```json
{
  "id": "agent-faq-support",
  "name": "客服问答助手",
  "description": "基于 FAQ 知识库回答用户常见问题",
  "type": "faq",
  "is_default": false,
  "middleware_flags": {
    "todo_enabled": false,
    "memory_enabled": true
  },
  "tool_policy": {
    "min_tool_calls": 0,
    "allow_direct_answer": true,
    "fallback_tool": "faq_search"
  },
  "knowledge_config": {
    "id": "kb-faq-default",
    "name": "FAQ 知识库",
    "type": "faq",
    "collection_name": "faq_entries",
    "top_k": 5,
    "rerank_enabled": false
  }
}
```

### 示例三：知识库助手

```json
{
  "id": "agent-kb-internal",
  "name": "内部知识库助手",
  "description": "基于内部文档知识库回答问题",
  "type": "kb",
  "is_default": false,
  "middleware_flags": {
    "memory_enabled": true
  },
  "tool_policy": {
    "min_tool_calls": 1,
    "allow_direct_answer": false,
    "fallback_tool": "kb_search"
  },
  "knowledge_config": {
    "id": "kb-internal-docs",
    "name": "内部文档库",
    "type": "vector",
    "collection_name": "internal_docs",
    "top_k": 10,
    "rerank_enabled": true,
    "similarity_threshold": 0.7
  }
}
```

## 使用方式

### 方式一：使用文件（推荐）

1. 在 `.env` 中启用目录加载：
   ```bash
   ENV_JSON_DIR=.env.json
   ```

2. 复制示例文件并修改：
   ```bash
   cp .env.json.example/DEFAULT_AGENTS_JSON.json .env.json/DEFAULT_AGENTS_JSON.json
   ```

3. 编辑配置文件添加或修改 Agent

### 方式二：使用环境变量

在 `.env` 中直接设置（不推荐，配置复杂）：

```bash
DEFAULT_AGENTS_JSON='[{"id":"agent-1","name":"助手1",...}]'
```

## Agent 类型说明

### product - 商品推荐助手
- **用途**：商品搜索、推荐、比较
- **特点**：支持多种商品相关工具
- **模式**：通常使用 `natural` 模式

### faq - FAQ 客服助手
- **用途**：回答常见问题
- **特点**：基于 FAQ 知识库
- **模式**：通常使用 `natural` 模式

### kb - 知识库助手
- **用途**：基于文档库回答问题
- **特点**：严格基于知识库内容
- **模式**：通常使用 `strict` 模式

## 中间件功能说明

| 中间件 | 功能 | 适用场景 |
|--------|------|----------|
| `todo_enabled` | 复杂任务规划与跟踪 | 多步骤任务 |
| `memory_enabled` | 对话记忆 | 需要上下文的对话 |
| `summarization_enabled` | 对话摘要 | 长对话场景 |
| `tool_retry_enabled` | 工具调用失败重试 | 提高稳定性 |
| `tool_limit_enabled` | 限制工具调用次数 | 防止无限循环 |

## 常见问题

### Q: 如何创建自定义 Agent？

A: 在配置文件中添加新的 Agent 对象，设置唯一的 `id` 和合适的配置。

### Q: 可以有多个默认 Agent 吗？

A: 不可以，只能有一个 `is_default: true` 的 Agent。

### Q: 如何选择合适的聊天模式？

A: 
- `natural`: 适合商品推荐等场景
- `free`: 适合开放式聊天
- `strict`: 适合必须基于知识库回答的场景

### Q: 工具分类有什么作用？

A: 定义 Agent 可以使用哪些类别的工具，用于权限控制和功能限制。

### Q: 知识库配置是必须的吗？

A: 仅对 `faq` 和 `kb` 类型的 Agent 必须，`product` 类型可选。

## 相关配置

- `AGENT_TODO_ENABLED`: 全局 TODO 中间件开关
- `AGENT_TOOL_LIMIT_ENABLED`: 全局工具限制开关
- 更多 Agent 相关配置请查看 `.env.example`
