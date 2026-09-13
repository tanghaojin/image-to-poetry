from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.poetry.repository import PoetryRepository
from app.poetry.schemas import MatchResponse, PoemResponse, UnderstandingInput
from app.poetry.service import PoetryMatchingService


router = APIRouter(prefix="/api/v1/poems", tags=["poetry"])


def get_matching_service(session: Annotated[AsyncSession, Depends(get_db_session)]) -> PoetryMatchingService:
    return PoetryMatchingService(PoetryRepository(session))


@router.post("/match", response_model=MatchResponse, response_model_by_alias=True)
async def match_poem(
    payload: UnderstandingInput,
    request: Request,
    service: Annotated[PoetryMatchingService, Depends(get_matching_service)],
) -> MatchResponse:
    return await service.match(payload, getattr(request.state, "request_id", None))


@router.get("/{poem_slug}", response_model=PoemResponse, response_model_by_alias=True)
async def poem_detail(
    poem_slug: str,
    service: Annotated[PoetryMatchingService, Depends(get_matching_service)],
) -> PoemResponse:
    return await service.detail(poem_slug)

