"""会话热度评分服务

基于现有数据库字段计算会话热度得分，用于客服工作台排序。

热度算法（基于现有字段）：
- 状态权重：pending=50, human=30, ai=0
- 等待时长：每分钟+1分，上限30分
- 未读消息：每条+5分，上限25分
- 用户在线：+10分
- 时间衰减：超30分钟无活动，每10分钟-2分
"""

import time
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.conversation import Conversation, HandoffState
from app.models.message import Message

if TYPE_CHECKING:
    pass

logger = get_logger("support.heat_score")

# 状态权重配置
STATE_WEIGHTS = {
    HandoffState.PENDING.value: 50,  # 等待接入，最高优先
    HandoffState.HUMAN.value: 30,    # 人工服务中
    HandoffState.AI.value: 0,        # AI 模式
}

# 得分上限配置
MAX_WAIT_SCORE = 30      # 等待时长最高分
MAX_UNREAD_SCORE = 25    # 未读消息最高分
USER_ONLINE_BONUS = 10   # 用户在线加成
DECAY_THRESHOLD_MIN = 30 # 开始衰减的阈值（分钟）
DECAY_PER_10MIN = 2      # 每10分钟衰减分数


def calculate_heat_score(
    handoff_state: str,
    updated_at: datetime,
    unread_count: int,
    user_online: bool,
    handoff_at: datetime | None = None,
) -> int:
    """计算单个会话的热度得分
    
    Args:
        handoff_state: 会话状态 (ai/pending/human)
        updated_at: 最后更新时间
        unread_count: 未读消息数
        user_online: 用户是否在线
        handoff_at: 请求人工的时间（可选）
        
    Returns:
        热度得分（整数，0-100+）
    """
    now = datetime.now()
    score = 0
    
    # 1. 状态权重
    score += STATE_WEIGHTS.get(handoff_state, 0)
    
    # 2. 等待时长得分
    wait_base = handoff_at if handoff_at and handoff_state == HandoffState.PENDING.value else updated_at
    wait_minutes = (now - wait_base).total_seconds() / 60
    wait_score = min(int(wait_minutes), MAX_WAIT_SCORE)
    score += wait_score
    
    # 3. 未读消息得分
    unread_score = min(unread_count * 5, MAX_UNREAD_SCORE)
    score += unread_score
    
    # 4. 用户在线加成
    if user_online:
        score += USER_ONLINE_BONUS
    
    # 5. 时间衰减（仅对 AI 模式应用）
    if handoff_state == HandoffState.AI.value:
        inactive_minutes = (now - updated_at).total_seconds() / 60
        if inactive_minutes > DECAY_THRESHOLD_MIN:
            decay = int((inactive_minutes - DECAY_THRESHOLD_MIN) / 10) * DECAY_PER_10MIN
            score = max(0, score - decay)
    
    return score


class HeatScoreService:
    """热度评分服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_unread_count(self, conversation_id: str) -> int:
        """获取会话的未读用户消息数"""
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.role == "user",
                Message.read_at.is_(None),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def get_unread_counts_batch(self, conversation_ids: list[str]) -> dict[str, int]:
        """批量获取多个会话的未读消息数"""
        if not conversation_ids:
            return {}
        
        start = time.perf_counter()
        logger.debug(f"get_unread_counts_batch: 开始查询 {len(conversation_ids)} 个会话的未读数")
            
        stmt = (
            select(Message.conversation_id, func.count().label("count"))
            .where(
                Message.conversation_id.in_(conversation_ids),
                Message.role == "user",
                Message.read_at.is_(None),
            )
            .group_by(Message.conversation_id)
        )
        result = await self.session.execute(stmt)
        data = {row.conversation_id: row.count for row in result.all()}
        
        elapsed = (time.perf_counter() - start) * 1000
        logger.debug(f"get_unread_counts_batch: 完成，耗时 {elapsed:.2f}ms，返回 {len(data)} 条记录")
        return data
    
    async def calculate_for_conversation(self, conversation: Conversation) -> int:
        """计算单个会话的热度得分"""
        unread_count = await self.get_unread_count(conversation.id)
        return calculate_heat_score(
            handoff_state=conversation.handoff_state,
            updated_at=conversation.updated_at,
            unread_count=unread_count,
            user_online=conversation.user_online,
            handoff_at=conversation.handoff_at,
        )
    
    async def calculate_for_conversations_batch(
        self,
        conversations: list[Conversation],
    ) -> dict[str, int]:
        """批量计算多个会话的热度得分"""
        if not conversations:
            return {}
        
        # 批量获取未读数
        conversation_ids = [c.id for c in conversations]
        unread_counts = await self.get_unread_counts_batch(conversation_ids)
        
        # 计算得分
        scores = {}
        for conv in conversations:
            scores[conv.id] = calculate_heat_score(
                handoff_state=conv.handoff_state,
                updated_at=conv.updated_at,
                unread_count=unread_counts.get(conv.id, 0),
                user_online=conv.user_online,
                handoff_at=conv.handoff_at,
            )
        
        return scores

    async def get_latest_message_previews_batch(
        self,
        conversation_ids: list[str],
    ) -> dict[str, dict[str, str | datetime | None]]:
        """批量获取会话的最后一条消息预览。

        这个方法服务于客服工作台列表页，避免前端为了显示预览再逐条请求会话详情，
        让队列接口一次返回可直接渲染的最新消息摘要。
        """
        if not conversation_ids:
            return {}

        ranked_messages = (
            select(
                Message.conversation_id.label("conversation_id"),
                Message.content.label("content"),
                Message.created_at.label("created_at"),
                Message.role.label("role"),
                func.row_number()
                .over(
                    partition_by=Message.conversation_id,
                    order_by=(Message.created_at.desc(), Message.id.desc()),
                )
                .label("row_number"),
            )
            .where(Message.conversation_id.in_(conversation_ids))
            .subquery()
        )

        stmt = select(
            ranked_messages.c.conversation_id,
            ranked_messages.c.content,
            ranked_messages.c.created_at,
            ranked_messages.c.role,
        ).where(ranked_messages.c.row_number == 1)

        result = await self.session.execute(stmt)
        previews: dict[str, dict[str, str | datetime | None]] = {}
        for row in result.all():
            previews[row.conversation_id] = {
                "last_message": row.content,
                "last_message_at": row.created_at,
                "last_message_role": row.role,
            }
        return previews


async def get_conversations_with_heat(
    session: AsyncSession,
    *,
    state: str | None = None,
    sort_by: str = "heat",  # heat | time
    limit: int = 50,
    offset: int = 0,
    include_message_preview: bool = True,
) -> tuple[list[dict], int]:
    """获取带热度得分的会话列表
    
    Args:
        session: 数据库会话
        state: 筛选状态（可选）
        sort_by: 排序方式 - heat(热度优先) 或 time(时间优先)
        limit: 分页大小
        offset: 分页偏移
        include_message_preview: 是否附带最后一条消息预览

    Returns:
        (会话列表, 总数)
    """
    total_start = time.perf_counter()
    logger.debug(f"get_conversations_with_heat: 开始 state={state}, sort_by={sort_by}, limit={limit}, offset={offset}")
    
    # 构建查询
    stmt = select(Conversation)
    count_stmt = select(func.count()).select_from(Conversation)
    
    if state:
        stmt = stmt.where(Conversation.handoff_state == state)
        count_stmt = count_stmt.where(Conversation.handoff_state == state)
    
    # 按时间倒序获取（热度在内存计算后重排）
    stmt = stmt.order_by(Conversation.updated_at.desc())
    
    # 获取总数
    step_start = time.perf_counter()
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    logger.debug(f"get_conversations_with_heat: [1/4] count查询完成，total={total}，耗时 {(time.perf_counter() - step_start) * 1000:.2f}ms")
    
    # 如果按热度排序，需要获取更多数据来计算
    if sort_by == "heat":
        # 获取最近的会话（热度排序需要在内存中处理）
        fetch_limit = min(limit + offset + 100, 500)  # 防止内存溢出
        stmt = stmt.limit(fetch_limit)
    else:
        stmt = stmt.offset(offset).limit(limit)
    
    step_start = time.perf_counter()
    result = await session.execute(stmt)
    conversations = list(result.scalars().all())
    logger.debug(f"get_conversations_with_heat: [2/4] 会话列表查询完成，获取 {len(conversations)} 条，耗时 {(time.perf_counter() - step_start) * 1000:.2f}ms")
    
    # 计算热度和未读数
    heat_service = HeatScoreService(session)
    step_start = time.perf_counter()
    heat_scores = await heat_service.calculate_for_conversations_batch(conversations)
    logger.debug(f"get_conversations_with_heat: [3/4] 热度计算完成，耗时 {(time.perf_counter() - step_start) * 1000:.2f}ms")
    
    step_start = time.perf_counter()
    unread_counts = await heat_service.get_unread_counts_batch([c.id for c in conversations])
    logger.debug(f"get_conversations_with_heat: [4/4] 未读数查询完成，耗时 {(time.perf_counter() - step_start) * 1000:.2f}ms")

    latest_message_previews: dict[str, dict[str, str | datetime | None]] = {}
    if include_message_preview:
        step_start = time.perf_counter()
        latest_message_previews = await heat_service.get_latest_message_previews_batch(
            [c.id for c in conversations]
        )
        logger.debug(
            "get_conversations_with_heat: [5/5] 最新消息预览查询完成，耗时 "
            f"{(time.perf_counter() - step_start) * 1000:.2f}ms"
        )

    # 构建响应数据
    items = []
    for conv in conversations:
        latest_preview = latest_message_previews.get(conv.id, {})
        items.append({
            "id": conv.id,
            "user_id": conv.user_id,
            "title": conv.title,
            "conversation_mode": conv.conversation_mode,
            "handoff_state": conv.handoff_state,
            "handoff_operator": conv.handoff_operator,
            "handoff_reason": conv.handoff_reason,
            "user_online": conv.user_online,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "heat_score": heat_scores.get(conv.id, 0),
            "unread_count": unread_counts.get(conv.id, 0),
            "current_ticket_id": conv.current_ticket_id,
            "ticket_status": conv.complaint_status,
            "primary_issue_tag": conv.primary_issue_tag,
            "current_agent_tag": conv.current_agent_tag,
            "risk_level": conv.risk_level,
            "review_status": conv.review_status,
            "review_score": conv.review_score,
            "secondary_issue_detected": bool(conv.secondary_issues),
            "last_message": latest_preview.get("last_message"),
            "last_message_at": latest_preview.get("last_message_at"),
            "last_message_role": latest_preview.get("last_message_role"),
        })
    
    # 按热度排序
    if sort_by == "heat":
        items.sort(key=lambda x: (-x["heat_score"], -x["updated_at"].timestamp()))
        items = items[offset:offset + limit]
    
    logger.debug(f"get_conversations_with_heat: 全部完成，返回 {len(items)} 条，总耗时 {(time.perf_counter() - total_start) * 1000:.2f}ms")
    return items, total


async def get_support_stats(session: AsyncSession) -> dict:
    """获取客服统计数据（用于红点提醒）
    
    Returns:
        {
            "pending_count": 等待接入数,
            "human_count": 人工服务中数,
            "total_unread": 总未读消息数,
            "high_heat_count": 高热会话数(得分>60),
        }
    """
    total_start = time.perf_counter()
    logger.debug("get_support_stats: 开始")
    
    # 状态统计
    step_start = time.perf_counter()
    state_stmt = (
        select(Conversation.handoff_state, func.count().label("count"))
        .group_by(Conversation.handoff_state)
    )
    state_result = await session.execute(state_stmt)
    state_counts = {row.handoff_state: row.count for row in state_result.all()}
    logger.debug(f"get_support_stats: [1/3] 状态统计完成，耗时 {(time.perf_counter() - step_start) * 1000:.2f}ms")
    
    # 未读消息总数（pending 和 human 状态的会话）
    step_start = time.perf_counter()
    unread_stmt = (
        select(func.count())
        .select_from(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.handoff_state.in_([HandoffState.PENDING.value, HandoffState.HUMAN.value]),
            Message.role == "user",
            Message.read_at.is_(None),
        )
    )
    unread_result = await session.execute(unread_stmt)
    total_unread = unread_result.scalar() or 0
    logger.debug(f"get_support_stats: [2/3] 未读消息统计完成，total_unread={total_unread}，耗时 {(time.perf_counter() - step_start) * 1000:.2f}ms")
    
    # 计算高热会话数（需要获取会话详情）
    step_start = time.perf_counter()
    hot_conversations, _ = await get_conversations_with_heat(
        session,
        sort_by="heat",
        limit=100,
        include_message_preview=False,
    )
    high_heat_count = sum(1 for c in hot_conversations if c["heat_score"] > 60)
    logger.debug(f"get_support_stats: [3/3] 高热会话统计完成，high_heat_count={high_heat_count}，耗时 {(time.perf_counter() - step_start) * 1000:.2f}ms")
    
    logger.debug(f"get_support_stats: 全部完成，总耗时 {(time.perf_counter() - total_start) * 1000:.2f}ms")
    return {
        "pending_count": state_counts.get(HandoffState.PENDING.value, 0),
        "human_count": state_counts.get(HandoffState.HUMAN.value, 0),
        "total_unread": total_unread,
        "high_heat_count": high_heat_count,
    }
