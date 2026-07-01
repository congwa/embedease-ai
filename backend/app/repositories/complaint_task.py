"""客诉任务 Repository

本文件的业务职责是提供问题单任务的基础查询和状态更新能力，
服务于 triage、plan、execute、review 等处理链路。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_task import ComplaintTask
from app.repositories.base import BaseRepository


class ComplaintTaskRepository(BaseRepository[ComplaintTask]):
    """客诉任务数据访问。"""

    model = ComplaintTask

    def __init__(self, session: AsyncSession):
        """初始化客诉任务仓储。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        super().__init__(session)

    async def list_by_ticket_id(self, ticket_id: str) -> list[ComplaintTask]:
        """获取问题单下的全部任务。

        这个方法服务于工作台查看处理链路和后续任务追踪。
        """
        result = await self.session.execute(
            select(ComplaintTask)
            .where(ComplaintTask.ticket_id == ticket_id)
            .order_by(ComplaintTask.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_latest_by_ticket_id(self, ticket_id: str) -> ComplaintTask | None:
        """获取问题单最近一条任务。

        这个方法服务于 planner 决策和工作台当前阶段展示。
        """
        result = await self.session.execute(
            select(ComplaintTask)
            .where(ComplaintTask.ticket_id == ticket_id)
            .order_by(ComplaintTask.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
