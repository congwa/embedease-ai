"""BaseRepository 测试

测试基础 Repository 的 CRUD 操作逻辑。
由于需要数据库连接，这里主要测试 Repository 的初始化和类型定义。
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import TypeVar

from app.repositories.base import BaseRepository, ModelT


class TestBaseRepositoryInit:
    """测试 BaseRepository 初始化"""

    def test_init_with_session(self):
        """测试使用 session 初始化"""
        mock_session = MagicMock()
        
        # 创建一个具体的 Repository 子类来测试
        class TestRepository(BaseRepository):
            model = MagicMock()
        
        repo = TestRepository(mock_session)
        assert repo.session is mock_session

    def test_repository_has_model_attribute(self):
        """测试 Repository 有 model 属性"""
        mock_session = MagicMock()
        
        class TestRepository(BaseRepository):
            model = MagicMock()
        
        repo = TestRepository(mock_session)
        assert hasattr(repo, 'model')


class TestBaseRepositoryMethods:
    """测试 BaseRepository 方法签名"""

    def test_has_get_by_id_method(self):
        """测试有 get_by_id 方法"""
        assert hasattr(BaseRepository, 'get_by_id')
        assert callable(getattr(BaseRepository, 'get_by_id'))

    def test_has_get_all_method(self):
        """测试有 get_all 方法"""
        assert hasattr(BaseRepository, 'get_all')
        assert callable(getattr(BaseRepository, 'get_all'))

    def test_has_create_method(self):
        """测试有 create 方法"""
        assert hasattr(BaseRepository, 'create')
        assert callable(getattr(BaseRepository, 'create'))

    def test_has_update_method(self):
        """测试有 update 方法"""
        assert hasattr(BaseRepository, 'update')
        assert callable(getattr(BaseRepository, 'update'))

    def test_has_delete_method(self):
        """测试有 delete 方法"""
        assert hasattr(BaseRepository, 'delete')
        assert callable(getattr(BaseRepository, 'delete'))


class TestBaseRepositoryTypeHints:
    """测试 BaseRepository 类型提示"""

    def test_is_generic_class(self):
        """测试是泛型类"""
        from typing import Generic
        # BaseRepository 是 Generic 的子类
        assert issubclass(BaseRepository, Generic)

    def test_model_type_var(self):
        """测试 ModelT 类型变量"""
        assert ModelT is not None
        # ModelT 是 TypeVar
        assert isinstance(ModelT, TypeVar)
