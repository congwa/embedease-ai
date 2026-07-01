"""消息仓储测试

本文件的业务职责，是验证未读统计查询会正确使用数据库层的 IS NULL 条件，
避免客服工作台、会话状态接口和 WebSocket 初始状态拿到错误的未读数。
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.message import MessageRepository


class TestMessageRepository:
    """测试消息仓储中的未读统计逻辑。"""

    @pytest.mark.anyio
    async def test_get_unread_count_uses_sql_is_null_and_count(self):
        """测试未读数统计使用 COUNT 查询和 SQL IS NULL 过滤。"""
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute = AsyncMock(return_value=mock_result)

        repository = MessageRepository(mock_session)
        count = await repository.get_unread_count("conv_123", "agent")

        assert count == 3
        executed_stmt = mock_session.execute.await_args.args[0]
        compiled_sql = str(
            executed_stmt.compile(compile_kwargs={"literal_binds": True})
        )
        assert "count" in compiled_sql.lower()
        assert "messages.read_at IS NULL" in compiled_sql

