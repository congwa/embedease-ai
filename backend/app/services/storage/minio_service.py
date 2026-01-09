"""MinIO 对象存储服务"""

from __future__ import annotations

import uuid
from datetime import timedelta
from io import BytesIO
from typing import TYPE_CHECKING, BinaryIO

from minio import Minio
from minio.error import S3Error
from PIL import Image

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("services.storage.minio")


class MinIOService:
    """MinIO 存储服务
    
    提供图片上传、下载、删除等功能，支持自动生成缩略图。
    """

    def __init__(self) -> None:
        if not settings.MINIO_ENABLED:
            logger.warning("MinIO 未启用，存储服务不可用")
            self._client = None
            return

        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
        )
        self._bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket()

    @property
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self._client is not None

    def _ensure_bucket(self) -> None:
        """确保 bucket 存在"""
        if not self._client:
            return
        try:
            if not self._client.bucket_exists(self._bucket_name):
                self._client.make_bucket(self._bucket_name)
                logger.info("创建 MinIO bucket", bucket=self._bucket_name)
        except S3Error as e:
            logger.error("MinIO bucket 检查失败", error=str(e))

    def upload_image(
        self,
        file_data: bytes,
        user_id: str,
        filename: str,
        content_type: str,
        *,
        generate_thumbnail: bool = True,
    ) -> dict:
        """上传图片并生成缩略图
        
        Args:
            file_data: 文件二进制数据
            user_id: 用户 ID（用于目录隔离）
            filename: 原始文件名
            content_type: MIME 类型
            generate_thumbnail: 是否生成缩略图
        
        Returns:
            {
                "id": "图片唯一 ID",
                "url": "完整图片 URL",
                "thumbnail_url": "缩略图 URL",
                "object_name": "对象名称",
                "size": 文件大小,
                "width": 图片宽度,
                "height": 图片高度
            }
        """
        if not self._client:
            raise RuntimeError("MinIO 服务未启用")

        # 生成唯一 ID 和对象名
        image_id = str(uuid.uuid4())
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        object_name = f"{user_id}/{image_id}.{ext}"
        
        file_size = len(file_data)
        
        # 获取图片尺寸
        width, height = 0, 0
        try:
            img = Image.open(BytesIO(file_data))
            width, height = img.size
        except Exception as e:
            logger.warning("获取图片尺寸失败", error=str(e))
        
        # 上传原图
        self._client.put_object(
            self._bucket_name,
            object_name,
            BytesIO(file_data),
            length=file_size,
            content_type=content_type,
        )
        
        url = self._get_public_url(object_name)
        result = {
            "id": image_id,
            "url": url,
            "thumbnail_url": url,
            "object_name": object_name,
            "size": file_size,
            "width": width,
            "height": height,
            "filename": filename,
            "mime_type": content_type,
        }
        
        # 生成缩略图
        if generate_thumbnail and width > 0:
            try:
                thumb_name = f"{user_id}/{image_id}_thumb.{ext}"
                thumb_data = self._create_thumbnail(file_data, ext)
                
                self._client.put_object(
                    self._bucket_name,
                    thumb_name,
                    BytesIO(thumb_data),
                    length=len(thumb_data),
                    content_type=content_type,
                )
                
                result["thumbnail_url"] = self._get_public_url(thumb_name)
            except Exception as e:
                logger.warning("缩略图生成失败", error=str(e))
        
        logger.info(
            "图片上传成功",
            image_id=image_id,
            object_name=object_name,
            size=file_size,
            dimensions=f"{width}x{height}",
        )
        return result

    def _create_thumbnail(self, image_data: bytes, ext: str) -> bytes:
        """创建缩略图"""
        img = Image.open(BytesIO(image_data))
        
        # 保持宽高比缩放
        max_size = settings.IMAGE_THUMBNAIL_SIZE
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        output = BytesIO()
        # 根据扩展名选择格式
        fmt = "JPEG" if ext.lower() in ("jpg", "jpeg") else ext.upper()
        if fmt == "JPG":
            fmt = "JPEG"
        
        # PNG 和 GIF 保持原格式，其他转 JPEG
        if fmt not in ("PNG", "GIF", "WEBP"):
            fmt = "JPEG"
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
        
        img.save(output, format=fmt, quality=85)
        return output.getvalue()

    def _get_public_url(self, object_name: str) -> str:
        """获取公开访问 URL"""
        return f"{settings.MINIO_PUBLIC_URL}/{self._bucket_name}/{object_name}"

    def get_presigned_url(
        self,
        object_name: str,
        expires: timedelta = timedelta(hours=1),
    ) -> str:
        """获取预签名 URL（用于私有文件）"""
        if not self._client:
            raise RuntimeError("MinIO 服务未启用")
        return self._client.presigned_get_object(
            self._bucket_name,
            object_name,
            expires=expires,
        )

    def delete_image(self, object_name: str) -> bool:
        """删除图片
        
        Args:
            object_name: 对象名称
            
        Returns:
            是否删除成功
        """
        if not self._client:
            return False
        try:
            self._client.remove_object(self._bucket_name, object_name)
            logger.info("图片删除成功", object_name=object_name)
            return True
        except S3Error as e:
            logger.error("图片删除失败", object_name=object_name, error=str(e))
            return False

    def get_image_as_base64(self, object_name: str) -> str | None:
        """获取图片的 base64 编码（用于发送给大模型）
        
        Args:
            object_name: 对象名称
            
        Returns:
            base64 编码的图片数据，失败返回 None
        """
        if not self._client:
            return None
        try:
            import base64
            response = self._client.get_object(self._bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return base64.b64encode(data).decode("utf-8")
        except Exception as e:
            logger.error("获取图片 base64 失败", object_name=object_name, error=str(e))
            return None


# 全局单例
_minio_service: MinIOService | None = None


def get_minio_service() -> MinIOService:
    """获取 MinIO 服务单例"""
    global _minio_service
    if _minio_service is None:
        _minio_service = MinIOService()
    return _minio_service
