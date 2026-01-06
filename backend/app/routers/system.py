"""系统功能状态 API

提供系统功能开关状态查询接口，供前端判断哪些功能可用。
"""

from fastapi import APIRouter

from app.core.config import settings
from app.core.health import dependency_registry
from app.core.logging import get_logger

router = APIRouter(prefix="/api/v1/system", tags=["system"])
logger = get_logger("api.system")


@router.get("/features")
async def get_features():
    """获取系统功能状态
    
    返回各功能模块的启用状态和健康信息，供前端控制导航和页面渲染。
    """
    def get_feature_info(dep_name: str, enabled_flag: bool):
        """获取功能信息"""
        info = dependency_registry.get_status(dep_name)
        return {
            "enabled": enabled_flag,
            "status": info.status.value if info else "unknown",
            "message": info.fallback_message if info else None,
            "last_error": info.last_error if info else None,
        }
    
    return {
        "crawler": get_feature_info("crawler", settings.CRAWLER_ENABLED),
        "memory": {
            "enabled": settings.MEMORY_ENABLED,
            "store_enabled": settings.MEMORY_STORE_ENABLED,
            "fact_enabled": settings.MEMORY_FACT_ENABLED,
            "graph_enabled": settings.MEMORY_GRAPH_ENABLED,
        },
        "rerank": get_feature_info("rerank", settings.RERANK_ENABLED),
        "notifications": {
            "wework": get_feature_info("wework", bool(getattr(settings, "WEWORK_CORP_ID", None))),
            "webhook": get_feature_info("webhook", bool(getattr(settings, "NOTIFY_WEBHOOK_URL", None))),
        },
    }
