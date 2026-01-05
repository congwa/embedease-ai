"""用户画像服务

从事实/图谱中提取结构化画像信息，统一管理画像的读写与更新。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from app.core.logging import get_logger
from app.services.memory.models import Fact, KnowledgeGraph

logger = get_logger("memory.profile_service")


class ProfileUpdateSource(StrEnum):
    """画像更新来源"""

    FACT = "fact"  # 从事实抽取
    GRAPH = "graph"  # 从图谱抽取
    USER_INPUT = "user_input"  # 用户显式输入
    SYSTEM = "system"  # 系统自动


# 来源优先级：用户输入 > 系统 > 事实 > 图谱
SOURCE_PRIORITY = {
    ProfileUpdateSource.USER_INPUT: 4,
    ProfileUpdateSource.SYSTEM: 3,
    ProfileUpdateSource.FACT: 2,
    ProfileUpdateSource.GRAPH: 1,
}


@dataclass
class ProfileUpdate:
    """画像更新记录"""

    field_name: str
    old_value: Any
    new_value: Any
    source: ProfileUpdateSource
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ProfileUpdateResult:
    """画像更新结果"""

    updated_fields: list[str] = field(default_factory=list)
    updates: list[ProfileUpdate] = field(default_factory=list)
    success: bool = True
    error: str | None = None


# ============ 规则引擎：从事实/图谱提取画像字段 ============


# 预算提取正则
BUDGET_PATTERNS = [
    # "预算3000" "预算 3000元" "预算3k"
    r"预算[：:\s]*(\d+\.?\d*)\s*[kK千]?\s*(?:元|块|左右)?",
    # "3000-5000" "3000～5000" "3000到5000"
    r"(\d+\.?\d*)\s*[kK千]?\s*[-~～到至]\s*(\d+\.?\d*)\s*[kK千]?",
    # "3000左右" "大概3000"
    r"(?:大概|大约|左右|差不多)[：:\s]*(\d+\.?\d*)\s*[kK千]?",
    r"(\d+\.?\d*)\s*[kK千]?\s*(?:左右|上下|差不多)",
    # "不超过5000" "最多5000"
    r"(?:不超过|最多|上限)[：:\s]*(\d+\.?\d*)\s*[kK千]?",
    # "至少3000" "最少3000"
    r"(?:至少|最少|下限|起码)[：:\s]*(\d+\.?\d*)\s*[kK千]?",
]

# 品类/偏好关键词
CATEGORY_KEYWORDS = [
    "手机",
    "电脑",
    "笔记本",
    "轻薄本",
    "游戏本",
    "平板",
    "耳机",
    "音箱",
    "相机",
    "电视",
    "冰箱",
    "洗衣机",
    "空调",
    "键盘",
    "鼠标",
    "显示器",
    "手表",
    "智能手表",
    "运动鞋",
    "跑鞋",
]

# 品牌关键词
BRAND_KEYWORDS = [
    "苹果",
    "Apple",
    "iPhone",
    "MacBook",
    "华为",
    "Huawei",
    "小米",
    "Xiaomi",
    "OPPO",
    "vivo",
    "三星",
    "Samsung",
    "联想",
    "Lenovo",
    "戴尔",
    "Dell",
    "惠普",
    "HP",
    "索尼",
    "Sony",
    "佳能",
    "Canon",
    "尼康",
    "Nikon",
]

# 语气偏好关键词
TONE_PATTERNS = {
    "友好": ["友好", "亲切", "温和", "热情"],
    "专业": ["专业", "正式", "严谨", "商务"],
    "简洁": ["简洁", "简短", "直接", "干脆"],
    "详细": ["详细", "详尽", "完整", "全面"],
}


def _normalize_budget(value: str) -> float:
    """将预算字符串标准化为数值"""
    value = value.strip()
    multiplier = 1.0
    if value.endswith(("k", "K", "千")):
        multiplier = 1000.0
        value = value[:-1]
    try:
        return float(value) * multiplier
    except ValueError:
        return 0.0


def extract_budget_from_text(text: str) -> tuple[float | None, float | None]:
    """从文本中提取预算区间

    Returns:
        (budget_min, budget_max) 元组，未提取到则返回 None
    """
    budget_min = None
    budget_max = None

    for pattern in BUDGET_PATTERNS:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            if len(groups) == 2 and groups[1]:
                # 区间模式
                budget_min = _normalize_budget(groups[0])
                budget_max = _normalize_budget(groups[1])
            elif len(groups) >= 1 and groups[0]:
                # 单值模式，设置为中心值 ±20%
                value = _normalize_budget(groups[0])
                if "不超过" in text or "最多" in text or "上限" in text:
                    budget_max = value
                elif "至少" in text or "最少" in text or "下限" in text:
                    budget_min = value
                else:
                    # 默认 ±20% 区间
                    budget_min = value * 0.8
                    budget_max = value * 1.2
            break

    return budget_min, budget_max


def extract_categories_from_text(text: str) -> list[str]:
    """从文本中提取品类偏好"""
    found = []
    text_lower = text.lower()
    for keyword in CATEGORY_KEYWORDS:
        if keyword.lower() in text_lower:
            if keyword not in found:
                found.append(keyword)
    return found


def extract_brands_from_text(text: str) -> list[str]:
    """从文本中提取品牌偏好"""
    found = []
    text_lower = text.lower()
    for keyword in BRAND_KEYWORDS:
        if keyword.lower() in text_lower:
            if keyword not in found:
                found.append(keyword)
    return found


def extract_tone_from_text(text: str) -> str | None:
    """从文本中提取语气偏好"""
    for tone, keywords in TONE_PATTERNS.items():
        for keyword in keywords:
            if keyword in text:
                return tone
    return None


def derive_profile_updates_from_facts(
    facts: list[Fact],
) -> dict[str, Any]:
    """从事实列表中提取画像更新

    Args:
        facts: 事实列表

    Returns:
        画像字段更新字典
    """
    updates: dict[str, Any] = {}

    all_categories: list[str] = []
    all_brands: list[str] = []

    for fact in facts:
        text = fact.content

        # 提取预算
        budget_min, budget_max = extract_budget_from_text(text)
        if budget_min is not None and "budget_min" not in updates:
            updates["budget_min"] = budget_min
        if budget_max is not None and "budget_max" not in updates:
            updates["budget_max"] = budget_max

        # 提取品类
        categories = extract_categories_from_text(text)
        all_categories.extend(categories)

        # 提取品牌
        brands = extract_brands_from_text(text)
        all_brands.extend(brands)

        # 提取语气偏好
        tone = extract_tone_from_text(text)
        if tone and "tone_preference" not in updates:
            updates["tone_preference"] = tone

    # 去重并限制数量
    if all_categories:
        updates["favorite_categories"] = list(dict.fromkeys(all_categories))[:10]

    if all_brands:
        updates.setdefault("custom_data", {})
        updates["custom_data"]["brand_preferences"] = list(
            dict.fromkeys(all_brands)
        )[:10]

    return updates


def derive_profile_updates_from_graph(
    graph: KnowledgeGraph,
) -> dict[str, Any]:
    """从知识图谱中提取画像更新

    Args:
        graph: 知识图谱

    Returns:
        画像字段更新字典
    """
    updates: dict[str, Any] = {}

    # 从关系中提取偏好
    preferred_items: list[str] = []
    for relation in graph.relations:
        if relation.relation_type.upper() in ("PREFERS", "LIKES", "WANTS", "喜欢", "偏好"):
            preferred_items.append(relation.to_entity)

    if preferred_items:
        # 判断是品类还是品牌
        categories = []
        brands = []
        for item in preferred_items:
            if any(kw.lower() in item.lower() for kw in CATEGORY_KEYWORDS):
                categories.append(item)
            elif any(kw.lower() in item.lower() for kw in BRAND_KEYWORDS):
                brands.append(item)
            else:
                # 默认归入品类
                categories.append(item)

        if categories:
            updates["favorite_categories"] = list(dict.fromkeys(categories))[:10]
        if brands:
            updates.setdefault("custom_data", {})
            updates["custom_data"]["brand_preferences"] = list(
                dict.fromkeys(brands)
            )[:10]

    # 从实体观察中提取任务进度
    for entity in graph.entities:
        if entity.entity_type.upper() in ("TASK", "任务", "GOAL", "目标"):
            task_id = entity.name.replace(" ", "_").lower()
            task_info = {
                "name": entity.name,
                "observations": entity.observations,
                "updated_at": datetime.now().isoformat(),
            }
            updates.setdefault("task_progress", {})
            updates["task_progress"][task_id] = task_info

    return updates


# ============ ProfileService 主类 ============


class ProfileService:
    """用户画像服务

    统一管理画像的读写、更新、冲突解决。

    用法：
    ```python
    service = await get_profile_service()

    # 从事实更新画像
    result = await service.update_from_facts(user_id, facts)

    # 从图谱更新画像
    result = await service.update_from_graph(user_id, graph)

    # 用户显式更新
    result = await service.update_profile(user_id, {"budget_max": 5000}, source=ProfileUpdateSource.USER_INPUT)

    # 获取画像
    profile = await service.get_profile(user_id)
    ```
    """

    def __init__(self):
        self._store = None

    async def _get_store(self):
        """获取 Store 实例"""
        if self._store is None:
            from app.services.memory.store import get_user_profile_store

            self._store = await get_user_profile_store()
        return self._store

    async def get_profile(self, user_id: str) -> dict[str, Any] | None:
        """获取用户画像"""
        store = await self._get_store()
        return await store.get_user_profile(user_id)

    async def update_profile(
        self,
        user_id: str,
        updates: dict[str, Any],
        source: ProfileUpdateSource = ProfileUpdateSource.SYSTEM,
    ) -> ProfileUpdateResult:
        """更新用户画像

        Args:
            user_id: 用户 ID
            updates: 要更新的字段
            source: 更新来源

        Returns:
            ProfileUpdateResult 包含更新详情
        """
        if not updates:
            return ProfileUpdateResult()

        try:
            store = await self._get_store()
            existing = await store.get_user_profile(user_id) or {}

            # 记录更新详情
            result = ProfileUpdateResult()
            final_updates: dict[str, Any] = {}

            for key, new_value in updates.items():
                old_value = existing.get(key)

                # 特殊处理嵌套字段（如 custom_data、task_progress）
                if key in ("custom_data", "task_progress") and isinstance(
                    new_value, dict
                ):
                    merged = dict(old_value) if isinstance(old_value, dict) else {}
                    merged.update(new_value)
                    new_value = merged

                # 特殊处理列表字段（合并去重）
                if key == "favorite_categories" and isinstance(new_value, list):
                    old_list = old_value if isinstance(old_value, list) else []
                    merged = list(dict.fromkeys(old_list + new_value))[:15]
                    new_value = merged

                # 检查是否有变化
                if old_value != new_value:
                    final_updates[key] = new_value
                    result.updates.append(
                        ProfileUpdate(
                            field_name=key,
                            old_value=old_value,
                            new_value=new_value,
                            source=source,
                        )
                    )
                    result.updated_fields.append(key)

            if final_updates:
                # 记录更新来源
                final_updates["_last_update_source"] = source.value
                final_updates["_last_update_at"] = datetime.now().isoformat()

                await store.update_user_profile(user_id, final_updates)

                logger.info(
                    "画像更新成功",
                    user_id=user_id,
                    source=source.value,
                    updated_fields=result.updated_fields,
                )

            return result

        except Exception as e:
            logger.error("画像更新失败", user_id=user_id, error=str(e))
            return ProfileUpdateResult(success=False, error=str(e))

    async def update_from_facts(
        self,
        user_id: str,
        facts: list[Fact],
    ) -> ProfileUpdateResult:
        """从事实列表更新画像

        Args:
            user_id: 用户 ID
            facts: 事实列表

        Returns:
            ProfileUpdateResult
        """
        if not facts:
            return ProfileUpdateResult()

        updates = derive_profile_updates_from_facts(facts)
        if not updates:
            return ProfileUpdateResult()

        return await self.update_profile(
            user_id, updates, source=ProfileUpdateSource.FACT
        )

    async def update_from_graph(
        self,
        user_id: str,
        graph: KnowledgeGraph,
    ) -> ProfileUpdateResult:
        """从知识图谱更新画像

        Args:
            user_id: 用户 ID
            graph: 知识图谱

        Returns:
            ProfileUpdateResult
        """
        if not graph.entities and not graph.relations:
            return ProfileUpdateResult()

        updates = derive_profile_updates_from_graph(graph)
        if not updates:
            return ProfileUpdateResult()

        return await self.update_profile(
            user_id, updates, source=ProfileUpdateSource.GRAPH
        )

    async def delete_profile(self, user_id: str) -> bool:
        """删除用户画像"""
        store = await self._get_store()
        return await store.delete(("users", user_id), "profile")


# 单例
_profile_service_instance: ProfileService | None = None


async def get_profile_service() -> ProfileService:
    """获取 ProfileService 单例"""
    global _profile_service_instance
    if _profile_service_instance is None:
        _profile_service_instance = ProfileService()
    return _profile_service_instance
