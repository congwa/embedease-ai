"""UserProfileStore 测试"""

from datetime import datetime

import pytest

from app.services.memory.store import Item


class TestItem:
    """测试 Store 条目"""

    def test_item_creation(self):
        """测试条目创建"""
        now = datetime.now()
        item = Item(
            namespace=("users", "user_123"),
            key="profile",
            value={"nickname": "小明"},
            created_at=now,
            updated_at=now,
        )
        assert item.namespace == ("users", "user_123")
        assert item.key == "profile"
        assert item.value["nickname"] == "小明"
        assert item.created_at == now
        assert item.updated_at == now

    def test_item_repr(self):
        """测试条目字符串表示"""
        item = Item(
            namespace=("users", "user_456"),
            key="preferences",
            value={"theme": "dark"},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        repr_str = repr(item)
        assert "users" in repr_str
        assert "user_456" in repr_str
        assert "preferences" in repr_str

    def test_item_with_complex_value(self):
        """测试复杂值的条目"""
        item = Item(
            namespace=("users", "user_1"),
            key="data",
            value={
                "profile": {
                    "name": "测试用户",
                    "age": 25,
                },
                "preferences": ["手机", "电脑"],
                "scores": [0.8, 0.9, 0.95],
            },
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert item.value["profile"]["name"] == "测试用户"
        assert "手机" in item.value["preferences"]
        assert len(item.value["scores"]) == 3

    def test_item_namespace_tuple(self):
        """测试命名空间元组"""
        item = Item(
            namespace=("app", "users", "user_123", "settings"),
            key="notifications",
            value={"email": True, "sms": False},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert len(item.namespace) == 4
        assert item.namespace[0] == "app"
        assert item.namespace[-1] == "settings"

    def test_item_empty_value(self):
        """测试空值条目"""
        item = Item(
            namespace=("test",),
            key="empty",
            value={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert item.value == {}

    def test_item_timestamps_different(self):
        """测试不同的创建和更新时间"""
        created = datetime(2024, 1, 1, 10, 0, 0)
        updated = datetime(2024, 6, 15, 14, 30, 0)
        item = Item(
            namespace=("users", "user_1"),
            key="profile",
            value={"version": 2},
            created_at=created,
            updated_at=updated,
        )
        assert item.created_at < item.updated_at
        assert item.created_at.year == 2024
        assert item.updated_at.month == 6
