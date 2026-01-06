"""统一错误处理

提供标准化的错误响应结构和自定义异常类。
"""

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorPayload(BaseModel):
    """标准错误响应结构"""

    code: str
    message: str
    data: dict[str, Any] | None = None
    timestamp: str


class AppError(HTTPException):
    """应用自定义异常

    使用示例:
        raise AppError(
            code="agent_not_found",
            message="Agent 不存在",
            status_code=404,
            data={"agent_id": agent_id}
        )
    """

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        data: dict[str, Any] | None = None,
    ):
        self.code = code
        self.error_message = message
        self.data = data
        super().__init__(status_code=status_code, detail=message)


def create_error_response(
    code: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """创建标准错误响应"""
    return {
        "error": {
            "code": code,
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    }


# 常用错误快捷函数
def raise_not_found(resource: str, resource_id: str | None = None) -> None:
    """抛出资源不存在错误"""
    raise AppError(
        code=f"{resource}_not_found",
        message=f"{resource.capitalize()} 不存在",
        status_code=status.HTTP_404_NOT_FOUND,
        data={"resource": resource, "id": resource_id} if resource_id else {"resource": resource},
    )


def raise_forbidden(message: str = "无权限访问") -> None:
    """抛出权限不足错误"""
    raise AppError(
        code="forbidden",
        message=message,
        status_code=status.HTTP_403_FORBIDDEN,
    )


def raise_bad_request(code: str, message: str, data: dict[str, Any] | None = None) -> None:
    """抛出请求参数错误"""
    raise AppError(
        code=code,
        message=message,
        status_code=status.HTTP_400_BAD_REQUEST,
        data=data,
    )


def raise_service_unavailable(
    service: str,
    message: str | None = None,
    *,
    cause: Exception | None = None,
) -> None:
    """抛出服务不可用错误"""
    raise AppError(
        code="feature_disabled",
        message=message or f"{service} 服务不可用",
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        data={"feature": service, "service": service},
    ) from cause
