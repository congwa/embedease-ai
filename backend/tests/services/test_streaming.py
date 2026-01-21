"""Streaming 服务测试

测试 SSE 流服务的逻辑。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.schemas.events import (
    StreamLevelEventType,
    LLMCallBoundaryEventType,
    LLMCallInternalEventType,
    ToolCallEventType,
    DataEventType,
)


class TestStreamLevelEventType:
    """测试流级别事件类型"""

    def test_meta_start_event(self):
        """测试 meta.start 事件"""
        assert StreamLevelEventType.META_START.value == "meta.start"

    def test_assistant_final_event(self):
        """测试 assistant.final 事件"""
        assert StreamLevelEventType.ASSISTANT_FINAL.value == "assistant.final"

    def test_error_event(self):
        """测试 error 事件"""
        assert StreamLevelEventType.ERROR.value == "error"


class TestLLMCallBoundaryEventType:
    """测试 LLM 调用边界事件"""

    def test_llm_call_start(self):
        """测试 LLM 调用开始事件"""
        assert LLMCallBoundaryEventType.LLM_CALL_START.value == "llm.call.start"

    def test_llm_call_end(self):
        """测试 LLM 调用结束事件"""
        assert LLMCallBoundaryEventType.LLM_CALL_END.value == "llm.call.end"


class TestToolCallEventType:
    """测试工具调用事件"""

    def test_tool_start(self):
        """测试工具开始事件"""
        assert ToolCallEventType.TOOL_START.value == "tool.start"

    def test_tool_end(self):
        """测试工具结束事件"""
        assert ToolCallEventType.TOOL_END.value == "tool.end"


class TestStreamEventValues:
    """测试所有流事件值"""

    def test_stream_level_events_have_string_values(self):
        """测试流级别事件都有字符串值"""
        for event in StreamLevelEventType:
            assert isinstance(event.value, str)
            assert len(event.value) > 0

    def test_llm_boundary_events_have_string_values(self):
        """测试 LLM 边界事件都有字符串值"""
        for event in LLMCallBoundaryEventType:
            assert isinstance(event.value, str)
            assert len(event.value) > 0

    def test_tool_events_have_string_values(self):
        """测试工具事件都有字符串值"""
        for event in ToolCallEventType:
            assert isinstance(event.value, str)
            assert len(event.value) > 0
