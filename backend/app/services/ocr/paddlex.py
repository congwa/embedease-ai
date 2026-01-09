"""PaddleX 处理器 - PP-StructureV3 版面解析

通过 HTTP API 调用 PP-StructureV3 服务进行文档版面解析和内容提取。
支持复杂版面（表格、图片、公式）的识别。
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

logger = get_logger("ocr.paddlex")


class PaddleXProcessor(BaseOCRProcessor):
    """PaddleX PP-StructureV3 文档解析器

    通过 HTTP API 调用 PP-StructureV3 服务进行版面解析。
    需要独立部署 PP-StructureV3 服务。
    """

    def __init__(
        self,
        server_url: str | None = None,
        timeout: int = 300,
    ):
        """初始化 PaddleX 处理器

        Args:
            server_url: PP-StructureV3 服务地址
            timeout: 请求超时时间（秒）
        """
        self.server_url = server_url or settings.PADDLEX_URI or "http://localhost:8080"
        self.base_url = self.server_url.rstrip("/")
        self.endpoint = f"{self.base_url}/layout-parsing"
        self.timeout = timeout

    def get_service_name(self) -> str:
        return "paddlex_ocr"

    def get_supported_extensions(self) -> list[str]:
        return [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]

    def _encode_file_to_base64(self, file_path: str) -> str:
        """将文件编码为 Base64"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def check_health(self) -> dict[str, Any]:
        """检查 PP-StructureV3 服务健康状态"""
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.base_url}/health")

                if response.status_code == 200:
                    return {
                        "status": "healthy",
                        "message": "PP-StructureV3 服务运行正常",
                        "details": {"server_url": self.server_url},
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": f"PP-StructureV3 服务响应异常: {response.status_code}",
                        "details": {"server_url": self.server_url},
                    }

        except httpx.ConnectError:
            return {
                "status": "unavailable",
                "message": "PP-StructureV3 服务无法连接，请检查服务是否启动",
                "details": {"server_url": self.server_url},
            }
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "message": "PP-StructureV3 服务连接超时",
                "details": {"server_url": self.server_url},
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"PP-StructureV3 健康检查失败: {str(e)}",
                "details": {"server_url": self.server_url, "error": str(e)},
            }

    def _call_layout_api(
        self,
        file_path: str,
        file_type: int | None = None,
        use_table_recognition: bool = True,
        use_formula_recognition: bool = True,
        use_seal_recognition: bool = False,
    ) -> dict[str, Any]:
        """调用 PP-StructureV3 版面解析 API"""
        # 编码文件
        file_base64 = self._encode_file_to_base64(file_path)

        payload = {"file": file_base64}

        # 添加参数
        if file_type is not None:
            payload["fileType"] = file_type
        payload["useTableRecognition"] = use_table_recognition
        payload["useFormulaRecognition"] = use_formula_recognition
        payload["useSealRecognition"] = use_seal_recognition

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"PP-StructureV3 API 请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data}"
                except Exception:
                    error_msg = f"{error_msg} - {response.text[:200]}"
                raise OCRException(error_msg, self.get_service_name(), "api_error")

    async def _acall_layout_api(
        self,
        file_path: str,
        file_type: int | None = None,
        use_table_recognition: bool = True,
        use_formula_recognition: bool = True,
        use_seal_recognition: bool = False,
    ) -> dict[str, Any]:
        """异步调用 PP-StructureV3 版面解析 API"""
        file_base64 = self._encode_file_to_base64(file_path)

        payload = {"file": file_base64}

        if file_type is not None:
            payload["fileType"] = file_type
        payload["useTableRecognition"] = use_table_recognition
        payload["useFormulaRecognition"] = use_formula_recognition
        payload["useSealRecognition"] = use_seal_recognition

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"PP-StructureV3 API 请求失败: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = f"{error_msg} - {error_data}"
                except Exception:
                    error_msg = f"{error_msg} - {response.text[:200]}"
                raise OCRException(error_msg, self.get_service_name(), "api_error")

    def _parse_api_result(self, api_result: dict[str, Any]) -> str:
        """解析 API 返回结果，提取文本"""
        # 检查是否有错误
        if api_result.get("errorCode") != 0:
            error_msg = api_result.get("errorMsg", "未知错误")
            raise OCRException(f"PP-StructureV3 API 错误: {error_msg}", self.get_service_name(), "api_error")

        result_data = api_result.get("result", {})
        layout_results = result_data.get("layoutParsingResults", [])

        all_text_content = []

        for page_result in layout_results:
            # 提取 Markdown 内容
            if "markdown" in page_result:
                markdown = page_result["markdown"]
                if markdown.get("text"):
                    all_text_content.append(markdown["text"])

        return "\n\n".join(all_text_content)

    def process_file(self, file_path: str, params: dict[str, Any] | None = None) -> str:
        """处理文件并返回提取的文本"""
        if not os.path.exists(file_path):
            raise OCRException(f"文件不存在: {file_path}", self.get_service_name(), "file_not_found")

        file_ext = Path(file_path).suffix.lower()
        if not self.supports_file_type(file_ext):
            raise OCRException(f"不支持的文件类型: {file_ext}", self.get_service_name(), "unsupported_file_type")

        # 检查服务健康状态
        health = self.check_health()
        if health["status"] != "healthy":
            raise OCRException(
                f"PP-StructureV3 服务不可用: {health['message']}", self.get_service_name(), health["status"]
            )

        try:
            start_time = time.time()
            params = params or {}

            # 判断文件类型：0 = PDF, 1 = 图像
            file_type = 0 if file_ext == ".pdf" else 1

            logger.info(f"PP-StructureV3 开始处理: {os.path.basename(file_path)}")

            api_result = self._call_layout_api(
                file_path=file_path,
                file_type=file_type,
                use_table_recognition=params.get("use_table_recognition", True),
                use_formula_recognition=params.get("use_formula_recognition", True),
                use_seal_recognition=params.get("use_seal_recognition", False),
            )

            text = self._parse_api_result(api_result)

            processing_time = time.time() - start_time
            logger.info(f"PP-StructureV3 处理完成: {len(text)} 字符 ({processing_time:.2f}s)")

            return text

        except OCRException:
            raise
        except Exception as e:
            error_msg = f"PP-StructureV3 处理失败: {str(e)}"
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
            params = params or {}

            file_type = 0 if file_ext == ".pdf" else 1

            logger.info(f"PP-StructureV3 开始处理: {os.path.basename(file_path)}")

            api_result = await self._acall_layout_api(
                file_path=file_path,
                file_type=file_type,
                use_table_recognition=params.get("use_table_recognition", True),
                use_formula_recognition=params.get("use_formula_recognition", True),
                use_seal_recognition=params.get("use_seal_recognition", False),
            )

            text = self._parse_api_result(api_result)

            processing_time = time.time() - start_time
            logger.info(f"PP-StructureV3 处理完成: {len(text)} 字符 ({processing_time:.2f}s)")

            return text

        except OCRException:
            raise
        except Exception as e:
            error_msg = f"PP-StructureV3 处理失败: {str(e)}"
            logger.error(error_msg)
            raise OCRException(error_msg, self.get_service_name(), "processing_failed")
