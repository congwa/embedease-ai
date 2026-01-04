"""工具调用 Repository"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool_call import ToolCall
from app.repositories.base import BaseRepository


class ToolCallRepository(BaseRepository[ToolCall]):
    """工具调用数据访问"""

    model = ToolCall

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def get_by_message_id(self, message_id: str) -> list[ToolCall]:
        """获取消息的所有工具调用"""
        result = await self.session.execute(
            select(ToolCall)
            .where(ToolCall.message_id == message_id)
            .order_by(ToolCall.created_at)
        )
        return list(result.scalars().all())

    async def get_by_tool_call_id(self, tool_call_id: str) -> ToolCall | None:
        """根据 LangGraph tool_call_id 获取工具调用"""
        result = await self.session.execute(
            select(ToolCall).where(ToolCall.tool_call_id == tool_call_id)
        )
        return result.scalar_one_or_none()

    async def create_tool_call(
        self,
        message_id: str,
        tool_name: str,
        tool_input: dict[str, Any] | None = None,
        tool_call_id: str | None = None,
        status: str = "pending",
    ) -> ToolCall:
        """创建工具调用记录"""
        tool_call = ToolCall(
            message_id=message_id,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_input=tool_input or {},
            status=status,
        )
        return await self.create(tool_call)

    async def update_tool_call_output(
        self,
        tool_call_id: str,
        tool_output: str,
        status: str = "success",
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> ToolCall | None:
        """根据 tool_call_id 更新工具调用结果"""
        tool_call = await self.get_by_tool_call_id(tool_call_id)
        if not tool_call:
            return None

        tool_call.tool_output = tool_output
        tool_call.status = status
        if error_message:
            tool_call.error_message = error_message
        if duration_ms is not None:
            tool_call.duration_ms = duration_ms

        return await self.update(tool_call)

    async def batch_create_tool_calls(
        self,
        message_id: str,
        tool_calls_data: list[dict[str, Any]],
    ) -> list[ToolCall]:
        """批量创建工具调用记录
        
        Args:
            message_id: 消息 ID
            tool_calls_data: 工具调用数据列表，每项包含:
                - tool_call_id: LangGraph tool_call_id
                - name: 工具名称
                - input: 工具输入参数
                - status: 状态（可选，默认 pending）
                - output: 工具输出（可选）
        """
        created = []
        for tc_data in tool_calls_data:
            tool_call = ToolCall(
                message_id=message_id,
                tool_call_id=tc_data.get("tool_call_id"),
                tool_name=tc_data.get("name", "unknown"),
                tool_input=tc_data.get("input", {}),
                tool_output=tc_data.get("output"),
                status=tc_data.get("status", "pending"),
                duration_ms=tc_data.get("duration_ms"),
            )
            self.session.add(tool_call)
            created.append(tool_call)

        await self.session.flush()
        for tc in created:
            await self.session.refresh(tc)

        return created
