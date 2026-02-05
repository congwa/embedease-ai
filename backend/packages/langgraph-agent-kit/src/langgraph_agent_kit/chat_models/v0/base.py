"""推理模型基类定义（v0 兼容层 - 已废弃）

⚠️ 本模块已废弃，请使用 v1 模块

============================================================
核心设计理念
============================================================

本模块采用**多态架构**，让不同平台（SiliconFlow、OpenAI 等）在各自的子类中
完成推理内容的提取与归一化，Agent 层只消费统一的 `ReasoningChunk` 结构。

**关键约束**：
- 不再使用 `additional_kwargs["reasoning_content"]`
- Agent 层通过 `extract_reasoning(message)` 获取推理内容
- 新增平台只需继承 `BaseReasoningChatModel` 并覆盖 `_normalize_reasoning_from_chunk()`

============================================================
统一数据结构
============================================================

`ReasoningChunk` 是本项目的推理内容统一载体：

```python
@dataclass
class ReasoningChunk:
    delta: str              # 推理增量文本
    provider: str           # 来源平台标识（siliconflow, openai, ...）
    source: str             # 数据来源路径（chunk.delta, content.block, ...）
```

============================================================
扩展方式
============================================================

新增平台只需：
1. 继承 `BaseReasoningChatModel`
2. 覆盖 `_normalize_reasoning_from_chunk(chunk, message)` 方法
3. 实现 `provider_name` 属性

Agent 层代码无需任何修改。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI


@dataclass(frozen=True, slots=True)
class ReasoningChunk:
    """推理内容统一载体
    
    这是 Agent 层消费推理内容的唯一数据结构。
    不同平台的子类负责把各自的原始格式转换为此结构。
    
    Attributes:
        delta: 推理增量文本（当前 chunk 的推理内容）
        provider: 来源平台标识（如 siliconflow, openai）
        source: 数据来源路径（如 chunk.delta.reasoning_content）
    """
    delta: str
    provider: str = "unknown"
    source: str = "unknown"


class BaseReasoningChatModel(ChatOpenAI, ABC):
    """推理模型抽象基类
    
    所有支持推理内容的模型都应该继承此类并实现 `_normalize_reasoning_from_chunk()`。
    
    设计原则：
    - 基类不写入 additional_kwargs（彻底废弃该方案）
    - 子类通过多态实现平台特定的推理提取逻辑
    - Agent 层通过 `extract_reasoning(message)` 获取统一结构
    
    子类必须实现：
    - `_normalize_reasoning_from_chunk(chunk, message)`: 从原始 chunk/message 提取推理
    - `provider_name`: 平台标识（用于 ReasoningChunk.provider）
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """平台标识（如 siliconflow, openai）
        
        子类必须实现此属性，用于标识推理内容的来源平台。
        """
        ...

    @abstractmethod
    def _normalize_reasoning_from_chunk(
        self,
        chunk: dict | None,
        message: Any,
    ) -> ReasoningChunk | None:
        """从原始 chunk 或 message 中提取推理内容（子类必须实现）
        
        这是多态的核心方法。每个平台子类根据自己的 API 返回结构，
        把推理内容转换为统一的 ReasoningChunk。
        
        Args:
            chunk: 路径 A 的原始 dict chunk（可能为 None）
            message: LangChain 的 AIMessageChunk 对象
        
        Returns:
            ReasoningChunk 或 None（无推理内容时返回 None）
        """
        ...

    def extract_reasoning(
        self, message: Any, *, raw_chunk: dict | None = None
    ) -> ReasoningChunk | None:
        """从 message 中提取推理内容（Agent 层调用此方法）
        
        这是 Agent 层获取推理内容的统一入口。内部会调用子类实现的
        `_normalize_reasoning_from_chunk()` 完成多态转换。
        
        Args:
            message: LangChain 的 AIMessageChunk 或 AIMessage 对象
            raw_chunk: 原始的 dict chunk（路径 A 场景下传入）
        
        Returns:
            ReasoningChunk 或 None
        """
        if message is None:
            return None
        return self._normalize_reasoning_from_chunk(raw_chunk, message)


class StandardChatModel(ChatOpenAI):
    """标准模型实现（非推理模型）
    
    用于 `reasoning_output=False` 的模型，不处理推理内容。
    直接继承 ChatOpenAI，无需任何额外逻辑。
    """
    pass
