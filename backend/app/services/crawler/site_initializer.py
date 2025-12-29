"""站点配置初始化器

负责在应用启动时从配置文件导入预置站点到数据库。
"""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.crawler import CrawlSite, CrawlSiteStatus
from app.repositories.crawler import CrawlSiteRepository
from app.services.crawler.utils import generate_site_id, normalize_domain

logger = get_logger("crawler.initializer")


async def init_config_sites(session: AsyncSession) -> list[str]:
    """初始化配置文件中的站点
    
    从 settings.crawler_sites 读取站点配置，导入到数据库。
    对于已存在的站点，会更新配置（除了 id 和 domain）。
    
    Args:
        session: 数据库会话
        
    Returns:
        导入的站点 ID 列表
    """
    if not settings.CRAWLER_ENABLED:
        logger.debug("爬虫模块未启用，跳过站点初始化")
        return []
    
    sites_config = settings.crawler_sites
    logger.info(f"Final crawler sites config: {sites_config}")
    if not sites_config:
        logger.debug("未配置预置站点")
        return []
    
    repo = CrawlSiteRepository(session)
    imported_site_ids = []
    
    for site_data in sites_config:
        try:
            # 提取必要字段
            site_id = site_data.get("id")
            start_url = site_data.get("start_url")
            name = site_data.get("name")
            
            if not start_url or not name:
                logger.warning("站点配置缺少必要字段", site_data=site_data)
                continue
            
            # 规范化域名
            domain = normalize_domain(start_url)
            
            # 如果未提供 ID，根据域名生成
            if not site_id:
                site_id = generate_site_id(domain)
            
            # 检查是否已存在
            existing = await repo.get_by_id(site_id)
            
            # 准备站点数据
            site_fields = {
                "name": name,
                "start_url": start_url,
                "domain": domain,
                "status": site_data.get("status", CrawlSiteStatus.ACTIVE.value),
                "is_system_site": True,  # 标记为系统配置站点
                "link_pattern": site_data.get("link_pattern"),
                "max_depth": site_data.get("max_depth", settings.CRAWLER_DEFAULT_MAX_DEPTH),
                "max_pages": site_data.get("max_pages", settings.CRAWLER_DEFAULT_MAX_PAGES),
                "crawl_delay": site_data.get("crawl_delay", settings.CRAWLER_DEFAULT_DELAY),
                "is_spa": site_data.get("is_spa", True),
                "wait_for_selector": site_data.get("wait_for_selector"),
                "wait_timeout": site_data.get("wait_timeout", 10),
                "cron_expression": site_data.get("cron_expression"),
            }
            
            # 处理 extraction_config
            extraction_config = site_data.get("extraction_config")
            if extraction_config:
                if isinstance(extraction_config, dict):
                    site_fields["extraction_config"] = json.dumps(extraction_config, ensure_ascii=False)
                elif isinstance(extraction_config, str):
                    site_fields["extraction_config"] = extraction_config
            
            if existing:
                # 更新现有站点（保留 id 和 domain）
                for key, value in site_fields.items():
                    if value is not None and key not in ("id", "domain"):
                        setattr(existing, key, value)
                await session.commit()
                logger.info("更新配置站点", site_id=site_id, name=name, domain=domain)
            else:
                # 创建新站点
                site = CrawlSite(id=site_id, **site_fields)
                session.add(site)
                await session.commit()
                logger.info("创建配置站点", site_id=site_id, name=name, domain=domain)
            
            imported_site_ids.append(site_id)
            
        except Exception as e:
            logger.error("导入站点配置失败", site_data=site_data, error=str(e))
            await session.rollback()
            continue
    
    if imported_site_ids:
        logger.info("站点配置初始化完成", count=len(imported_site_ids), site_ids=imported_site_ids)
    
    return imported_site_ids
