from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from opencc import OpenCC


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".upstream" / "chinese-poetry"
SOURCE = UPSTREAM / "全唐诗" / "唐诗三百首.json"
OUTPUT = ROOT / "data" / "seeds" / "tang_poems_366.json"
MANIFEST = ROOT / "data" / "seeds" / "source-manifest.json"
EXPECTED_COMMIT = "b8594f81a89752241442f2ce267d6f66f96704ee"
SOURCE_REPOSITORY = "https://github.com/chinese-poetry/chinese-poetry"

# Pinning both the index and UUID makes upstream drift fail loudly.
SELECTIONS: list[tuple[int, str, str | None]] = [
    (2, "c244a5b4-0ed0-48fe-8694-95309acac184", None), (169, "de6b7e3d-03cd-4daa-bdc2-7fb820fda441", "出塞"),
    (6, "bcdf6f13-4cb9-418f-9279-c690522e0a27", "出塞"), (10, "e0eb3016-9288-4dc0-9257-3de36e5ad73c", None),
    (12, "d7c6d072-6e84-482e-856a-5a4c21226a3c", None), (13, "75db753d-e7da-48a1-a6c0-6ed9147e58db", None),
    (57, "204e287b-8194-4c2d-808b-11cc260412ae", None), (74, "8de30193-fba7-4aef-9ff9-c3726a22104d", None),
    (78, "d12edd29-d467-4b19-b3f5-533fa5c8d56a", None), (96, "a746d1f0-a72c-44d2-8b1c-c5c990749257", None),
    (107, "56ca5b29-4bb9-4f12-9200-6bc7c72e4e47", None), (111, "6975adab-25d0-40c6-af3a-3a05847e7717", None),
    (118, "9309205e-1d08-4a7b-99ef-4a05a9ee4370", None), (121, "cb168b3b-d104-4df7-9868-1e1225ddb941", None),
    (122, "0bed9b02-991e-4e28-b631-86640147a712", None), (133, "e4354c00-c83e-43da-9341-7007889dd625", None),
    (134, "00f12a19-bb96-4980-a4f5-11a1b9d604dd", None), (136, "40cd6eec-c6ce-4659-a225-61063cd210e9", None),
    (137, "a5b1f5c9-1ba7-4533-b497-55b1d4af1bbb", None), (143, "2e8999a9-9df8-4483-ab1e-0231c3e46320", "鹿柴"),
    (144, "36e09cb4-4fb7-48be-b6c6-c9bd906d9331", "竹里馆"), (147, "8baa7c35-9afb-40bf-b5e4-41d9895e2710", None),
    (148, "6bbd1c2c-8c43-4ffb-b7b3-506d74266cee", None), (149, "1575c835-1241-4d7b-99dc-6d700549ac65", None),
    (171, "4ac3f099-73da-43e8-a4e5-1dbbd9427491", None), (172, "090b7792-2942-4f3c-a34d-caccd066c76f", "芙蓉楼送辛渐"),
    (180, "0174cbbc-31fa-4daf-b1cf-7f91c6a646a9", None), (183, "4f6575cc-12cc-4986-8bfc-5cedac7bb68f", None),
    (203, "469dec8b-ba5e-4faf-b52f-2ad203e38d81", None), (204, "1f92134b-bca9-46eb-b2fe-87b30413041a", None),
    (205, "51b1aeeb-9a66-412d-b15c-4afaa6c6b1d7", None), (208, "e9e6425c-6c14-4f69-8694-87a8b96a43de", None),
    (211, "c1280e87-ac81-4f9b-9de5-377d6af38ae8", None), (218, "a4d718ee-c020-42b4-97df-499cd0076f7b", None),
    (222, "f96506ea-e8ac-47e0-a0a6-ccd306e56645", None), (233, "2c152693-c25f-45ce-8ef2-cbedce1a62bc", None),
    (241, "12fdaad8-b197-4526-b56d-c7c713267248", None), (269, "4fa92777-9bd6-45ca-9272-bac30459cf5e", "乌衣巷"),
    (280, "3cda5a92-ffa2-4af0-9217-97ce36113705", None), (292, "0ae0e3bd-a32e-481f-9719-b283da2da964", None),
    (295, "294bc7b2-b4f8-4a53-be17-a40ded4afd1a", None), (300, "07238ad9-c348-43d4-b1d7-25d89369286d", None),
    (307, "4be77185-992e-4614-9746-de2e73c8a3c3", None), (311, "ca2c489a-e433-4c0f-8248-77d354f0665e", None),
    (321, "d43a4767-2240-44b7-8d5b-c2acdc689839", None), (322, "bf8918b8-a05a-4ccf-bb2e-3f9b81f6bbfc", None),
    (327, "9525f99d-39cb-4d04-8650-263493d223e0", None), (329, "83e70b6e-ff59-4a3b-8e81-249ab0cda0c3", "月下独酌"),
    (361, "63950163-6a10-4e74-af8a-09886e4ef2a8", None), (124, "e5e5f969-ddac-4491-9cfe-d77742e1416d", None),
]

# One primary mood/theme/atmosphere per poem, manually curated for image matching.
CURATION: dict[int, tuple[str, str, str]] = {
    2: ("苍凉", "怀古", "辽阔"), 169: ("壮阔", "边塞", "雄浑"), 6: ("思乡", "边塞", "苍茫"),
    10: ("怅惘", "追忆", "朦胧"), 12: ("感慨", "惜时", "暮色"), 13: ("思念", "思乡", "清寂"),
    57: ("闲适", "田园", "质朴"), 74: ("忧思", "怀古", "夜色"), 78: ("孤寂", "宫怨", "清冷"),
    96: ("宁静", "送别", "幽远"), 107: ("思念", "怀友", "高远"), 111: ("壮阔", "山水", "浩渺"),
    118: ("喜悦", "田园", "温暖"), 121: ("惬意", "惜春", "清新"), 122: ("羁愁", "思乡", "静谧"),
    133: ("宁静", "寻幽", "幽深"), 134: ("闲适", "山水", "清幽"), 136: ("淡泊", "归隐", "清远"),
    137: ("壮阔", "山水", "雄奇"), 143: ("宁静", "山水", "空灵"), 144: ("孤高", "归隐", "幽静"),
    147: ("思念", "爱情", "含蓄"), 148: ("思乡", "怀亲", "深沉"), 149: ("惜别", "送别", "清润"),
    171: ("哀怨", "闺怨", "明丽"), 172: ("惜别", "送别", "清寒"), 180: ("惜别", "送别", "蓬勃"),
    183: ("淡然", "寻访", "幽静"), 203: ("孤寂", "隐居", "清幽"), 204: ("孤高", "山水", "清寒"),
    205: ("超然", "山水", "奇幻"), 208: ("悲怆", "忧国", "沉郁"), 211: ("思念", "怀亲", "清冷"),
    218: ("悲秋", "羁旅", "苍凉"), 222: ("孤独", "羁旅", "旷远"), 233: ("思念", "望月", "静谧"),
    241: ("豪迈", "登临", "雄伟"), 269: ("感慨", "怀古", "寂寥"), 280: ("羁愁", "羁旅", "清冷"),
    292: ("闲适", "山水", "幽雅"), 295: ("豪迈", "送别", "壮丽"), 300: ("思乡", "羁旅", "真挚"),
    307: ("思乡", "边塞", "苍茫"), 311: ("思乡", "怀乡", "静谧"), 321: ("惜别", "送别", "明朗"),
    322: ("思乡", "远行", "开阔"), 327: ("喜悦", "行旅", "轻快"), 329: ("孤独", "饮酒", "浪漫"),
    361: ("豪迈", "登临", "壮阔"), 124: ("豪放", "饮酒", "奔放"),
}

# The repository is the acquisition source. These records use historical variants;
# the product stores one current, widely used standard display text as previously agreed.
STANDARD_TEXT_OVERRIDES: dict[int, list[str]] = {
    204: ["千山鸟飞绝，万径人踪灭。", "孤舟蓑笠翁，独钓寒江雪。"],
    280: ["月落乌啼霜满天，江枫渔火对愁眠。", "姑苏城外寒山寺，夜半钟声到客船。"],
    311: ["床前明月光，疑是地上霜。", "举头望明月，低头思故乡。"],
    321: ["故人西辞黄鹤楼，烟花三月下扬州。", "孤帆远影碧空尽，唯见长江天际流。"],
    327: ["朝辞白帝彩云间，千里江陵一日还。", "两岸猿声啼不尽，轻舟已过万重山。"],
}

VISUAL_TERMS = {
    "月": "明月", "山": "山峦", "江": "江水", "河": "河流", "湖": "湖水", "水": "水面", "雨": "雨",
    "雪": "雪", "云": "云", "风": "风", "花": "花", "草": "草木", "树": "树木", "松": "松树",
    "竹": "竹林", "鸟": "飞鸟", "雁": "雁", "猿": "猿", "舟": "舟船", "船": "舟船", "日": "太阳",
    "霞": "晚霞", "星": "星空", "霜": "霜", "露": "露水", "泉": "泉水", "寺": "古寺", "城": "城郭",
    "楼": "楼阁", "关": "关塞", "灯": "灯火", "田": "田野", "柳": "柳树", "红豆": "红豆",
    "天": "天空", "夕阳": "夕阳", "茱萸": "茱萸", "马": "马", "火": "灯火",
}

MOOD_RULES = [
    (("愁", "恨", "悲", "泪", "怨"), "愁绪"),
    (("独", "孤", "空", "寂"), "孤寂"),
    (("思", "忆", "梦", "故乡", "故园"), "思念"),
    (("送", "别", "离"), "惜别"),
    (("笑", "喜", "乐"), "喜悦"),
    (("醉", "酒", "杯"), "豪放"),
]
THEME_RULES = [
    (("送", "别", "离"), "送别"),
    (("塞", "关", "戍", "胡", "羌"), "边塞"),
    (("田", "园", "耕", "桑", "村"), "田园"),
    (("山", "江", "湖", "溪", "泉"), "山水"),
    (("乡", "故园", "故国", "家"), "思乡"),
    (("古", "旧", "故宫", "遗迹"), "怀古"),
    (("宫", "君王", "妃"), "宫怨"),
]
ATMOSPHERE_RULES = [
    (("雪", "霜", "寒", "冰"), "清寒"),
    (("夜", "月", "星", "灯"), "静谧"),
    (("云", "天", "海", "大江"), "辽阔"),
    (("花", "春", "莺", "燕"), "明丽"),
    (("空", "寂", "幽", "深"), "清幽"),
]


def add_tag(tags: list[dict[str, Any]], dimension: str, name: str, weight: float, evidence: list[int],
            source: str = "manual", reviewed: bool = True) -> None:
    if not any(item["dimension"] == dimension and item["name"] == name for item in tags):
        tags.append({"dimension": dimension, "name": name, "weight": weight, "evidenceLines": evidence,
                     "source": source, "reviewed": reviewed})


def find_evidence(lines: list[str], term: str) -> list[int]:
    return [i for i, line in enumerate(lines) if term in line][:2]


def genre(tags: list[str]) -> str:
    joined = "|".join(tags)
    if "绝句" in joined: return "绝句"
    if "律诗" in joined: return "律诗"
    if "古诗" in joined: return "古体诗"
    if "乐府" in joined: return "乐府"
    return "其他"


def normalize(value: str) -> str:
    return re.sub(r"[\s，。！？、；：‘’“”（）《》·]", "", value)


def first_rule(text: str, rules: list[tuple[tuple[str, ...], str]], fallback: str) -> str:
    for markers, value in rules:
        if any(marker in text for marker in markers):
            return value
    return fallback


def add_rule_tags(tags: list[dict[str, Any]], lines: list[str], upstream_tags: list[str]) -> None:
    text = "".join(lines)
    add_tag(tags, "mood", first_rule(text, MOOD_RULES, "宁静"), 0.62, [], "rule", False)
    add_tag(tags, "theme", first_rule(text, THEME_RULES, "咏怀"), 0.62, [], "rule", False)
    add_tag(tags, "atmosphere", first_rule(text, ATMOSPHERE_RULES, "古朴"), 0.6, [], "rule", False)
    for term, tag_name in VISUAL_TERMS.items():
        evidence = find_evidence(lines, term)
        if evidence:
            add_tag(tags, "subject", tag_name, 0.82 if len(term) > 1 else 0.72, evidence, "rule", False)
    for marker, name in [("春", "春"), ("夏", "夏"), ("秋", "秋"), ("冬", "冬")]:
        evidence = find_evidence(lines, marker)
        if evidence or any(marker in tag for tag in upstream_tags):
            add_tag(tags, "season", name, 0.78, evidence, "rule", False)
    for marker, name in [("夜", "夜晚"), ("夕", "黄昏"), ("暮", "黄昏"), ("晓", "清晨"), ("朝", "清晨")]:
        evidence = find_evidence(lines, marker)
        if evidence:
            add_tag(tags, "time", name, 0.78, evidence, "rule", False)
    for marker, name in [("雨", "雨"), ("雪", "雪"), ("霜", "霜"), ("风", "风"), ("云", "多云")]:
        evidence = find_evidence(lines, marker)
        if evidence:
            add_tag(tags, "weather", name, 0.78, evidence, "rule", False)
    if not any(tag["dimension"] == "subject" for tag in tags):
        add_tag(tags, "subject", "人物", 0.5, [0], "rule", False)


def build() -> list[dict[str, Any]]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Missing upstream source: {SOURCE}")
    commit = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True,
                                     encoding="utf-8").strip()
    if commit != EXPECTED_COMMIT:
        raise RuntimeError(f"Upstream commit changed: expected {EXPECTED_COMMIT}, got {commit}")
    converter = OpenCC("t2s")
    source_rows = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_url = f"{SOURCE_REPOSITORY}/blob/{EXPECTED_COMMIT}/全唐诗/唐诗三百首.json"
    if len(source_rows) != 366:
        raise RuntimeError(f"Source record count changed: expected 366, got {len(source_rows)}")
    curated = {source_index: (source_id, display_title) for source_index, source_id, display_title in SELECTIONS}
    if len(curated) != 50:
        raise RuntimeError("Curated selection must contain exactly 50 unique source records")
    output: list[dict[str, Any]] = []
    for source_index, raw in enumerate(source_rows, start=1):
        curated_item = curated.get(source_index)
        if curated_item and raw["id"] != curated_item[0]:
            raise RuntimeError(f"Source identity mismatch at curated record {source_index}")
        source_title = converter.convert(raw["title"])
        title = (curated_item[1] if curated_item else None) or source_title
        author = converter.convert(raw["author"])
        lines = STANDARD_TEXT_OVERRIDES.get(
            source_index, [re.sub(r"[\[\]]", "", converter.convert(line)) for line in raw["paragraphs"]]
        )
        upstream_tags = [converter.convert(tag) for tag in raw.get("tags", [])]
        tags: list[dict[str, Any]] = []
        if source_index in CURATION:
            mood, theme, atmosphere = CURATION[source_index]
            add_tag(tags, "mood", mood, 1.0, [])
            add_tag(tags, "theme", theme, 1.0, [])
            add_tag(tags, "atmosphere", atmosphere, 0.95, [])
            for term, tag_name in VISUAL_TERMS.items():
                evidence = find_evidence(lines, term)
                if evidence:
                    add_tag(tags, "subject", tag_name, 0.95 if len(term) > 1 else 0.85, evidence, "rule")
            for marker, name in [("春", "春"), ("夏", "夏"), ("秋", "秋"), ("冬", "冬")]:
                evidence = find_evidence(lines, marker)
                if evidence or any(marker in tag for tag in upstream_tags):
                    add_tag(tags, "season", name, 0.9, evidence, "rule")
            for marker, name in [("夜", "夜晚"), ("夕", "黄昏"), ("暮", "黄昏"), ("晓", "清晨"), ("朝", "清晨")]:
                evidence = find_evidence(lines, marker)
                if evidence:
                    add_tag(tags, "time", name, 0.9, evidence, "rule")
            for marker, name in [("雨", "雨"), ("雪", "雪"), ("霜", "霜"), ("风", "风"), ("云", "多云")]:
                evidence = find_evidence(lines, marker)
                if evidence:
                    add_tag(tags, "weather", name, 0.9, evidence, "rule")
            if not any(tag["dimension"] == "subject" for tag in tags):
                add_tag(tags, "subject", "人物", 0.7, [0])
        else:
            add_rule_tags(tags, lines, upstream_tags)
        featured = max(range(len(lines)), key=lambda i: sum(term in lines[i] for term in VISUAL_TERMS), default=0)
        popularity = min(0.98, (0.72 if curated_item else 0.52)
                         + (0.12 if any("小学" in t or "初中" in t for t in upstream_tags) else 0)
                         + (0.08 if source_index <= 15 else 0))
        source_id = raw["id"]
        output.append({"sourceId": source_id, "sourceIndex": source_index, "slug": f"tang-{source_id[:8]}",
                       "title": title, "sourceTitle": source_title, "author": author, "dynasty": "唐",
                       "genre": genre(upstream_tags),
                       "lines": [{"text": line, "featured": i == featured} for i, line in enumerate(lines)],
                       "canonicalText": "\n".join(lines), "normalizedText": normalize("".join(lines)),
                       "aliases": [source_title] if source_title != title else [], "tags": tags,
                       "popularity": round(popularity, 3), "verificationStatus": "verified",
                       "sourceName": "chinese-poetry/chinese-poetry", "sourceUrl": source_url, "schemaVersion": 1})
    return output


def main() -> None:
    poems = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(poems, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {"sourceRepository": SOURCE_REPOSITORY, "sourceCommit": EXPECTED_COMMIT,
                "sourcePath": "全唐诗/唐诗三百首.json", "sourceRecordCount": 366,
                "importedRecordCount": len(poems), "curatedRecordCount": 50,
                "ruleTaggedRecordCount": len(poems) - 50, "license": "MIT", "textConversion": "OpenCC t2s",
                "selectionPolicy": "全量导入366条；保留50首人工策展标签，其余316首使用待复核规则标签",
                "canonicalTextPolicy": "数据库只保存一个标准展示版本，不保存异文和verificationNote"}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(poems)} poems: {OUTPUT}")


if __name__ == "__main__": main()
