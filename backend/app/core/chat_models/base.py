"""推理模型基类定义。

本文件做什么：
- 定义 `BaseReasoningChatModel`：抽象基类，统一处理推理内容提取
- 定义 `StandardChatModel`：标准模型实现，不处理推理内容

本文件不做什么：
- 不包含具体平台的实现逻辑
- 不包含模型匹配和注册逻辑
"""

from abc import ABC, abstractmethod
from typing import Any

from langchain_openai import ChatOpenAI


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
        """转换 chunk 以支持推理内容

        子类可以重写此方法来实现平台特定的推理内容提取逻辑。
        """
        # 调用父类方法获取基础转换
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )

        if generation_chunk is None:
            return None

        # 提取推理内容（由子类实现具体逻辑）
        reasoning_content = self._extract_reasoning_content(chunk)

        if reasoning_content:
            if not hasattr(generation_chunk.message, "additional_kwargs"):
                generation_chunk.message.additional_kwargs = {}

            generation_chunk.message.additional_kwargs["reasoning_content"] = reasoning_content

        return generation_chunk

    @abstractmethod
    def _extract_reasoning_content(self, chunk: dict) -> str | None:
        """从 chunk 中提取推理内容

        子类必须实现此方法，定义如何从平台特定的响应格式中提取推理内容。

        Args:
            chunk: 原始 chunk 数据（dict 格式）

        Returns:
            推理内容字符串，如果没有则返回 None
        """
        pass


class StandardChatModel(ChatOpenAI):
    """标准模型实现（不支持推理内容）

    这是默认实现，用于不支持推理内容的模型。
    直接使用 ChatOpenAI，不做任何修改。
    """

    pass
