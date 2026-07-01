"""客诉审查 Repository

本文件的业务职责是提供 review 记录的基础查询能力，
让上层业务可以快速知道最近一次审查是否通过、是否驳回以及为什么驳回。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.complaint_review import ComplaintReview
from app.repositories.base import BaseRepository


class ComplaintReviewRepository(BaseRepository[ComplaintReview]):
    """客诉审查数据访问。"""

    model = ComplaintReview

    def __init__(self, session: AsyncSession):
        """初始化客诉审查仓储。

        Args:
            session: 当前业务请求使用的数据库会话。
        """
        super().__init__(session)

    async def list_by_ticket_id(self, ticket_id: str) -> list[ComplaintReview]:
        """获取问题单全部审查记录。

        这个方法服务于工作台查看驳回历史和后续运营分析。
        """
        result = await self.session.execute(
            select(ComplaintReview)
            .where(ComplaintReview.ticket_id == ticket_id)
            .order_by(ComplaintReview.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_latest_by_ticket_id(self, ticket_id: str) -> ComplaintReview | None:
        """获取问题单最近一次审查结果。

        这个方法服务于当前快照同步和工作台最新风险展示。
        """
        result = await self.session.execute(
            select(ComplaintReview)
            .where(ComplaintReview.ticket_id == ticket_id)
            .order_by(ComplaintReview.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
