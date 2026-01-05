"""通知服务模块

可扩展的通知服务架构，支持多种推送渠道：
- 企业微信（WeWork）
- 钉钉（DingTalk）
- 飞书（Feishu/Lark）
- Webhook
- 邮件
- ...

使用方式：
    from app.services.support.notification import NotificationDispatcher
    
    dispatcher = NotificationDispatcher()
    await dispatcher.notify_new_message(conversation_id, message_preview)
"""

from app.services.support.notification.base import (
    BaseNotificationChannel,
    NotificationPayload,
    NotificationResult,
)
from app.services.support.notification.dispatcher import NotificationDispatcher

__all__ = [
    "NotificationDispatcher",
    "BaseNotificationChannel",
    "NotificationPayload",
    "NotificationResult",
]
