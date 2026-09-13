from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UnderstandingInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    subjects: list[str] = Field(default_factory=list, max_length=5)
    season: str | None = Field(default=None, max_length=20)
    time: str | None = Field(default=None, max_length=20)
    weather: str | None = Field(default=None, max_length=20)
    mood: str = Field(min_length=1, max_length=40)
    scene_summary: str = Field(default="", alias="sceneSummary", max_length=80)
    confidence: float = Field(ge=0, le=1)

    @field_validator("subjects")
    @classmethod
    def validate_subjects(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if len(cleaned) != len(set(cleaned)):
            cleaned = list(dict.fromkeys(cleaned))
        return cleaned


class PoemResponse(BaseModel):
    id: str
    title: str
    author: str
    dynasty: str
    genre: str
    lines: list[str]
    selected_line_indexes: list[int] = Field(alias="selectedLineIndexes")


class MatchInfo(BaseModel):
    score: float
    matched_tags: list[str] = Field(alias="matchedTags")
    reason: str
    algorithm_version: str = Field(alias="algorithmVersion")


class MatchResponse(BaseModel):
    request_id: str | None = Field(alias="requestId")
    understanding: UnderstandingInput
    poem: PoemResponse
    match: MatchInfo

