"""FastAPI 应用入口"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.crawler_database import get_crawler_db, init_crawler_db
from app.core.database import get_db_context, init_db
from app.core.logging import logger
from app.core.models_dev import get_model_profile
from app.routers import admin, chat, conversations, crawler, support, users, ws
from app.scheduler import task_registry, task_scheduler
from app.scheduler.routers import router as scheduler_router
from app.scheduler.tasks import CrawlSiteTask
from app.services.agent.agent import agent_service
from app.services.crawler.site_initializer import init_config_sites
from app.services.websocket.heartbeat import heartbeat_manager


def _init_model_profiles() -> None:
    """启动时初始化模型配置（拉取 models.dev 并打印）"""
    model_name = settings.LLM_CHAT_MODEL

    if settings.MODELS_DEV_ENABLED:
        logger.info(
            "正在从 models.dev 获取模型配置...",
            module="app",
            provider=settings.LLM_PROVIDER,
            model=model_name,
            provider_id=settings.effective_models_dev_provider_id,
            api_url=settings.MODELS_DEV_API_URL,
        )
        profile = get_model_profile(
            model_name=model_name,
            api_url=settings.MODELS_DEV_API_URL,
            provider_id=settings.effective_models_dev_provider_id,
            timeout_seconds=settings.MODELS_DEV_TIMEOUT_SECONDS,
            cache_ttl_seconds=settings.MODELS_DEV_CACHE_TTL_SECONDS,
            env_profiles=settings.model_profiles,
        )
    else:
        model_key = model_name.strip().lower()
        profile = settings.model_profiles.get(model_key, {})
        logger.info(
            "models.dev 已禁用，使用 .env 配置",
            module="app",
            provider=settings.LLM_PROVIDER,
            model=model_name,
        )

    # 打印最终生效的模型配置
    logger.info(
        "模型配置已加载",
        module="app",
        provider=settings.LLM_PROVIDER,
        model=model_name,
        profile=profile,
        reasoning_output=profile.get("reasoning_output"),
        tool_calling=profile.get("tool_calling"),
        structured_output=profile.get("structured_output"),
        max_input_tokens=profile.get("max_input_tokens"),
        max_output_tokens=profile.get("max_output_tokens"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时配置日志（确保最先执行）
    logger.configure()

    logger.info("启动应用...", module="app")
    settings.ensure_data_dir()

    # 初始化模型配置（拉取 models.dev）
    _init_model_profiles()

    await init_db()

    # 初始化爬虫配置站点
    if settings.CRAWLER_ENABLED:
        # 初始化爬虫独立数据库
        await init_crawler_db()
        
        # 使用爬虫数据库会话初始化站点配置
        async with get_crawler_db() as crawler_session:
            imported_site_ids = await init_config_sites(crawler_session)
            
            # 为每个配置站点注册调度任务
            if imported_site_ids:
                from app.repositories.crawler import CrawlSiteRepository
                site_repo = CrawlSiteRepository(crawler_session)
                
                for site_id in imported_site_ids:
                    site = await site_repo.get_by_id(site_id)
                    if site and site.cron_expression:
                        # 创建并注册该站点的定时任务
                        task = CrawlSiteTask(
                            site_id=site_id,
                            cron_expression=site.cron_expression,
                            run_on_start=settings.CRAWLER_RUN_ON_START,
                        )
                        task_registry.register(task)
                        logger.info("注册配置站点任务", site_id=site_id, cron=site.cron_expression)
            else:
                # 如果没有配置站点，注册默认任务（兼容旧逻辑）
                task_registry.register(CrawlSiteTask())
    
    # 启动调度器（即使没有任务也启动，方便后续动态注册）
    await task_scheduler.start()
    logger.info("任务调度器已启动", module="app", task_count=len(task_registry))

    # 启动 WebSocket 心跳检测
    await heartbeat_manager.start()

    logger.info("应用启动完成", module="app", host=settings.API_HOST, port=settings.API_PORT)

    yield

    logger.info("正在关闭应用...", module="app")

    # 0. 关闭 WebSocket 心跳检测
    await heartbeat_manager.stop()
    logger.debug("WebSocket 心跳检测已关闭", module="app")

    # 1. 关闭任务调度器
    await task_scheduler.stop()
    logger.debug("任务调度器已关闭", module="app")
    
    # 1. 关闭 Agent 服务（checkpointer 连接）
    await agent_service.close()
    
    # 2. 关闭 Qdrant 客户端（仅清理已初始化的资源）
    try:
        from app.services.agent.retriever import get_qdrant_client, get_vector_store
        
        # 检查是否有缓存的实例
        if get_qdrant_client.cache_info().currsize > 0:
            try:
                client = get_qdrant_client()
                client.close()
                logger.debug("Qdrant 客户端已关闭", module="app")
            except Exception:
                pass
        
        # 清理 LRU 缓存
        get_qdrant_client.cache_clear()
        get_vector_store.cache_clear()
        logger.debug("向量存储缓存已清理", module="app")
    except Exception as e:
        logger.warning("清理 Qdrant 资源时出错", module="app", error=str(e))
    
    # 3. 关闭数据库引擎
    try:
        from app.core.database import engine
        await engine.dispose()
        logger.debug("主数据库引擎已关闭", module="app")
    except Exception as e:
        logger.warning("关闭主数据库引擎时出错", module="app", error=str(e))
    
    # 3.1 关闭爬虫数据库引擎
    if settings.CRAWLER_ENABLED:
        try:
            from app.core.crawler_database import crawler_engine
            await crawler_engine.dispose()
            logger.debug("爬虫数据库引擎已关闭", module="app")
        except Exception as e:
            logger.warning("关闭爬虫数据库引擎时出错", module="app", error=str(e))
    
    # 4. 关闭 OpenAI 客户端（仅清理已初始化的资源）
    try:
        from app.core.llm import get_embeddings, get_chat_model
        
        # 只有在缓存中有实例时才关闭
        if get_embeddings.cache_info().currsize > 0:
            try:
                embeddings = get_embeddings()
                if hasattr(embeddings, 'client') and embeddings.client:
                    await embeddings.client.close()
                if hasattr(embeddings, 'async_client') and embeddings.async_client:
                    await embeddings.async_client.aclose()
                logger.debug("Embeddings 客户端已关闭", module="app")
            except Exception:
                pass
        
        # 清理 LRU 缓存
        get_embeddings.cache_clear()
        get_chat_model.cache_clear()
        logger.debug("LLM 缓存已清理", module="app")
    except Exception as e:
        logger.warning("关闭 OpenAI 客户端时出错", module="app", error=str(e))
    
    logger.info("应用已关闭", module="app")


app = FastAPI(
    title="商品推荐 Agent",
    description="基于 LangChain v1.1 的智能商品推荐系统",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(crawler.router)
app.include_router(support.router)
app.include_router(users.router)
app.include_router(ws.router)
app.include_router(scheduler_router)


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
