"""独立私有文档桶；所有阻塞 SDK 调用均在线程内执行。"""

import asyncio
from io import BytesIO

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager, Retry, Timeout

from app.core.config import settings
from app.services.knowledge.rag.settings import RagError


class DocumentStorage:
    """不生成公开链接，原始内容只经受控后端接口返回。"""

    def _client(self) -> Minio:
        """按当前运行配置创建客户端，禁用服务时明确失败。"""
        if not settings.MINIO_ENABLED:
            raise RagError("文档存储未启用，请配置 MinIO", 503)
        if settings.KNOWLEDGE_BUCKET == settings.MINIO_BUCKET_NAME:
            raise RagError("知识文档桶必须与聊天图片桶分离", 503)
        return Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_SSL,
            http_client=PoolManager(
                timeout=Timeout(connect=5, read=30), retries=Retry(total=2, backoff_factor=0.2)
            ),
        )

    def _private_client(self) -> Minio:
        """拒绝已有公开桶，不自动修改其他业务的桶策略。"""
        client = self._client()
        bucket = settings.KNOWLEDGE_BUCKET
        if not client.bucket_exists(bucket):
            try:
                client.make_bucket(bucket)
            except S3Error as exc:
                if exc.code not in {"BucketAlreadyOwnedByYou", "BucketAlreadyExists"}:
                    raise
        try:
            policy = client.get_bucket_policy(bucket)
        except S3Error as exc:
            if exc.code not in {"NoSuchBucketPolicy", "NoSuchPolicy"}:
                raise
        else:
            if policy:
                raise RagError("知识文档桶存在访问策略，请使用无公开策略的独立私有桶", 503)
        return client

    async def put(self, key: str, data: bytes, mime: str) -> None:
        """保存原始字节，内容哈希由业务层记录。"""

        def upload():
            client = self._private_client()
            client.put_object(
                settings.KNOWLEDGE_BUCKET, key, BytesIO(data), len(data), content_type=mime
            )

        await asyncio.to_thread(upload)

    async def get(self, key: str) -> bytes:
        """读取受大小限制的原始文件并释放连接。"""

        def download():
            response = self._private_client().get_object(settings.KNOWLEDGE_BUCKET, key)
            try:
                data = response.read(settings.KNOWLEDGE_MAX_FILE_BYTES + 1)
                if len(data) > settings.KNOWLEDGE_MAX_FILE_BYTES:
                    raise RagError("原文件超过当前大小限制")
                return data
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(download)

    async def delete(self, key: str) -> None:
        """幂等删除，失败交由持久任务重试。"""

        def remove():
            try:
                self._client().remove_object(settings.KNOWLEDGE_BUCKET, key)
            except S3Error as exc:
                if exc.code not in {"NoSuchBucket", "NoSuchKey"}:
                    raise

        await asyncio.to_thread(remove)

    async def objects(self) -> list[tuple[str, float]]:
        """巡检暂存对象，只暴露对象键及修改时间给清理器。"""

        def listing():
            client = self._private_client()
            return [
                (o.object_name, o.last_modified.timestamp())
                for o in client.list_objects(
                    settings.KNOWLEDGE_BUCKET, prefix="documents/", recursive=True
                )
            ]

        return await asyncio.to_thread(listing)
