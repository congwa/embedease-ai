"""依赖健康检查函数注册

在应用启动时导入此模块，自动注册所有依赖的健康检查函数。
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.health import DependencyCategory, DependencyStatus, dependency_registry
from app.core.logging import get_logger

logger = get_logger("health_checks")
settings = get_settings()


# ============================================================
# Qdrant 向量数据库
# ============================================================

@dependency_registry.register(
    "qdrant",
    category=DependencyCategory.VECTOR_DB,
    is_critical=True,
    timeout=5.0,
    fallback_message="向量数据库不可用，商品搜索和记忆功能已降级",
)
async def check_qdrant() -> bool:
    """检查 Qdrant 连接"""
    from qdrant_client import QdrantClient
    
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        timeout=5.0,
    )
    try:
        client.get_collections()
        return True
    finally:
        client.close()


# ============================================================
# LLM 服务
# ============================================================

@dependency_registry.register(
    "llm",
    category=DependencyCategory.LLM,
    is_critical=True,
    timeout=10.0,
    check_interval=120.0,  # LLM 检查间隔长一些
    fallback_message="AI 模型服务不可用，请稍后再试",
)
async def check_llm() -> bool:
    """检查 LLM 服务（简单连通性检查）"""
    import httpx
    
    base_url = settings.LLM_BASE_URL
    if not base_url:
        return True  # 使用默认 OpenAI，不检查
        
    # 尝试访问 /models 端点
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
            )
            return resp.status_code < 500
    except Exception:
        return False


# ============================================================
# Embedding 服务
# ============================================================

@dependency_registry.register(
    "embedding",
    category=DependencyCategory.EMBEDDING,
    is_critical=True,
    timeout=10.0,
    check_interval=120.0,
    fallback_message="嵌入服务不可用，搜索功能已降级",
)
async def check_embedding() -> bool:
    """检查 Embedding 服务"""
    import httpx
    
    base_url = settings.effective_embedding_base_url
    if not base_url:
        return True
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.effective_embedding_api_key}"},
            )
            return resp.status_code < 500
    except Exception:
        return False


# ============================================================
# Rerank 服务
# ============================================================

@dependency_registry.register(
    "rerank",
    category=DependencyCategory.EXTERNAL_API,
    is_critical=False,  # 非关键，可降级
    timeout=5.0,
    fallback_message="重排序服务不可用，搜索结果未优化",
)
async def check_rerank() -> bool:
    """检查 Rerank 服务"""
    if not settings.RERANK_ENABLED:
        # 已禁用，设置为 DISABLED 状态
        dependency_registry.set_status("rerank", DependencyStatus.DISABLED)
        return True
        
    import httpx
    
    base_url = settings.effective_rerank_base_url
    if not base_url:
        return True
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.effective_rerank_api_key}"},
            )
            return resp.status_code < 500
    except Exception:
        return False


# ============================================================
# SQLite 数据库
# ============================================================

@dependency_registry.register(
    "database",
    category=DependencyCategory.DATABASE,
    is_critical=True,
    timeout=5.0,
    fallback_message="数据库不可用，请检查存储",
)
async def check_database() -> bool:
    """检查 SQLite 数据库"""
    import aiosqlite
    
    try:
        async with aiosqlite.connect(settings.DATABASE_PATH) as db:
            await db.execute("SELECT 1")
        return True
    except Exception:
        return False


# ============================================================
# 企业微信通知
# ============================================================

@dependency_registry.register(
    "wework",
    category=DependencyCategory.NOTIFICATION,
    is_critical=False,
    timeout=10.0,
    check_interval=300.0,  # 5 分钟检查一次
    fallback_message="企业微信通知不可用",
)
async def check_wework() -> bool:
    """检查企业微信配置"""
    corp_id = getattr(settings, "WEWORK_CORP_ID", None)
    agent_id = getattr(settings, "WEWORK_AGENT_ID", None)
    secret = getattr(settings, "WEWORK_AGENT_SECRET", None)
    
    if not all([corp_id, agent_id, secret]):
        dependency_registry.set_status("wework", DependencyStatus.DISABLED)
        return True
        
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
                params={"corpid": corp_id, "corpsecret": secret},
            )
            data = resp.json()
            return data.get("errcode") == 0
    except Exception:
        return False


# ============================================================
# Webhook 通知
# ============================================================

@dependency_registry.register(
    "webhook",
    category=DependencyCategory.NOTIFICATION,
    is_critical=False,
    timeout=10.0,
    check_interval=300.0,
    fallback_message="Webhook 通知不可用",
)
async def check_webhook() -> bool:
    """检查 Webhook 配置"""
    webhook_url = getattr(settings, "NOTIFY_WEBHOOK_URL", None)
    
    if not webhook_url:
        dependency_registry.set_status("webhook", DependencyStatus.DISABLED)
        return True
        
    # Webhook 只检查配置是否存在，不实际发送
    return True


# ============================================================
# models.dev API
# ============================================================

@dependency_registry.register(
    "models_dev",
    category=DependencyCategory.EXTERNAL_API,
    is_critical=False,
    timeout=10.0,
    check_interval=600.0,  # 10 分钟
    fallback_message="models.dev 配置服务不可用，使用本地配置",
)
async def check_models_dev() -> bool:
    """检查 models.dev API"""
    if not settings.MODELS_DEV_ENABLED:
        dependency_registry.set_status("models_dev", DependencyStatus.DISABLED)
        return True
        
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(settings.MODELS_DEV_API_URL)
            return resp.status_code == 200
    except Exception:
        return False


# ============================================================
# Crawler 爬虫模块
# ============================================================

@dependency_registry.register(
    "crawler",
    category=DependencyCategory.EXTERNAL_API,
    is_critical=False,
    timeout=1.0,
    fallback_message="爬虫模块未启用，请在环境变量中设置 CRAWLER_ENABLED=true",
)
async def check_crawler() -> bool:
    """检查 Crawler 模块是否启用"""
    if not settings.CRAWLER_ENABLED:
        dependency_registry.set_status("crawler", DependencyStatus.DISABLED)
        return True
    
    # 已启用，检查数据库是否可访问
    try:
        import aiosqlite
        async with aiosqlite.connect(settings.CRAWLER_DATABASE_PATH) as db:
            await db.execute("SELECT 1")
        return True
    except Exception:
        return False


# ============================================================
# 启动时初始化检查
# ============================================================

async def run_startup_checks() -> dict:
    """启动时运行所有健康检查
    
    Returns:
        健康状态摘要
    """
    logger.info("开始启动健康检查...")
    
    await dependency_registry.check_all(force=True)
    summary = dependency_registry.get_summary()
    
    # 记录不健康的关键依赖
    unhealthy_critical = dependency_registry.get_unhealthy_critical()
    if unhealthy_critical:
        for dep in unhealthy_critical:
            logger.error(
                "关键依赖不可用",
                dependency=dep.name,
                error=dep.last_error,
                fallback_message=dep.fallback_message,
                report_type="dependency_unavailable",
            )
    
    logger.info(
        "健康检查完成",
        overall=summary["overall"],
        healthy=summary["healthy"],
        degraded=summary["degraded"],
        unhealthy=summary["unhealthy"],
    )
    
    return summary
