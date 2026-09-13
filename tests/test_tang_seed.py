import json
from pathlib import Path

from scripts.validate_seed import validate

ROOT = Path(__file__).resolve().parents[1]

def test_tang_seed_is_complete_and_valid() -> None:
    counts = validate()
    assert counts["poems"] == 366
    assert counts["lines"] >= 700
    assert counts["tags"] >= 1400


def test_original_curated_poems_are_preserved() -> None:
    curated = json.loads((ROOT / "data" / "seeds" / "tang_poems_50.json").read_text(encoding="utf-8"))
    complete = json.loads((ROOT / "data" / "seeds" / "tang_poems_366.json").read_text(encoding="utf-8"))
    complete_by_source_id = {poem["sourceId"]: poem for poem in complete}
    protected_fields = ("title", "sourceTitle", "author", "canonicalText", "tags")

    assert len(curated) == 50
    for poem in curated:
        imported = complete_by_source_id[poem["sourceId"]]
        assert all(imported[field] == poem[field] for field in protected_fields)
