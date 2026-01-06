"""健康检查 API

提供系统健康状态查询接口，支持：
- 整体健康状态
- 各依赖详细状态
- 强制刷新检查
"""

from fastapi import APIRouter, Query

from app.core.health import DependencyStatus, dependency_registry
from app.core.logging import get_logger

router = APIRouter(prefix="/health", tags=["health"])
logger = get_logger("api.health")


@router.get("")
async def health_check():
    """基础健康检查（用于负载均衡/K8s 探针）"""
    summary = dependency_registry.get_summary()
    
    # 只有关键依赖全部不可用时才返回 503
    if summary["overall"] == DependencyStatus.UNHEALTHY.value:
        critical_unhealthy = dependency_registry.get_unhealthy_critical()
        if critical_unhealthy:
            return {
                "status": "unhealthy",
                "message": "关键服务不可用",
                "unhealthy_dependencies": [d.name for d in critical_unhealthy],
            }
    
    return {
        "status": "ok",
        "overall": summary["overall"],
    }


@router.get("/ready")
async def readiness_check():
    """就绪检查（K8s readiness probe）"""
    summary = dependency_registry.get_summary()
    
    if summary["overall"] == DependencyStatus.UNHEALTHY.value:
        return {"ready": False, "reason": "dependencies_unhealthy"}
    
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """存活检查（K8s liveness probe）"""
    return {"alive": True}


@router.get("/dependencies")
async def get_dependencies_status(
    refresh: bool = Query(False, description="是否强制刷新检查"),
):
    """获取所有依赖状态详情"""
    if refresh:
        await dependency_registry.check_all(force=True)
    
    summary = dependency_registry.get_summary()
    
    return {
        "overall": summary["overall"],
        "summary": {
            "total": summary["total"],
            "healthy": summary["healthy"],
            "degraded": summary["degraded"],
            "unhealthy": summary["unhealthy"],
            "unknown": summary["unknown"],
        },
        "dependencies": summary["dependencies"],
    }


@router.get("/dependencies/{name}")
async def get_dependency_status(
    name: str,
    refresh: bool = Query(False, description="是否强制刷新检查"),
):
    """获取单个依赖状态"""
    if refresh:
        await dependency_registry.check(name, force=True)
    
    info = dependency_registry.get_status(name)
    if not info:
        return {"error": f"依赖 {name} 未注册"}
    
    return info.to_dict()


@router.post("/dependencies/{name}/check")
async def check_dependency(name: str):
    """强制检查单个依赖"""
    status = await dependency_registry.check(name, force=True)
    info = dependency_registry.get_status(name)
    
    return {
        "name": name,
        "status": status.value,
        "last_error": info.last_error if info else None,
    }
