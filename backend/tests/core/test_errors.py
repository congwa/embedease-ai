"""错误处理模块测试"""

import pytest
from fastapi import status

from app.core.errors import (
    AppError,
    create_error_response,
    raise_bad_request,
    raise_forbidden,
    raise_not_found,
    raise_service_unavailable,
)


class TestAppError:
    """测试 AppError 自定义异常"""

    def test_basic_error(self):
        """测试基本错误创建"""
        error = AppError(
            code="test_error",
            message="测试错误消息",
        )
        assert error.code == "test_error"
        assert error.error_message == "测试错误消息"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.data is None

    def test_error_with_custom_status(self):
        """测试自定义状态码"""
        error = AppError(
            code="not_found",
            message="资源不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )
        assert error.status_code == status.HTTP_404_NOT_FOUND

    def test_error_with_data(self):
        """测试带附加数据的错误"""
        error = AppError(
            code="validation_error",
            message="验证失败",
            data={"field": "name", "reason": "too_long"},
        )
        assert error.data == {"field": "name", "reason": "too_long"}


class TestCreateErrorResponse:
    """测试错误响应创建函数"""

    def test_basic_response(self):
        """测试基本响应结构"""
        response = create_error_response(
            code="test_code",
            message="测试消息",
        )
        assert "error" in response
        assert response["error"]["code"] == "test_code"
        assert response["error"]["message"] == "测试消息"
        assert response["error"]["data"] is None
        assert "timestamp" in response["error"]

    def test_response_with_data(self):
        """测试带数据的响应"""
        response = create_error_response(
            code="test_code",
            message="测试消息",
            data={"key": "value"},
        )
        assert response["error"]["data"] == {"key": "value"}

    def test_timestamp_format(self):
        """测试时间戳格式"""
        response = create_error_response(code="test", message="test")
        timestamp = response["error"]["timestamp"]
        assert timestamp.endswith("Z")
        assert "T" in timestamp


class TestRaiseNotFound:
    """测试 raise_not_found 快捷函数"""

    def test_raise_not_found_basic(self):
        """测试基本 404 错误"""
        with pytest.raises(AppError) as exc_info:
            raise_not_found("agent")

        error = exc_info.value
        assert error.code == "agent_not_found"
        assert "Agent" in error.error_message
        assert error.status_code == status.HTTP_404_NOT_FOUND

    def test_raise_not_found_with_id(self):
        """测试带资源 ID 的 404 错误"""
        with pytest.raises(AppError) as exc_info:
            raise_not_found("conversation", "conv_123")

        error = exc_info.value
        assert error.data["resource"] == "conversation"
        assert error.data["id"] == "conv_123"


class TestRaiseForbidden:
    """测试 raise_forbidden 快捷函数"""

    def test_raise_forbidden_default(self):
        """测试默认 403 消息"""
        with pytest.raises(AppError) as exc_info:
            raise_forbidden()

        error = exc_info.value
        assert error.code == "forbidden"
        assert error.status_code == status.HTTP_403_FORBIDDEN
        assert "无权限" in error.error_message

    def test_raise_forbidden_custom_message(self):
        """测试自定义 403 消息"""
        with pytest.raises(AppError) as exc_info:
            raise_forbidden("您没有管理员权限")

        error = exc_info.value
        assert error.error_message == "您没有管理员权限"


class TestRaiseBadRequest:
    """测试 raise_bad_request 快捷函数"""

    def test_raise_bad_request(self):
        """测试 400 错误"""
        with pytest.raises(AppError) as exc_info:
            raise_bad_request(
                code="invalid_input",
                message="输入参数无效",
                data={"field": "email"},
            )

        error = exc_info.value
        assert error.code == "invalid_input"
        assert error.error_message == "输入参数无效"
        assert error.status_code == status.HTTP_400_BAD_REQUEST
        assert error.data == {"field": "email"}


class TestRaiseServiceUnavailable:
    """测试 raise_service_unavailable 快捷函数"""

    def test_raise_service_unavailable_default(self):
        """测试默认 503 消息"""
        with pytest.raises(AppError) as exc_info:
            raise_service_unavailable("OCR")

        error = exc_info.value
        assert error.code == "feature_disabled"
        assert error.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "OCR" in error.error_message

    def test_raise_service_unavailable_custom_message(self):
        """测试自定义 503 消息"""
        with pytest.raises(AppError) as exc_info:
            raise_service_unavailable("Memory", "记忆服务维护中")

        error = exc_info.value
        assert error.error_message == "记忆服务维护中"
        assert error.data["service"] == "Memory"

    def test_raise_service_unavailable_with_cause(self):
        """测试带原因异常的 503 错误"""
        original_error = ValueError("Connection refused")
        with pytest.raises(AppError) as exc_info:
            raise_service_unavailable("Database", cause=original_error)

        error = exc_info.value
        assert error.__cause__ is original_error
