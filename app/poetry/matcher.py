from __future__ import annotations

import re
from dataclasses import dataclass

from app.poetry.domain import CandidateTag, PoemCandidate
from app.poetry.schemas import UnderstandingInput


ALGORITHM_VERSION = "tag-score-v1"
DIMENSION_WEIGHTS = {"subject": 0.35, "season": 0.12, "time": 0.08, "weather": 0.15, "mood": 0.22}
UNKNOWN_VALUES = {"", "无法确定", "不确定", "未知", "无", "none", "unknown"}

CONCEPT_GROUPS: dict[str, dict[str, set[str]]] = {
    "subject": {
        "舟船": {"舟船", "孤舟", "小舟", "扁舟", "渔舟", "船", "客船", "帆船"},
        "水域": {"江水", "江河", "河流", "溪流", "湖水", "湖面", "水面", "江", "河", "湖", "溪", "海"},
        "山峦": {"山峦", "山", "群山", "高山", "雪山", "山峰", "远山"},
        "明月": {"明月", "月亮", "月光", "月", "弯月", "圆月"},
        "太阳": {"太阳", "日光", "旭日", "落日", "夕阳"},
        "天空": {"天空", "天际", "长空"},
        "云": {"云", "云彩", "白云", "乌云"},
        "草木": {"草木", "草", "青草", "原野", "古原"},
        "花": {"花", "花朵", "春花", "桃花", "梅花"},
        "树木": {"树木", "树", "林木", "树林", "森林", "霜林"},
        "雪景": {"雪", "雪景", "冰雪", "积雪"},
        "霜景": {"霜", "白霜", "霜冻"},
        "飞鸟": {"飞鸟", "鸟", "鸟群", "乌鸦"},
        "楼阁": {"楼阁", "楼", "高楼", "亭台"},
        "城郭": {"城郭", "古城", "城市", "城墙"},
    },
    "season": {"春": {"春", "春天", "春季"}, "夏": {"夏", "夏天", "夏季"},
               "秋": {"秋", "秋天", "秋季", "深秋"}, "冬": {"冬", "冬天", "冬季", "寒冬"}},
    "time": {"清晨": {"清晨", "早晨", "晨", "黎明", "拂晓"}, "黄昏": {"黄昏", "傍晚", "日暮", "暮色", "夕照"},
             "夜晚": {"夜晚", "夜", "深夜", "月夜", "夜间"}, "白昼": {"白昼", "白天", "日间"}},
    "weather": {"雨": {"雨", "下雨", "雨天", "细雨", "春雨", "秋雨"}, "雪": {"雪", "下雪", "雪景", "大雪", "冬雪"},
                "霜": {"霜", "霜冻"}, "风": {"风", "大风", "微风", "清风"}, "多云": {"多云", "阴云", "云层"},
                "晴": {"晴", "晴天", "晴朗"}},
    "mood": {
        "宁静": {"宁静", "平静", "安静", "静谧", "淡然", "闲适", "惬意"},
        "孤寂": {"孤寂", "孤独", "孤高", "寂寞", "寂寥", "清寂", "羁愁"},
        "思乡": {"思乡", "怀乡", "乡愁"}, "思念": {"思念", "怀念", "想念"},
        "惜别": {"惜别", "离别", "送别", "不舍"}, "壮阔": {"壮阔", "豪迈", "豪放", "雄壮"},
        "喜悦": {"喜悦", "开心", "欢快", "愉悦"}, "感伤": {"悲秋", "悲怆", "忧思", "感慨", "怅惘", "哀怨"},
    },
}


def normalized(value: str) -> str:
    return re.sub(r"[\s，。！？、；：‘’“”（）《》·_-]", "", value).lower()


def concept(dimension: str, value: str) -> str:
    value_key = normalized(value)
    if dimension == "mood":
        if any(marker in value_key for marker in ("孤", "独", "寂")):
            return "孤寂"
        if any(marker in value_key for marker in ("乡", "故园", "故乡")):
            return "思乡"
    for canonical, aliases in CONCEPT_GROUPS.get(dimension, {}).items():
        normalized_aliases = sorted({normalized(item) for item in aliases}, key=len, reverse=True)
        if value_key in normalized_aliases or (
            dimension == "subject" and any(len(alias) >= 2 and alias in value_key for alias in normalized_aliases)
        ):
            return canonical
    return value_key


def meaningful(value: str | None) -> bool:
    return value is not None and normalized(value) not in {normalized(item) for item in UNKNOWN_VALUES}


@dataclass(frozen=True)
class ScoredMatch:
    poem: PoemCandidate
    score: float
    matched_tags: tuple[CandidateTag, ...]
    selected_line_indexes: tuple[int, ...]


def score_candidate(poem: PoemCandidate, understanding: UnderstandingInput) -> ScoredMatch:
    inputs: dict[str, list[str]] = {
        "subject": understanding.subjects,
        "season": [understanding.season] if meaningful(understanding.season) else [],
        "time": [understanding.time] if meaningful(understanding.time) else [],
        "weather": [understanding.weather] if meaningful(understanding.weather) else [],
        "mood": [understanding.mood] if meaningful(understanding.mood) else [],
    }
    semantic_total = 0.0
    active_weight = 0.0
    matched: dict[tuple[str, str], CandidateTag] = {}
    for dimension, input_values in inputs.items():
        if not input_values:
            continue
        dimension_weight = DIMENSION_WEIGHTS[dimension]
        active_weight += dimension_weight
        poem_tags = [tag for tag in poem.tags if tag.dimension == dimension]
        best_per_input: list[float] = []
        for input_value in input_values:
            input_concept = concept(dimension, input_value)
            matching = [tag for tag in poem_tags if concept(dimension, tag.name) == input_concept]
            best = max(matching, key=lambda tag: tag.weight, default=None)
            best_per_input.append(best.weight if best else 0.0)
            if best:
                matched[(best.dimension, best.name)] = best
        if best_per_input:
            coverage_score = 0.7 * max(best_per_input) + 0.3 * (sum(best_per_input) / len(best_per_input))
            semantic_total += dimension_weight * coverage_score
    semantic_score = semantic_total / active_weight if active_weight else 0.0
    confidence_factor = 0.85 + 0.15 * understanding.confidence
    total = (0.85 * semantic_score + 0.15 * poem.popularity) * confidence_factor
    selected = sorted({line for tag in matched.values() for line in tag.evidence_lines})[:2]
    if len(selected) < 2:
        selected.extend(line.line_no for line in poem.lines if line.featured and line.line_no not in selected)
    if len(selected) < 2:
        selected.extend(line.line_no for line in poem.lines if line.line_no not in selected)
    return ScoredMatch(poem=poem, score=round(min(1.0, total), 4),
                       matched_tags=tuple(matched.values()), selected_line_indexes=tuple(sorted(selected[:2])))


def best_match(candidates: list[PoemCandidate], understanding: UnderstandingInput) -> ScoredMatch | None:
    if not candidates:
        return None
    scored = [score_candidate(candidate, understanding) for candidate in candidates]
    return min(scored, key=lambda item: (-item.score, -item.poem.popularity, item.poem.id))
