"""MinerU 处理器 - HTTP API 文档解析

支持两种模式：
- mineru_ocr: 自建 MinerU HTTP 服务
- mineru_official: MinerU 官方云服务 API
"""

import asyncio
import base64
import os
import time
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ocr.base import BaseOCRProcessor, OCRException

logger = get_logger("ocr.mineru")


class MinerUProcessor(BaseOCRProcessor):
    """MinerU HTTP API 处理器

    通过 HTTP API 调用 MinerU 服务进行文档解析。
    支持自建服务或官方云服务。
    """

    def __init__(
        self,
        server_url: str | None = None,
        api_key: str | None = None,
        is_official: bool = False,
        timeout: int = 300,
    ):
        """初始化 MinerU 处理器

        Args:
            server_url: API 服务地址
            api_key: API 密钥（官方服务需要）
            is_official: 是否使用官方云服务
            timeout: 请求超时时间（秒）
        """
        self.is_official = is_official
        self.timeout = timeout

        if is_official:
            self.server_url = server_url or settings.MINERU_OFFICIAL_URL or "https://api.mineru.net"
            self.api_key = api_key or settings.MINERU_OFFICIAL_API_KEY
        else:
            self.server_url = server_url or settings.MINERU_API_URL or "http://localhost:8000"
            self.api_key = api_key or settings.MINERU_API_KEY

        self.base_url = self.server_url.rstrip("/")

    def get_service_name(self) -> str:
        return "mineru_official" if self.is_official else "mineru_ocr"

    def get_supported_extensions(self) -> list[str]:
        return [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".docx", ".pptx"]

    def _encode_file_to_base64(self, file_path: str) -> str:
        """将文件编码为 Base64"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def check_health(self) -> dict[str, Any]:
        """检查 MinerU 服务健康状态"""
        try:
            with httpx.Client(timeout=10) as client:
                # 尝试健康检查端点
                try:
                    response = client.get(f"{self.base_url}/health")
                    if response.status_code == 200:
                        return {
                            "status": "healthy",
                            "message": f"MinerU 服务运行正常",
                            "details": {"server_url": self.server_url, "is_official": self.is_official},
                        }
                except httpx.RequestError:
                    pass

                # 尝试根路径
                try:
                    response = client.get(f"{self.base_url}/")
                    if response.status_code in (200, 404):
                        return {
                            "status": "healthy",
                            "message": "MinerU 服务可达",
                            "details": {"server_url": self.server_url, "is_official": self.is_official},
                        }
                except httpx.RequestError:
                    pass

                return {
                    "status": "unavailable",
                    "message": "MinerU 服务无法连接",
                    "details": {"server_url": self.server_url},
                }

        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "message": "MinerU 服务连接超时",
                "details": {"server_url": self.server_url},
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"健康检查失败: {str(e)}",
                "details": {"server_url": self.server_url, "error": str(e)},
            }

    def _call_parse_api(self, file_path: str, params: dict | None = None) -> dict[str, Any]:
        """调用文档解析 API"""
        params = params or {}

        # 编码文件
        file_base64 = self._encode_file_to_base64(file_path)
        file_ext = Path(file_path).suffix.lower()

        # 构建请求
        payload = {
            "file": file_base64,
            "file_type": file_ext.lstrip("."),
            "filename": os.path.basename(file_path),
        }

        # 添加可选参数
        if params.get("enable_table"):
            payload["enable_table"] = True
        if params.get("enable_formula"):
            payload["enable_formula"] = True

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # 选择端点
        endpoint = f"{self.base_url}/parse" if not self.is_official else f"{self.base_url}/v1/parse"

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(endpoint, json=payload, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"MinerU API 请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('message', error_data)}"
                except Exception:
                    error_msg = f"{error_msg} - {response.text[:200]}"
                raise OCRException(error_msg, self.get_service_name(), "api_error")

    async def _acall_parse_api(self, file_path: str, params: dict | None = None) -> dict[str, Any]:
        """异步调用文档解析 API"""
        params = params or {}

        file_base64 = self._encode_file_to_base64(file_path)
        file_ext = Path(file_path).suffix.lower()

        payload = {
            "file": file_base64,
            "file_type": file_ext.lstrip("."),
            "filename": os.path.basename(file_path),
        }

        if params.get("enable_table"):
            payload["enable_table"] = True
        if params.get("enable_formula"):
            payload["enable_formula"] = True

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        endpoint = f"{self.base_url}/parse" if not self.is_official else f"{self.base_url}/v1/parse"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(endpoint, json=payload, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"MinerU API 请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data.get('message', error_data)}"
                except Exception:
                    error_msg = f"{error_msg} - {response.text[:200]}"
                raise OCRException(error_msg, self.get_service_name(), "api_error")

    def _extract_text_from_result(self, result: dict[str, Any]) -> str:
        """从 API 结果中提取文本"""
        # 尝试多种可能的响应格式
        if "text" in result:
            return result["text"]
        if "content" in result:
            return result["content"]
        if "markdown" in result:
            return result["markdown"]
        if "result" in result:
            inner = result["result"]
            if isinstance(inner, str):
                return inner
            if isinstance(inner, dict):
                return inner.get("text") or inner.get("content") or inner.get("markdown") or ""
        if "pages" in result:
            pages_text = []
            for page in result["pages"]:
                if isinstance(page, dict):
                    pages_text.append(page.get("text") or page.get("content") or "")
                elif isinstance(page, str):
                    pages_text.append(page)
            return "\n\n".join(pages_text)

        logger.warning(f"无法从 MinerU 响应中提取文本: {list(result.keys())}")
        return ""

    def process_file(self, file_path: str, params: dict[str, Any] | None = None) -> str:
        """处理文件并返回提取的文本"""
        if not os.path.exists(file_path):
            raise OCRException(f"文件不存在: {file_path}", self.get_service_name(), "file_not_found")

        file_ext = Path(file_path).suffix.lower()
        if not self.supports_file_type(file_ext):
            raise OCRException(f"不支持的文件类型: {file_ext}", self.get_service_name(), "unsupported_file_type")

        # 检查服务健康状态
        health = self.check_health()
        if health["status"] not in ("healthy",):
            raise OCRException(
                f"MinerU 服务不可用: {health['message']}", self.get_service_name(), health["status"]
            )

        try:
            start_time = time.time()
            logger.info(f"MinerU 开始处理: {os.path.basename(file_path)}")

            result = self._call_parse_api(file_path, params)
            text = self._extract_text_from_result(result)

            processing_time = time.time() - start_time
            logger.info(f"MinerU 处理完成: {len(text)} 字符 ({processing_time:.2f}s)")

            return text

        except OCRException:
            raise
        except Exception as e:
            error_msg = f"MinerU 处理失败: {str(e)}"
            logger.error(error_msg)
            raise OCRException(error_msg, self.get_service_name(), "processing_failed")

    async def aprocess_file(self, file_path: str, params: dict[str, Any] | None = None) -> str:
        """异步处理文件"""
        if not os.path.exists(file_path):
            raise OCRException(f"文件不存在: {file_path}", self.get_service_name(), "file_not_found")

        file_ext = Path(file_path).suffix.lower()
        if not self.supports_file_type(file_ext):
            raise OCRException(f"不支持的文件类型: {file_ext}", self.get_service_name(), "unsupported_file_type")

        try:
            start_time = time.time()
            logger.info(f"MinerU 开始处理: {os.path.basename(file_path)}")

            result = await self._acall_parse_api(file_path, params)
            text = self._extract_text_from_result(result)

            processing_time = time.time() - start_time
            logger.info(f"MinerU 处理完成: {len(text)} 字符 ({processing_time:.2f}s)")

            return text

        except OCRException:
            raise
        except Exception as e:
            error_msg = f"MinerU 处理失败: {str(e)}"
            logger.error(error_msg)
            raise OCRException(error_msg, self.get_service_name(), "processing_failed")
