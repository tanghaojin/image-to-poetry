from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, func, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.models import Author, Poem, PoemLine, PoemTag, Tag  # noqa: E402
from app.db.models.enums import PoemGenre, TagDimension, VerificationStatus  # noqa: E402
from app.db.session import AsyncSessionFactory, close_database  # noqa: E402

SEED = ROOT / "data" / "seeds" / "tang_poems_366.json"


async def get_or_create_author(session, name: str) -> Author:
    author = await session.scalar(select(Author).where(Author.dynasty == "唐", Author.normalized_name == name))
    if author is None:
        author = Author(slug=f"tang-author-{len(name)}-{sum(map(ord, name))}", name=name,
                        normalized_name=name, dynasty="唐", aliases=[])
        session.add(author)
        await session.flush()
    return author


async def get_or_create_tag(session, dimension: str, name: str) -> Tag:
    enum_dimension = TagDimension(dimension)
    tag = await session.scalar(select(Tag).where(Tag.dimension == enum_dimension, Tag.normalized_name == name))
    if tag is None:
        tag = Tag(dimension=enum_dimension, name=name, normalized_name=name, enabled=True)
        session.add(tag)
        await session.flush()
    return tag


async def import_seed() -> dict[str, int]:
    records = json.loads(SEED.read_text(encoding="utf-8"))
    async with AsyncSessionFactory() as session:
        async with session.begin():
            for record in records:
                author = await get_or_create_author(session, record["author"])
                poem = await session.scalar(select(Poem).where(Poem.slug == record["slug"]))
                if poem is None:
                    poem = Poem(slug=record["slug"], title=record["title"], normalized_title=record["title"],
                                author_id=author.id, dynasty="唐", genre=PoemGenre(record["genre"]),
                                canonical_text=record["canonicalText"], normalized_text=record["normalizedText"],
                                aliases=record["aliases"], popularity=Decimal(str(record["popularity"])),
                                verification_status=VerificationStatus.VERIFIED,
                                source_name=record["sourceName"], source_url=record["sourceUrl"],
                                verified_at=datetime.now(timezone.utc), schema_version=record["schemaVersion"])
                    session.add(poem)
                    await session.flush()
                else:
                    poem.title = record["title"]
                    poem.normalized_title = record["title"]
                    poem.author_id = author.id
                    poem.genre = PoemGenre(record["genre"])
                    poem.canonical_text = record["canonicalText"]
                    poem.normalized_text = record["normalizedText"]
                    poem.aliases = record["aliases"]
                    poem.popularity = Decimal(str(record["popularity"]))
                    poem.verification_status = VerificationStatus.VERIFIED
                    poem.source_name = record["sourceName"]
                    poem.source_url = record["sourceUrl"]
                    poem.verified_at = datetime.now(timezone.utc)
                    poem.schema_version = record["schemaVersion"]
                    await session.execute(delete(PoemLine).where(PoemLine.poem_id == poem.id))
                    await session.execute(delete(PoemTag).where(PoemTag.poem_id == poem.id))
                for line_no, line in enumerate(record["lines"]):
                    session.add(PoemLine(poem_id=poem.id, line_no=line_no, text=line["text"],
                                         normalized_text=line["text"], is_featured=line["featured"]))
                for item in record["tags"]:
                    tag = await get_or_create_tag(session, item["dimension"], item["name"])
                    session.add(PoemTag(poem_id=poem.id, tag_id=tag.id,
                                        weight=Decimal(str(item["weight"])), evidence_lines=item["evidenceLines"],
                                        source=item["source"], reviewed=item["reviewed"]))
        counts: dict[str, int] = {}
        for label, model in [("poems", Poem), ("authors", Author), ("lines", PoemLine),
                             ("tags", Tag), ("poemTags", PoemTag)]:
            counts[label] = int(await session.scalar(select(func.count()).select_from(model)) or 0)
        counts["verifiedPoems"] = int(await session.scalar(
            select(func.count()).select_from(Poem).where(Poem.verification_status == VerificationStatus.VERIFIED)
        ) or 0)
        return counts


async def main() -> None:
    try:
        print(json.dumps(await import_seed(), ensure_ascii=False))
    finally:
        await close_database()


if __name__ == "__main__": asyncio.run(main())
