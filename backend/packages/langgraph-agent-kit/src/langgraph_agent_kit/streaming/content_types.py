"""v1 内容块类型定义

提供 LangChain v1 content_blocks 的类型守卫函数。
"""

from typing import Any, TypeGuard

try:
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
except ImportError:
    # 兼容旧版本 langchain_core
    ContentBlock = dict
    TextContentBlock = dict
    ReasoningContentBlock = dict
    ToolCallBlock = dict
    ToolCallChunk = dict
    InvalidToolCall = dict
    ImageContentBlock = dict
    AudioContentBlock = dict
    VideoContentBlock = dict
    FileContentBlock = dict
    NonStandardContentBlock = dict

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
