
# 1) LangChain OpenAI：两种 streaming 路径与数据结构（源码对齐）

你现在遇到的“推理字段从哪里来”，本质上取决于 LangChain 走的是哪条流式路径：

## 1.1 路径 A：Chat Completions streaming（`chunk["choices"][0]["delta"]`）

对应源码（[langchain_openai/chat_models/base.py::_convert_chunk_to_generation_chunk](cci:1://file:///Users/wang/code/github/langchain/libs/partners/openai/langchain_openai/chat_models/base.py:1060:4-1122:9)）：

- **输入 `chunk`（dict）典型结构**
  - `chunk["choices"]` 是 list，取第一个 `choice`
  - `choice["delta"]` 是 dict（如果 `None` 直接跳过）
  - `choice["finish_reason"]` 可能出现于最后一个 chunk
  - `chunk["usage"]` 可能存在（用于 usage metadata）

- **LangChain 输出**
  - 返回 `ChatGenerationChunk(message=message_chunk, generation_info=...)`
  - 其中 `message_chunk` 由 [_convert_delta_to_message_chunk(delta, ...)](cci:1://file:///Users/wang/code/github/langchain/libs/partners/openai/langchain_openai/chat_models/base.py:361:0-414:75) 构造
  - **关键点：LangChain 默认不会把 `delta.reasoning` / `delta.reasoning_content` 放进 `additional_kwargs`**
    - 它主要处理 `content`、`function_call`、`tool_calls` 等
    - 所以你才需要在你项目层做注入

- **最终你在 Agent 层能拿到的结构（典型）**
  - `generation_chunk.message` 是 `AIMessageChunk`
  - `generation_chunk.message.content` 通常是字符串（或在新 output_version 下可能是 list，但 ChatCompletions 更常见还是增量文本）
  - `generation_chunk.message.additional_kwargs` 里**默认没有** reasoning，需要你注入

你项目里目前的两类 provider：
- OpenAI 标准：从 `choices[0].delta.reasoning` 取
- SiliconFlow/兼容：从 `choices[0].delta.reasoning_content` 取  
这正好覆盖了 ChatCompletions 的两种供应商差异。

---

## 1.2 路径 B：Responses API streaming（事件流：`response.output_text.delta` / `response.reasoning_summary_text.delta` 等）

对应源码（同文件 [langchain_openai/chat_models/base.py::_stream_responses](cci:1://file:///Users/wang/code/github/langchain/libs/partners/openai/langchain_openai/chat_models/base.py:1134:4-1186:42) + [_convert_responses_chunk_to_generation_chunk](cci:1://file:///Users/wang/code/github/langchain/libs/partners/openai/langchain_openai/chat_models/base.py:4357:0-4596:5)）：

- **输入 `chunk` 不是 dict choices delta，而是 event 对象**（`chunk.type` 是字符串枚举）
  - 常见类型：
    - `response.output_text.delta`：输出文本增量
    - `response.reasoning_summary_text.delta`：推理摘要增量
    - `response.output_item.added` 且 `chunk.item.type == "reasoning"`：推理块出现
    - `response.completed` / `response.incomplete`：收尾/结束

- **LangChain 输出（非常关键）**
  - 返回 `ChatGenerationChunk(message=AIMessageChunk(...))`
  - `AIMessageChunk.content` 是 **list[dict]**（content blocks）
    - 文本块会被归一为形如：
      ```python
      {"type": "text", "text": "...", "index": current_index}
      ```
    - 推理块会被塞进 content list，典型形如：
      ```python
      {
        "type": "reasoning",
        "summary": [{"index": ..., "type": "summary_text", "text": "..."}],
        "index": current_index,
        "id": "msg_..."  # 某些事件里会有
      }
      ```
  - `additional_kwargs` 在这条路径里主要用于：
    - `parsed`（结构化输出解析结果等）
    - **不是 reasoning 的主要落点**（reasoning 主要在 `content` blocks 里）

- **兼容层（[_compat._convert_to_v03_ai_message](cci:1://file:///Users/wang/code/github/langchain/libs/partners/openai/langchain_openai/chat_models/_compat.py:80:0-149:18)）**
  - 如果 `output_version == "v0"`，LangChain 会把 `content` 里的 `{"type":"reasoning", ...}` **挪到** `message.additional_kwargs["reasoning"]`
  - 注意：它用的是 key `"reasoning"`，不是 `"reasoning_content"`  
  - 这就是你要“向后兼容”时必须面对的差异之一：  
    - v0.3 风格：reasoning 在 `additional_kwargs["reasoning"]`（dict 形态）
    - Responses/v1 风格：reasoning 在 `content` blocks（list[dict] 形态）

