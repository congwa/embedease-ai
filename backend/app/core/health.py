"""统一依赖健康检查与状态管理

设计目标：
1. 统一管理所有外部依赖的连接状态
2. 提供健康检查 API 供前端/运维使用
3. 支持降级策略和错误通知
4. 便于扩展新依赖

使用方式：
    from app.core.health import dependency_registry, DependencyStatus

    # 注册依赖
    @dependency_registry.register("qdrant", category="vector_db")
    async def check_qdrant() -> bool:
        client = QdrantClient(...)
        client.get_collections()
        return True

    # 检查状态
    status = await dependency_registry.check("qdrant")
    
    # 获取所有状态
    all_status = await dependency_registry.check_all()
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine

from app.core.logging import get_logger

logger = get_logger("health")


class DependencyStatus(str, Enum):
    """依赖状态枚举"""
    
    HEALTHY = "healthy"          # 正常
    DEGRADED = "degraded"        # 降级（部分功能可用）
    UNHEALTHY = "unhealthy"      # 不可用
    UNKNOWN = "unknown"          # 未检查
    DISABLED = "disabled"        # 已禁用（配置关闭）


class DependencyCategory(str, Enum):
    """依赖分类"""
    
    LLM = "llm"                  # 大语言模型
    EMBEDDING = "embedding"      # 嵌入模型
    VECTOR_DB = "vector_db"      # 向量数据库
    DATABASE = "database"        # 关系数据库
    CACHE = "cache"              # 缓存
    EXTERNAL_API = "external_api"  # 外部 API
    NOTIFICATION = "notification"  # 通知渠道


@dataclass
class DependencyInfo:
    """依赖信息"""
    
    name: str                                    # 依赖名称
    category: DependencyCategory                 # 分类
    status: DependencyStatus = DependencyStatus.UNKNOWN
    last_check_time: float = 0                   # 上次检查时间戳
    last_error: str | None = None                # 最近错误信息
    check_interval: float = 60.0                 # 检查间隔（秒）
    timeout: float = 5.0                         # 检查超时（秒）
    is_critical: bool = True                     # 是否关键依赖
    fallback_message: str = ""                   # 降级提示信息
    extra: dict[str, Any] = field(default_factory=dict)  # 额外信息
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "category": self.category.value,
            "status": self.status.value,
            "last_check_time": self.last_check_time,
            "last_error": self.last_error,
            "is_critical": self.is_critical,
            "fallback_message": self.fallback_message,
            "extra": self.extra,
        }


# 健康检查函数类型
HealthCheckFunc = Callable[[], Coroutine[Any, Any, bool]]


class DependencyRegistry:
    """依赖注册中心
    
    单例模式，统一管理所有外部依赖的健康状态。
    """
    
    _instance: DependencyRegistry | None = None
    
    def __new__(cls) -> DependencyRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._dependencies: dict[str, DependencyInfo] = {}
        self._check_funcs: dict[str, HealthCheckFunc] = {}
        self._lock = asyncio.Lock()
        self._initialized = True
        logger.info("DependencyRegistry 初始化完成")
    
    def register(
        self,
        name: str,
        *,
        category: DependencyCategory | str = DependencyCategory.EXTERNAL_API,
        is_critical: bool = True,
        check_interval: float = 60.0,
        timeout: float = 5.0,
        fallback_message: str = "",
    ) -> Callable[[HealthCheckFunc], HealthCheckFunc]:
        """注册依赖（装饰器方式）
        
        Args:
            name: 依赖名称（唯一标识）
            category: 依赖分类
            is_critical: 是否关键依赖
            check_interval: 检查间隔（秒）
            timeout: 检查超时（秒）
            fallback_message: 降级时的提示信息
            
        Example:
            @dependency_registry.register("qdrant", category="vector_db")
            async def check_qdrant() -> bool:
                ...
        """
        if isinstance(category, str):
            category = DependencyCategory(category)
            
        def decorator(func: HealthCheckFunc) -> HealthCheckFunc:
            self._dependencies[name] = DependencyInfo(
                name=name,
                category=category,
                is_critical=is_critical,
                check_interval=check_interval,
                timeout=timeout,
                fallback_message=fallback_message or f"{name} 服务不可用，相关功能已降级",
            )
            self._check_funcs[name] = func
            logger.debug("注册依赖", name=name, category=category.value)
            return func
        return decorator
    
    def register_simple(
        self,
        name: str,
        check_func: HealthCheckFunc,
        *,
        category: DependencyCategory | str = DependencyCategory.EXTERNAL_API,
        is_critical: bool = True,
        check_interval: float = 60.0,
        timeout: float = 5.0,
        fallback_message: str = "",
    ) -> None:
        """直接注册依赖（非装饰器方式）"""
        if isinstance(category, str):
            category = DependencyCategory(category)
            
        self._dependencies[name] = DependencyInfo(
            name=name,
            category=category,
            is_critical=is_critical,
            check_interval=check_interval,
            timeout=timeout,
            fallback_message=fallback_message or f"{name} 服务不可用，相关功能已降级",
        )
        self._check_funcs[name] = check_func
        logger.debug("注册依赖", name=name, category=category.value)
    
    def set_status(
        self,
        name: str,
        status: DependencyStatus,
        error: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """手动设置依赖状态（用于运行时更新）"""
        if name not in self._dependencies:
            logger.warning("设置未注册依赖的状态", name=name)
            return
            
        info = self._dependencies[name]
        info.status = status
        info.last_check_time = time.time()
        info.last_error = error
        if extra:
            info.extra.update(extra)
            
        log_method = logger.warning if status == DependencyStatus.UNHEALTHY else logger.info
        log_method(
            "依赖状态更新",
            name=name,
            status=status.value,
            error=error,
            dependency=name,
            report_type="dependency_status_change" if status == DependencyStatus.UNHEALTHY else None,
        )
    
    async def check(self, name: str, force: bool = False) -> DependencyStatus:
        """检查单个依赖状态
        
        Args:
            name: 依赖名称
            force: 是否强制检查（忽略缓存）
            
        Returns:
            依赖状态
        """
        if name not in self._dependencies:
            logger.warning("检查未注册的依赖", name=name)
            return DependencyStatus.UNKNOWN
            
        info = self._dependencies[name]
        now = time.time()
        
        # 检查是否需要重新检查
        if not force and (now - info.last_check_time) < info.check_interval:
            return info.status
            
        # 执行健康检查
        check_func = self._check_funcs.get(name)
        if not check_func:
            return info.status
            
        try:
            async with self._lock:
                result = await asyncio.wait_for(
                    check_func(),
                    timeout=info.timeout,
                )
                
            if result:
                self.set_status(name, DependencyStatus.HEALTHY)
            else:
                self.set_status(name, DependencyStatus.DEGRADED)
                
        except asyncio.TimeoutError:
            self.set_status(
                name,
                DependencyStatus.UNHEALTHY,
                error=f"健康检查超时 ({info.timeout}s)",
            )
        except Exception as e:
            self.set_status(
                name,
                DependencyStatus.UNHEALTHY,
                error=str(e),
            )
            
        return info.status
    
    async def check_all(self, force: bool = False) -> dict[str, DependencyInfo]:
        """检查所有依赖状态
        
        Args:
            force: 是否强制检查
            
        Returns:
            所有依赖的状态信息
        """
        tasks = [self.check(name, force=force) for name in self._dependencies]
        await asyncio.gather(*tasks, return_exceptions=True)
        return self._dependencies.copy()
    
    def get_status(self, name: str) -> DependencyInfo | None:
        """获取依赖状态（不执行检查）"""
        return self._dependencies.get(name)
    
    def get_all_status(self) -> dict[str, DependencyInfo]:
        """获取所有依赖状态（不执行检查）"""
        return self._dependencies.copy()
    
    def is_healthy(self, name: str) -> bool:
        """判断依赖是否健康"""
        info = self._dependencies.get(name)
        if not info:
            return False
        return info.status in (DependencyStatus.HEALTHY, DependencyStatus.DEGRADED)
    
    def get_unhealthy_critical(self) -> list[DependencyInfo]:
        """获取所有不健康的关键依赖"""
        return [
            info for info in self._dependencies.values()
            if info.is_critical and info.status == DependencyStatus.UNHEALTHY
        ]
    
    def get_summary(self) -> dict[str, Any]:
        """获取健康状态摘要"""
        total = len(self._dependencies)
        healthy = sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.HEALTHY)
        degraded = sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.DEGRADED)
        unhealthy = sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.UNHEALTHY)
        unknown = sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.UNKNOWN)
        
        overall = DependencyStatus.HEALTHY
        if unhealthy > 0:
            # 检查是否有关键依赖不可用
            critical_unhealthy = self.get_unhealthy_critical()
            if critical_unhealthy:
                overall = DependencyStatus.UNHEALTHY
            else:
                overall = DependencyStatus.DEGRADED
        elif degraded > 0:
            overall = DependencyStatus.DEGRADED
        elif unknown == total:
            overall = DependencyStatus.UNKNOWN
            
        return {
            "overall": overall.value,
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "unknown": unknown,
            "dependencies": {
                name: info.to_dict() for name, info in self._dependencies.items()
            },
        }


# 全局单例
dependency_registry = DependencyRegistry()


class DependencyError(Exception):
    """依赖不可用异常
    
    用于在依赖不可用时抛出，调用方可捕获并处理。
    """
    
    def __init__(
        self,
        dependency_name: str,
        message: str | None = None,
        fallback_message: str | None = None,
        original_error: Exception | None = None,
    ):
        self.dependency_name = dependency_name
        self.fallback_message = fallback_message or f"{dependency_name} 服务不可用"
        self.original_error = original_error
        super().__init__(message or self.fallback_message)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为可序列化的字典"""
        return {
            "code": "dependency_unavailable",
            "dependency": self.dependency_name,
            "message": self.fallback_message,
            "detail": str(self.original_error) if self.original_error else None,
        }


def require_dependency(name: str) -> Callable:
    """装饰器：要求依赖可用
    
    如果依赖不可用，抛出 DependencyError。
    
    Example:
        @require_dependency("qdrant")
        async def search_products(query: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            info = dependency_registry.get_status(name)
            if info and info.status == DependencyStatus.UNHEALTHY:
                raise DependencyError(
                    dependency_name=name,
                    fallback_message=info.fallback_message,
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_dependency(name: str) -> tuple[bool, str | None]:
    """检查依赖是否可用（同步版本）
    
    Returns:
        (is_available, error_message)
    """
    info = dependency_registry.get_status(name)
    if not info:
        return True, None  # 未注册的依赖默认可用
    if info.status == DependencyStatus.UNHEALTHY:
        return False, info.fallback_message
    return True, None
