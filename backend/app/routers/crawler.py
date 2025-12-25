"""爬取模块 API 路由

提供站点配置管理、任务管理和统计查询接口
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.crawler import CrawlSite, CrawlTask
from app.repositories.crawler import (
    CrawlPageRepository,
    CrawlSiteRepository,
    CrawlTaskRepository,
)
from app.schemas.crawler import (
    CrawlPageResponse,
    CrawlSiteCreate,
    CrawlSiteResponse,
    CrawlSiteUpdate,
    CrawlStats,
    CrawlTaskCreate,
    CrawlTaskResponse,
    ExtractionConfig,
)
from app.services.crawler import CrawlerService

logger = get_logger("router.crawler")
router = APIRouter(prefix="/crawler", tags=["crawler"])


def check_crawler_enabled():
    """检查爬取模块是否启用"""
    if not settings.CRAWLER_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="爬取模块未启用，请在 .env 中设置 CRAWLER_ENABLED=true",
        )


# ==================== 站点管理 ====================


@router.post("/sites", response_model=CrawlSiteResponse)
async def create_site(
    site_data: CrawlSiteCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """创建站点配置"""
    check_crawler_enabled()

    repo = CrawlSiteRepository(session)

    # 检查是否已存在
    existing = await repo.get_by_id(site_data.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"站点 ID 已存在: {site_data.id}",
        )

    # 序列化提取配置
    extraction_config_json = None
    if site_data.extraction_config:
        extraction_config_json = site_data.extraction_config.model_dump_json()

    # 创建站点
    site = CrawlSite(
        id=site_data.id,
        name=site_data.name,
        start_url=site_data.start_url,
        status=site_data.status.value,
        link_pattern=site_data.link_pattern,
        max_depth=site_data.max_depth,
        max_pages=site_data.max_pages,
        crawl_delay=site_data.crawl_delay,
        is_spa=site_data.is_spa,
        wait_for_selector=site_data.wait_for_selector,
        wait_timeout=site_data.wait_timeout,
        extraction_config=extraction_config_json,
        cron_expression=site_data.cron_expression,
    )
    site = await repo.create(site)

    logger.info("创建站点配置", site_id=site.id, name=site.name)
    return _site_to_response(site)


@router.get("/sites", response_model=list[CrawlSiteResponse])
async def list_sites(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """获取所有站点配置"""
    check_crawler_enabled()

    repo = CrawlSiteRepository(session)
    sites = await repo.get_all()
    return [_site_to_response(site) for site in sites]


@router.get("/sites/{site_id}", response_model=CrawlSiteResponse)
async def get_site(
    site_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """获取站点配置详情"""
    check_crawler_enabled()

    repo = CrawlSiteRepository(session)
    site = await repo.get_by_id(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"站点不存在: {site_id}",
        )
    return _site_to_response(site)


@router.patch("/sites/{site_id}", response_model=CrawlSiteResponse)
async def update_site(
    site_id: str,
    update_data: CrawlSiteUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """更新站点配置"""
    check_crawler_enabled()

    repo = CrawlSiteRepository(session)
    site = await repo.get_by_id(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"站点不存在: {site_id}",
        )

    # 更新字段
    if update_data.name is not None:
        site.name = update_data.name
    if update_data.start_url is not None:
        site.start_url = update_data.start_url
    if update_data.status is not None:
        site.status = update_data.status.value
    if update_data.link_pattern is not None:
        site.link_pattern = update_data.link_pattern
    if update_data.max_depth is not None:
        site.max_depth = update_data.max_depth
    if update_data.max_pages is not None:
        site.max_pages = update_data.max_pages
    if update_data.crawl_delay is not None:
        site.crawl_delay = update_data.crawl_delay
    if update_data.is_spa is not None:
        site.is_spa = update_data.is_spa
    if update_data.wait_for_selector is not None:
        site.wait_for_selector = update_data.wait_for_selector
    if update_data.wait_timeout is not None:
        site.wait_timeout = update_data.wait_timeout
    if update_data.extraction_config is not None:
        site.extraction_config = update_data.extraction_config.model_dump_json()
    if update_data.cron_expression is not None:
        site.cron_expression = update_data.cron_expression

    site = await repo.update(site)

    logger.info("更新站点配置", site_id=site.id)
    return _site_to_response(site)


@router.delete("/sites/{site_id}")
async def delete_site(
    site_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """删除站点配置"""
    check_crawler_enabled()

    repo = CrawlSiteRepository(session)
    site = await repo.get_by_id(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"站点不存在: {site_id}",
        )

    await repo.delete(site)
    logger.info("删除站点配置", site_id=site_id)
    return {"message": f"站点 {site_id} 已删除"}


# ==================== 任务管理 ====================


@router.post("/tasks", response_model=CrawlTaskResponse)
async def create_task(
    task_data: CrawlTaskCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """手动触发爬取任务"""
    check_crawler_enabled()

    # 检查站点是否存在
    site_repo = CrawlSiteRepository(session)
    site = await site_repo.get_by_id(task_data.site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"站点不存在: {task_data.site_id}",
        )

    # 创建任务
    crawler = CrawlerService(session)
    try:
        task_id = await crawler.crawl_site(task_data.site_id)
    finally:
        await crawler.close()

    # 获取任务详情
    task_repo = CrawlTaskRepository(session)
    task = await task_repo.get_by_id(task_id)

    logger.info("手动触发爬取任务", site_id=task_data.site_id, task_id=task_id)
    return _task_to_response(task)


@router.get("/tasks", response_model=list[CrawlTaskResponse])
async def list_tasks(
    session: Annotated[AsyncSession, Depends(get_db)],
    site_id: str | None = None,
    limit: int = 20,
):
    """获取任务列表"""
    check_crawler_enabled()

    repo = CrawlTaskRepository(session)
    if site_id:
        tasks = await repo.get_tasks_by_site(site_id, limit=limit)
    else:
        tasks = await repo.get_all()
        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=True)[:limit]

    return [_task_to_response(task) for task in tasks]


@router.get("/tasks/{task_id}", response_model=CrawlTaskResponse)
async def get_task(
    task_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """获取任务详情"""
    check_crawler_enabled()

    repo = CrawlTaskRepository(session)
    task = await repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务不存在: {task_id}",
        )
    return _task_to_response(task)


@router.get("/tasks/{task_id}/pages", response_model=list[CrawlPageResponse])
async def get_task_pages(
    task_id: int,
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 100,
    offset: int = 0,
):
    """获取任务的页面列表"""
    check_crawler_enabled()

    repo = CrawlPageRepository(session)
    pages = await repo.get_pages_by_task(task_id, limit=limit, offset=offset)
    return [
        CrawlPageResponse(
            id=page.id,
            site_id=page.site_id,
            task_id=page.task_id,
            url=page.url,
            depth=page.depth,
            status=page.status,
            is_product_page=page.is_product_page,
            product_id=page.product_id,
            crawled_at=page.crawled_at,
            parsed_at=page.parsed_at,
            parse_error=page.parse_error,
        )
        for page in pages
    ]


# ==================== 统计与状态 ====================


@router.get("/stats", response_model=CrawlStats)
async def get_stats(
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """获取爬取统计信息"""
    check_crawler_enabled()

    site_repo = CrawlSiteRepository(session)
    task_repo = CrawlTaskRepository(session)
    page_repo = CrawlPageRepository(session)

    site_stats = await site_repo.count_by_status()
    task_stats = await task_repo.count_by_status()
    total_pages = await page_repo.count_total()

    return CrawlStats(
        total_sites=sum(site_stats.values()),
        active_sites=site_stats.get("active", 0),
        total_tasks=sum(task_stats.values()),
        running_tasks=task_stats.get("running", 0),
        total_pages=total_pages,
        total_products=0,  # TODO: 从商品表统计
    )


# ==================== 辅助函数 ====================


def _site_to_response(site: CrawlSite) -> CrawlSiteResponse:
    """将站点模型转换为响应"""
    extraction_config = None
    if site.extraction_config:
        try:
            config_dict = json.loads(site.extraction_config)
            extraction_config = ExtractionConfig(**config_dict)
        except Exception:
            pass

    return CrawlSiteResponse(
        id=site.id,
        name=site.name,
        start_url=site.start_url,
        status=site.status,
        link_pattern=site.link_pattern,
        max_depth=site.max_depth,
        max_pages=site.max_pages,
        crawl_delay=site.crawl_delay,
        is_spa=site.is_spa,
        wait_for_selector=site.wait_for_selector,
        wait_timeout=site.wait_timeout,
        extraction_config=extraction_config,
        cron_expression=site.cron_expression,
        last_crawl_at=site.last_crawl_at,
        next_crawl_at=site.next_crawl_at,
        created_at=site.created_at,
        updated_at=site.updated_at,
    )


def _task_to_response(task: CrawlTask) -> CrawlTaskResponse:
    """将任务模型转换为响应"""
    return CrawlTaskResponse(
        id=task.id,
        site_id=task.site_id,
        status=task.status,
        pages_crawled=task.pages_crawled,
        pages_parsed=task.pages_parsed,
        pages_failed=task.pages_failed,
        products_found=task.products_found,
        products_created=task.products_created,
        products_updated=task.products_updated,
        started_at=task.started_at,
        finished_at=task.finished_at,
        error_message=task.error_message,
        created_at=task.created_at,
    )
