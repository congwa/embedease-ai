"""聊天流适配器 - 根据配置选择实现

通过 USE_AGENT_SDK 配置切换 SDK 和 Legacy 实现。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    from app.services.agent.core.service import AgentService


def get_chat_stream_orchestrator():
    """获取聊天流编排器类
    
    根据 USE_AGENT_SDK 配置返回对应实现：
    - True: 使用 SDK 实现（默认）
    - False: 使用旧实现
    
    Returns:
        ChatStreamOrchestrator 类（SDK 或 Legacy）
    """
    if settings.USE_AGENT_SDK:
        from app.services.chat_stream_sdk import ChatStreamOrchestratorSDK
        return ChatStreamOrchestratorSDK
    else:
        from app.services.chat_stream_legacy import ChatStreamOrchestrator
        return ChatStreamOrchestrator


def get_agent_service() -> "AgentService":
    """获取 Agent 服务实例
    
    根据 USE_AGENT_SDK 配置返回对应实现。
    目前两种模式使用同一个 AgentService 实例。
    
    Returns:
        AgentService 实例
    """
    from app.services.agent.core.service import agent_service
    return agent_service
