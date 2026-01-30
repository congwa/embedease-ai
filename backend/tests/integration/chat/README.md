# 聊天流集成测试

本目录包含聊天流、SSE 事件推送和工具调用的集成测试，通过真实 AI 调用验证完整的对话流程。

> **前置条件**：需在 `.env` 中配置 `LLM_API_KEY` 和 `LLM_PROVIDER`，否则测试自动跳过。

---

## 目录结构

```
chat/
├── conftest.py           # 测试配置和 fixtures
├── test_chat_stream.py   # 聊天流基础测试
├── test_sse_events.py    # SSE 事件结构测试
├── test_tool_calls.py    # 工具调用测试
└── README.md
```

---

## 聊天流基础测试 (`test_chat_stream.py`)

测试完整的聊天流程，验证事件流的正确性。

### 测试用例详解

#### 1. `test_chat_stream_basic_flow`

**测试内容**：基本聊天流程

**输入**："你好"

**验证**：
- `meta.start` 事件正确发出
- `assistant.delta` 事件包含文本增量
- `assistant.final` 事件包含完整内容
- `meta.start` 包含正确的 `message_id`

**保证**：基本对话能够正常完成，事件流完整

---

#### 2. `test_chat_stream_with_tool_call`

**测试内容**：带工具调用的聊天流程

**输入**："推荐一款降噪耳机"

**验证**：
- 触发 `tool.start` 事件
- 工具执行完成后触发 `tool.end` 事件
- `tool.start` 包含 `tool_call_id` 和 `name`
- `tool.end` 包含 `status`（success/error/empty）

**保证**：商品查询能触发工具调用，工具执行有完整的生命周期事件

---

#### 3. `test_chat_stream_event_sequence`

**测试内容**：事件序列正确性

**输入**："你好"

**验证**：
- `seq` 序号严格递增
- `meta.start` 是第一个事件
- `assistant.final` 在 `meta.start` 之后

**保证**：事件顺序正确，可用于前端按序渲染

---

#### 5. `test_chat_stream_error_handling`

**测试内容**：错误处理

**输入**：使用模拟的错误 Agent

**验证**：
- 异常情况下发送 `error` 事件
- `error` 事件包含错误信息

**保证**：异常能被正确捕获并通知前端

---

## SSE 事件结构测试 (`test_sse_events.py`)

测试各类 SSE 事件的结构和内容正确性。

### 测试用例详解

#### 1. `test_meta_start_event_structure`

**测试内容**：`meta.start` 事件结构

**验证**：
- 包含版本号 `v`
- 包含事件 `id`
- 包含序号 `seq`
- 包含 `conversation_id`
- 包含 `message_id`
- payload 包含 `user_message_id` 和 `assistant_message_id`

**期望结构**：
```json
{
  "v": 1,
  "id": "evt_xxx",
  "seq": 1,
  "conversation_id": "conv_xxx",
  "message_id": "msg_xxx",
  "type": "meta.start",
  "payload": {
    "user_message_id": "msg_user_xxx",
    "assistant_message_id": "msg_asst_xxx"
  }
}
```

---

#### 2. `test_assistant_delta_event_structure`

**测试内容**：`assistant.delta` 事件结构

**验证**：
- `delta` 字段存在且为字符串
- 多个 delta 事件的 `seq` 递增

**期望结构**：
```json
{
  "type": "assistant.delta",
  "payload": {
    "delta": "你好"
  }
}
```

---

#### 3. `test_assistant_final_event_structure`

**测试内容**：`assistant.final` 事件结构

**验证**：
- `content` 字段存在
- 可选的 `reasoning`、`products` 字段

**期望结构**：
```json
{
  "type": "assistant.final",
  "payload": {
    "content": "完整回复内容",
    "reasoning": "推理过程（可选）",
    "products": [...]  // 商品列表（可选）
  }
}
```

---

#### 4. `test_tool_events_structure`

**测试内容**：工具调用事件结构

**验证**：
- `tool.start` 包含 `tool_call_id`, `name`, `input`
- `tool.end` 包含 `tool_call_id`, `name`, `status`, `count`
- `tool_call_id` 在 start 和 end 中匹配

**期望结构**：
```json
// tool.start
{
  "type": "tool.start",
  "payload": {
    "tool_call_id": "tc_xxx",
    "name": "search_products",
    "input": {"query": "耳机"}
  }
}

// tool.end
{
  "type": "tool.end",
  "payload": {
    "tool_call_id": "tc_xxx",
    "name": "search_products",
    "status": "success",
    "count": 5,
    "output_preview": [...]
  }
}
```

---

#### 5. `test_products_event_structure`

**测试内容**：商品数据事件结构

**验证**：
- `assistant.products` 事件包含 `items` 数组
- 每个商品包含 `id`, `name`, `price`

**期望结构**：
```json
{
  "type": "assistant.products",
  "payload": {
    "items": [
      {"id": "P001", "name": "索尼耳机", "price": 2999},
      {"id": "P002", "name": "Bose耳机", "price": 2499}
    ]
  }
}
```

---

#### 6. `test_event_encoding`

**测试内容**：SSE 事件编码

**验证**：
- 事件能正确序列化为 JSON
- `encode_sse` 函数输出格式正确（`data: {...}\n\n`）

**保证**：SSE 编码符合标准，前端能正确解析

---

#### 7. `test_event_versioning`

**测试内容**：事件版本控制

**验证**：
- 所有事件包含版本号 `v`
- 版本号一致

**保证**：协议版本可追溯，便于前后端兼容

---

#### 8. `test_llm_call_boundary_events`

**测试内容**：LLM 调用边界事件

**验证**：
- `llm.call.start` 和 `llm.call.end` 成对出现
- `llm.call.end` 包含 `elapsed_ms`

**保证**：LLM 调用有完整的生命周期追踪

---

## 工具调用测试 (`test_tool_calls.py`)

测试各类工具的调用和执行。

### 测试用例详解

#### 1. `test_search_products_tool`

**测试内容**：商品搜索工具

**输入**："帮我找一款降噪耳机"

**验证**：
- 触发 `search_products` 工具
- 返回商品列表或 `empty` 状态
- 成功时 `count > 0`

**保证**：商品搜索功能正常

---

#### 2. `test_filter_price_tool`

**测试内容**：价格筛选工具

**输入**："500元以下的耳机有哪些"

**验证**：
- 可能触发价格筛选工具
- 工具正确处理价格范围

**保证**：价格筛选功能正常

---

#### 3. `test_get_product_details_tool`

**测试内容**：商品详情工具

**输入**："告诉我这款耳机的详细参数"

**验证**：
- 可能触发商品详情工具
- 工具返回详细信息或错误

**保证**：商品详情查询功能正常

---

#### 4. `test_compare_products_tool`

**测试内容**：商品对比工具

**输入**："对比一下索尼和Bose的降噪耳机"

**验证**：
- 可能触发对比工具
- 工具返回对比结果

**保证**：商品对比功能正常

---

#### 5. `test_tool_error_handling`

**测试内容**：工具错误处理

**输入**："推荐耳机、手机、电脑"（多品类查询）

**验证**：
- 工具执行失败时返回 `error` 状态
- 错误信息被正确记录

**保证**：工具错误能被正确处理和报告

---

#### 6. `test_tool_call_duration`

**测试内容**：工具调用耗时统计

**验证**：
- `tool.start` 的 `seq` 小于 `tool.end` 的 `seq`
- 时序正确

**保证**：工具调用有正确的时序

---

#### 7. `test_multiple_tool_calls`

**测试内容**：多次工具调用

**输入**："先搜索降噪耳机，然后告诉我最便宜的那款的详细信息"

**验证**：
- 复杂请求可能触发多次工具调用
- 每次调用都有完整的 start/end 对
- `tool_call_id` 正确匹配

**保证**：多步骤任务能正确执行

---

#### 8. `test_tool_input_validation`

**测试内容**：工具输入验证

**验证**：
- 工具 `input` 参数被正确传递
- `input` 格式为 dict

**保证**：工具参数传递正确

---

#### 9. `test_tool_output_preview`

**测试内容**：工具输出预览

**验证**：
- `tool.end` 可能包含 `output_preview`
- `output_preview` 格式正确

**保证**：工具结果预览可用于调试

---

## 运行测试

### 运行所有聊天流测试

```bash
pytest backend/tests/integration/chat/ -v -m integration
```

### 运行特定测试文件

```bash
# 聊天流基础测试
pytest backend/tests/integration/chat/test_chat_stream.py -v

# SSE 事件结构测试
pytest backend/tests/integration/chat/test_sse_events.py -v

# 工具调用测试
pytest backend/tests/integration/chat/test_tool_calls.py -v
```

### 运行单个测试

```bash
pytest backend/tests/integration/chat/test_chat_stream.py::TestChatStreamIntegration::test_chat_stream_basic_flow -v
```

---

## 质量保证总结

| 模块 | 测试数量 | 保证的核心能力 |
|------|---------|---------------|
| 聊天流 | 5 | 完整对话流程、事件序列、错误处理 |
| SSE 事件 | 8 | 事件结构正确、编码标准、版本控制 |
| 工具调用 | 9 | 工具执行、错误处理、多步骤任务 |

**总计 22 个集成测试用例**，覆盖聊天流的核心功能。
