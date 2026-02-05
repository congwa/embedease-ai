"""v1 内容块解析器

提供按块类型分流的解析功能，将 AIMessage/AIMessageChunk 的 content_blocks
解析为结构化的 ParsedContent。
"""

from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, AIMessageChunk

from langgraph_agent_kit.streaming.content_types import (
    is_text_block,
    is_reasoning_block,
    is_tool_call_block,
    is_tool_call_chunk_block,
    get_block_type,
)

__all__ = [
    "ParsedContent",
    "parse_content_blocks",
    "parse_content_blocks_from_chunk",
]


@dataclass
class ParsedContent:
    """解析后的内容结构
    
    将 content_blocks 按类型分流存储，提供便捷的访问接口。
    
    Attributes:
        text_blocks: 文本块列表
        reasoning_blocks: 推理块列表
        tool_calls: 工具调用块列表
        tool_call_chunks: 工具调用增量块列表
        other_blocks: 其他类型块列表
    """
    text_blocks: list[dict[str, Any]] = field(default_factory=list)
    reasoning_blocks: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_chunks: list[dict[str, Any]] = field(default_factory=list)
    other_blocks: list[dict[str, Any]] = field(default_factory=list)
    
    @property
    def text(self) -> str:
        """合并所有文本块的内容"""
        return "".join(
            block.get("text", "") 
            for block in self.text_blocks 
            if isinstance(block.get("text"), str)
        )
    
    @property
    def reasoning(self) -> str:
        """合并所有推理块的内容"""
        return "".join(
            block.get("reasoning", "") 
            for block in self.reasoning_blocks 
            if isinstance(block.get("reasoning"), str)
        )
    
    @property
    def has_text(self) -> bool:
        """是否包含文本内容"""
        return bool(self.text)
    
    @property
    def has_reasoning(self) -> bool:
        """是否包含推理内容"""
        return bool(self.reasoning)
    
    @property
    def has_tool_calls(self) -> bool:
        """是否包含工具调用"""
        return bool(self.tool_calls) or bool(self.tool_call_chunks)
    
    def merge(self, other: "ParsedContent") -> "ParsedContent":
        """合并两个 ParsedContent"""
        return ParsedContent(
            text_blocks=self.text_blocks + other.text_blocks,
            reasoning_blocks=self.reasoning_blocks + other.reasoning_blocks,
            tool_calls=self.tool_calls + other.tool_calls,
            tool_call_chunks=self.tool_call_chunks + other.tool_call_chunks,
            other_blocks=self.other_blocks + other.other_blocks,
        )


def _get_content_blocks(message: AIMessage | AIMessageChunk) -> list[dict[str, Any]]:
    """从消息中获取 content_blocks
    
    优先使用 content_blocks 属性（v1 标准），
    如果 content 本身就是列表则直接使用。
    """
    # v1 模式下，content_blocks 属性会返回标准化的块
    if hasattr(message, "content_blocks"):
        try:
            return list(message.content_blocks)
        except Exception:
            pass
    
    # 降级：直接处理 content
    content = message.content
    if isinstance(content, str):
        if content:
            return [{"type": "text", "text": content}]
        return []
    elif isinstance(content, list):
        return content
    
    return []


def parse_content_blocks(message: AIMessage | AIMessageChunk) -> ParsedContent:
    """解析消息的 content_blocks，按类型分流
    
    Args:
        message: LangChain AIMessage 或 AIMessageChunk
        
    Returns:
        ParsedContent: 按类型分流后的内容结构
    """
    result = ParsedContent()
    blocks = _get_content_blocks(message)
    
    for block in blocks:
        if not isinstance(block, dict):
            # 字符串内容转为文本块
            if isinstance(block, str) and block:
                result.text_blocks.append({"type": "text", "text": block})
            continue
        
        if is_text_block(block):
            result.text_blocks.append(block)
        elif is_reasoning_block(block):
            result.reasoning_blocks.append(block)
        elif is_tool_call_block(block):
            result.tool_calls.append(block)
        elif is_tool_call_chunk_block(block):
            result.tool_call_chunks.append(block)
        else:
            # 其他类型（image, audio, non_standard 等）
            result.other_blocks.append(block)
    
    return result


def parse_content_blocks_from_chunk(
    chunk: AIMessageChunk,
    previous: ParsedContent | None = None,
) -> tuple[ParsedContent, ParsedContent]:
    """从增量消息中解析内容块
    
    用于流式场景，返回当前增量和累积结果。
    
    Args:
        chunk: 当前增量消息
        previous: 之前累积的 ParsedContent（可选）
        
    Returns:
        (delta, accumulated): 当前增量内容和累积内容
    """
    delta = parse_content_blocks(chunk)
    
    if previous is None:
        return delta, delta
    
    accumulated = previous.merge(delta)
    return delta, accumulated
