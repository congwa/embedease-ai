from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from app.services.agent.middleware.llm_call_sse import SSEMiddleware
from app.services.streaming.context import ChatContext


@dataclass
class _DummyEmitter:
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, type: str, payload: Any) -> None:
        self.events.append({"type": type, "payload": payload})


class _DummyTool:
    name = "dummy_tool"
    description = "dummy"


class _DummyModel:
    model_name = "dummy-model"


@pytest.mark.anyio
async def test_sse_middleware_emits_start_end_on_success() -> None:
    emitter = _DummyEmitter()
    chat_context = ChatContext(
        conversation_id="c1",
        user_id="u1",
        assistant_message_id="a1",
        emitter=emitter,
    )
    runtime = Runtime(context=chat_context)

    request = ModelRequest(
        model=_DummyModel(),  # type: ignore[arg-type]
        messages=[HumanMessage(content="hi")],
        system_message=SystemMessage(content="sys"),
        tools=[_DummyTool()],  # type: ignore[list-item]
        runtime=runtime,  # type: ignore[arg-type]
        state={"messages": [HumanMessage(content="hi")]},
    )

    async def handler(_: ModelRequest) -> ModelResponse:
        return ModelResponse(result=[AIMessage(content="ok")], structured_response=None)

    middleware = SSEMiddleware()
    resp = await middleware.awrap_model_call(request, handler)

    assert isinstance(resp, ModelResponse)
    assert len(emitter.events) == 2
    assert emitter.events[0]["type"] == "llm.call.start"
    assert emitter.events[1]["type"] == "llm.call.end"

    start_payload = emitter.events[0]["payload"]
    end_payload = emitter.events[1]["payload"]
    assert isinstance(start_payload, dict)
    assert isinstance(end_payload, dict)

    assert start_payload.get("llm_call_id")
    assert start_payload["llm_call_id"] == end_payload.get("llm_call_id")
    assert start_payload.get("message_count") == 2
    assert end_payload.get("elapsed_ms") is not None


@pytest.mark.anyio
async def test_sse_middleware_emits_end_on_error() -> None:
    emitter = _DummyEmitter()
    chat_context = ChatContext(
        conversation_id="c1",
        user_id="u1",
        assistant_message_id="a1",
        emitter=emitter,
    )
    runtime = Runtime(context=chat_context)

    request = ModelRequest(
        model=_DummyModel(),  # type: ignore[arg-type]
        messages=[HumanMessage(content="hi")],
        system_message=None,
        tools=[],
        runtime=runtime,  # type: ignore[arg-type]
        state={"messages": [HumanMessage(content="hi")]},
    )

    async def handler(_: ModelRequest) -> ModelResponse:
        raise RuntimeError("boom")

    middleware = SSEMiddleware()
    with pytest.raises(RuntimeError, match="boom"):
        await middleware.awrap_model_call(request, handler)

    assert len(emitter.events) == 2
    assert emitter.events[0]["type"] == "llm.call.start"
    assert emitter.events[1]["type"] == "llm.call.end"
    assert emitter.events[1]["payload"].get("error") == "boom"
