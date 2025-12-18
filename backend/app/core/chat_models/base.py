"""推理模型基类定义。

本文件做什么：
- 定义 `BaseReasoningChatModel`：推理模型基类，负责把“推理内容”归一化到统一字段
- 定义 `StandardChatModel`：标准模型实现，不处理推理内容

本文件不做什么：
- 不包含具体平台的实现逻辑（平台差异由可选覆盖钩子 `_extract_reasoning_content` 处理）
- 不包含模型匹配和注册逻辑（参见 `registry.py`）

------------------------------------------------------------
前因后果（为什么要在这里做“归一化”）
------------------------------------------------------------

LangChain 的 OpenAI 集成在“流式输出（streaming）”上存在两条并行路径：

1) 路径 A：Chat Completions streaming（OpenAI v1 / choices[0].delta）
2) 路径 B：Responses API streaming（OpenAI responses / 事件流 chunk.type）

两条路径在上游 chunk 结构、以及 LangChain 转换出的 `AIMessageChunk` 结构上差异很大。
更关键的是：

- 路径 A：推理内容可能出现在原始 chunk 的 `choices[0].delta.reasoning`
  或 `choices[0].delta.reasoning_content`，但 LangChain 默认不会把这些字段放到
  `AIMessageChunk.additional_kwargs`。

- 路径 B：推理内容主要出现在 `AIMessageChunk.content` 里，作为 content blocks
  （`{"type": "reasoning", ...}`），而不是 `additional_kwargs`。

因此，如果业务层（Agent / SSE / 前端协议）想要“稳定地消费推理内容”，必须在模型层
把不同来源统一成同一个字段，否则业务层就会被迫写大量 if/else 并跟随 LangChain 升级
而频繁改动。

------------------------------------------------------------
本项目的统一约定（最终形态）
------------------------------------------------------------

无论上游走哪条路径、供应商用哪个字段名、LangChain 处于哪个 output_version：

- 我们统一写入：

  `AIMessageChunk.additional_kwargs["reasoning_content"]: str`

业务层（例如 Agent 流式推送逻辑）只读取 `reasoning_content` 即可。

该归一化由 `_ensure_reasoning_content(...)` 完成。

------------------------------------------------------------
路径 A：Chat Completions streaming（raw chunk 结构与归一化）
------------------------------------------------------------

上游 raw chunk（典型结构，dict）：

```python
chunk = {
    "id": "chatcmpl_...",
    "model": "...",
    "choices": [
        {
            "index": 0,
            "delta": {
                # 文本增量：
                "content": "hello",

                # 推理增量（OpenAI 标准推理模型常见字段）：
                "reasoning": "step 1 ...",

                # 推理增量（部分兼容平台/代理字段名）：
                "reasoning_content": "...",
            },
            "finish_reason": None,
        }
    ],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}
```

LangChain 产物（本项目可观察到的关键字段）：

- `ChatGenerationChunk.message` 是 `AIMessageChunk`
- `AIMessageChunk.content` 通常是字符串（增量文本）
- `AIMessageChunk.additional_kwargs` 默认不会包含 reasoning 字段

本项目做的归一化：

- 从 raw chunk 中优先抽取：
  - `choices[0].delta.reasoning`
  - `choices[0].delta.reasoning_content`
  - 或者 chunk 根层同名字段
- 写入：`additional_kwargs["reasoning_content"]`

归一化入口：`_convert_chunk_to_generation_chunk(...) -> _ensure_reasoning_content(...)`

------------------------------------------------------------
路径 B：Responses API streaming（事件流结构与归一化）
------------------------------------------------------------

在 Responses API streaming 中，OpenAI 返回的是“事件流”。LangChain 会把事件流
增量转换为 `AIMessageChunk.content = list[dict]`（content blocks）。关键点：

- 文本块（示例）：

```python
{"type": "text", "text": "foo", "index": 0}
```

- 推理块（示例）：

```python
{
    "type": "reasoning",
    "summary": [
        {"type": "summary_text", "text": "A", "index": 0},
        {"type": "summary_text", "text": "B", "index": 1},
    ],
    "index": 2,
    "id": "msg_...",  # 有些事件/版本会带
}
```

注意：路径 B 的推理信息通常不在 raw dict chunk 里，也不在 `additional_kwargs`，而是在
`message.content` 的 reasoning blocks 中。

为了保证路径 B 也能得到统一字段，本项目在 `BaseReasoningChatModel` 中额外 override：

- `_stream_responses(...)`
- `_astream_responses(...)`

对 super() yield 出来的每个 `ChatGenerationChunk` 执行 `_ensure_reasoning_content`，从
`message.content` blocks 提取 reasoning 并写入 `additional_kwargs["reasoning_content"]`。

------------------------------------------------------------
v0 compat（LangChain 兼容层 additional_kwargs["reasoning"]）
------------------------------------------------------------

LangChain 为旧版本格式提供兼容转换：在某些 output_version 下，会把 reasoning blocks
搬运/折叠到：

`AIMessageChunk.additional_kwargs["reasoning"]: dict`

此时我们仍需要把它统一转成 `reasoning_content: str`。
本项目会从该 dict 中尝试提取：

- `summary[].text`
- `text`

并拼接成最终字符串。
"""

from abc import ABC
from collections.abc import AsyncIterator, Iterator
from typing import Any

from langchain_openai import ChatOpenAI


def _extract_reasoning_content_from_message_content(content: Any) -> str | None:
    """从 `AIMessageChunk.content` 的 reasoning blocks 中提取推理文本。

    适用场景：
    - Responses API streaming（路径 B）：LangChain 会将 reasoning 作为 content blocks 放入
      `AIMessageChunk.content: list[dict]`。
    - 其它返回 content blocks 的实现也可复用。

    Args:
        content: `AIMessageChunk.content`，在路径 B 下通常为 `list[dict]`。

    Returns:
        拼接后的推理文本（可能为空字符串，此时返回 None）。
    """
    if not isinstance(content, list):
        return None

    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "reasoning":
            continue

        summary = block.get("summary")
        if isinstance(summary, list):
            for item in summary:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text:
                    parts.append(text)

        text = block.get("text")
        if isinstance(text, str) and text:
            parts.append(text)

    joined = "".join(parts)
    return joined or None


def _extract_reasoning_content_from_v03_reasoning_dict(reasoning: Any) -> str | None:
    """从 LangChain v0 compat 的 `additional_kwargs["reasoning"]`（dict）提取推理文本。

    适用场景：
    - 某些 output_version 下，LangChain 会把 reasoning blocks 从 message.content 搬运到
      `additional_kwargs["reasoning"]`。

    Args:
        reasoning: `AIMessageChunk.additional_kwargs.get("reasoning")`

    Returns:
        拼接后的推理文本。
    """
    if not isinstance(reasoning, dict):
        return None
    return _extract_reasoning_content_from_message_content([reasoning])


class BaseReasoningChatModel(ChatOpenAI, ABC):
    """推理模型抽象基类

    所有支持推理内容的模型实现都应该继承此类。
    通过多态特性，Agent 层可以无感知地使用不同的模型实现。
    """

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> Any:
        """路径 A 注入点：将 ChatCompletions streaming 的 raw dict chunk 归一化。

        LangChain `ChatOpenAI._convert_chunk_to_generation_chunk` 会把 raw dict chunk 转为
        `ChatGenerationChunk(message=AIMessageChunk(...))`，但不会自动处理推理字段。

        本项目在这里做两件事：
        1) 调用 super() 获得 `generation_chunk`
        2) 调用 `_ensure_reasoning_content(message, raw_chunk=chunk)`，尝试从 raw chunk
           的 `choices[0].delta.reasoning` / `choices[0].delta.reasoning_content` 等字段抽取
           推理文本，并写入 `additional_kwargs["reasoning_content"]`
        """
        # 调用父类方法获取基础转换
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )

        if generation_chunk is None:
            return None

        if not hasattr(generation_chunk.message, "additional_kwargs"):
            generation_chunk.message.additional_kwargs = {}

        self._ensure_reasoning_content(generation_chunk.message, raw_chunk=chunk)

        return generation_chunk

    def _stream_responses(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """路径 B 注入点（同步）：对 Responses API streaming 的产物做后处理归一化。

        `ChatOpenAI._stream_responses` 直接 yield `ChatGenerationChunk`，其 message.content
        往往是 content blocks（list[dict]），其中 reasoning 存在于 `{"type": "reasoning"}`
        block。此路径不会经过 `_convert_chunk_to_generation_chunk`，因此必须在这里统一注入。
        """
        for generation_chunk in super()._stream_responses(
            messages, stop=stop, run_manager=run_manager, **kwargs
        ):
            self._ensure_reasoning_content(getattr(generation_chunk, "message", None))
            yield generation_chunk

    async def _astream_responses(
        self,
        messages: list[Any],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[Any]:
        """路径 B 注入点（异步）：对 Responses API streaming 的产物做后处理归一化。"""
        async for generation_chunk in super()._astream_responses(
            messages, stop=stop, run_manager=run_manager, **kwargs
        ):
            self._ensure_reasoning_content(getattr(generation_chunk, "message", None))
            yield generation_chunk

    def _extract_reasoning_content_from_chunk_fields(
        self, chunk: dict, delta_fields: tuple[str, ...]
    ) -> str | None:
        """从路径 A 的 raw dict chunk 中按字段优先级抽取推理文本。

        Args:
            chunk: Chat Completions streaming 的 raw dict chunk。
            delta_fields: 需要尝试的字段名列表，既会尝试 `choices[0].delta`，也会尝试 chunk 根层。

        Returns:
            第一个命中的非空字符串。
        """
        if not isinstance(chunk, dict):
            return None

        choices = chunk.get("choices", [])
        if choices and len(choices) > 0:
            choice0 = choices[0]
            delta = choice0.get("delta", {}) if isinstance(choice0, dict) else {}
            if isinstance(delta, dict):
                for field in delta_fields:
                    value = delta.get(field)
                    if isinstance(value, str) and value:
                        return value

        for field in delta_fields:
            value = chunk.get(field)
            if isinstance(value, str) and value:
                return value

        return None

    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        """从 chunk 中提取推理内容（可选覆盖钩子）。

        默认实现同时兼容 OpenAI 标准 `reasoning` 与各类兼容平台常见的
        `reasoning_content` 字段。子类可覆盖此方法实现平台特定逻辑。
        """

        return self._extract_reasoning_content_from_chunk_fields(
            chunk, ("reasoning", "reasoning_content")
        )

    def _extract_reasoning_content_from_message(self, message: Any) -> str | None:
        """从 LangChain 的 message 对象中提取推理文本。

        覆盖范围：
        - `additional_kwargs["reasoning_content"]`：若已存在则直接使用
        - `additional_kwargs["reasoning"]`：v0 compat dict，解析 summary/text
        - `message.content`：Responses API 的 reasoning blocks
        """
        if message is None:
            return None

        additional_kwargs = getattr(message, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            existing = additional_kwargs.get("reasoning_content")
            if isinstance(existing, str) and existing:
                return existing

            v03_reasoning = additional_kwargs.get("reasoning")
            v03_extracted = _extract_reasoning_content_from_v03_reasoning_dict(v03_reasoning)
            if v03_extracted:
                return v03_extracted

        return _extract_reasoning_content_from_message_content(
            getattr(message, "content", None)
        )

    def _ensure_reasoning_content(self, message: Any, *, raw_chunk: dict | None = None) -> None:
        """保证 message 上存在统一字段 `additional_kwargs["reasoning_content"]`。

        这是本项目的“归一化核心函数”。它把不同来源的推理信息，统一转换为一个稳定的字符串字段。

        归一化顺序（只在未存在 reasoning_content 时执行）：
        1) 如果提供了 `raw_chunk`（路径 A）：优先从 raw chunk 的 delta/root 字段提取
        2) 否则/提取失败：从 message 上提取（v0 compat additional_kwargs["reasoning"] 或
           Responses content blocks）

        重要约束：
        - 不覆盖已有的 `reasoning_content`（避免重复拼接/覆盖导致前端显示异常）
        """
        if message is None:
            return

        additional_kwargs = getattr(message, "additional_kwargs", None)
        if not isinstance(additional_kwargs, dict):
            message.additional_kwargs = {}
            additional_kwargs = message.additional_kwargs

        existing = additional_kwargs.get("reasoning_content")
        if isinstance(existing, str) and existing:
            return

        reasoning_content: str | None = None
        if isinstance(raw_chunk, dict):
            reasoning_content = self._extract_reasoning_content(raw_chunk)
            if not reasoning_content:
                reasoning_content = self._extract_reasoning_content_from_chunk_fields(
                    raw_chunk, ("reasoning", "reasoning_content")
                )

        if not reasoning_content:
            reasoning_content = self._extract_reasoning_content_from_message(message)

        if reasoning_content:
            additional_kwargs["reasoning_content"] = reasoning_content


class StandardChatModel(ChatOpenAI):
    """标准模型实现（不支持推理内容）

    这是默认实现，用于不支持推理内容的模型。
    直接使用 ChatOpenAI，不做任何修改。
    """

    pass
