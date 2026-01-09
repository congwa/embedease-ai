"""FastAPI 依赖注入

最佳实践：
1. 路由层使用 Depends(get_db_session) 获取会话
2. 服务层通过 ServiceContainer 统一管理
3. WebSocket handlers 使用 get_services() 上下文管理器
4. 后台任务使用 get_db_context()（无 request 上下文）
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_db_context

if TYPE_CHECKING:
    from app.repositories.conversation import ConversationRepository
    from app.repositories.message import MessageRepository
    from app.services.conversation import ConversationService
    from app.services.support.handoff import HandoffService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（用于 FastAPI 路由依赖注入）"""
    async for session in get_db():
        yield session


@dataclass
class ServiceContainer:
    """服务容器 - 统一管理常用服务实例
    
    用途：
    - 减少代码重复（避免每个 handler 都创建服务实例）
    - 统一服务实例的生命周期管理
    - 便于单元测试（可 mock 整个容器）
    
    使用方式：
    ```python
    # 在 WebSocket handler 中
    async with get_services() as services:
        await services.conversation.add_message(...)
        await services.handoff.start_handoff(...)
    
    # 在 FastAPI 路由中
    def my_route(services: ServiceContainer = Depends(get_service_container)):
        ...
    ```
    """
    
    db: AsyncSession
    
    # Lazy-loaded services
    _conversation: "ConversationService | None" = None
    _handoff: "HandoffService | None" = None
    _message_repo: "MessageRepository | None" = None
    _conversation_repo: "ConversationRepository | None" = None
    
    @property
    def conversation(self) -> "ConversationService":
        """会话服务"""
        if self._conversation is None:
            from app.services.conversation import ConversationService
            self._conversation = ConversationService(self.db)
        return self._conversation
    
    @property
    def handoff(self) -> "HandoffService":
        """人工介入服务"""
        if self._handoff is None:
            from app.services.support.handoff import HandoffService
            self._handoff = HandoffService(self.db)
        return self._handoff
    
    @property
    def message_repo(self) -> "MessageRepository":
        """消息仓库"""
        if self._message_repo is None:
            from app.repositories.message import MessageRepository
            self._message_repo = MessageRepository(self.db)
        return self._message_repo
    
    @property
    def conversation_repo(self) -> "ConversationRepository":
        """会话仓库"""
        if self._conversation_repo is None:
            from app.repositories.conversation import ConversationRepository
            self._conversation_repo = ConversationRepository(self.db)
        return self._conversation_repo


@asynccontextmanager
async def get_services() -> AsyncGenerator[ServiceContainer, None]:
    """获取服务容器（上下文管理器）
    
    用于 WebSocket handlers 和其他非路由代码。
    会话在退出时自动提交/回滚。
    
    示例：
    ```python
    async with get_services() as services:
        await services.conversation.add_message(...)
    ```
    """
    async with get_db_context() as session:
        yield ServiceContainer(db=session)


async def get_service_container(
    db: AsyncSession = Depends(get_db_session),
) -> ServiceContainer:
    """获取服务容器（用于 FastAPI 路由依赖注入）
    
    示例：
    ```python
    @router.post("/chat")
    async def chat(services: ServiceContainer = Depends(get_service_container)):
        await services.conversation.add_message(...)
    ```
    """
    return ServiceContainer(db=db)
