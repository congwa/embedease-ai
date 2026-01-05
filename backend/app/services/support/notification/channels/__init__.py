"""通知渠道实现

每个渠道一个文件，便于维护和扩展。
"""

from app.services.support.notification.channels.webhook import WebhookChannel
from app.services.support.notification.channels.wework import WeWorkChannel

__all__ = ["WeWorkChannel", "WebhookChannel"]
