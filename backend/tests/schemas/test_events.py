"""Events Schema 测试"""

from app.schemas.events import (
    StreamEventType,
    StreamLevelEventType,
    LLMCallBoundaryEventType,
    LLMCallInternalEventType,
    ToolCallEventType,
    DataEventType,
    PostProcessEventType,
    SupportEventType,
    SupervisorEventType,
    MetaStartPayload,
    TextDeltaPayload,
    ToolStartPayload,
    ToolEndPayload,
    LlmCallStartPayload,
    LlmCallEndPayload,
    ErrorPayload,
    TodoItem,
    TodosPayload,
    ContextSummarizedPayload,
    ContextTrimmedPayload,
    AgentRoutedPayload,
    AgentHandoffPayload,
    AgentCompletePayload,
)


class TestStreamLevelEventType:
    """测试流级别事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert StreamLevelEventType.META_START == "meta.start"
        assert StreamLevelEventType.ASSISTANT_FINAL == "assistant.final"
        assert StreamLevelEventType.ERROR == "error"


class TestLLMCallBoundaryEventType:
    """测试 LLM 调用边界事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert LLMCallBoundaryEventType.LLM_CALL_START == "llm.call.start"
        assert LLMCallBoundaryEventType.LLM_CALL_END == "llm.call.end"


class TestLLMCallInternalEventType:
    """测试 LLM 调用内部事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert LLMCallInternalEventType.ASSISTANT_REASONING_DELTA == "assistant.reasoning.delta"
        assert LLMCallInternalEventType.ASSISTANT_DELTA == "assistant.delta"


class TestToolCallEventType:
    """测试工具调用事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert ToolCallEventType.TOOL_START == "tool.start"
        assert ToolCallEventType.TOOL_END == "tool.end"


class TestDataEventType:
    """测试数据事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert DataEventType.ASSISTANT_PRODUCTS == "assistant.products"
        assert DataEventType.ASSISTANT_TODOS == "assistant.todos"
        assert DataEventType.CONTEXT_SUMMARIZED == "context.summarized"
        assert DataEventType.CONTEXT_TRIMMED == "context.trimmed"


class TestPostProcessEventType:
    """测试后处理事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert PostProcessEventType.MEMORY_EXTRACTION_START == "memory.extraction.start"
        assert PostProcessEventType.MEMORY_EXTRACTION_COMPLETE == "memory.extraction.complete"
        assert PostProcessEventType.MEMORY_PROFILE_UPDATED == "memory.profile.updated"


class TestSupportEventType:
    """测试客服支持事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert SupportEventType.SUPPORT_HANDOFF_STARTED == "support.handoff_started"
        assert SupportEventType.SUPPORT_HANDOFF_ENDED == "support.handoff_ended"
        assert SupportEventType.SUPPORT_HUMAN_MESSAGE == "support.human_message"
        assert SupportEventType.SUPPORT_CONNECTED == "support.connected"
        assert SupportEventType.SUPPORT_PING == "support.ping"


class TestSupervisorEventType:
    """测试 Supervisor 事件类型"""

    def test_event_values(self):
        """测试事件值"""
        assert SupervisorEventType.AGENT_ROUTED == "agent.routed"
        assert SupervisorEventType.AGENT_HANDOFF == "agent.handoff"
        assert SupervisorEventType.AGENT_COMPLETE == "agent.complete"


class TestStreamEventType:
    """测试完整的流事件类型枚举"""

    def test_all_events_present(self):
        """测试所有事件类型都存在"""
        # 流级别
        assert StreamEventType.META_START == "meta.start"
        assert StreamEventType.ASSISTANT_FINAL == "assistant.final"
        assert StreamEventType.ERROR == "error"

        # LLM 调用
        assert StreamEventType.LLM_CALL_START == "llm.call.start"
        assert StreamEventType.LLM_CALL_END == "llm.call.end"
        assert StreamEventType.ASSISTANT_REASONING_DELTA == "assistant.reasoning.delta"
        assert StreamEventType.ASSISTANT_DELTA == "assistant.delta"

        # 工具调用
        assert StreamEventType.TOOL_START == "tool.start"
        assert StreamEventType.TOOL_END == "tool.end"

        # 数据事件
        assert StreamEventType.ASSISTANT_PRODUCTS == "assistant.products"
        assert StreamEventType.ASSISTANT_TODOS == "assistant.todos"

        # 后处理
        assert StreamEventType.MEMORY_EXTRACTION_START == "memory.extraction.start"
        assert StreamEventType.MEMORY_EXTRACTION_COMPLETE == "memory.extraction.complete"

        # Supervisor
        assert StreamEventType.AGENT_ROUTED == "agent.routed"
        assert StreamEventType.AGENT_HANDOFF == "agent.handoff"


class TestPayloadTypedDicts:
    """测试 Payload TypedDict 结构"""

    def test_meta_start_payload(self):
        """测试 MetaStartPayload"""
        payload: MetaStartPayload = {
            "user_message_id": "msg_user_123",
            "assistant_message_id": "msg_asst_456",
        }
        assert payload["user_message_id"] == "msg_user_123"
        assert payload["assistant_message_id"] == "msg_asst_456"

    def test_text_delta_payload(self):
        """测试 TextDeltaPayload"""
        payload: TextDeltaPayload = {"delta": "Hello"}
        assert payload["delta"] == "Hello"

    def test_tool_start_payload(self):
        """测试 ToolStartPayload"""
        payload: ToolStartPayload = {
            "tool_call_id": "call_123",
            "name": "search_products",
            "input": {"query": "手机"},
        }
        assert payload["name"] == "search_products"

    def test_tool_end_payload(self):
        """测试 ToolEndPayload"""
        payload: ToolEndPayload = {
            "tool_call_id": "call_123",
            "name": "search_products",
            "status": "success",
            "count": 5,
        }
        assert payload["status"] == "success"
        assert payload["count"] == 5

    def test_llm_call_start_payload(self):
        """测试 LlmCallStartPayload"""
        payload: LlmCallStartPayload = {
            "message_count": 10,
            "llm_call_id": "llm_123",
        }
        assert payload["message_count"] == 10

    def test_llm_call_end_payload(self):
        """测试 LlmCallEndPayload"""
        payload: LlmCallEndPayload = {
            "elapsed_ms": 1500,
            "message_count": 12,
        }
        assert payload["elapsed_ms"] == 1500

    def test_error_payload(self):
        """测试 ErrorPayload"""
        payload: ErrorPayload = {
            "message": "服务器错误",
            "code": "internal_error",
        }
        assert payload["message"] == "服务器错误"

    def test_todo_item(self):
        """测试 TodoItem"""
        item: TodoItem = {
            "content": "搜索商品",
            "status": "completed",
        }
        assert item["content"] == "搜索商品"
        assert item["status"] == "completed"

    def test_todos_payload(self):
        """测试 TodosPayload"""
        payload: TodosPayload = {
            "todos": [
                {"content": "任务1", "status": "pending"},
                {"content": "任务2", "status": "in_progress"},
            ]
        }
        assert len(payload["todos"]) == 2

    def test_context_summarized_payload(self):
        """测试 ContextSummarizedPayload"""
        payload: ContextSummarizedPayload = {
            "messages_before": 100,
            "messages_after": 20,
            "tokens_before": 5000,
            "tokens_after": 1000,
        }
        assert payload["messages_before"] == 100
        assert payload["messages_after"] == 20

    def test_context_trimmed_payload(self):
        """测试 ContextTrimmedPayload"""
        payload: ContextTrimmedPayload = {
            "messages_before": 60,
            "messages_after": 50,
            "strategy": "messages",
        }
        assert payload["strategy"] == "messages"

    def test_agent_routed_payload(self):
        """测试 AgentRoutedPayload"""
        payload: AgentRoutedPayload = {
            "source_agent": "supervisor",
            "target_agent": "product_agent",
            "target_agent_name": "商品推荐助手",
            "reason": "用户询问商品推荐",
        }
        assert payload["target_agent"] == "product_agent"

    def test_agent_handoff_payload(self):
        """测试 AgentHandoffPayload"""
        payload: AgentHandoffPayload = {
            "from_agent": "faq_agent",
            "to_agent": "product_agent",
            "to_agent_name": "商品助手",
        }
        assert payload["from_agent"] == "faq_agent"

    def test_agent_complete_payload(self):
        """测试 AgentCompletePayload"""
        payload: AgentCompletePayload = {
            "agent_id": "product_agent",
            "agent_name": "商品助手",
            "elapsed_ms": 2000,
            "status": "success",
        }
        assert payload["elapsed_ms"] == 2000
