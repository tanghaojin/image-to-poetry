from __future__ import annotations

import re

from app.poetry.domain import PoemCandidate
from app.poetry.matcher import ALGORITHM_VERSION, best_match
from app.poetry.repository import PoetryRepository
from app.poetry.schemas import MatchInfo, MatchResponse, PoemResponse, UnderstandingInput
from core.errors import ApiError, ERRORS


class PoetryMatchingService:
    def __init__(self, repository: PoetryRepository) -> None:
        self.repository = repository

    async def match(self, understanding: UnderstandingInput, request_id: str | None) -> MatchResponse:
        result = best_match(await self.repository.list_matchable(), understanding)
        if result is None:
            raise ApiError(ERRORS["POETRY_CORPUS_UNAVAILABLE"])
        poem = result.poem
        display_lines, selected_indexes = display_lines_and_selection(poem, result.selected_line_indexes)
        matched_names = list(dict.fromkeys(tag.name for tag in result.matched_tags))
        if matched_names:
            visible = "、".join(matched_names[:3])
            reason = f"画面中的{visible}与《{poem.title}》的意象相合。"
        else:
            reason = f"《{poem.title}》在现有诗词中与画面整体意境最接近。"
        return MatchResponse(
            requestId=request_id,
            understanding=understanding,
            poem=PoemResponse(
                id=poem.slug,
                title=poem.title,
                author=poem.author,
                dynasty=poem.dynasty,
                genre=poem.genre,
                lines=display_lines,
                selectedLineIndexes=selected_indexes,
            ),
            match=MatchInfo(
                score=result.score,
                matchedTags=matched_names,
                reason=reason,
                algorithmVersion=ALGORITHM_VERSION,
            ),
        )

    async def detail(self, slug: str) -> PoemResponse:
        poem = await self.repository.get_verified(slug)
        if poem is None:
            raise ApiError(ERRORS["POEM_NOT_FOUND"])
        display_lines, selected = display_lines_and_selection(
            poem, tuple(line.line_no for line in poem.lines if line.featured)
        )
        return PoemResponse(id=poem.slug, title=poem.title, author=poem.author, dynasty=poem.dynasty,
                            genre=poem.genre, lines=display_lines, selectedLineIndexes=selected)


def display_lines_and_selection(poem: PoemCandidate, source_indexes: tuple[int, ...]) -> tuple[list[str], list[int]]:
    display_lines: list[str] = []
    source_to_display: dict[int, list[int]] = {}
    for line in poem.lines:
        clauses = [part.strip() for part in re.findall(r"[^，。！？；]+[，。！？；]?", line.text) if part.strip()]
        source_to_display[line.line_no] = list(range(len(display_lines), len(display_lines) + len(clauses)))
        display_lines.extend(clauses)

    featured_indexes = [line.line_no for line in poem.lines if line.featured]
    chosen_source = next((index for index in featured_indexes if index in source_indexes), None)
    if chosen_source is None:
        chosen_source = source_indexes[0] if source_indexes else (featured_indexes[0] if featured_indexes else 0)
    selected = source_to_display.get(chosen_source, [])[:2]
    if len(selected) < 2:
        selected.extend(index for index in range(len(display_lines)) if index not in selected)
    return display_lines, sorted(selected[:2])
