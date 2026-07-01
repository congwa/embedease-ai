"""客服支持模块

包含：
- notification/: 通知服务（可扩展，支持企业微信、钉钉等）
- handoff.py: 客服介入状态管理
- state_service.py: 客服工作台状态组装
- gateway.py: 人工客服消息网关
"""

from app.services.support.handoff import HandoffService
from app.services.support.state_service import SupportStateService

__all__ = ["HandoffService", "SupportStateService"]
