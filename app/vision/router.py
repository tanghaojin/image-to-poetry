from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.services.rate_limiter import fingerprint_rate_limiter
from app.db.session import get_db_session
from app.poetry.repository import PoetryRepository
from app.poetry.service import PoetryMatchingService
from app.vision.image_processor import prepare_image
from app.vision.providers import VisionProviderError, vision_provider_router
from app.vision.schemas import ImagePoetryMatchResponse, ProcessingMeta
from core.config import settings
from core.errors import ApiError, ERRORS


router = APIRouter(prefix="/api/v1/poetry", tags=["image-poetry"])


@router.post("/match", response_model=ImagePoetryMatchResponse, response_model_by_alias=True)
async def match_image_to_poetry(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    image: Annotated[UploadFile | None, File()] = None,
    fingerprint: Annotated[str | None, Header(alias="X-Device-Fingerprint")] = None,
) -> ImagePoetryMatchResponse:
    started = perf_counter()
    image_bytes = await prepare_image(image)
    await fingerprint_rate_limiter.consume(fingerprint)
    try:
        async with asyncio.timeout(settings.vision_total_timeout):
            vision = await vision_provider_router.analyze(image_bytes)
            matched = await PoetryMatchingService(PoetryRepository(session)).match(
                vision.understanding, getattr(request.state, "request_id", None)
            )
    except TimeoutError as exc:
        raise ApiError(ERRORS["VISION_TIMEOUT"]) from exc
    except VisionProviderError as exc:
        raise ApiError(ERRORS["VISION_PROVIDER_UNAVAILABLE"]) from exc
    return ImagePoetryMatchResponse(
        requestId=matched.request_id,
        understanding=matched.understanding,
        poem=matched.poem,
        match=matched.match,
        meta=ProcessingMeta(processingMs=round((perf_counter() - started) * 1000)),
    )
