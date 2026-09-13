"""Run the real image-to-poetry flow without Docker for local UI testing.

Vision requests still use the configured providers. Poetry candidates are loaded
from the reviewed 50-poem seed and the fingerprint quota uses an in-process
fakeredis instance, so restarting this process resets the local quota.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import fakeredis.aioredis
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.common.services.redis_service import redis_service
from app.db.session import get_db_session
from app.poetry.domain import CandidateLine, CandidateTag, PoemCandidate
from app.poetry.repository import PoetryRepository


SEED_PATH = ROOT / "data" / "seeds" / "tang_poems_50.json"


def load_candidates() -> list[PoemCandidate]:
    records: list[dict[str, Any]] = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    return [
        PoemCandidate(
            id=index,
            slug=record["slug"],
            title=record["title"],
            author=record["author"],
            dynasty=record["dynasty"],
            genre=record["genre"],
            popularity=float(record["popularity"]),
            lines=tuple(
                CandidateLine(line_no, line["text"], bool(line["featured"]))
                for line_no, line in enumerate(record["lines"])
            ),
            tags=tuple(
                CandidateTag(
                    dimension=tag["dimension"],
                    name=tag["name"],
                    weight=float(tag["weight"]),
                    evidence_lines=tuple(tag["evidenceLines"]),
                )
                for tag in record["tags"]
                if tag["reviewed"]
            ),
        )
        for index, record in enumerate(records, start=1)
        if record["verificationStatus"] == "verified"
    ]


CANDIDATES = load_candidates()


async def in_memory_redis_connect() -> bool:
    redis_service.client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return True


async def in_memory_redis_close() -> None:
    if redis_service.client is not None:
        await redis_service.client.aclose()
        redis_service.client = None


async def list_local_candidates(_: PoetryRepository) -> list[PoemCandidate]:
    return CANDIDATES


async def get_local_candidate(_: PoetryRepository, slug: str) -> PoemCandidate | None:
    return next((candidate for candidate in CANDIDATES if candidate.slug == slug), None)


async def local_session():
    yield object()


def create_demo_app():
    redis_service.connect = in_memory_redis_connect  # type: ignore[method-assign]
    redis_service.close = in_memory_redis_close  # type: ignore[method-assign]
    PoetryRepository.list_matchable = list_local_candidates  # type: ignore[method-assign]
    PoetryRepository.get_verified = get_local_candidate  # type: ignore[method-assign]

    from main import app

    app.dependency_overrides[get_db_session] = local_session
    return app


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    uvicorn.run(create_demo_app(), host="127.0.0.1", port=8000, log_level="info")
