"""核心爬取服务

提供网站爬取、页面解析和商品导入的完整流程
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, Page
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_context
from app.core.logging import get_logger
from app.models.crawler import CrawlPageStatus, CrawlSiteStatus, CrawlTaskStatus
from app.repositories.crawler import (
    CrawlPageRepository,
    CrawlSiteRepository,
    CrawlTaskRepository,
)
from app.repositories.product import ProductRepository
from app.schemas.crawler import ExtractionConfig, ParsedProductData
from app.services.crawler.page_parser import PageParser

logger = get_logger("crawler.service")


class CrawlerService:
    """核心爬取服务

    负责：
    1. 管理站点配置
    2. 执行爬取任务
    3. 解析页面内容
    4. 导入商品数据
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.site_repo = CrawlSiteRepository(session)
        self.task_repo = CrawlTaskRepository(session)
        self.page_repo = CrawlPageRepository(session)
        self.product_repo = ProductRepository(session)
        self.parser = PageParser()

        # 浏览器实例（延迟初始化）
        self._browser: Browser | None = None
        self._playwright = None

    async def _get_browser(self) -> Browser:
        """获取浏览器实例（延迟初始化）"""
        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=settings.CRAWLER_HEADLESS,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            logger.info("浏览器实例已启动")
        return self._browser

    async def close(self):
        """关闭浏览器实例"""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
            logger.info("浏览器实例已关闭")

    async def crawl_site(self, site_id: str) -> int:
        """执行站点爬取任务

        Args:
            site_id: 站点 ID

        Returns:
            任务 ID
        """
        # 获取站点配置
        site = await self.site_repo.get_by_id(site_id)
        if not site:
            raise ValueError(f"站点不存在: {site_id}")

        if site.status != CrawlSiteStatus.ACTIVE.value:
            raise ValueError(f"站点未启用: {site_id}")

        # 创建任务
        task = await self.task_repo.create_task(site_id)
        task_id = task.id
        logger.info("创建爬取任务", site_id=site_id, task_id=task_id)

        # 异步执行爬取（使用独立的数据库会话，避免 session 生命周期冲突）
        # 注意：不能直接使用当前 self.session，因为调用方的 session 可能在后台任务执行前就已提交/关闭
        asyncio.create_task(self._run_with_new_session(site_id, task_id))

        return task_id

    async def _run_with_new_session(self, site_id: str, task_id: int) -> None:
        """为后台爬取任务创建独立的数据库会话
        
        这个方法确保后台协程使用自己的 session，不会受到调用方 session 生命周期的影响。
        当调用方（如 CrawlSiteTask.run）的 async with get_db_context() 退出后，
        其 session 会进入 prepared 状态，无法再执行 SQL。
        因此后台任务必须创建新的 session。
        
        Args:
            site_id: 站点 ID
            task_id: 任务 ID
        """
        async with get_db_context() as session:
            # 为后台任务创建新的 CrawlerService 实例，使用独立的 session
            service = CrawlerService(session)
            try:
                await service._execute_crawl(site_id, task_id)
            finally:
                # 确保浏览器资源被正确释放
                await service.close()

    async def _execute_crawl(self, site_id: str, task_id: int) -> None:
        """执行爬取任务（内部方法）"""
        try:
            # 更新任务状态为运行中
            await self.task_repo.update_task_status(task_id, CrawlTaskStatus.RUNNING)

            # 获取站点配置
            site = await self.site_repo.get_by_id(site_id)
            if not site:
                raise ValueError(f"站点不存在: {site_id}")

            # 解析提取配置
            extraction_config = None
            if site.extraction_config:
                try:
                    config_dict = json.loads(site.extraction_config)
                    extraction_config = ExtractionConfig(**config_dict)
                except Exception as e:
                    logger.warning("解析提取配置失败，使用 LLM 模式", error=str(e))

            # 初始化爬取队列
            visited_urls: set[str] = set()
            queue: list[tuple[str, int]] = [(site.start_url, 0)]  # (url, depth)

            pages_crawled = 0
            max_pages = site.max_pages
            max_depth = site.max_depth
            crawl_delay = site.crawl_delay

            logger.info(
                "开始爬取",
                site_id=site_id,
                start_url=site.start_url,
                max_pages=max_pages,
                max_depth=max_depth,
            )

            # 获取浏览器
            browser = await self._get_browser()

            while queue and pages_crawled < max_pages:
                url, depth = queue.pop(0)
                logger.info(
                    "开始处理页面",
                    url=url,
                    depth=depth,
                    queue_remaining=len(queue),
                    pages_crawled=pages_crawled,
                )

                # 跳过已访问的 URL（本次任务内去重）
                if url in visited_urls:
                    logger.info("页面已处理，跳过", url=url, depth=depth)
                    continue
                visited_urls.add(url)

                try:
                    # 爬取页面
                    html_content = await self._fetch_page(
                        browser,
                        url,
                        is_spa=site.is_spa,
                        wait_for_selector=site.wait_for_selector,
                        wait_timeout=site.wait_timeout,
                    )

                    if not html_content:
                        logger.warning("页面内容为空", url=url)
                        continue

                    # 保存页面（增量模式：检测内容变化）
                    page, is_new, content_changed = await self.page_repo.create_or_update_page(
                        site_id=site_id,
                        task_id=task_id,
                        url=url,
                        depth=depth,
                        html_content=html_content,
                    )

                    pages_crawled += 1

                    if not content_changed:
                        # 内容未变化，跳过解析
                        await self.task_repo.increment_task_stats(
                            task_id, pages_crawled=1, pages_skipped_duplicate=1
                        )
                        logger.debug(
                            "页面内容未变化，跳过解析",
                            url=url,
                            version=page.version,
                        )
                    else:
                        # 新页面或内容已变化，需要解析
                        await self.task_repo.increment_task_stats(
                            task_id, pages_crawled=1
                        )
                        logger.info(
                            "爬取页面成功",
                            url=url,
                            depth=depth,
                            is_new=is_new,
                            version=page.version,
                            pages_crawled=pages_crawled,
                        )

                        # 解析页面
                        await self._parse_and_save_product(
                            page.id, html_content, url, site_id, task_id, extraction_config
                        )

                    # 提取链接并加入队列（无论内容是否变化都要提取链接）
                    if depth < max_depth:
                        links = self.parser.extract_links(
                            html_content, url, site.link_pattern
                        )
                        new_links = 0
                        for link in links:
                            if link not in visited_urls:
                                queue.append((link, depth + 1))
                                new_links += 1
                        logger.info(
                            "提取链接完成",
                            url=url,
                            depth=depth,
                            next_depth=depth + 1,
                            links_found=len(links),
                            links_enqueued=new_links,
                            queue_size=len(queue),
                            links=links,
                        )
                    else:
                        logger.info(
                            "达到最大爬取深度，停止扩展链接",
                            url=url,
                            depth=depth,
                            max_depth=max_depth,
                        )

                    # 延迟
                    if crawl_delay > 0:
                        await asyncio.sleep(crawl_delay)

                except Exception as e:
                    logger.error("爬取页面失败", url=url, error=str(e))
                    continue

            # 更新站点爬取时间
            await self.site_repo.update_crawl_time(
                site_id, datetime.now(), None  # next_crawl_at 由调度器计算
            )

            # 更新任务状态为完成
            await self.task_repo.update_task_status(task_id, CrawlTaskStatus.COMPLETED)
            logger.info(
                "爬取任务完成",
                site_id=site_id,
                task_id=task_id,
                pages_crawled=pages_crawled,
            )

        except Exception as e:
            logger.error("爬取任务失败", site_id=site_id, task_id=task_id, error=str(e))
            await self.task_repo.update_task_status(
                task_id, CrawlTaskStatus.FAILED, error_message=str(e)
            )

    async def _fetch_page(
        self,
        browser: Browser,
        url: str,
        is_spa: bool = True,
        wait_for_selector: str | None = None,
        wait_timeout: int = 10,
    ) -> str | None:
        """获取页面内容

        Args:
            browser: 浏览器实例
            url: 页面 URL
            is_spa: 是否为 SPA 网站
            wait_for_selector: 等待的 CSS 选择器
            wait_timeout: 等待超时（秒）

        Returns:
            HTML 内容
        """
        page: Page | None = None
        try:
            page = await browser.new_page()

            # 设置 User-Agent
            await page.set_extra_http_headers({
                "User-Agent": settings.CRAWLER_USER_AGENT,
            })

            # 访问页面
            await page.goto(url, wait_until="domcontentloaded", timeout=wait_timeout * 1000)

            # SPA 等待
            if is_spa:
                if wait_for_selector:
                    try:
                        await page.wait_for_selector(
                            wait_for_selector, timeout=wait_timeout * 1000
                        )
                    except Exception:
                        logger.debug("等待选择器超时", selector=wait_for_selector)
                else:
                    # 默认等待网络空闲
                    await page.wait_for_load_state("networkidle", timeout=wait_timeout * 1000)

            # 获取 HTML
            html_content = await page.content()
            logger.debug(
                "页面 HTML 预览",
                url=url,
                length=len(html_content),
                snippet=html_content[:20],
            )
            return html_content

        except Exception as e:
            logger.error("获取页面失败", url=url, error=str(e))
            return None

        finally:
            if page:
                await page.close()

    async def _parse_and_save_product(
        self,
        page_id: int,
        html_content: str,
        url: str,
        site_id: str,
        task_id: int,
        extraction_config: ExtractionConfig | None,
    ) -> None:
        """解析页面并保存商品

        Args:
            page_id: 页面 ID
            html_content: HTML 内容
            url: 页面 URL
            site_id: 站点 ID
            task_id: 任务 ID
            extraction_config: 提取配置
        """
        try:
            # 解析页面
            logger.debug("解析页面")
            is_product, product_data, error = await self.parser.parse(
                html_content, url, extraction_config
            )

            if error:
                logger.error("解析页面失败", url=url, error=error)
                await self.page_repo.update_page_parsed(
                    page_id,
                    CrawlPageStatus.FAILED,
                    is_product_page=False,
                    parse_error=error,
                )
                await self.task_repo.increment_task_stats(task_id, pages_failed=1)
                return

            if not is_product or not product_data:
                logger.debug("页面不包含商品")
                await self.page_repo.update_page_parsed(
                    page_id,
                    CrawlPageStatus.SKIPPED,
                    is_product_page=False,
                )
                return

            # 生成商品 ID
            logger.debug("生成商品 ID")
            product_id = product_data.id
            if not product_id:
                # 从 URL 生成 ID
                product_id = f"{site_id}_{hashlib.md5(url.encode()).hexdigest()[:8]}"

            # 保存商品
            logger.debug("保存商品")
            is_new = await self._save_product(product_id, product_data, site_id)

            # 更新页面状态
            logger.debug("更新页面状态")
            await self.page_repo.update_page_parsed(
                page_id,
                CrawlPageStatus.PARSED,
                is_product_page=True,
                parsed_data=product_data.model_dump_json(),
                product_id=product_id,
            )

            # 更新任务统计
            if is_new:
                logger.debug("商品为新商品")
                await self.task_repo.increment_task_stats(
                    task_id,
                    pages_parsed=1,
                    products_found=1,
                    products_created=1,
                )
            else:
                logger.debug("商品为已存在商品")
                await self.task_repo.increment_task_stats(
                    task_id,
                    pages_parsed=1,
                    products_found=1,
                    products_updated=1,
                )

            logger.info(
                "商品解析成功",
                product_id=product_id,
                name=product_data.name,
                is_new=is_new,
            )

        except Exception as e:
            logger.error("解析商品失败", url=url, error=str(e))
            await self.page_repo.update_page_parsed(
                page_id,
                CrawlPageStatus.FAILED,
                is_product_page=False,
                parse_error=str(e),
            )
            await self.task_repo.increment_task_stats(task_id, pages_failed=1)

    async def _save_product(
        self, product_id: str, data: ParsedProductData, site_id: str
    ) -> bool:
        """保存商品到数据库

        Args:
            product_id: 商品 ID
            data: 商品数据
            site_id: 来源站点 ID

        Returns:
            是否为新商品
        """
        # 检查是否存在
        existing = await self.product_repo.get_by_id(product_id)
        is_new = existing is None

        # 序列化 JSON 字段
        tags_json = json.dumps(data.tags, ensure_ascii=False) if data.tags else None
        image_urls_json = (
            json.dumps(data.image_urls, ensure_ascii=False) if data.image_urls else None
        )
        specs_json = json.dumps(data.specs, ensure_ascii=False) if data.specs else None
        extra_metadata_json = (
            json.dumps(data.extra_metadata, ensure_ascii=False) if data.extra_metadata else None
        )

        # 创建或更新商品
        await self.product_repo.upsert_product(
            product_id=product_id,
            name=data.name,
            summary=data.summary,
            description=data.description,
            price=data.price,
            category=data.category,
            url=data.url,
            tags=tags_json,
            brand=data.brand,
            image_urls=image_urls_json,
            specs=specs_json,
            extra_metadata=extra_metadata_json,
            source_site_id=site_id,
        )

        return is_new

    async def reparse_pending_pages(self, site_id: str, limit: int = 100) -> int:
        """重新解析待处理的页面

        Args:
            site_id: 站点 ID
            limit: 最大处理数量

        Returns:
            处理的页面数
        """
        site = await self.site_repo.get_by_id(site_id)
        if not site:
            raise ValueError(f"站点不存在: {site_id}")

        # 解析提取配置
        extraction_config = None
        if site.extraction_config:
            try:
                config_dict = json.loads(site.extraction_config)
                extraction_config = ExtractionConfig(**config_dict)
            except Exception:
                pass

        # 获取待处理页面
        pages = await self.page_repo.get_pending_pages(site_id, limit=limit)
        processed = 0

        for page in pages:
            if page.html_content:
                await self._parse_and_save_product(
                    page.id,
                    page.html_content,
                    page.url,
                    site_id,
                    page.task_id or 0,
                    extraction_config,
                )
                processed += 1

        return processed


async def create_crawler_service() -> CrawlerService:
    """创建爬取服务实例（用于外部调用）"""
    async with get_db_context() as session:
        return CrawlerService(session)
