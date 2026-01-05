"""商品库画像服务 - 生成商品库统计摘要用于指导 Agent 检索"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.app_metadata import AppMetadata

# 画像存储 Key 常量
PROFILE_KEY_STATS = "catalog_profile.stats"
PROFILE_KEY_PROMPT = "catalog_profile.prompt_short"
PROFILE_KEY_FINGERPRINT = "catalog_profile.fingerprint"


class CatalogProfileService:
    """商品库画像服务
    
    职责：
    1. 从导入的商品数据生成统计画像
    2. 渲染为短提示词（<=100 字）
    3. 计算指纹用于判断变化
    4. 读写 DB metadata 表
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def build_profile_from_products(
        self, products: list[dict[str, Any]], *, top_n: int | None = None
    ) -> dict[str, Any]:
        """从商品列表生成画像统计
        
        Args:
            products: 标准化后的商品列表（每项包含 id/name/category/price 等）
            top_n: Top 类目数量，默认使用配置
            
        Returns:
            画像统计字典
        """
        if top_n is None:
            top_n = settings.CATALOG_PROFILE_TOP_CATEGORIES

        total = len(products)

        # 统计类目
        category_counts: dict[str, int] = {}
        for p in products:
            cat = (p.get("category") or "").strip()
            if cat:
                category_counts[cat] = category_counts.get(cat, 0) + 1

        # 按数量排序取 Top N
        sorted_cats = sorted(category_counts.items(), key=lambda x: -x[1])
        top_categories = [{"name": name, "count": count} for name, count in sorted_cats[:top_n]]

        # 统计价格
        prices = [p["price"] for p in products if p.get("price") is not None]
        priced_count = len(prices)
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None

        return {
            "total_products": total,
            "top_categories": top_categories,
            "category_count": len(category_counts),
            "priced_count": priced_count,
            "unpriced_count": total - priced_count,
            "min_price": min_price,
            "max_price": max_price,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def render_prompt(self, profile: dict[str, Any]) -> str:
        """渲染短提示词（<=100 字）
        
        模板：库提示：主类目{cats}；价位{min}-{max}。未命中先问类目/预算/场景；仅基于检索结果推荐。
        
        Args:
            profile: build_profile_from_products 的返回值
            
        Returns:
            短提示词字符串
        """
        # 类目片段
        top_cats = profile.get("top_categories", [])
        if top_cats:
            cats_str = "、".join(c["name"] for c in top_cats)
        else:
            cats_str = "未知"

        # 价格片段
        priced = profile.get("priced_count", 0)
        min_p = profile.get("min_price")
        max_p = profile.get("max_price")
        if priced > 0 and min_p is not None and max_p is not None:
            # 保留整数或一位小数
            min_s = f"{min_p:.0f}" if min_p == int(min_p) else f"{min_p:.1f}"
            max_s = f"{max_p:.0f}" if max_p == int(max_p) else f"{max_p:.1f}"
            price_str = f"价位{min_s}-{max_s}"
        else:
            price_str = "价位未知"

        # 行为约束（固定后缀）
        suffix = "未命中先问类目/预算/场景；仅基于检索结果推荐。"

        # 组装
        prompt = f"库提示：主类目{cats_str}；{price_str}。{suffix}"

        # 长度兜底：如果超 100 字，缩短类目
        if len(prompt) > 100 and len(top_cats) > 2:
            cats_str = "、".join(c["name"] for c in top_cats[:2])
            prompt = f"库提示：主类目{cats_str}；{price_str}。{suffix}"

        # 仍超：去掉价格
        if len(prompt) > 100:
            prompt = f"库提示：主类目{cats_str}。{suffix}"

        return prompt

    def compute_fingerprint(self, profile: dict[str, Any]) -> str:
        """计算画像指纹（用于判断是否变化）
        
        基于统计结果的稳定 hash，忽略 generated_at 时间戳
        
        Args:
            profile: 画像统计字典
            
        Returns:
            sha256 hex 指纹
        """
        # 复制并移除时间戳（避免每次都变）
        stable = {k: v for k, v in profile.items() if k != "generated_at"}
        # 稳定序列化（key 排序）
        stable_json = json.dumps(stable, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(stable_json.encode("utf-8")).hexdigest()

    async def save_profile(
        self,
        stats: dict[str, Any],
        prompt_short: str,
        fingerprint: str,
    ) -> None:
        """保存画像到 metadata 表
        
        Args:
            stats: 统计 JSON
            prompt_short: 短提示词
            fingerprint: 指纹
        """
        now = datetime.now(timezone.utc)

        # Upsert 三条记录
        for key, value in [
            (PROFILE_KEY_STATS, json.dumps(stats, ensure_ascii=False)),
            (PROFILE_KEY_PROMPT, prompt_short),
            (PROFILE_KEY_FINGERPRINT, fingerprint),
        ]:
            stmt = select(AppMetadata).where(AppMetadata.key == key)
            result = await self.session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.value = value
                existing.updated_at = now
            else:
                self.session.add(AppMetadata(key=key, value=value, updated_at=now))

    async def load_profile(self) -> dict[str, str | None]:
        """从 metadata 表加载画像
        
        Returns:
            包含 stats/prompt_short/fingerprint 的字典（值可能为 None）
        """
        result: dict[str, str | None] = {
            "stats": None,
            "prompt_short": None,
            "fingerprint": None,
        }

        keys = [PROFILE_KEY_STATS, PROFILE_KEY_PROMPT, PROFILE_KEY_FINGERPRINT]
        stmt = select(AppMetadata).where(AppMetadata.key.in_(keys))
        rows = await self.session.execute(stmt)

        for row in rows.scalars():
            if row.key == PROFILE_KEY_STATS:
                result["stats"] = row.value
            elif row.key == PROFILE_KEY_PROMPT:
                result["prompt_short"] = row.value
            elif row.key == PROFILE_KEY_FINGERPRINT:
                result["fingerprint"] = row.value

        return result

    async def get_prompt_and_fingerprint(self) -> tuple[str, str]:
        """获取短提示词和指纹（Agent 侧使用）
        
        Returns:
            (prompt_short, fingerprint) 元组，不存在则返回空字符串
        """
        data = await self.load_profile()
        return data.get("prompt_short") or "", data.get("fingerprint") or ""
