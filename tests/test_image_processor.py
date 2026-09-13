from io import BytesIO

import pytest
from PIL import Image
from starlette.datastructures import Headers, UploadFile

from app.vision.image_processor import prepare_image
from core.errors import ApiError


def upload(content: bytes, content_type: str) -> UploadFile:
    return UploadFile(BytesIO(content), filename="fixture.png", headers=Headers({"content-type": content_type}))


def png_fixture() -> bytes:
    output = BytesIO()
    Image.new("RGBA", (2200, 1100), (0, 0, 0, 0)).save(output, "PNG")
    return output.getvalue()


@pytest.mark.asyncio
async def test_image_is_resized_flattened_and_converted_to_jpeg() -> None:
    result = await prepare_image(upload(png_fixture(), "image/png"))
    with Image.open(BytesIO(result)) as image:
        assert image.format == "JPEG"
        assert image.mode == "RGB"
        assert image.size == (1600, 800)
        assert image.getpixel((0, 0))[0] > 230


@pytest.mark.asyncio
async def test_invalid_image_content_is_rejected() -> None:
    with pytest.raises(ApiError) as exc_info:
        await prepare_image(upload(b"not an image", "image/png"))
    assert exc_info.value.spec.code == "IMAGE_DECODE_FAILED"


@pytest.mark.asyncio
async def test_unsupported_content_type_is_rejected() -> None:
    with pytest.raises(ApiError) as exc_info:
        await prepare_image(upload(b"content", "image/gif"))
    assert exc_info.value.spec.code == "IMAGE_TYPE_UNSUPPORTED"

