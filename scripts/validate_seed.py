from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "seeds" / "tang_poems_366.json"
CURATED_SEED = ROOT / "data" / "seeds" / "tang_poems_50.json"
DIMENSIONS = {"subject", "season", "time", "weather", "mood", "theme", "atmosphere"}
CURATED_SOURCE_INDEXES = {
    poem["sourceIndex"] for poem in json.loads(CURATED_SEED.read_text(encoding="utf-8"))
}

def validate() -> dict[str, int]:
    poems = json.loads(SEED.read_text(encoding="utf-8"))
    assert len(poems) == 366
    assert len({poem["sourceId"] for poem in poems}) == 366
    assert len({poem["slug"] for poem in poems}) == 366
    assert len(CURATED_SOURCE_INDEXES) == 50
    tag_count = line_count = 0
    for poem in poems:
        assert poem["dynasty"] == "唐" and poem["title"] and poem["author"] and poem["canonicalText"]
        assert "[" not in poem["canonicalText"] and "]" not in poem["canonicalText"]
        assert poem["verificationStatus"] == "verified"
        assert poem["lines"] and sum(bool(line["featured"]) for line in poem["lines"]) == 1
        line_count += len(poem["lines"])
        assert {"subject", "mood", "theme", "atmosphere"} <= {tag["dimension"] for tag in poem["tags"]}
        if poem["sourceIndex"] in CURATED_SOURCE_INDEXES:
            assert sum(tag["source"] == "manual" and tag["reviewed"] is True for tag in poem["tags"]) >= 3
        for tag in poem["tags"]:
            assert tag["dimension"] in DIMENSIONS and 0 < tag["weight"] <= 1
            assert tag["source"] in {"manual", "rule"}
            if poem["sourceIndex"] not in CURATED_SOURCE_INDEXES:
                assert tag["source"] == "rule" and tag["reviewed"] is False
            assert all(0 <= index < len(poem["lines"]) for index in tag["evidenceLines"])
        tag_count += len(poem["tags"])
    return {"poems": len(poems), "lines": line_count, "tags": tag_count}

if __name__ == "__main__": print(json.dumps(validate(), ensure_ascii=False))
