"""Agent 绩效快照 Repository

本文件的业务职责是为运营统计任务提供绩效快照读写入口，
让后续日报、榜单和知识运营都围绕统一快照表展开。
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_score_snapshot import AgentScoreSnapshot
from app.repositories.base import BaseRepository


class AgentScoreSnapshotRepository(BaseRepository[AgentScoreSnapshot]):
    """Agent 绩效快照数据访问。"""

    model = AgentScoreSnapshot

    def __init__(self, session: AsyncSession):
        """初始化绩效快照仓储。

        Args:
            session: 当前业务请求或后台任务使用的数据库会话。
        """
        super().__init__(session)

    async def list_by_window_type(
        self,
        window_type: str,
        *,
        limit: int = 50,
    ) -> list[AgentScoreSnapshot]:
        """获取指定窗口类型的最近绩效快照。

        这个方法服务于后续运营报表和排行榜，快速读取最近一批日榜或周榜数据。
        """
        result = await self.session.execute(
            select(AgentScoreSnapshot)
            .where(AgentScoreSnapshot.window_type == window_type)
            .order_by(AgentScoreSnapshot.window_end.desc(), AgentScoreSnapshot.agent_tag.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
