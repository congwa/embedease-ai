"""图片上传 API 路由"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger
from app.services.storage import get_minio_service

logger = get_logger("routers.upload")

router = APIRouter(prefix="/upload", tags=["upload"])


class ImageUploadResponse(BaseModel):
    """图片上传响应"""

    id: str
    url: str
    thumbnail_url: str
    filename: str
    size: int
    width: int
    height: int
    mime_type: str


class UploadConfigResponse(BaseModel):
    """上传配置响应"""

    enabled: bool
    max_size_mb: int
    max_count_per_message: int
    allowed_types: list[str]


@router.get("/config", response_model=UploadConfigResponse)
async def get_upload_config() -> UploadConfigResponse:
    """获取上传配置"""
    return UploadConfigResponse(
        enabled=settings.MINIO_ENABLED,
        max_size_mb=settings.IMAGE_MAX_SIZE_MB,
        max_count_per_message=settings.IMAGE_MAX_COUNT_PER_MESSAGE,
        allowed_types=settings.image_allowed_types_list,
    )


@router.post("/image", response_model=ImageUploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    user_id: str = "",
) -> ImageUploadResponse:
    """上传图片
    
    Args:
        file: 图片文件
        user_id: 用户 ID（用于目录隔离）
    
    Returns:
        上传结果，包含图片 URL 等信息
    """
    # 检查 MinIO 是否启用
    minio_service = get_minio_service()
    if not minio_service.is_available:
        raise HTTPException(
            status_code=503,
            detail="图片上传服务未启用，请配置 MINIO_ENABLED=true",
        )

    # 验证文件类型
    content_type = file.content_type or "application/octet-stream"
    if content_type not in settings.image_allowed_types_list:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的图片类型: {content_type}，允许的类型: {settings.image_allowed_types_list}",
        )

    # 读取文件内容
    file_data = await file.read()
    file_size = len(file_data)

    # 验证文件大小
    if file_size > settings.image_max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"图片太大: {file_size / 1024 / 1024:.2f}MB，最大允许: {settings.IMAGE_MAX_SIZE_MB}MB",
        )

    # 验证文件不为空
    if file_size == 0:
        raise HTTPException(status_code=400, detail="图片文件为空")

    # 获取文件名
    filename = file.filename or "image.jpg"

    # 使用默认 user_id 如果未提供
    if not user_id:
        user_id = "anonymous"

    try:
        result = minio_service.upload_image(
            file_data=file_data,
            user_id=user_id,
            filename=filename,
            content_type=content_type,
        )
        
        logger.info(
            "图片上传成功",
            image_id=result["id"],
            user_id=user_id,
            filename=filename,
            size=file_size,
        )
        
        return ImageUploadResponse(
            id=result["id"],
            url=result["url"],
            thumbnail_url=result["thumbnail_url"],
            filename=result["filename"],
            size=result["size"],
            width=result["width"],
            height=result["height"],
            mime_type=result["mime_type"],
        )
    except Exception as e:
        logger.error("图片上传失败", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"图片上传失败: {e!s}")


@router.delete("/image/{image_id}")
async def delete_image(image_id: str, user_id: str = "") -> dict:
    """删除图片
    
    Args:
        image_id: 图片 ID
        user_id: 用户 ID
    
    Returns:
        删除结果
    """
    minio_service = get_minio_service()
    if not minio_service.is_available:
        raise HTTPException(status_code=503, detail="图片上传服务未启用")

    if not user_id:
        user_id = "anonymous"

    # 尝试删除各种可能的扩展名
    deleted = False
    for ext in ["jpg", "jpeg", "png", "webp", "gif"]:
        object_name = f"{user_id}/{image_id}.{ext}"
        if minio_service.delete_image(object_name):
            deleted = True
            # 同时尝试删除缩略图
            thumb_name = f"{user_id}/{image_id}_thumb.{ext}"
            minio_service.delete_image(thumb_name)
            break

    if not deleted:
        raise HTTPException(status_code=404, detail="图片不存在")

    return {"success": True, "message": "图片已删除"}
