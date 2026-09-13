from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Poem, PoemTag
from app.db.models.enums import VerificationStatus
from app.poetry.domain import CandidateLine, CandidateTag, PoemCandidate


class PoetryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_matchable(self) -> list[PoemCandidate]:
        statement = (
            select(Poem)
            .where(Poem.verification_status == VerificationStatus.VERIFIED)
            .options(
                selectinload(Poem.author),
                selectinload(Poem.lines),
                selectinload(Poem.poem_tags).selectinload(PoemTag.tag),
            )
            .order_by(Poem.id.asc())
        )
        poems = (await self.session.scalars(statement)).all()
        candidates: list[PoemCandidate] = []
        for poem in poems:
            reviewed_tags = tuple(
                CandidateTag(
                    dimension=poem_tag.tag.dimension.value,
                    name=poem_tag.tag.name,
                    weight=float(poem_tag.weight),
                    evidence_lines=tuple(poem_tag.evidence_lines),
                )
                for poem_tag in poem.poem_tags
                if poem_tag.reviewed and poem_tag.tag.enabled
            )
            candidates.append(
                PoemCandidate(
                    id=poem.id,
                    slug=poem.slug,
                    title=poem.title,
                    author=poem.author.name,
                    dynasty=poem.dynasty,
                    genre=poem.genre.value,
                    popularity=float(poem.popularity),
                    lines=tuple(CandidateLine(line.line_no, line.text, line.is_featured) for line in poem.lines),
                    tags=reviewed_tags,
                )
            )
        return candidates

    async def get_verified(self, slug: str) -> PoemCandidate | None:
        candidates = await self.list_matchable()
        return next((candidate for candidate in candidates if candidate.slug == slug), None)

