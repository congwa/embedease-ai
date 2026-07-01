"""客诉问题单 Repository

本文件的业务职责是提供问题单的基础读写能力，
让上层 merge、planner、handoff、patrol 等服务围绕统一的数据入口工作。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_ticket import ComplaintTicket
from app.repositories.base import BaseRepository


class ComplaintTicketRepository(BaseRepository[ComplaintTicket]):
    """客诉问题单数据访问。

    这个仓储层服务于“找到当前主活动问题单”和“维护 ticket 生命周期”这两个核心业务动作。
    """

    model = ComplaintTicket

    def __init__(self, session: AsyncSession):
        """初始化客诉问题单仓储。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        super().__init__(session)

    async def get_active_by_conversation_id(self, conversation_id: str) -> ComplaintTicket | None:
        """获取会话当前主活动问题单。

        这个方法是后续消息归并、拆单和工作台当前状态展示的唯一主入口。
        """
        result = await self.session.execute(
            select(ComplaintTicket)
            .where(
                ComplaintTicket.conversation_id == conversation_id,
                ComplaintTicket.is_primary_active.is_(True),
            )
            .order_by(ComplaintTicket.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_conversation_id(self, conversation_id: str) -> list[ComplaintTicket]:
        """获取会话下全部历史问题单。

        这个方法服务于后续人工回溯、拆单审计和历史问题链查看。
        """
        result = await self.session.execute(
            select(ComplaintTicket)
            .where(ComplaintTicket.conversation_id == conversation_id)
            .order_by(ComplaintTicket.updated_at.desc())
        )
        return list(result.scalars().all())

    async def list_primary_active_by_statuses(
        self,
        statuses: list[str],
    ) -> list[ComplaintTicket]:
        """获取指定状态下的主活动问题单。

        这个方法服务于 patrol 等后台任务，批量扫描当前仍在运行中的异常 ticket。
        """
        result = await self.session.execute(
            select(ComplaintTicket)
            .where(
                ComplaintTicket.is_primary_active.is_(True),
                ComplaintTicket.status.in_(statuses),
            )
            .order_by(ComplaintTicket.updated_at.asc())
        )
        return list(result.scalars().all())

    async def list_primary_active_with_rework_at_least(
        self,
        min_rework_count: int,
    ) -> list[ComplaintTicket]:
        """获取返工次数达到阈值的主活动问题单。

        这个方法服务于巡查识别“返工死循环”场景，避免同一张 ticket 被无限返工。
        """
        result = await self.session.execute(
            select(ComplaintTicket)
            .where(
                ComplaintTicket.is_primary_active.is_(True),
                ComplaintTicket.rework_count >= min_rework_count,
            )
            .order_by(ComplaintTicket.updated_at.asc())
        )
        return list(result.scalars().all())
