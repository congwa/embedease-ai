"""ConversationService 测试

测试会话服务的业务逻辑。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.conversation import ConversationService


class TestConversationServiceInit:
    """测试 ConversationService 初始化"""

    def test_init_with_session(self):
        """测试使用 session 初始化"""
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        assert service.session is mock_session
        assert service.conversation_repo is not None
        assert service.message_repo is not None
        assert service.tool_call_repo is not None
        assert service.user_repo is not None

    def test_repositories_initialized(self):
        """测试所有 Repository 都被初始化"""
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # 验证各 Repository 被正确初始化
        from app.repositories.conversation import ConversationRepository
        from app.repositories.message import MessageRepository
        from app.repositories.tool_call import ToolCallRepository
        from app.repositories.user import UserRepository
        
        assert isinstance(service.conversation_repo, ConversationRepository)
        assert isinstance(service.message_repo, MessageRepository)
        assert isinstance(service.tool_call_repo, ToolCallRepository)
        assert isinstance(service.user_repo, UserRepository)


class TestConversationServiceMethods:
    """测试 ConversationService 方法签名"""

    def test_has_get_user_conversations(self):
        """测试有 get_user_conversations 方法"""
        assert hasattr(ConversationService, 'get_user_conversations')

    def test_has_get_conversation_with_messages(self):
        """测试有 get_conversation_with_messages 方法"""
        assert hasattr(ConversationService, 'get_conversation_with_messages')

    def test_has_create_conversation(self):
        """测试有 create_conversation 方法"""
        assert hasattr(ConversationService, 'create_conversation')


class TestConversationServiceAsync:
    """测试 ConversationService 异步方法"""

    @pytest.mark.anyio
    async def test_get_user_conversations_calls_repo(self):
        """测试 get_user_conversations 调用 Repository"""
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # Mock repository 方法
        service.conversation_repo.get_by_user_id = AsyncMock(return_value=[])
        
        result = await service.get_user_conversations("user_123")
        
        service.conversation_repo.get_by_user_id.assert_called_once_with("user_123")
        assert result == []

    @pytest.mark.anyio
    async def test_get_conversation_with_messages_calls_repo(self):
        """测试 get_conversation_with_messages 调用 Repository"""
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # Mock repository 方法
        service.conversation_repo.get_with_messages = AsyncMock(return_value=None)
        
        result = await service.get_conversation_with_messages("conv_123")
        
        service.conversation_repo.get_with_messages.assert_called_once_with("conv_123")
        assert result is None


class TestConversationServiceCreateConversation:
    """测试创建会话"""

    @pytest.mark.anyio
    async def test_create_conversation_basic(self):
        """测试基本创建会话"""
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        # Mock repository 方法
        mock_conversation = MagicMock()
        mock_conversation.id = "conv_123"
        
        service.user_repo.get_or_create = AsyncMock(return_value=MagicMock())
        service.conversation_repo.create_conversation = AsyncMock(return_value=mock_conversation)
        
        result = await service.create_conversation(
            user_id="user_123",
            agent_id=None,
            channel="web",
        )
        
        # 验证调用
        service.user_repo.get_or_create.assert_called_once_with("user_123")
        assert result is mock_conversation

    @pytest.mark.anyio
    async def test_create_conversation_with_agent(self):
        """测试带 Agent 创建会话"""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        
        service = ConversationService(mock_session)
        
        mock_conversation = MagicMock()
        service.user_repo.get_or_create = AsyncMock(return_value=MagicMock())
        service.conversation_repo.create_conversation = AsyncMock(return_value=mock_conversation)
        
        result = await service.create_conversation(
            user_id="user_123",
            agent_id="agent_456",
            channel="web",
        )
        
        assert result is mock_conversation

    @pytest.mark.anyio
    async def test_create_conversation_default_channel(self):
        """测试默认渠道"""
        mock_session = MagicMock()
        service = ConversationService(mock_session)
        
        mock_conversation = MagicMock()
        service.user_repo.get_or_create = AsyncMock(return_value=MagicMock())
        service.conversation_repo.create_conversation = AsyncMock(return_value=mock_conversation)
        
        # 不传 channel 参数
        result = await service.create_conversation(user_id="user_123")
        
        assert result is mock_conversation
