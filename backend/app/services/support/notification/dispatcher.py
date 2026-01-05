"""通知分发器

负责管理和调度所有通知渠道，支持：
- 自动发现和注册渠道
- 并行发送到多个渠道
- 失败重试和降级
"""

import asyncio
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.support.notification.base import (
    BaseNotificationChannel,
    NotificationPayload,
    NotificationResult,
    NotificationType,
)
from app.services.support.notification.channels import WebhookChannel, WeWorkChannel

logger = get_logger("notification.dispatcher")


class NotificationDispatcher:
    """通知分发器
    
    单例模式，管理所有通知渠道的生命周期和消息分发。
    
    使用方式：
        dispatcher = NotificationDispatcher()
        
        # 发送新消息通知
        results = await dispatcher.notify_new_message(
            conversation_id="xxx",
            user_id="yyy",
            message_preview="用户说：...",
        )
        
        # 或直接发送自定义通知
        results = await dispatcher.dispatch(payload)
    """

    _instance: "NotificationDispatcher | None" = None
    _channels: list[BaseNotificationChannel]
    _initialized: bool = False

    def __new__(cls) -> "NotificationDispatcher":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._channels = []
            cls._instance._initialized = False
        return cls._instance

    def _ensure_initialized(self) -> None:
        """确保渠道已初始化"""
        if self._initialized:
            return

        self._channels = []

        wework = WeWorkChannel()
        if wework.is_enabled():
            self._channels.append(wework)
            logger.info("已注册通知渠道: wework")

        webhook = WebhookChannel()
        if webhook.is_enabled():
            self._channels.append(webhook)
            logger.info("已注册通知渠道: webhook")

        self._initialized = True

        if not self._channels:
            logger.warning("未配置任何通知渠道，消息通知将被跳过")

    def register_channel(self, channel: BaseNotificationChannel) -> None:
        """手动注册通知渠道（用于扩展）"""
        self._ensure_initialized()
        if channel.is_enabled():
            self._channels.append(channel)
            logger.info(f"已注册通知渠道: {channel.channel_name}")

    @property
    def enabled_channels(self) -> list[str]:
        """获取已启用的渠道列表"""
        self._ensure_initialized()
        return [ch.channel_name for ch in self._channels]

    async def dispatch(
        self,
        payload: NotificationPayload,
        *,
        channels: list[str] | None = None,
    ) -> list[NotificationResult]:
        """分发通知到所有（或指定）渠道
        
        Args:
            payload: 通知负载
            channels: 指定渠道列表（None 表示全部）
            
        Returns:
            各渠道的发送结果列表
        """
        self._ensure_initialized()

        if not self._channels:
            logger.debug("无可用通知渠道，跳过通知")
            return []

        target_channels = self._channels
        if channels:
            target_channels = [ch for ch in self._channels if ch.channel_name in channels]

        if not target_channels:
            logger.debug("无匹配的通知渠道", requested=channels)
            return []

        tasks = [ch.send(payload) for ch in target_channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results: list[NotificationResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(
                    NotificationResult(
                        success=False,
                        channel=target_channels[i].channel_name,
                        error=str(result),
                    )
                )
            else:
                final_results.append(result)

        success_count = sum(1 for r in final_results if r.success)
        logger.info(
            "通知分发完成",
            total=len(final_results),
            success=success_count,
            type=payload.type.value,
            conversation_id=payload.conversation_id,
        )

        return final_results

    async def notify_new_message(
        self,
        *,
        conversation_id: str,
        user_id: str,
        message_preview: str,
        entry_page: str = "",
        console_url: str = "",
        extra: dict[str, Any] | None = None,
    ) -> list[NotificationResult]:
        """发送新消息通知
        
        用户发送消息时调用，通知客服有新访客。
        """
        settings = get_settings()

        if not console_url:
            console_url = getattr(settings, "SUPPORT_CONSOLE_URL", "")
            if console_url:
                console_url = f"{console_url}/conversations/{conversation_id}"

        payload = NotificationPayload(
            type=NotificationType.NEW_MESSAGE,
            conversation_id=conversation_id,
            user_id=user_id,
            title="新访客消息",
            message_preview=message_preview,
            entry_page=entry_page,
            console_url=console_url,
            extra=extra or {},
        )

        return await self.dispatch(payload)

    async def notify_waiting_reminder(
        self,
        *,
        conversation_id: str,
        user_id: str,
        wait_seconds: int,
    ) -> list[NotificationResult]:
        """发送等待提醒
        
        用户等待超过 SLA 时间后调用。
        """
        settings = get_settings()
        console_url = getattr(settings, "SUPPORT_CONSOLE_URL", "")
        if console_url:
            console_url = f"{console_url}/conversations/{conversation_id}"

        payload = NotificationPayload(
            type=NotificationType.WAITING_REMINDER,
            conversation_id=conversation_id,
            user_id=user_id,
            title="访客等待提醒",
            message_preview=f"用户已等待 {wait_seconds // 60} 分钟，请及时响应",
            console_url=console_url,
            extra={"wait_seconds": wait_seconds},
        )

        return await self.dispatch(payload)

    async def notify_handoff_request(
        self,
        *,
        conversation_id: str,
        user_id: str,
        reason: str = "",
    ) -> list[NotificationResult]:
        """发送转人工请求通知
        
        用户主动请求人工客服时调用。
        """
        settings = get_settings()
        console_url = getattr(settings, "SUPPORT_CONSOLE_URL", "")
        if console_url:
            console_url = f"{console_url}/conversations/{conversation_id}"

        payload = NotificationPayload(
            type=NotificationType.HANDOFF_REQUEST,
            conversation_id=conversation_id,
            user_id=user_id,
            title="用户请求人工客服",
            message_preview=reason or "用户请求与真人客服对话",
            console_url=console_url,
        )

        return await self.dispatch(payload)


notification_dispatcher = NotificationDispatcher()
