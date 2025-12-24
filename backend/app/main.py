"""FastAPI 应用入口"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import logger
from app.core.models_dev import get_model_profile
from app.routers import chat, conversations, crawler, users
from app.services.agent.agent import agent_service


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

    # 初始化爬取调度器
    if settings.CRAWLER_ENABLED:
        from app.services.crawler import CrawlScheduler
        crawler_scheduler = CrawlScheduler.get_instance()
        await crawler_scheduler.start()
        logger.info("爬取调度器已启动", module="app")

    logger.info("应用启动完成", module="app", host=settings.API_HOST, port=settings.API_PORT)

    yield

    logger.info("正在关闭应用...", module="app")

    # 0. 关闭爬取调度器
    if settings.CRAWLER_ENABLED:
        from app.services.crawler import CrawlScheduler
        crawler_scheduler = CrawlScheduler.get_instance()
        await crawler_scheduler.stop()
        logger.debug("爬取调度器已关闭", module="app")
    
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
        logger.debug("数据库引擎已关闭", module="app")
    except Exception as e:
        logger.warning("关闭数据库引擎时出错", module="app", error=str(e))
    
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
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(crawler.router)
app.include_router(users.router)


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
