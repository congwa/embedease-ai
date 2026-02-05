from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.runtime import Runtime

from app.services.agent.middleware.logging import LoggingMiddleware
from langgraph_agent_kit import ChatContext


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
async def test_llm_logging_middleware_emits_start_end_with_same_call_id() -> None:
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

    middleware = LoggingMiddleware()
    resp = await middleware.awrap_model_call(request, handler)

    assert isinstance(resp, ModelResponse)
    assert emitter.events == []


@pytest.mark.anyio
async def test_llm_logging_middleware_emits_end_on_error() -> None:
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

    middleware = LoggingMiddleware()
    with pytest.raises(RuntimeError, match="boom"):
        await middleware.awrap_model_call(request, handler)

    assert emitter.events == []
