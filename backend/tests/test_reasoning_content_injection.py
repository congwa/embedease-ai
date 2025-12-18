from __future__ import annotations

from typing import Any

import pytest
from langchain_core.messages import AIMessageChunk

from app.core.chat_models.base import BaseReasoningChatModel


class _DummyReasoningModel(BaseReasoningChatModel):
    pass


def _make_model() -> _DummyReasoningModel:
    return _DummyReasoningModel(model="dummy", openai_api_key="test", openai_api_base="https://example.invalid")


def test_inject_reasoning_content_from_delta_reasoning() -> None:
    model = _make_model()
    msg = AIMessageChunk(content="")
    model._ensure_reasoning_content(
        msg,
        raw_chunk={"choices": [{"delta": {"reasoning": "R1"}}]},
    )
    assert msg.additional_kwargs.get("reasoning_content") == "R1"


def test_inject_reasoning_content_from_delta_reasoning_content() -> None:
    model = _make_model()
    msg = AIMessageChunk(content="")
    model._ensure_reasoning_content(
        msg,
        raw_chunk={"choices": [{"delta": {"reasoning_content": "R2"}}]},
    )
    assert msg.additional_kwargs.get("reasoning_content") == "R2"


def test_inject_reasoning_content_from_message_content_blocks() -> None:
    model = _make_model()
    msg = AIMessageChunk(
        content=[
            {
                "type": "reasoning",
                "summary": [
                    {"type": "summary_text", "text": "A"},
                    {"type": "summary_text", "text": "B"},
                ],
            }
        ]
    )
    model._ensure_reasoning_content(msg)
    assert msg.additional_kwargs.get("reasoning_content") == "AB"


def test_inject_reasoning_content_from_v03_additional_kwargs_reasoning_dict() -> None:
    model = _make_model()
    msg = AIMessageChunk(content="")
    msg.additional_kwargs["reasoning"] = {
        "type": "reasoning",
        "summary": [{"type": "summary_text", "text": "C"}],
    }
    model._ensure_reasoning_content(msg)
    assert msg.additional_kwargs.get("reasoning_content") == "C"


def test_does_not_override_existing_reasoning_content() -> None:
    model = _make_model()
    msg = AIMessageChunk(content="")
    msg.additional_kwargs["reasoning_content"] = "EXISTING"
    model._ensure_reasoning_content(
        msg,
        raw_chunk={"choices": [{"delta": {"reasoning": "NEW"}}]},
    )
    assert msg.additional_kwargs.get("reasoning_content") == "EXISTING"
