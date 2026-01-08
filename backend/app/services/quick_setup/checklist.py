"""Quick Setup 检查清单服务

检查系统各项配置的状态，识别：
- 已正确配置的项目
- 仍使用默认值的项目（需要调整）
- 缺失或错误的配置项
"""

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.quick_setup import (
    ChecklistItem,
    ChecklistItemStatus,
    ChecklistResponse,
)

logger = get_logger("quick_setup.checklist")


class ChecklistService:
    """配置检查清单服务"""

    def __init__(self):
        self._default_values = {
            "LLM_PROVIDER": "siliconflow",
            "LLM_BASE_URL": "https://api.siliconflow.cn/v1",
            "EMBEDDING_PROVIDER": "siliconflow",
            "QDRANT_HOST": "localhost",
            "QDRANT_PORT": 6333,
            "QDRANT_COLLECTION": "products",
        }

    def _mask_value(self, value: str | None, sensitive: bool = False) -> str | None:
        """脱敏处理"""
        if value is None:
            return None
        if sensitive:
            if len(value) < 8:
                return "***"
            return f"{value[:4]}...{value[-4:]}"
        return value

    def _check_item(
        self,
        key: str,
        label: str,
        category: str,
        current_value: Any,
        default_value: Any = None,
        required: bool = True,
        sensitive: bool = False,
        step_index: int | None = None,
        description: str | None = None,
    ) -> ChecklistItem:
        """检查单个配置项"""
        # 确定状态
        if current_value is None or current_value == "":
            status = ChecklistItemStatus.MISSING if required else ChecklistItemStatus.OK
        elif default_value is not None and current_value == default_value:
            status = ChecklistItemStatus.DEFAULT
        else:
            status = ChecklistItemStatus.OK

        return ChecklistItem(
            key=key,
            label=label,
            category=category,
            status=status,
            current_value=self._mask_value(str(current_value) if current_value else None, sensitive),
            default_value=str(default_value) if default_value is not None else None,
            description=description,
            step_index=step_index,
        )

    def get_checklist(self) -> ChecklistResponse:
        """获取完整的配置检查清单"""
        items: list[ChecklistItem] = []

        # LLM 配置
        items.extend([
            self._check_item(
                key="LLM_PROVIDER",
                label="LLM 提供商",
                category="llm",
                current_value=settings.LLM_PROVIDER,
                default_value=self._default_values.get("LLM_PROVIDER"),
                step_index=2,
            ),
            self._check_item(
                key="LLM_API_KEY",
                label="LLM API Key",
                category="llm",
                current_value=settings.LLM_API_KEY,
                required=True,
                sensitive=True,
                step_index=2,
                description="必须配置有效的 API Key",
            ),
            self._check_item(
                key="LLM_BASE_URL",
                label="LLM Base URL",
                category="llm",
                current_value=settings.LLM_BASE_URL,
                default_value=self._default_values.get("LLM_BASE_URL"),
                step_index=2,
            ),
            self._check_item(
                key="LLM_CHAT_MODEL",
                label="LLM 模型",
                category="llm",
                current_value=settings.LLM_CHAT_MODEL,
                required=True,
                step_index=2,
            ),
        ])

        # Embedding 配置
        items.extend([
            self._check_item(
                key="EMBEDDING_PROVIDER",
                label="Embedding 提供商",
                category="embedding",
                current_value=settings.EMBEDDING_PROVIDER,
                default_value=self._default_values.get("EMBEDDING_PROVIDER"),
                step_index=2,
            ),
            self._check_item(
                key="EMBEDDING_MODEL",
                label="Embedding 模型",
                category="embedding",
                current_value=settings.EMBEDDING_MODEL,
                required=True,
                step_index=2,
            ),
            self._check_item(
                key="EMBEDDING_DIMENSION",
                label="Embedding 维度",
                category="embedding",
                current_value=settings.EMBEDDING_DIMENSION,
                required=True,
                step_index=2,
            ),
        ])

        # Qdrant 配置
        items.extend([
            self._check_item(
                key="QDRANT_HOST",
                label="Qdrant 主机",
                category="qdrant",
                current_value=settings.QDRANT_HOST,
                default_value=self._default_values.get("QDRANT_HOST"),
                step_index=2,
            ),
            self._check_item(
                key="QDRANT_PORT",
                label="Qdrant 端口",
                category="qdrant",
                current_value=settings.QDRANT_PORT,
                default_value=self._default_values.get("QDRANT_PORT"),
                step_index=2,
            ),
            self._check_item(
                key="QDRANT_COLLECTION",
                label="Qdrant 集合",
                category="qdrant",
                current_value=settings.QDRANT_COLLECTION,
                default_value=self._default_values.get("QDRANT_COLLECTION"),
                step_index=2,
            ),
        ])

        # Rerank 配置
        items.extend([
            self._check_item(
                key="RERANK_ENABLED",
                label="Rerank 启用状态",
                category="rerank",
                current_value=settings.RERANK_ENABLED,
                required=False,
                step_index=2,
            ),
        ])
        if settings.RERANK_ENABLED:
            items.append(
                self._check_item(
                    key="RERANK_MODEL",
                    label="Rerank 模型",
                    category="rerank",
                    current_value=settings.RERANK_MODEL,
                    required=True,
                    step_index=2,
                )
            )

        # Memory 配置
        items.extend([
            self._check_item(
                key="MEMORY_ENABLED",
                label="记忆系统",
                category="memory",
                current_value=settings.MEMORY_ENABLED,
                required=False,
                step_index=2,
            ),
        ])

        # Agent 中间件配置
        items.extend([
            self._check_item(
                key="AGENT_TODO_ENABLED",
                label="TODO 规划中间件",
                category="middleware",
                current_value=settings.AGENT_TODO_ENABLED,
                required=False,
                step_index=3,
            ),
            self._check_item(
                key="AGENT_SUMMARIZATION_ENABLED",
                label="上下文压缩中间件",
                category="middleware",
                current_value=settings.AGENT_SUMMARIZATION_ENABLED,
                required=False,
                step_index=3,
            ),
        ])

        # Crawler 配置
        items.append(
            self._check_item(
                key="CRAWLER_ENABLED",
                label="爬虫模块",
                category="crawler",
                current_value=settings.CRAWLER_ENABLED,
                required=False,
                step_index=5,
            )
        )

        # 客服支持配置
        items.extend([
            self._check_item(
                key="WEWORK_CORP_ID",
                label="企业微信 Corp ID",
                category="support",
                current_value=settings.WEWORK_CORP_ID or None,
                required=False,
                step_index=5,
                description="配置后可接收企业微信通知",
            ),
            self._check_item(
                key="NOTIFY_WEBHOOK_URL",
                label="Webhook 通知 URL",
                category="support",
                current_value=settings.NOTIFY_WEBHOOK_URL or None,
                required=False,
                step_index=5,
            ),
        ])

        # 统计
        ok_count = sum(1 for item in items if item.status == ChecklistItemStatus.OK)
        default_count = sum(1 for item in items if item.status == ChecklistItemStatus.DEFAULT)
        missing_count = sum(1 for item in items if item.status == ChecklistItemStatus.MISSING)

        return ChecklistResponse(
            items=items,
            total=len(items),
            ok_count=ok_count,
            default_count=default_count,
            missing_count=missing_count,
        )

    def get_category_summary(self) -> dict[str, dict[str, int]]:
        """获取按类别分组的摘要"""
        checklist = self.get_checklist()
        summary: dict[str, dict[str, int]] = {}

        for item in checklist.items:
            if item.category not in summary:
                summary[item.category] = {"ok": 0, "default": 0, "missing": 0, "error": 0}
            summary[item.category][item.status.value] += 1

        return summary


# 全局实例
_checklist_service: ChecklistService | None = None


def get_checklist_service() -> ChecklistService:
    """获取检查清单服务单例"""
    global _checklist_service
    if _checklist_service is None:
        _checklist_service = ChecklistService()
    return _checklist_service
