from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateLine:
    line_no: int
    text: str
    featured: bool


@dataclass(frozen=True)
class CandidateTag:
    dimension: str
    name: str
    weight: float
    evidence_lines: tuple[int, ...]


@dataclass(frozen=True)
class PoemCandidate:
    id: int
    slug: str
    title: str
    author: str
    dynasty: str
    genre: str
    popularity: float
    lines: tuple[CandidateLine, ...]
    tags: tuple[CandidateTag, ...]

