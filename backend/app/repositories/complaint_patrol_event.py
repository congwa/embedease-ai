"""客诉巡查事件 Repository

本文件的业务职责是为后续巡查与自愈能力提供统一数据入口。
Phase 1 先提供基础查询能力，Phase 2 再接入真实巡查任务。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_patrol_event import ComplaintPatrolEvent
from app.repositories.base import BaseRepository


class ComplaintPatrolEventRepository(BaseRepository[ComplaintPatrolEvent]):
    """客诉巡查事件数据访问。"""

    model = ComplaintPatrolEvent

    def __init__(self, session: AsyncSession):
        """初始化客诉巡查事件仓储。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        super().__init__(session)

    async def list_by_ticket_id(self, ticket_id: str) -> list[ComplaintPatrolEvent]:
        """获取问题单下的全部巡查事件。

        这个方法服务于后续工作台显示和巡查审计。
        """
        result = await self.session.execute(
            select(ComplaintPatrolEvent)
            .where(ComplaintPatrolEvent.ticket_id == ticket_id)
            .order_by(ComplaintPatrolEvent.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_latest_by_ticket_id_and_event_type(
        self,
        ticket_id: str,
        event_type: str,
    ) -> ComplaintPatrolEvent | None:
        """获取问题单某类巡查事件的最近一条记录。

        这个方法服务于巡查去重，避免同一张已待人工 ticket 每轮巡查都重复告警。
        """
        result = await self.session.execute(
            select(ComplaintPatrolEvent)
            .where(
                ComplaintPatrolEvent.ticket_id == ticket_id,
                ComplaintPatrolEvent.event_type == event_type,
            )
            .order_by(ComplaintPatrolEvent.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def has_recent_event(
        self,
        *,
        ticket_id: str,
        event_type: str,
        since: datetime,
    ) -> bool:
        """判断某类巡查事件是否在冷却时间内已发生过。

        这个方法服务于巡查告警节流，防止同一问题单在短时间内反复触发相同事件。
        """
        latest_event = await self.get_latest_by_ticket_id_and_event_type(ticket_id, event_type)
        if latest_event is None:
            return False
        return latest_event.created_at >= since
