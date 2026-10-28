"""商品导入脚本 - 导入 JSON 数据并创建 Qdrant 向量索引"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


from app.core.database import get_db_context, init_db
from app.schemas.product import ProductCreate
from app.services.catalog_profile import CatalogProfileService
from app.services.product import ProductService


def normalize_product(raw: dict) -> dict:
    """标准化单个商品数据（源头规范化）

    确保：
    - id/name 为 str 且 strip
    - category 为 None 或非空字符串
    - price 为 float 或 None
    - summary/description/url 为 None 或非空字符串
    - tags/image_urls 为 list 或 None
    - specs/extra_metadata 为 dict 或 None
    - brand/source_site_id 为 str 或 None
    """
    product_id = str(raw.get("id", "")).strip()
    name = str(raw.get("name", "")).strip()

    # category: 空串当 None
    cat = raw.get("category")
    if isinstance(cat, str):
        cat = cat.strip() or None
    else:
        cat = None

    # price: 转 float，非法当 None
    price = raw.get("price")
    if price is not None:
        try:
            price = float(price)
        except (ValueError, TypeError):
            price = None

    # summary/description/url: 空串当 None
    def clean_str(val):
        if isinstance(val, str):
            return val.strip() or None
        return None

    # 列表字段: 确保为 list 或 None
    def clean_list(val):
        if isinstance(val, list):
            return [str(v).strip() for v in val if v] or None
        return None

    # 字典字段: 确保为 dict 或 None
    def clean_dict(val):
        if isinstance(val, dict):
            return val or None
        return None

    return {
        "id": product_id,
        "name": name,
        "category": cat,
        "price": price,
        "summary": clean_str(raw.get("summary")),
        "description": clean_str(raw.get("description")),
        "url": clean_str(raw.get("url")),
        # 扩展字段（向后兼容，可选）
        "tags": clean_list(raw.get("tags")),
        "brand": clean_str(raw.get("brand")),
        "image_urls": clean_list(raw.get("image_urls")),
        "specs": clean_dict(raw.get("specs")),
        "extra_metadata": clean_dict(raw.get("extra_metadata")),
        "source_site_id": clean_str(raw.get("source_site_id")),
    }


async def import_products(json_path: str) -> None:
    """导入商品数据"""
    print(f"[import] 开始导入商品数据: {json_path}")

    # 读取 JSON 文件
    with open(json_path, encoding="utf-8") as f:
        products_data_raw = json.load(f)

    print(f"[import] 读取到 {len(products_data_raw)} 个商品")

    # 标准化商品数据（源头规范化）
    products_data = [normalize_product(p) for p in products_data_raw]
    # 过滤掉无效商品（无 id 或无 name）
    products_data = [p for p in products_data if p["id"] and p["name"]]
    print(f"[import] 标准化后有效商品: {len(products_data)} 个")

    # 初始化数据库
    await init_db()

    # 保存到 SQLite + 生成画像
    async with get_db_context() as session:
        # 1. 保存商品
        product_service = ProductService(session)
        for product_data in products_data:
            product = ProductCreate(**product_data)
            await product_service.create_or_update_product(product)
        print(f"[import] 已保存 {len(products_data)} 个商品到数据库")

        # 2. 生成并保存商品库画像
        await generate_and_save_catalog_profile(session, products_data)

    # 创建 Qdrant 向量索引
    await create_vector_index(products_data)

    # 关闭数据库连接
    from app.core.db.provider import get_database_provider

    await get_database_provider().close()

    print("[import] 导入完成!")


async def generate_and_save_catalog_profile(session, products_data: list[dict]) -> None:
    """生成并保存商品库画像

    在导入时调用，基于标准化后的商品数据生成画像并入库
    """
    print("[import] 生成商品库画像...")

    profile_service = CatalogProfileService(session)

    # 1. 生成统计
    profile_stats = profile_service.build_profile_from_products(products_data)

    # 2. 渲染短提示词
    prompt_short = profile_service.render_prompt(profile_stats)

    # 3. 计算指纹
    fingerprint = profile_service.compute_fingerprint(profile_stats)

    # 4. 保存到 metadata 表
    await profile_service.save_profile(profile_stats, prompt_short, fingerprint)

    # 打印摘要
    top_cats = [c["name"] for c in profile_stats.get("top_categories", [])]
    print(
        f"[import] 画像统计: 商品总数={profile_stats['total_products']}, "
        f"类目数={profile_stats['category_count']}, "
        f"有价格={profile_stats['priced_count']}"
    )
    print(f"[import] Top 类目: {', '.join(top_cats) if top_cats else '无'}")
    print(f"[import] 短提示词({len(prompt_short)}字): {prompt_short}")
    print(f"[import] 指纹: {fingerprint[:16]}...")


async def create_vector_index(products_data: list[dict]) -> None:
    """增量写入商品向量，禁止删除其他商品的集合或数据。"""
    from app.services.product_index import index_products

    await index_products(products_data)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        # 默认使用 fixtures/products.json
        json_path = Path(__file__).parent.parent / "fixtures" / "products.json"
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

    # 使用 asyncio.run() 运行主任务，它会自动清理事件循环
    try:
        asyncio.run(import_products(str(json_path)))
        print("[import] 程序正常退出")
        sys.exit(0)  # 显式退出，确保所有资源被释放
    except KeyboardInterrupt:
        print("\n[import] 导入已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n[error] 导入失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
