from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    message: str
    status_code: int
    retryable: bool = False


ERRORS = {
    "DEVICE_FINGERPRINT_MISSING": ErrorSpec(
        "DEVICE_FINGERPRINT_MISSING", "请求信息不完整。", 400
    ),
    "IMAGE_MISSING": ErrorSpec("IMAGE_MISSING", "请选择一张图片。", 400),
    "IMAGE_TOO_LARGE": ErrorSpec("IMAGE_TOO_LARGE", "图片超过 10 MB。", 413),
    "IMAGE_TYPE_UNSUPPORTED": ErrorSpec(
        "IMAGE_TYPE_UNSUPPORTED", "仅支持 JPG、PNG、WebP 图片。", 415
    ),
    "IMAGE_DECODE_FAILED": ErrorSpec("IMAGE_DECODE_FAILED", "图片内容损坏。", 422),
    "VISION_PROVIDER_UNAVAILABLE": ErrorSpec(
        "VISION_PROVIDER_UNAVAILABLE", "图片分析服务暂时不可用。", 502, True
    ),
    "VISION_TIMEOUT": ErrorSpec("VISION_TIMEOUT", "图片分析等待超时。", 504, True),
    "SERVER_BUSY": ErrorSpec("SERVER_BUSY", "服务器繁忙，请稍后再试。", 429),
    "DEPENDENCY_UNAVAILABLE": ErrorSpec(
        "DEPENDENCY_UNAVAILABLE", "服务器繁忙，请稍后再试。", 503, True
    ),
    "POETRY_CORPUS_UNAVAILABLE": ErrorSpec(
        "POETRY_CORPUS_UNAVAILABLE", "诗词库尚未就绪。", 503, True
    ),
    "POEM_NOT_FOUND": ErrorSpec("POEM_NOT_FOUND", "没有找到这首诗。", 404),
    "INTERNAL_ERROR": ErrorSpec("INTERNAL_ERROR", "服务处理异常。", 500, True),
}


class ApiError(Exception):
    def __init__(self, spec: ErrorSpec, details: Any = None) -> None:
        super().__init__(spec.message)
        self.spec = spec
        self.details = details
