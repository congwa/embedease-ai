"""Rerank API 客户端 - 支持多提供商"""


import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("rerank")
settings = get_settings()


class RerankDocument(BaseModel):
    """Rerank 文档"""

    text: str = Field(description="文档文本内容")


class RerankResultItem(BaseModel):
    """Rerank 结果项"""

    # return_documents=false 时，返回的 results 里不会包含 document 字段
    document: RerankDocument | None = Field(default=None, description="文档内容（可选）")
    index: int = Field(description="原始索引")
    relevance_score: float = Field(description="相关性分数")


class RerankResponse(BaseModel):
    """Rerank API 响应"""

    id: str = Field(description="请求 ID")
    results: list[RerankResultItem] = Field(description="重排序结果")
    tokens: dict[str, int] | None = Field(default=None, description="Token 使用统计")


class RerankClient:
    """Rerank API 客户端

    支持所有兼容标准 Rerank API 格式的提供商
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        """初始化 Rerank 客户端

        Args:
            api_key: API Key，默认从配置读取
            base_url: API Base URL，默认从配置读取
            model: Rerank 模型，默认从配置读取
            provider: 提供商名称（可选）
            timeout: 请求超时时间（秒）
        """
        self.api_key = api_key or settings.effective_rerank_api_key
        self.base_url = (base_url or settings.effective_rerank_base_url or "").rstrip("/")
        self.model = model or settings.RERANK_MODEL
        self.provider = provider or settings.effective_rerank_provider
        self.timeout = timeout
        self.rerank_url = f"{self.base_url}/rerank"

        logger.info(
            "RerankClient 初始化",
            provider=self.provider,
            base_url=self.base_url,
            model=self.model,
            timeout=timeout,
        )

    async def rerank(
        self,
        query: str,
        documents: list[str],
        *,
        top_n: int | None = None,
        instruction: str | None = None,
        return_documents: bool = True,
    ) -> RerankResponse:
        """调用 Rerank API 对文档进行重排序

        Args:
            query: 查询文本
            documents: 待重排序的文档列表
            top_n: 返回前 N 个结果，默认从配置读取
            instruction: 重排序指令，默认从配置读取
            return_documents: 是否返回文档内容

        Returns:
            重排序结果

        Raises:
            httpx.HTTPError: HTTP 请求失败
            ValueError: API 返回错误
        """
        if not documents:
            msg = "documents 不能为空"
            raise ValueError(msg)

        top_n = top_n or settings.RERANK_TOP_N
        instruction = instruction or settings.RERANK_INSTRUCTION

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "top_n": min(top_n, len(documents)),
            "return_documents": return_documents,
        }

        if instruction:
            payload["instruction"] = instruction

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(
            "调用 Rerank API",
            query=query,
            doc_count=len(documents),
            top_n=top_n,
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.rerank_url,
                json=payload,
                headers=headers,
            )

            if response.status_code != 200:
                error_msg = f"Rerank API 请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data}"
                except Exception:
                    error_msg = f"{error_msg} - {response.text}"
                logger.error("Rerank API 错误", error=error_msg)
                raise ValueError(error_msg)

            result_data = response.json()
            result = RerankResponse(**result_data)

            logger.info(
                "Rerank API 调用成功",
                result_count=len(result.results),
                tokens=result.tokens,
            )

            return result


# 全局客户端实例（懒加载）
_rerank_client: RerankClient | None = None


def get_rerank_client() -> RerankClient:
    """获取 Rerank 客户端单例

    Returns:
        Rerank 客户端实例
    """
    global _rerank_client
    if _rerank_client is None:
        _rerank_client = RerankClient()
    return _rerank_client


async def rerank_documents(
    query: str,
    documents: list[str],
    *,
    top_n: int | None = None,
    instruction: str | None = None,
) -> list[tuple[int, float]]:
    """对文档进行重排序（便捷函数）

    Args:
        query: 查询文本
        documents: 待重排序的文档列表
        top_n: 返回前 N 个结果
        instruction: 重排序指令

    Returns:
        重排序结果，格式为 [(原始索引, 相关性分数), ...]
    """
    if not settings.RERANK_ENABLED:
        logger.warning("Rerank 功能已禁用，返回原始顺序")
        return [(i, 1.0) for i in range(len(documents))]

    try:
        client = get_rerank_client()
        result = await client.rerank(
            query=query,
            documents=documents,
            top_n=top_n,
            instruction=instruction,
            return_documents=False,
        )
        return [(item.index, item.relevance_score) for item in result.results]
    except Exception as e:
        logger.error("Rerank 失败，回退到原始顺序", error=str(e), exc_info=True)
        return [(i, 1.0) for i in range(len(documents))]
