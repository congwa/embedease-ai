"""OCR 服务模块

支持三种 OCR 处理模式：
- RapidOCR: 本地 ONNX 模型推理
- MinerU: HTTP API / 官方云服务
- PaddleX: PP-StructureV3 版面解析 HTTP 服务
"""

from app.services.ocr.base import (
    BaseOCRProcessor,
    DocumentProcessorException,
    OCRException,
    ServiceHealthCheckException,
)
from app.services.ocr.factory import OcrProcessorFactory, get_ocr_processor

__all__ = [
    "BaseOCRProcessor",
    "DocumentProcessorException",
    "OCRException",
    "ServiceHealthCheckException",
    "OcrProcessorFactory",
    "get_ocr_processor",
]
