#!/bin/sh
# 首次发布创建空向量集合与图片 bucket；重复运行保留已有业务数据。
set -eu
container=$(docker ps -q --filter label=com.docker.compose.project=embedease_sfo --filter label=com.docker.compose.service=backend)
[ -n "$container" ] || { echo "Backend container is not running" >&2; exit 1; }
docker exec -i "$container" /app/.venv/bin/python - <<'PY'
import json
from minio import Minio
from qdrant_client import QdrantClient, models
from app.core.config import settings

client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
names = {settings.QDRANT_COLLECTION}
for agent in settings.default_agents:
    collection = (agent.get('knowledge_config') or {}).get('collection_name')
    if collection:
        names.add(collection)
for name in sorted(names):
    if not client.collection_exists(name):
        client.create_collection(name, vectors_config=models.VectorParams(size=settings.EMBEDDING_DIMENSION, distance=models.Distance.COSINE))
client.close()

storage = Minio(settings.MINIO_ENDPOINT, access_key=settings.MINIO_ACCESS_KEY, secret_key=settings.MINIO_SECRET_KEY, secure=settings.MINIO_USE_SSL)
bucket = settings.MINIO_BUCKET_NAME
if not storage.bucket_exists(bucket):
    storage.make_bucket(bucket)
storage.set_bucket_policy(bucket, json.dumps({'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Principal': {'AWS': ['*']}, 'Action': ['s3:GetObject'], 'Resource': [f'arn:aws:s3:::{bucket}/*']}]}))
print('Vector collections and image storage ready')
PY
