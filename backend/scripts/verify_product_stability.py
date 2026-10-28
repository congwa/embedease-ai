"""离线回归商品召回、精确详情、预算约束和增量索引；仅创建一次性 SQLite。"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from langchain_core.documents import Document  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_db_context  # noqa: E402
from app.core.db import provider  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.services import product_index  # noqa: E402
from app.services.agent.retrieval.enhanced import enhanced_search, price_bounds  # noqa: E402
from app.services.agent.tools.product.compare import compare_products  # noqa: E402
from app.services.agent.tools.product.details import get_product_details  # noqa: E402


class Emitter:
    """记录真实工具函数的业务事件，不注入模型或网络。"""

    def __init__(self):
        self.events = []

    def emit(self, kind, payload):
        """保留状态和输出，验证成功与失败契约。"""
        self.events.append((kind, payload))


class ProductChecks(unittest.IsolatedAsyncioTestCase):
    """用真实 SQL 与工具函数校验商品身份、约束和长文上下文。"""

    async def asyncSetUp(self):
        """创建隔离数据库，所有业务读取指向该库。"""
        self.tmp = tempfile.TemporaryDirectory()
        self.db = provider.SQLiteProvider("sqlite+aiosqlite:///" + self.tmp.name + "/app.db")
        self.mock = patch.object(provider, "_provider", self.db)
        self.mock.start()
        await self.db.init_db(Base)
        async with get_db_context() as db:
            db.add_all(
                [
                    Product(
                        id="A",
                        name="静音键盘",
                        price=129,
                        category="键盘",
                        summary="静音无线",
                        description="完整规则：保修23个月。",
                        specs='{"续航":"30天"}',
                    ),
                    Product(
                        id="B",
                        name="机械键盘",
                        price=249,
                        category="键盘",
                        description="机械键盘完整说明",
                    ),
                ]
            )
        self.emitter = Emitter()
        self.runtime = SimpleNamespace(context=SimpleNamespace(emitter=self.emitter))

    async def asyncTearDown(self):
        """关闭隔离连接，不改变项目数据库。"""
        await self.db.close()
        self.mock.stop()
        self.tmp.cleanup()

    async def test_exact_details(self):
        """ID 精确读取完整规格，已存在商品不依赖向量排名。"""
        obj = json.loads(await get_product_details.coroutine(product_id="A", runtime=self.runtime))
        self.assertEqual(obj["id"], "A")
        self.assertIn("23个月", obj["description"])
        self.assertEqual(obj["specs"]["续航"], "30天")
        missing = json.loads(
            await get_product_details.coroutine(product_id="missing", runtime=self.runtime)
        )
        self.assertIn("error", missing)

    async def test_comparison(self):
        """对比按唯一 ID 获取所有完整商品。"""
        obj = json.loads(
            await compare_products.coroutine(product_ids=["A", "B"], runtime=self.runtime)
        )
        self.assertEqual({p["id"] for p in obj["products"]}, {"A", "B"})
        self.assertIn("23个月", obj["products"][0]["description"])

    async def test_semantics_budget_and_aggregation(self):
        """口语同义词不清空候选；旧元数据、重复块和已删除商品不污染结果。"""
        docs = [
            Document(
                page_content="x" * 250 + "末尾命中规则：23个月",
                metadata={"product_id": "A", "price": 999, "product_name": "旧名称"},
            ),
            Document(page_content="第二个块", metadata={"product_id": "A"}),
            Document(page_content="机械键盘", metadata={"product_id": "B"}),
            Document(page_content="已删除", metadata={"product_id": "deleted"}),
        ]
        retriever = SimpleNamespace(ainvoke=AsyncMock(return_value=docs))
        with patch(
            "app.services.agent.retrieval.product.get_retriever_async",
            AsyncMock(return_value=retriever),
        ):
            result = await enhanced_search(
                "室友睡觉时用的安静键盘", max_price=150, enable_rerank=False
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].metadata["product_name"], "静音键盘")
            self.assertEqual(result[0].metadata["price"], 129)
            self.assertIn("末尾命中规则：23个月", result[0].page_content)
            result = await enhanced_search("100元以内 键盘", enable_rerank=False)
            self.assertEqual(result, [])
            result = await enhanced_search("键盘", category="不存在分类", enable_rerank=False)
            self.assertEqual(result, [])

    async def test_price_filter_uses_sql(self):
        """价格过滤不遗漏向量候选之外的商品。"""
        from app.services.agent.tools.product.filter_price import filter_by_price

        result = json.loads(await filter_by_price.coroutine(runtime=self.runtime, max_price=150))
        self.assertEqual([p["id"] for p in result], ["A"])

    async def test_similar_source_identity(self):
        """相似推荐的源商品先按 SQL ID 精确确认。"""
        from app.services.agent.tools.product.similar import find_similar_products

        docs = [
            Document(
                page_content="相似的键盘",
                metadata={
                    "product_id": "B",
                    "product_name": "机械键盘",
                    "price": 249,
                    "category": "键盘",
                },
            )
        ]
        with patch(
            "app.services.agent.tools.product.similar.enhanced_search", AsyncMock(return_value=docs)
        ):
            result = json.loads(
                await find_similar_products.coroutine(product_id="A", runtime=self.runtime)
            )
        self.assertEqual(result["similar_products"][0]["id"], "B")

    async def test_vector_initialization_off_loop(self):
        """网络客户端和向量存储的同步初始化都在线程中执行。"""
        import threading

        from app.services.agent.retrieval.product import get_vector_store_async

        main_thread = threading.get_ident()
        threads = []

        def info(*args):
            threads.append(threading.get_ident())
            return SimpleNamespace(
                config=SimpleNamespace(
                    params=SimpleNamespace(
                        vectors=SimpleNamespace(size=settings.EMBEDDING_DIMENSION)
                    )
                )
            )

        def client():
            threads.append(threading.get_ident())
            return SimpleNamespace(get_collection=info)

        def store(*args, **kwargs):
            threads.append(threading.get_ident())
            return SimpleNamespace()

        with (
            patch("app.services.agent.retrieval.product.get_qdrant_client", client),
            patch("app.services.agent.retrieval.product.QdrantVectorStore", store),
            patch(
                "app.services.agent.retrieval.product.get_product_embeddings",
                AsyncMock(return_value=object()),
            ),
        ):
            self.assertIsNotNone(await get_vector_store_async())
        self.assertTrue(threads and all(t != main_thread for t in threads))

    def test_budget_parser(self):
        """范围、上限和型号数字不能相互混淆。"""
        self.assertEqual(price_bounds("预算300到800元"), (300, 800))
        self.assertEqual(price_bounds("150元以内"), (None, 150))
        self.assertEqual(price_bounds("严格不超过100元"), (None, 100))
        self.assertEqual(price_bounds("DEMO-ANC01 100元左右"), (None, None))
        self.assertEqual(price_bounds("预算300元左右"), (None, None))

    async def test_embedding_transport(self):
        """商品工厂与默认商品模型均明确发送原文。"""
        from app.core.llm import get_embeddings
        from app.services.agent.retrieval.product import (
            get_default_product_embeddings,
            get_product_embeddings,
        )

        with patch.object(settings, "LLM_API_KEY", "qa-only-key"):
            get_embeddings.cache_clear()
            get_default_product_embeddings.cache_clear()
            self.assertTrue(get_embeddings().check_embedding_ctx_length)
            self.assertFalse(get_default_product_embeddings().check_embedding_ctx_length)
            self.assertFalse((await get_product_embeddings()).check_embedding_ctx_length)
            get_embeddings.cache_clear()
            get_default_product_embeddings.cache_clear()


class IndexChecks(unittest.IsolatedAsyncioTestCase):
    """模拟存储故障，验证只清理当前商品、幂等重试与保留旧块。"""

    async def test_incremental_lifecycle(self):
        """生产索引函数写入、缩短、失败重试和删除均不清整集合。"""
        store = {}
        exists = False
        fail = False

        def matching(point, flt):
            """按实际使用的 product_id 与排除新 ID 过滤。"""
            pid = flt.must[0].match.value
            excluded = set(flt.must_not[0].has_id) if flt.must_not else set()
            return point.payload["metadata"]["product_id"] == pid and point.id not in excluded

        class Client:
            def __init__(self, **kwargs):
                pass

            def collection_exists(self, c):
                return exists

            def create_collection(self, *a, **kw):
                nonlocal exists
                exists = True

            def get_collection(self, c):
                return SimpleNamespace(
                    config=SimpleNamespace(params=SimpleNamespace(vectors=SimpleNamespace(size=3)))
                )

            def scroll(self, *a, **kw):
                return list(store.values())[:1], None

            def upsert(self, c, points, wait):
                for p in points:
                    store[p.id] = p

            def delete(self, c, points_selector, wait):
                if fail:
                    raise ConnectionError("QA cleanup outage")
                for pid, p in list(store.items()):
                    if matching(p, points_selector.filter):
                        del store[pid]

            def count(self, c, count_filter, exact):
                return SimpleNamespace(count=sum(matching(p, count_filter) for p in store.values()))

            def close(self):
                pass

        embeddings = SimpleNamespace(
            aembed_documents=AsyncMock(side_effect=lambda texts: [[1.0, 0.0, 0.0] for _ in texts])
        )
        a = {"id": "A", "name": "长文商品", "description": "唯一段落介绍。" * 80, "price": 129}
        b = {"id": "B", "name": "其他商品", "description": "保留其他商品", "price": 249}
        with (
            patch.object(product_index, "QdrantClient", Client),
            patch.object(
                product_index, "get_product_embeddings", AsyncMock(return_value=embeddings)
            ),
            patch.object(settings, "EMBEDDING_DIMENSION", 3),
            patch.object(settings, "CHUNK_SIZE", 120),
            patch.object(settings, "CHUNK_OVERLAP", 20),
        ):
            await product_index.index_products([a, b])
            self.assertGreater(len(store), 2)
            new = {**a, "description": "更新后的短规则"}
            fail = True
            with self.assertRaises(ConnectionError):
                await product_index.index_products([new])
            self.assertTrue(any(p.payload["metadata"]["product_id"] == "B" for p in store.values()))
            fail = False
            await product_index.index_products([new])
            self.assertEqual(len(store), 2)
            await product_index.index_products([new])
            self.assertEqual(len(store), 2)
            self.assertTrue(
                any("更新后的短规则" in p.payload["page_content"] for p in store.values())
            )
            await product_index.remove_product_vectors("A")
            self.assertEqual(len(store), 1)
            self.assertEqual(next(iter(store.values())).payload["metadata"]["product_id"], "B")
            self.assertTrue(
                all(
                    isinstance(t, str)
                    for call in embeddings.aembed_documents.call_args_list
                    for t in call.args[0]
                )
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
