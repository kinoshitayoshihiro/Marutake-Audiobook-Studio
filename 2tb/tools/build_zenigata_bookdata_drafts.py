#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_CSV = ROOT / "reports" / "zenigata_heiji_works_catalog.csv"
OUTPUT_DIR = ROOT / "bookdata" / "3_nomura"

COMMON_GLOSSARY = {
    "銭形平次": (
        "ぜにがたへいじ",
        "神田明神下で活躍する御用聞き。投げ銭の妙技で知られる。",
    ),
    "八五郎": ("はちごろう", "平次の子分。通称ガラッ八。"),
    "ガラッ八": ("がらっぱち", "八五郎の通称。"),
    "御用聞き": ("ごようきき", "町奉行所の捜査に協力する岡っ引き。"),
    "岡っ引": ("おかっぴき", "町奉行所の手先として探索を行う者。"),
    "神田": ("かんだ", "銭形平次ゆかりの土地としてたびたび登場する江戸の町。"),
    "江戸": ("えど", "作品の主な舞台となる時代都市。"),
}

EMOTION_MAP = {
    "怪異・妖異": ["緊張", "不安", "恐怖", "驚き", "安堵"],
    "復讐・因果": ["怒り", "悲哀", "緊張", "哀切", "納得"],
    "恋愛・嫉妬": ["切なさ", "嫉妬", "緊張", "哀愁", "安堵"],
    "人情・家族": ["哀愁", "感動", "優しさ", "切なさ", "安堵"],
    "盗賊・悪党": ["緊張", "警戒", "怒り", "爽快", "安堵"],
    "謎解き・トリック": ["緊張", "好奇心", "驚き", "納得", "爽快"],
    "大店・家督・金": ["欲望", "不安", "緊張", "驚き", "安堵"],
    "八五郎活躍": ["軽快", "緊張", "親しみ", "驚き", "爽快"],
    "長編・冒険": ["冒険", "緊張", "驚き", "恐怖", "爽快"],
    "事件のどんでん返し": ["緊張", "驚き", "納得", "余韻", "爽快"],
}

SUBGENRE_MAP = {
    "怪異・妖異": "怪異捕物・怪談",
    "復讐・因果": "復讐劇・因果譚",
    "恋愛・嫉妬": "恋愛劇・情念ミステリ",
    "人情・家族": "人情劇・家族譚",
    "盗賊・悪党": "盗賊捕物・悪党物",
    "謎解き・トリック": "本格捕物・謎解き",
    "大店・家督・金": "大店事件・家督騒動",
    "八五郎活躍": "八五郎もの・捕物喜劇",
    "長編・冒険": "長編伝奇・冒険譚",
    "事件のどんでん返し": "捕物ミステリ",
}

LOCATION_HINTS = [
    "江戸",
    "神田",
    "両国",
    "音羽",
    "雑司ヶ谷",
    "大塚",
    "小石川",
    "本所",
    "浅草",
    "深川",
    "八丁堀",
    "小伝馬町",
    "品川",
    "上野",
    "芝",
    "下谷",
]

CHAPTER_NUM_RE = re.compile(r"^[一二三四五六七八九十百]+$")
CHAPTER_BRACKET_RE = re.compile(r"^【[^】]+】$")


def split_pipe(text: str) -> list[str]:
    return [item.strip() for item in str(text or "").split("|") if item.strip()]


def split_slash(text: str) -> list[str]:
    return [item.strip() for item in str(text or "").split("/") if item.strip()]


def read_catalog() -> list[dict[str, str]]:
    with CATALOG_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def read_text_best_effort(path: Path) -> str:
    for encoding in ("utf-8", "cp932", "shift_jis", "utf-8-sig"):
        try:
            return path.read_text(encoding=encoding)
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def normalize_spaces(text: str) -> str:
    return re.sub(r"[\s\u3000]+", " ", str(text or "")).strip()


def find_text_source(row: dict[str, str]) -> Path | None:
    for rel in split_pipe(row.get("source_paths", "")):
        path = ROOT / rel
        if not path.exists() or path.is_dir():
            continue
        if path.suffix.lower() in {".txt", ".tex", ".vrew", ".vjm", ".py"}:
            return path
    return None


def infer_location(*parts: str) -> str:
    text = " ".join(parts)
    found = [name for name in LOCATION_HINTS if name in text]
    if not found:
        return "江戸"
    unique: list[str] = []
    for name in found:
        if name not in unique:
            unique.append(name)
    return "・".join(unique[:5])


def make_highlights(row: dict[str, str]) -> list[str]:
    synopsis = normalize_spaces(row.get("synopsis", "") or row.get("summary", ""))
    parts = [part.strip() for part in re.split(r"[。！？]", synopsis) if part.strip()]
    highlights = parts[:5]
    if highlights:
        return highlights
    lineage = normalize_spaces(row.get("story_lineage", "")) or "捕物"
    title = normalize_spaces(row.get("title", ""))
    return [
        f"{title} ならではの {lineage} の魅力",
        "事件の発端から真相露見までの運び",
        "平次と八五郎の掛け合いと探索",
    ]


def make_character_entries(row: dict[str, str]) -> list[dict[str, str]]:
    names = split_slash(row.get("characters", ""))[:8]
    entries = []
    for index, name in enumerate(names):
        desc = "本文・既存カタログから抽出した人物名。要補正。"
        if index == 0 and "平次" in name:
            desc = "主人公。事件の真相を追う御用聞き。"
        elif "八五郎" in name or "ガラッ八" in name:
            desc = "平次の子分。聞き込みや現場で活躍する。"
        entries.append({"name": name, "desc": desc})
    return entries


def make_glossary(row: dict[str, str], text: str) -> list[dict[str, str]]:
    glossary = []
    joined = "\n".join([text, row.get("synopsis", ""), row.get("summary", "")])
    for term, (reading, desc) in COMMON_GLOSSARY.items():
        if term in joined:
            glossary.append({"term": term, "reading": reading, "desc": desc})
    return glossary[:10]


def split_chapters(text: str) -> list[dict[str, str]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters: list[dict[str, str]] = []
    current_title = "本文"
    current_lines: list[str] = []
    pending_prefix = ""

    def flush() -> None:
        nonlocal current_title, current_lines
        content = "\n".join(current_lines).strip()
        if content:
            chapters.append({"title": current_title, "content": content})
        current_lines = []

    for raw_line in lines:
        line = raw_line.strip()
        if CHAPTER_BRACKET_RE.match(line):
            pending_prefix = line
            continue
        if CHAPTER_NUM_RE.match(line):
            flush()
            current_title = f"{pending_prefix}\n{line}".strip()
            pending_prefix = ""
            continue
        if pending_prefix:
            flush()
            current_title = pending_prefix
            pending_prefix = ""
        current_lines.append(raw_line)
    flush()
    if not chapters:
        return [{"title": "本文", "content": text.strip()}]
    return chapters


def make_keywords(row: dict[str, str]) -> list[str]:
    values = [
        "銭形平次捕物控",
        row.get("title", ""),
        "野村胡堂",
        row.get("story_lineage", ""),
        row.get("publication_years", ""),
        row.get("magazines", ""),
        *split_slash(row.get("tags", ""))[:10],
        *split_slash(row.get("characters", ""))[:8],
    ]
    unique: list[str] = []
    for value in values:
        clean = normalize_spaces(value)
        if clean and clean not in unique:
            unique.append(clean)
    return unique[:30]


def build_payload(row: dict[str, str], text_path: Path, text: str) -> dict[str, Any]:
    title = normalize_spaces(row.get("title", ""))
    lineage = normalize_spaces(row.get("story_lineage", "")) or "事件のどんでん返し"
    synopsis = normalize_spaces(row.get("synopsis", "") or row.get("summary", ""))
    themes = [lineage, *split_slash(row.get("theme_secondary", ""))]
    deduped_themes: list[str] = []
    for theme in themes:
        clean = normalize_spaces(theme)
        if clean and clean not in deduped_themes:
            deduped_themes.append(clean)
    setting = normalize_spaces(row.get("summary", "") or synopsis)
    location = infer_location(title, synopsis, setting, text[:2000])
    return {
        "title": f"銭形平次捕物控 {title}",
        "author": "野村胡堂",
        "genre": "時代小説",
        "japanese_genre": "捕物帳",
        "sub_genre": SUBGENRE_MAP.get(lineage, "捕物ミステリ"),
        "setting": setting or synopsis or "江戸を舞台にした捕物事件。",
        "location": location,
        "time_period": "江戸時代",
        "keywords": make_keywords(row),
        "themes": deduped_themes[:6],
        "emotions": EMOTION_MAP.get(lineage, ["緊張", "驚き", "納得", "哀愁", "爽快"]),
        "synopsis": synopsis or "既存カタログから要約未取得。本文から要補筆。",
        "highlights": make_highlights(row),
        "characters": make_character_entries(row),
        "glossary": make_glossary(row, text),
        "authorProfile": {
            "name": "野村胡堂",
            "desc": "『銭形平次捕物控』で知られる大衆文芸作家。江戸の人情と謎解きを軽妙に描く捕物帳の名手。",
        },
        "chapters": split_chapters(text),
    }


def output_path_for(title: str) -> Path:
    return OUTPUT_DIR / f"銭形平次捕物控_{title}.json"


def should_generate(row: dict[str, str]) -> bool:
    has_local_text = str(row.get("has_local_text", "")).strip().lower() == "yes"
    has_bookdata = str(row.get("has_bookdata", "")).strip().lower() == "yes"
    return has_local_text and not has_bookdata


def main() -> int:
    rows = read_catalog()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    skipped = 0
    for row in rows:
        if not should_generate(row):
            continue
        title = normalize_spaces(row.get("title", ""))
        out_path = output_path_for(title)
        if out_path.exists():
            skipped += 1
            continue
        text_path = find_text_source(row)
        if text_path is None:
            skipped += 1
            continue
        text = read_text_best_effort(text_path)
        payload = build_payload(row, text_path, text)
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        generated += 1
        print(
            f"generated: {out_path.relative_to(ROOT)} <- {text_path.relative_to(ROOT)}"
        )
    print(f"Generated: {generated}")
    print(f"Skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
