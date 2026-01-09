"""OCR 处理器工厂

提供统一的 OCR 处理器创建和管理接口。
"""

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ocr.base import BaseOCRProcessor

logger = get_logger("ocr.factory")

# 处理器实例缓存
_PROCESSOR_CACHE: dict[str, BaseOCRProcessor] = {}


class OcrProcessorFactory:
    """OCR 处理器工厂

    支持的处理器类型：
    - rapid_ocr: RapidOCR 本地 ONNX 模型
    - mineru_ocr: MinerU 自建 HTTP API
    - mineru_official: MinerU 官方云服务 API
    - paddlex_ocr: PP-StructureV3 版面解析
    """

    PROCESSOR_TYPES = {
        "rapid_ocr": "RapidOCRProcessor",
        "mineru_ocr": "MinerUProcessor",
        "mineru_official": "MinerUProcessor",
        "paddlex_ocr": "PaddleXProcessor",
    }

    @classmethod
    def get_processor(cls, processor_type: str, **kwargs) -> BaseOCRProcessor:
        """获取 OCR 处理器实例（单例模式）

        Args:
            processor_type: 处理器类型
                - "rapid_ocr": RapidOCR 本地 ONNX 模型
                - "mineru_ocr": MinerU 自建 HTTP API
                - "mineru_official": MinerU 官方云服务 API
                - "paddlex_ocr": PP-StructureV3 版面解析
            **kwargs: 处理器初始化参数

        Returns:
            BaseOCRProcessor: 处理器实例

        Raises:
            ValueError: 不支持的处理器类型
        """
        if processor_type not in cls.PROCESSOR_TYPES:
            raise ValueError(
                f"不支持的处理器类型: {processor_type}. 支持的类型: {list(cls.PROCESSOR_TYPES.keys())}"
            )

        # 生成缓存键
        cache_key = f"{processor_type}_{hash(frozenset(kwargs.items()))}"

        if cache_key not in _PROCESSOR_CACHE:
            processor = cls._create_processor(processor_type, **kwargs)
            _PROCESSOR_CACHE[cache_key] = processor
            logger.debug(f"创建 OCR 处理器: {processor_type}")

        return _PROCESSOR_CACHE[cache_key]

    @classmethod
    def _create_processor(cls, processor_type: str, **kwargs) -> BaseOCRProcessor:
        """创建处理器实例"""
        if processor_type == "rapid_ocr":
            from app.services.ocr.rapid_ocr import RapidOCRProcessor

            return RapidOCRProcessor(**kwargs)

        elif processor_type == "mineru_ocr":
            from app.services.ocr.mineru import MinerUProcessor

            return MinerUProcessor(is_official=False, **kwargs)

        elif processor_type == "mineru_official":
            from app.services.ocr.mineru import MinerUProcessor

            return MinerUProcessor(is_official=True, **kwargs)

        elif processor_type == "paddlex_ocr":
            from app.services.ocr.paddlex import PaddleXProcessor

            return PaddleXProcessor(**kwargs)

        else:
            raise ValueError(f"未知的处理器类型: {processor_type}")

    @classmethod
    def process_file(
        cls, processor_type: str, file_path: str, params: dict | None = None
    ) -> str:
        """使用指定处理器处理文件（便捷方法）

        Args:
            processor_type: 处理器类型
            file_path: 文件路径
            params: 处理参数

        Returns:
            str: 提取的文本

        Raises:
            DocumentProcessorException: 处理失败
        """
        processor = cls.get_processor(processor_type)
        return processor.process_file(file_path, params)

    @classmethod
    async def aprocess_file(
        cls, processor_type: str, file_path: str, params: dict | None = None
    ) -> str:
        """异步使用指定处理器处理文件

        Args:
            processor_type: 处理器类型
            file_path: 文件路径
            params: 处理参数

        Returns:
            str: 提取的文本

        Raises:
            DocumentProcessorException: 处理失败
        """
        processor = cls.get_processor(processor_type)
        return await processor.aprocess_file(file_path, params)

    @classmethod
    def check_health(cls, processor_type: str) -> dict[str, Any]:
        """检查指定处理器的健康状态

        Args:
            processor_type: 处理器类型

        Returns:
            dict: 健康状态信息
        """
        try:
            processor = cls.get_processor(processor_type)
            return processor.check_health()
        except Exception as e:
            return {
                "status": "error",
                "message": f"健康检查失败: {str(e)}",
                "details": {"error": str(e)},
            }

    @classmethod
    def check_all_health(cls) -> dict[str, dict[str, Any]]:
        """检查所有处理器的健康状态

        Returns:
            dict: 各处理器的健康状态
        """
        health_status = {}
        for processor_type in cls.PROCESSOR_TYPES:
            health_status[processor_type] = cls.check_health(processor_type)
        return health_status

    @classmethod
    def get_available_processors(cls) -> list[str]:
        """返回所有可用的处理器类型"""
        return list(cls.PROCESSOR_TYPES.keys())

    @classmethod
    def get_default_processor_type(cls) -> str:
        """获取默认处理器类型"""
        return settings.OCR_DEFAULT_PROVIDER or "rapid_ocr"


def get_ocr_processor(processor_type: str | None = None, **kwargs) -> BaseOCRProcessor:
    """获取 OCR 处理器的便捷函数

    Args:
        processor_type: 处理器类型，如果为 None 则使用默认配置
        **kwargs: 处理器初始化参数

    Returns:
        BaseOCRProcessor: 处理器实例
    """
    if processor_type is None:
        processor_type = OcrProcessorFactory.get_default_processor_type()
    return OcrProcessorFactory.get_processor(processor_type, **kwargs)
