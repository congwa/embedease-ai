"""RapidOCR 处理器 - 本地 ONNX 模型推理

使用 RapidOCR (PP-OCRv4) 进行文字识别，支持 PDF 和图像文件。
"""

import asyncio
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.ocr.base import BaseOCRProcessor, OCRException

logger = get_logger("ocr.rapid_ocr")


class RapidOCRProcessor(BaseOCRProcessor):
    """RapidOCR 处理器 - 使用本地 ONNX 模型进行文字识别

    依赖：
    - rapidocr_onnxruntime
    - PyMuPDF (fitz) 用于 PDF 渲染
    - Pillow 用于图像处理

    模型文件需放置在 MODEL_DIR/SWHL/RapidOCR/PP-OCRv4/ 目录下
    """

    def __init__(self, det_box_thresh: float = 0.3):
        self.ocr = None
        self.det_box_thresh = det_box_thresh
        self._model_loaded = False

    def get_service_name(self) -> str:
        return "rapid_ocr"

    def get_supported_extensions(self) -> list[str]:
        return [".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"]

    def _get_model_dir(self) -> str | None:
        """获取模型目录"""
        return settings.OCR_MODEL_DIR

    def _get_model_paths(self) -> tuple[str, str] | None:
        """获取模型文件路径"""
        model_dir = self._get_model_dir()
        if not model_dir:
            return None

        base_path = os.path.join(model_dir, "SWHL/RapidOCR/PP-OCRv4")
        det_model_path = os.path.join(base_path, "ch_PP-OCRv4_det_infer.onnx")
        rec_model_path = os.path.join(base_path, "ch_PP-OCRv4_rec_infer.onnx")
        return det_model_path, rec_model_path

    def check_health(self) -> dict[str, Any]:
        """检查 RapidOCR 模型是否可用"""
        try:
            model_paths = self._get_model_paths()
            if not model_paths:
                return {
                    "status": "unavailable",
                    "message": "未配置 OCR_MODEL_DIR",
                    "details": {"model_dir": None},
                }

            det_model_path, rec_model_path = model_paths
            model_dir = os.path.dirname(os.path.dirname(det_model_path))

            if not os.path.exists(model_dir):
                return {
                    "status": "unavailable",
                    "message": f"模型目录不存在: {model_dir}",
                    "details": {"model_dir": model_dir},
                }

            if not os.path.exists(det_model_path) or not os.path.exists(rec_model_path):
                return {
                    "status": "unavailable",
                    "message": "模型文件缺失",
                    "details": {
                        "det_model": det_model_path,
                        "rec_model": rec_model_path,
                        "det_exists": os.path.exists(det_model_path),
                        "rec_exists": os.path.exists(rec_model_path),
                    },
                }

            # 尝试加载模型
            try:
                from rapidocr_onnxruntime import RapidOCR

                test_ocr = RapidOCR(
                    det_box_thresh=self.det_box_thresh,
                    det_model_path=det_model_path,
                    rec_model_path=rec_model_path,
                )
                del test_ocr
                return {
                    "status": "healthy",
                    "message": "RapidOCR 模型可用",
                    "details": {"model_path": model_paths},
                }
            except ImportError:
                return {
                    "status": "unavailable",
                    "message": "rapidocr_onnxruntime 未安装",
                    "details": {"error": "missing_dependency"},
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"模型加载失败: {str(e)}",
                    "details": {"error": str(e)},
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"健康检查失败: {str(e)}",
                "details": {"error": str(e)},
            }

    def _load_model(self):
        """延迟加载 OCR 模型"""
        if self._model_loaded:
            return

        logger.info("加载 RapidOCR 模型...")

        health = self.check_health()
        if health["status"] != "healthy":
            raise OCRException(health["message"], self.get_service_name(), health["status"])

        try:
            from rapidocr_onnxruntime import RapidOCR

            det_model_path, rec_model_path = self._get_model_paths()
            self.ocr = RapidOCR(
                det_box_thresh=self.det_box_thresh,
                det_model_path=det_model_path,
                rec_model_path=rec_model_path,
            )
            self._model_loaded = True
            logger.info(f"RapidOCR 模型加载成功 (det_box_thresh={self.det_box_thresh})")
        except Exception as e:
            raise OCRException(f"RapidOCR 模型加载失败: {str(e)}", self.get_service_name(), "load_failed")

    def _process_image(self, image_input, params: dict | None = None) -> str:
        """处理单张图像并提取文本

        Args:
            image_input: 图像数据，支持文件路径、PIL.Image 或 numpy.ndarray
            params: 处理参数

        Returns:
            str: 提取的文本内容
        """
        self._load_model()

        try:
            cleanup_needed = False
            image_path = image_input

            # 如果不是字符串路径，需要创建临时文件
            if not isinstance(image_input, str):
                image_path = self._create_temp_image_file(image_input)
                cleanup_needed = True

            try:
                start_time = time.time()
                result, _ = self.ocr(image_path)
                processing_time = time.time() - start_time

                if result:
                    text = "\n".join([line[1] for line in result])
                    logger.debug(
                        f"RapidOCR 识别完成: {len(text)} 字符 ({processing_time:.2f}s)"
                    )
                    return text
                else:
                    logger.warning("RapidOCR 未识别到文本")
                    return ""

            finally:
                if cleanup_needed and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        logger.warning(f"临时文件清理失败: {e}")

        except OCRException:
            raise
        except Exception as e:
            error_msg = f"图像 OCR 处理失败: {str(e)}"
            logger.error(error_msg)
            raise OCRException(error_msg, self.get_service_name(), "processing_failed")

    def _create_temp_image_file(self, image) -> str:
        """将图像数据保存为临时文件"""
        try:
            from PIL import Image
            import numpy as np

            with tempfile.NamedTemporaryFile(mode="wb", suffix=".png", delete=False) as tmp_file:
                temp_path = tmp_file.name

                if isinstance(image, Image.Image):
                    image.save(temp_path)
                elif isinstance(image, np.ndarray):
                    Image.fromarray(image).save(temp_path)
                else:
                    raise ValueError("不支持的图像类型，必须是 PIL.Image 或 numpy.ndarray")

                return temp_path

        except Exception as e:
            raise OCRException(f"临时图像文件创建失败: {str(e)}", self.get_service_name(), "temp_file_error")

    def _process_pdf(self, pdf_path: str, params: dict | None = None) -> str:
        """处理 PDF 文件并提取文本

        Args:
            pdf_path: PDF 文件路径
            params: 处理参数
                - zoom_x: 横向缩放 (默认 2)
                - zoom_y: 纵向缩放 (默认 2)

        Returns:
            str: 提取的文本
        """
        if not os.path.exists(pdf_path):
            raise OCRException(f"PDF 文件不存在: {pdf_path}", self.get_service_name(), "file_not_found")

        try:
            import fitz
            from PIL import Image
        except ImportError as e:
            raise OCRException(f"缺少依赖: {str(e)}", self.get_service_name(), "missing_dependency")

        params = params or {}
        zoom_x = params.get("zoom_x", 2)
        zoom_y = params.get("zoom_y", 2)

        try:
            all_text = []
            pdf_doc = fitz.open(pdf_path)
            total_pages = pdf_doc.page_count

            logger.info(f"开始处理 PDF: {os.path.basename(pdf_path)} ({total_pages} 页)")

            for page_num in range(total_pages):
                page = pdf_doc[page_num]
                mat = fitz.Matrix(zoom_x, zoom_y)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                text = self._process_image(img_pil)
                all_text.append(text)

                if (page_num + 1) % 10 == 0:
                    logger.info(f"已处理 {page_num + 1}/{total_pages} 页")

            pdf_doc.close()

            result_text = "\n\n".join(all_text)
            logger.info(f"PDF OCR 完成: {os.path.basename(pdf_path)} - {len(result_text)} 字符")
            return result_text

        except OCRException:
            raise
        except Exception as e:
            error_msg = f"PDF OCR 处理失败: {str(e)}"
            logger.error(error_msg)
            raise OCRException(error_msg, self.get_service_name(), "pdf_processing_failed")

    def process_file(self, file_path: str, params: dict[str, Any] | None = None) -> str:
        """处理文件 (PDF 或图像)

        Args:
            file_path: 文件路径
            params: 处理参数

        Returns:
            str: 提取的文本
        """
        file_ext = Path(file_path).suffix.lower()

        if not self.supports_file_type(file_ext):
            raise OCRException(f"不支持的文件类型: {file_ext}", self.get_service_name(), "unsupported_file_type")

        if file_ext == ".pdf":
            return self._process_pdf(file_path, params)
        else:
            return self._process_image(file_path, params)

    async def aprocess_file(self, file_path: str, params: dict[str, Any] | None = None) -> str:
        """异步处理文件"""
        return await asyncio.to_thread(self.process_file, file_path, params)
