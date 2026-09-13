from __future__ import annotations

from pydantic import BaseModel, Field

from app.poetry.schemas import MatchInfo, PoemResponse, UnderstandingInput


class ProcessingMeta(BaseModel):
    processing_ms: int = Field(alias="processingMs")


class ImagePoetryMatchResponse(BaseModel):
    request_id: str | None = Field(alias="requestId")
    understanding: UnderstandingInput
    poem: PoemResponse
    match: MatchInfo
    meta: ProcessingMeta
