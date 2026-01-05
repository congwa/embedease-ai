"""通知渠道抽象基类

定义通知渠道的统一接口，所有具体实现（企业微信、钉钉等）继承此基类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class NotificationType(StrEnum):
    """通知类型"""

    NEW_MESSAGE = "new_message"  # 新消息通知
    WAITING_REMINDER = "waiting_reminder"  # 等待提醒
    HANDOFF_REQUEST = "handoff_request"  # 转人工请求
    HANDOFF_COMPLETED = "handoff_completed"  # 人工介入完成
    SESSION_CLOSED = "session_closed"  # 会话关闭


@dataclass
class NotificationPayload:
    """通知负载"""

    type: NotificationType
    conversation_id: str
    user_id: str

    title: str = ""
    message_preview: str = ""
    entry_page: str = ""
    console_url: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class NotificationResult:
    """通知发送结果"""

    success: bool
    channel: str
    message_id: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class BaseNotificationChannel(ABC):
    """通知渠道抽象基类
    
    所有具体的通知渠道实现（企业微信、钉钉等）需要继承此类并实现以下方法：
    - channel_name: 渠道名称（用于日志和配置）
    - is_enabled: 是否启用
    - send: 发送通知
    """

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """渠道名称"""
        ...

    @abstractmethod
    def is_enabled(self) -> bool:
        """检查渠道是否启用（配置是否完整）"""
        ...

    @abstractmethod
    async def send(self, payload: NotificationPayload) -> NotificationResult:
        """发送通知
        
        Args:
            payload: 通知负载
            
        Returns:
            发送结果
        """
        ...

    def format_message(self, payload: NotificationPayload) -> str:
        """格式化消息内容（可被子类覆盖）
        
        Args:
            payload: 通知负载
            
        Returns:
            格式化后的消息文本
        """
        lines = []

        if payload.type == NotificationType.NEW_MESSAGE:
            lines.append("📩 新访客消息")
        elif payload.type == NotificationType.WAITING_REMINDER:
            lines.append("⏳ 访客等待提醒")
        elif payload.type == NotificationType.HANDOFF_REQUEST:
            lines.append("🙋 访客请求人工客服")
        else:
            lines.append(f"📢 {payload.title or '通知'}")

        lines.append(f"会话ID: {payload.conversation_id[:8]}...")

        if payload.message_preview:
            preview = payload.message_preview[:100]
            if len(payload.message_preview) > 100:
                preview += "..."
            lines.append(f"消息: {preview}")

        if payload.entry_page:
            lines.append(f"入口: {payload.entry_page}")

        if payload.console_url:
            lines.append(f"查看: {payload.console_url}")

        return "\n".join(lines)
