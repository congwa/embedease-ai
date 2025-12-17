"""Pytest 配置"""

import os
import pytest


# 测试环境下为 Settings 提供必要的必填配置，避免导入 app.core.config 时报错。
# 这些值仅用于单测，不会触发任何真实网络调用。
os.environ.setdefault("LLM_PROVIDER", "test")
os.environ.setdefault("LLM_API_KEY", "test")
os.environ.setdefault("LLM_BASE_URL", "https://example.invalid")
os.environ.setdefault("LLM_CHAT_MODEL", "test-model")
os.environ.setdefault("EMBEDDING_MODEL", "test-embedding")
os.environ.setdefault("EMBEDDING_DIMENSION", "1024")
os.environ.setdefault("RERANK_ENABLED", "false")
os.environ.setdefault("RERANK_MODEL", "test-rerank")


@pytest.fixture
def anyio_backend():
    return "asyncio"
