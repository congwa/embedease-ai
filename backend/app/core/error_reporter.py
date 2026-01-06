"""统一错误报告模块

提供向前端/日志/监控系统报告错误的统一接口。
支持：
1. 依赖不可用错误
2. 服务降级通知
3. 运行时异常

使用方式：
    from app.core.error_reporter import report_dependency_error, report_to_emitter

    # 报告依赖错误（自动记日志+更新健康状态）
    report_dependency_error("qdrant", error, fallback_message="搜索功能已降级")

    # 向前端发送错误事件
    await report_to_emitter(emitter, "qdrant", "向量数据库不可用")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.health import DependencyStatus, dependency_registry
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.services.websocket.emitter import StreamEventEmitter

logger = get_logger("error_reporter")


def report_dependency_error(
    dependency_name: str,
    error: Exception | str | None = None,
    *,
    fallback_message: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """报告依赖不可用错误
    
    自动：
    1. 记录 ERROR 日志（带 report_type 标记）
    2. 更新 DependencyRegistry 状态
    
    Args:
        dependency_name: 依赖名称
        error: 错误信息或异常
        fallback_message: 降级提示信息
        extra: 额外上下文信息
    """
    error_str = str(error) if error else "未知错误"
    
    # 更新健康状态
    dependency_registry.set_status(
        dependency_name,
        DependencyStatus.UNHEALTHY,
        error=error_str,
        extra=extra,
    )
    
    # 记录日志
    logger.error(
        f"{dependency_name} 服务不可用",
        dependency=dependency_name,
        error=error_str,
        fallback_message=fallback_message,
        report_type="dependency_unavailable",
        **(extra or {}),
    )


def report_dependency_degraded(
    dependency_name: str,
    reason: str,
    *,
    fallback_message: str | None = None,
) -> None:
    """报告依赖降级（部分功能可用）
    
    Args:
        dependency_name: 依赖名称
        reason: 降级原因
        fallback_message: 降级提示信息
    """
    dependency_registry.set_status(
        dependency_name,
        DependencyStatus.DEGRADED,
        error=reason,
    )
    
    logger.warning(
        f"{dependency_name} 服务已降级",
        dependency=dependency_name,
        reason=reason,
        fallback_message=fallback_message,
        report_type="dependency_degraded",
    )


def report_dependency_recovered(dependency_name: str) -> None:
    """报告依赖恢复正常
    
    Args:
        dependency_name: 依赖名称
    """
    dependency_registry.set_status(dependency_name, DependencyStatus.HEALTHY)
    
    logger.info(
        f"{dependency_name} 服务已恢复",
        dependency=dependency_name,
        report_type="dependency_recovered",
    )


async def report_to_emitter(
    emitter: "StreamEventEmitter",
    dependency_name: str,
    message: str,
    *,
    code: str = "dependency_unavailable",
    detail: str | None = None,
) -> None:
    """向前端发送错误事件
    
    Args:
        emitter: SSE 事件发射器
        dependency_name: 依赖名称
        message: 用户友好的错误消息
        code: 错误代码
        detail: 详细错误信息（可选）
    """
    from app.services.websocket.emitter import StreamEventType
    
    try:
        await emitter.aemit(
            StreamEventType.ERROR.value,
            {
                "code": code,
                "dependency": dependency_name,
                "message": message,
                "detail": detail,
            },
        )
    except Exception as e:
        logger.warning(
            "向前端发送错误事件失败",
            error=str(e),
            dependency=dependency_name,
        )


async def report_warning_to_emitter(
    emitter: "StreamEventEmitter",
    message: str,
    *,
    code: str = "service_degraded",
    dependency_name: str | None = None,
) -> None:
    """向前端发送警告事件（服务降级等）
    
    Args:
        emitter: SSE 事件发射器
        message: 用户友好的警告消息
        code: 警告代码
        dependency_name: 相关依赖名称（可选）
    """
    from app.services.websocket.emitter import StreamEventType
    
    try:
        await emitter.aemit(
            StreamEventType.WARNING.value if hasattr(StreamEventType, "WARNING") else "warning",
            {
                "code": code,
                "message": message,
                "dependency": dependency_name,
            },
        )
    except Exception as e:
        logger.warning(
            "向前端发送警告事件失败",
            error=str(e),
        )


def get_dependency_error_message(dependency_name: str) -> str | None:
    """获取依赖的错误提示信息
    
    Args:
        dependency_name: 依赖名称
        
    Returns:
        如果依赖不可用，返回友好提示信息；否则返回 None
    """
    info = dependency_registry.get_status(dependency_name)
    if not info:
        return None
    if info.status == DependencyStatus.UNHEALTHY:
        return info.fallback_message
    return None


def check_critical_dependencies() -> tuple[bool, list[str]]:
    """检查关键依赖是否可用
    
    Returns:
        (all_healthy, list_of_unhealthy_names)
    """
    unhealthy = dependency_registry.get_unhealthy_critical()
    if not unhealthy:
        return True, []
    return False, [d.name for d in unhealthy]
