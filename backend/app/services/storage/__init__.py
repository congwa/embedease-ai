"""存储服务模块"""

from app.services.storage.minio_service import MinIOService, get_minio_service

__all__ = ["MinIOService", "get_minio_service"]
