
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
        "reasoning": "...",
        "index": current_index,
        "id": "msg_..."  # 某些事件里会有
      }
      ```

---

## Chat Models v1 架构

## 核心设计

本模块强制使用 **LangChain v1 输出格式**，基于 `content_blocks` 标准化消息内容。

**关键特性**：
- **强制** `output_version="v1"`，不可配置
- 使用 LangChain 标准 `content_blocks` 而非自定义结构
- 按块类型（text/reasoning/tool_call）分流处理
- **移除** 对 `model.extract_reasoning()` 的依赖

---

## 目录结构

```
chat_models/
├── __init__.py          # 统一入口（导出 v1 API）
├── registry.py          # 模型创建工厂（强制 v1）
├── v1/                  # ✨ v1 标准实现
│   ├── __init__.py
│   ├── types.py         # 类型定义、类型守卫
│   ├── parser.py        # 内容块解析器
│   └── models.py        # 模型基类（强制 v1 输出）
├── v0/                  # 兼容层（已废弃）
│   ├── __init__.py
│   ├── base.py          # 旧版 ReasoningChunk 结构
│   └── providers/
│       └── reasoning_content.py  # 旧版 SiliconFlow 实现
└── README.md            # 本文档
```

---

## v1 使用方式

```python
from app.core.chat_models import create_chat_model, parse_content_blocks
from app.services.agent.streams import StreamingResponseHandler

# 创建模型（默认 v1）
model = create_chat_model(
    model="...",
    base_url="...",
    api_key="...",
    provider="siliconflow",
)

# StreamingResponseHandler 自动检测版本
handler = StreamingResponseHandler(emitter=emitter, model=model)

# 或手动解析
parsed = parse_content_blocks(message)
print(parsed.text)       # 合并后的文本
print(parsed.reasoning)  # 合并后的推理
```

---

## v0 兼容模式（回退）

```python
# 创建 v0 模型
model = create_chat_model(..., use_v0=True)

# StreamingResponseHandler 自动检测为 v0，使用 model.extract_reasoning()
handler = StreamingResponseHandler(emitter=emitter, model=model)
```

---

## 版本自动检测机制

`StreamingResponseHandler` 根据 `model._chat_model_version` 属性自动选择解析方式：

```python
from app.core.chat_models import is_v1_model

is_v1_model(model)  # True: v1, False: v0
```

**设计优势**：
- 调用方只需在 `create_chat_model` 时指定版本
- `StreamingResponseHandler` 自动跟随，无需额外参数
- 避免版本不一致问题

---

## v1 vs v0 对比

| 特性 | v1（默认） | v0（兼容层） |
|------|-----------|-------------|
| 输出格式 | 强制 `output_version="v1"` | 默认 v0 |
| 内容解析 | `parse_content_blocks()` | `model.extract_reasoning()` |
| 数据结构 | LangChain 标准 `ContentBlock` | 自定义 `ReasoningChunk` |
| 版本标识 | `_chat_model_version="v1"` | 无该属性 |
| Handler 依赖 | 无需 model 引用 | 需要 model 实例 |

---

## 标准内容块类型

```python
@dataclass(frozen=True, slots=True)
class ReasoningChunk:
    delta: str              # 推理增量文本
    provider: str           # 来源平台标识（siliconflow, openai, ...）
    source: str             # 数据来源路径（chunk.delta.reasoning_content, ...）
```

---

## 使用方式

```python
from app.core.chat_models import create_chat_model

# 创建模型（自动选择实现）
model = create_chat_model(
    model="moonshotai/Kimi-K2-Thinking",
    base_url="https://api.siliconflow.cn/v1",
    api_key="sk-...",
    provider="siliconflow",
    profile={"reasoning_output": True},
)

# Agent 层获取推理内容（统一接口）
reasoning = model.extract_reasoning(message)
if reasoning:
    print(reasoning.delta)  # 推理增量文本
```

---

## LangChain 两条 streaming 路径（供 provider 子类参考）

### 路径 A：Chat Completions streaming
- 原始结构：`chunk["choices"][0]["delta"]["reasoning_content"]`（SiliconFlow）
- 原始结构：`chunk["choices"][0]["delta"]["reasoning"]`（OpenAI）
- LangChain 不会自动放入 additional_kwargs
- **本项目做法**：在 `_convert_chunk_to_generation_chunk` 中提取，存入 `message._reasoning_chunk`

### 路径 B：Responses API streaming
- 原始结构：`message.content = [{"type": "reasoning", "summary": [...]}]`
- LangChain 会把 reasoning 作为 content blocks
- **本项目做法**：如需支持，在 `_stream_responses` 中提取

---

## 扩展方式（新增平台）

1. 在 `providers/` 下新建文件（如 `moonshot.py`）
2. 继承 `BaseReasoningChatModel`
3. 实现 `provider_name` 属性和 `_normalize_reasoning_from_chunk()` 方法
4. 在 `registry.py` 的 `REASONING_MODEL_REGISTRY` 中注册

```python
# providers/moonshot.py
class MoonshotReasoningChatModel(BaseReasoningChatModel):
    @property
    def provider_name(self) -> str:
        return "moonshot"
    
    def _normalize_reasoning_from_chunk(self, chunk, message):
        # 从 chunk 中提取推理内容
        ...
```

```python
# registry.py
REASONING_MODEL_REGISTRY = {
    "siliconflow": (...),
    "moonshot": ("app.core.chat_models.providers.moonshot", "MoonshotReasoningChatModel"),
}
```

**Agent 层代码无需任何修改。**

