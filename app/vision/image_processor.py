from __future__ import annotations

from io import BytesIO

from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from core.config import settings
from core.errors import ApiError, ERRORS


SUPPORTED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}


async def prepare_image(upload: UploadFile | None) -> bytes:
    if upload is None:
        raise ApiError(ERRORS["IMAGE_MISSING"])
    if upload.content_type not in SUPPORTED_MIME_TYPES:
        raise ApiError(ERRORS["IMAGE_TYPE_UNSUPPORTED"])
    content = await upload.read(settings.image_max_bytes + 1)
    await upload.close()
    if len(content) > settings.image_max_bytes:
        raise ApiError(ERRORS["IMAGE_TOO_LARGE"])
    if not content:
        raise ApiError(ERRORS["IMAGE_DECODE_FAILED"])

    try:
        with Image.open(BytesIO(content)) as probe:
            if probe.format not in SUPPORTED_FORMATS:
                raise ApiError(ERRORS["IMAGE_TYPE_UNSUPPORTED"])
            probe.verify()
        with Image.open(BytesIO(content)) as source:
            image = ImageOps.exif_transpose(source)
            image.thumbnail((settings.image_max_edge, settings.image_max_edge), Image.Resampling.LANCZOS)
            if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (244, 240, 231, 255))
                background.alpha_composite(rgba)
                image = background.convert("RGB")
            else:
                image = image.convert("RGB")
            output = BytesIO()
            image.save(output, format="JPEG", quality=settings.image_jpeg_quality, optimize=True)
            return output.getvalue()
    except ApiError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ApiError(ERRORS["IMAGE_DECODE_FAILED"]) from exc
