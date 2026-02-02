"""v1 内容块类型定义

重导出 LangChain 标准类型，并提供类型守卫函数。
"""

from typing import Any, TypeGuard

from langchain_core.messages.content import (
    ContentBlock,
    TextContentBlock,
    ReasoningContentBlock,
    ToolCall as ToolCallBlock,
    ToolCallChunk,
    InvalidToolCall,
    ImageContentBlock,
    AudioContentBlock,
    VideoContentBlock,
    FileContentBlock,
    NonStandardContentBlock,
)

__all__ = [
    # LangChain 标准类型
    "ContentBlock",
    "TextContentBlock",
    "ReasoningContentBlock",
    "ToolCallBlock",
    "ToolCallChunk",
    "InvalidToolCall",
    "ImageContentBlock",
    "AudioContentBlock",
    "VideoContentBlock",
    "FileContentBlock",
    "NonStandardContentBlock",
    # 类型守卫
    "is_text_block",
    "is_reasoning_block",
    "is_tool_call_block",
    "is_tool_call_chunk_block",
    "is_image_block",
    "get_block_type",
]


def get_block_type(block: dict[str, Any]) -> str | None:
    """获取块类型"""
    if isinstance(block, dict):
        return block.get("type")
    return None


def is_text_block(block: dict[str, Any]) -> TypeGuard[TextContentBlock]:
    """判断是否为文本块"""
    return get_block_type(block) == "text"


def is_reasoning_block(block: dict[str, Any]) -> TypeGuard[ReasoningContentBlock]:
    """判断是否为推理块"""
    return get_block_type(block) == "reasoning"


def is_tool_call_block(block: dict[str, Any]) -> TypeGuard[ToolCallBlock]:
    """判断是否为工具调用块"""
    return get_block_type(block) == "tool_call"


def is_tool_call_chunk_block(block: dict[str, Any]) -> TypeGuard[ToolCallChunk]:
    """判断是否为工具调用增量块"""
    return get_block_type(block) == "tool_call_chunk"


def is_image_block(block: dict[str, Any]) -> TypeGuard[ImageContentBlock]:
    """判断是否为图片块"""
    return get_block_type(block) == "image"
