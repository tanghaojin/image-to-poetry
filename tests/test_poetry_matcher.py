import json
from pathlib import Path

from app.poetry.domain import CandidateLine, CandidateTag, PoemCandidate
from app.poetry.matcher import ALGORITHM_VERSION, best_match
from app.poetry.schemas import UnderstandingInput


def candidates() -> list[PoemCandidate]:
    records = json.loads((Path(__file__).parents[1] / "data" / "seeds" / "tang_poems_50.json").read_text("utf-8"))
    return [
        PoemCandidate(
            id=index,
            slug=poem["slug"], title=poem["title"], author=poem["author"], dynasty=poem["dynasty"],
            genre=poem["genre"], popularity=poem["popularity"],
            lines=tuple(CandidateLine(i, line["text"], line["featured"]) for i, line in enumerate(poem["lines"])),
            tags=tuple(CandidateTag(tag["dimension"], tag["name"], tag["weight"], tuple(tag["evidenceLines"]))
                       for tag in poem["tags"]),
        )
        for index, poem in enumerate(records, start=1)
    ]


def test_snowy_lonely_boat_matches_jiangxue() -> None:
    result = best_match(candidates(), UnderstandingInput(
        subjects=["孤舟", "江河", "雪景"], season="冬", time="白昼", weather="雪",
        mood="孤寂", sceneSummary="寒江之上，一叶孤舟独行", confidence=0.94,
    ))
    assert result is not None
    assert (result.poem.title, result.poem.author) == ("江雪", "柳宗元")
    assert {"舟船", "江水", "冬", "雪", "孤高"} <= {tag.name for tag in result.matched_tags}
    assert result.selected_line_indexes == (0, 1)


def test_autumn_moon_night_matches_guanshanyue() -> None:
    result = best_match(candidates(), UnderstandingInput(
        subjects=["月亮"], season="秋天", time="月夜", weather="无法确定",
        mood="乡愁", sceneSummary="秋夜月色", confidence=0.9,
    ))
    assert result is not None
    assert result.poem.title == "关山月"
    assert result.score > 0.8


def test_result_is_stable_when_candidate_order_changes() -> None:
    data = candidates()
    understanding = UnderstandingInput(subjects=["山", "树林"], season="秋", time="黄昏",
                                        weather="晴朗", mood="安静", sceneSummary="秋山", confidence=0.88)
    first = best_match(data, understanding)
    second = best_match(list(reversed(data)), understanding)
    assert first is not None and second is not None
    assert first.poem.id == second.poem.id
    assert ALGORITHM_VERSION == "tag-score-v1"


def test_compound_vision_subjects_are_normalized() -> None:
    result = best_match(candidates(), UnderstandingInput(
        subjects=["划船者与小舟", "湖面", "霜冻树林", "晨雾"], season="冬季", time="清晨",
        weather="薄雾", mood="清寒", sceneSummary="清晨薄雾中的湖面与小舟", confidence=0.95,
    ))
    assert result is not None
    assert (result.poem.title, result.poem.author) == ("江雪", "柳宗元")
    assert {"舟船", "江水"} <= {tag.name for tag in result.matched_tags}


def test_freeform_lonely_mood_is_normalized() -> None:
    result = best_match(candidates(), UnderstandingInput(
        subjects=["小船", "晨雾湖面", "霜雪树木"], season="冬季", time="清晨",
        weather="雾", mood="寒江独钓", sceneSummary="冬日湖中一人划船", confidence=0.95,
    ))
    assert result is not None
    assert result.poem.title == "江雪"
    assert "孤高" in {tag.name for tag in result.matched_tags}
