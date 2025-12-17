"""清理 Qdrant - 删除所有 collections"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient

from app.core.config import settings


def main():
    """清理 Qdrant collections"""
    print("[clean] 连接到 Qdrant...")
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    try:
        # 获取所有 collections
        collections = client.get_collections().collections
        print(f"[clean] 找到 {len(collections)} 个 collections:")
        for collection in collections:
            print(f"  - {collection.name}")

        if not collections:
            print("[clean] 没有需要清理的 collections")
            return

        # 删除所有 collections
        for collection in collections:
            print(f"[clean] 删除 collection: {collection.name}")
            client.delete_collection(collection.name)

        print(f"[clean] 已删除 {len(collections)} 个 collections")
        print("[clean] 清理完成！")

    finally:
        client.close()


if __name__ == "__main__":
    main()

