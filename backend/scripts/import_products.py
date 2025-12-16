"""商品导入脚本 - 导入 JSON 数据并创建 Qdrant 向量索引"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings
from app.core.database import get_db_context, init_db
from app.core.llm import get_embeddings
from app.schemas.product import ProductCreate
from app.services.product import ProductService
from app.utils.text import split_text


async def import_products(json_path: str) -> None:
    """导入商品数据"""
    print(f"[import] 开始导入商品数据: {json_path}")

    # 读取 JSON 文件
    with open(json_path, encoding="utf-8") as f:
        products_data = json.load(f)

    print(f"[import] 读取到 {len(products_data)} 个商品")

    # 初始化数据库
    await init_db()

    # 保存到 SQLite
    async with get_db_context() as session:
        product_service = ProductService(session)
        for product_data in products_data:
            product = ProductCreate(**product_data)
            await product_service.create_or_update_product(product)
        print(f"[import] 已保存 {len(products_data)} 个商品到数据库")

    # 创建 Qdrant 向量索引
    await create_vector_index(products_data)

    print("[import] 导入完成!")


async def create_vector_index(products_data: list[dict]) -> None:
    """创建 Qdrant 向量索引"""
    print("[import] 开始创建向量索引...")

    # 初始化嵌入模型
    embeddings = get_embeddings()

    # 连接 Qdrant
    client = QdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

    # 检查集合是否存在，如果存在则删除重建
    collection_name = settings.QDRANT_COLLECTION
    collections = client.get_collections().collections
    if any(c.name == collection_name for c in collections):
        print(f"[import] 删除现有集合: {collection_name}")
        client.delete_collection(collection_name)

    # 创建集合
    print(f"[import] 创建集合: {collection_name}")
    print(f"[import] 向量维度: {settings.SILICONFLOW_EMBEDDING_DIMENSION}")
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.SILICONFLOW_EMBEDDING_DIMENSION,
            distance=Distance.COSINE,
        ),
    )

    # 准备文档
    documents: list[Document] = []
    for product in products_data:
        # 组合商品信息作为嵌入文本
        text_parts = [
            f"商品名称: {product['name']}",
        ]
        if product.get("summary"):
            text_parts.append(f"核心卖点: {product['summary']}")
        if product.get("category"):
            text_parts.append(f"分类: {product['category']}")
        if product.get("description"):
            # 如果描述太长，进行分块
            description = product["description"]
            if len(description) > settings.CHUNK_SIZE:
                chunks = split_text(description)
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        page_content=f"{text_parts[0]}\n{chunk}",
                        metadata={
                            "product_id": product["id"],
                            "product_name": product["name"],
                            "price": product.get("price"),
                            "category": product.get("category"),
                            "url": product.get("url"),
                            "chunk_index": i + 1,  # 1 表示第一个分块
                        },
                    )
                    documents.append(doc)
            else:
                text_parts.append(f"描述: {description}")

        # 添加主文档（摘要）
        main_doc = Document(
            page_content="\n".join(text_parts),
            metadata={
                "product_id": product["id"],
                "product_name": product["name"],
                "price": product.get("price"),
                "category": product.get("category"),
                "url": product.get("url"),
                "chunk_index": 0,  # 0 表示摘要
            },
        )
        documents.append(main_doc)

    print(f"[import] 准备了 {len(documents)} 个文档")

    # 创建向量存储并添加文档
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embeddings,
    )

    # 批量添加文档
    batch_size = 10
    for i in range(0, len(documents), batch_size):
        batch = documents[i : i + batch_size]
        await asyncio.to_thread(vector_store.add_documents, batch)
        print(f"[import] 已添加 {min(i + batch_size, len(documents))}/{len(documents)} 个文档")

    print(f"[import] 向量索引创建完成，共 {len(documents)} 个向量")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        # 默认使用 data/products.json
        json_path = Path(__file__).parent.parent / "data" / "products.json"
    else:
        json_path = Path(sys.argv[1])

    if not json_path.exists():
        print(f"[error] 文件不存在: {json_path}")
        print("[info] 请创建商品数据文件，格式如下:")
        print("""
[
  {
    "id": "P001",
    "name": "商品名称",
    "summary": "核心卖点",
    "description": "详细描述",
    "price": 299.00,
    "category": "分类",
    "url": "https://example.com/product/P001"
  }
]
""")
        sys.exit(1)

    asyncio.run(import_products(str(json_path)))


if __name__ == "__main__":
    main()
