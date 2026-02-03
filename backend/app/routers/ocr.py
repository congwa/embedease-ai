"""OCR 服务 API

提供 OCR 健康检查、文件处理等接口。
"""

from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(prefix="/api/v1/admin/ocr", tags=["ocr"])
logger = get_logger("routers.ocr")


# ========== Response Models ==========


class OcrHealthStatus(BaseModel):
    """单个 OCR 处理器健康状态"""

    status: str = Field(..., description="状态: healthy, unhealthy, unavailable, error, timeout")
    message: str = Field(..., description="状态描述")
    details: dict[str, Any] = Field(default_factory=dict, description="详细信息")


class OcrHealthResponse(BaseModel):
    """OCR 健康检查响应"""

    enabled: bool = Field(..., description="OCR 功能是否启用")
    default_provider: str = Field(..., description="默认 OCR 处理器")
    processors: dict[str, OcrHealthStatus] = Field(
        default_factory=dict, description="各处理器健康状态"
    )


class OcrConfigResponse(BaseModel):
    """OCR 配置响应"""

    enabled: bool
    default_provider: str
    available_providers: list[str]
    model_dir: str | None = None
    mineru_api_url: str | None = None
    mineru_official_url: str | None = None
    paddlex_uri: str | None = None
    timeout: int


class OcrProcessRequest(BaseModel):
    """OCR 处理请求"""

    processor_type: str | None = Field(None, description="处理器类型，留空使用默认")
    params: dict[str, Any] = Field(default_factory=dict, description="处理参数")


class OcrProcessResponse(BaseModel):
    """OCR 处理响应"""

    success: bool
    text: str = ""
    error: str | None = None
    processor_type: str = ""
    file_name: str = ""
    processing_time_ms: int = 0


# ========== API Endpoints ==========


@router.get("/health", response_model=OcrHealthResponse)
async def check_ocr_health():
    """检查所有 OCR 处理器的健康状态"""
    from app.services.ocr.factory import OcrProcessorFactory

    processors_health = {}

    for processor_type in OcrProcessorFactory.get_available_processors():
        try:
            health = OcrProcessorFactory.check_health(processor_type)
            processors_health[processor_type] = OcrHealthStatus(
                status=health.get("status", "error"),
                message=health.get("message", "未知状态"),
                details=health.get("details", {}),
            )
        except Exception as e:
            processors_health[processor_type] = OcrHealthStatus(
                status="error",
                message=f"检查失败: {str(e)}",
                details={"error": str(e)},
            )

    return OcrHealthResponse(
        enabled=settings.OCR_ENABLED,
        default_provider=settings.OCR_DEFAULT_PROVIDER,
        processors=processors_health,
    )


@router.get("/health/{processor_type}", response_model=OcrHealthStatus)
async def check_processor_health(processor_type: str):
    """检查指定 OCR 处理器的健康状态"""
    from app.services.ocr.factory import OcrProcessorFactory

    if processor_type not in OcrProcessorFactory.get_available_processors():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的处理器类型: {processor_type}",
        )

    try:
        health = OcrProcessorFactory.check_health(processor_type)
        return OcrHealthStatus(
            status=health.get("status", "error"),
            message=health.get("message", "未知状态"),
            details=health.get("details", {}),
        )
    except Exception as e:
        return OcrHealthStatus(
            status="error",
            message=f"检查失败: {str(e)}",
            details={"error": str(e)},
        )


@router.get("/config", response_model=OcrConfigResponse)
async def get_ocr_config():
    """获取 OCR 配置信息"""
    from app.services.ocr.factory import OcrProcessorFactory

    return OcrConfigResponse(
        enabled=settings.OCR_ENABLED,
        default_provider=settings.OCR_DEFAULT_PROVIDER,
        available_providers=OcrProcessorFactory.get_available_processors(),
        model_dir=settings.OCR_MODEL_DIR,
        mineru_api_url=settings.MINERU_API_URL,
        mineru_official_url=settings.MINERU_OFFICIAL_URL,
        paddlex_uri=settings.PADDLEX_URI,
        timeout=settings.OCR_TIMEOUT,
    )


@router.post("/process", response_model=OcrProcessResponse)
async def process_file(
    file: UploadFile = File(...),
    processor_type: str | None = Query(None, description="处理器类型"),
):
    """处理上传的文件并返回 OCR 结果"""
    import os
    import tempfile
    import time

    from app.services.ocr.base import DocumentProcessorException
    from app.services.ocr.factory import OcrProcessorFactory

    if not settings.OCR_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OCR 功能未启用",
        )

    # 使用默认处理器
    if not processor_type:
        processor_type = settings.OCR_DEFAULT_PROVIDER

    if processor_type not in OcrProcessorFactory.get_available_processors():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的处理器类型: {processor_type}",
        )

    # 保存上传文件到临时目录
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if not file_ext:
        file_ext = ".bin"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name

        start_time = time.time()

        try:
            text = await OcrProcessorFactory.aprocess_file(processor_type, tmp_path)
            processing_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "OCR 处理完成",
                processor=processor_type,
                file_name=file.filename,
                text_length=len(text),
                time_ms=processing_time_ms,
            )

            return OcrProcessResponse(
                success=True,
                text=text,
                processor_type=processor_type,
                file_name=file.filename or "",
                processing_time_ms=processing_time_ms,
            )

        except DocumentProcessorException as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                "OCR 处理失败",
                processor=processor_type,
                file_name=file.filename,
                error=str(e),
            )
            return OcrProcessResponse(
                success=False,
                error=str(e),
                processor_type=processor_type,
                file_name=file.filename or "",
                processing_time_ms=processing_time_ms,
            )

    finally:
        # 清理临时文件
        if "tmp_path" in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@router.get("/providers")
async def list_providers():
    """列出所有可用的 OCR 处理器"""
    from app.services.ocr.factory import OcrProcessorFactory

    providers = []
    for processor_type in OcrProcessorFactory.get_available_processors():
        try:
            processor = OcrProcessorFactory.get_processor(processor_type)
            providers.append(
                {
                    "type": processor_type,
                    "name": processor.get_service_name(),
                    "supported_extensions": processor.get_supported_extensions(),
                }
            )
        except Exception as e:
            providers.append(
                {
                    "type": processor_type,
                    "name": processor_type,
                    "supported_extensions": [],
                    "error": str(e),
                }
            )

    return {
        "default": settings.OCR_DEFAULT_PROVIDER,
        "providers": providers,
    }
