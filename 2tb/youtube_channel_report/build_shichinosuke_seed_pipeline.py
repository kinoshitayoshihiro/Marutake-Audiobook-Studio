#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"
OLD_REPORT_DIR = Path(__file__).resolve().parent / "old_channel_report"
ALL_VIDEOS_PATH = OLD_REPORT_DIR / "youtube_video_report_last_90_days_all_videos.csv"
CATALOG_PATH = REPORTS_DIR / "shichinosuke_works_catalog.json"
OUT_CSV_PATH = REPORTS_DIR / "shichinosuke_seed_shortworks.csv"
OUT_MD_PATH = REPORTS_DIR / "shichinosuke_seed_shortworks.md"

TITLE_NOISE = (
    "七之助捕物帳",
    "納言恭平著",
    "ナレーター七味春五郎",
    "朗読",
    "朗読時代劇",
    "朗読一人でドラマ",
    "毎週火曜夜八時は",
    "発行元丸竹書房",
    "七味春五郎",
)
EXCLUDE_MARKERS = ("総集編", "主題歌", "睡眠", "作業用", "ハイライト", "紹介")
VARIANT_MAP = {
    "生きている小町娘": "生きていた小町娘",
    "夢の首つり": "夢の首吊り",
    "蛇の目の女": "蛇の眼の女",
    "人食い花": "人喰い花",
    "仇討ち幽霊": "仇討幽霊",
    "鳥追いお巻": "鳥追お巻",
    "お高祖頭巾の女": "お高祖頭巾",
    "水野深川": "水の深川",
    "射的競べの怪": "射的競べの怪",
}

FIELDNAMES = [
    "rank",
    "work_key",
    "seed_title",
    "title",
    "short_title",
    "published_at",
    "channel_title",
    "duration_seconds",
    "views",
    "estimated_minutes_watched",
    "average_view_duration_seconds",
    "score",
    "major_category",
    "has_text",
    "has_audio",
    "privacy",
]


def parse_int(value: Any) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return 0


def normalize_title(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"第[一二三四五六七八九十百0-9]+巻", " ", text)
    text = re.sub(r"第[一二三四五六七八九十百0-9]+話", " ", text)
    text = re.sub(r"[『「【](.*?)[』」】]", r" \1 ", text)
    for source, target in VARIANT_MAP.items():
        text = text.replace(source, target)
    lowered = text.lower()
    for marker in TITLE_NOISE:
        lowered = lowered.replace(marker.lower(), " ")
    lowered = re.sub(r"[｜|／/・「」『』【】（）()、。!！,:：\-_　\s]+", "", lowered)
    return lowered


def candidate_names(work: dict[str, Any]) -> list[str]:
    seen: list[str] = []
    for value in (
        work.get("title", ""),
        work.get("short_title", ""),
        work.get("canonical_title", ""),
    ):
        cleaned = normalize_title(value)
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    for source, target in VARIANT_MAP.items():
        canonical = str(work.get("canonical_title", "")).strip()
        short = str(work.get("short_title", "")).strip()
        if canonical in {source, target} or short in {source, target}:
            cleaned = normalize_title(source)
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
    return seen


def preferred_seed_title(work: dict[str, Any]) -> str:
    short_title = str(work.get("short_title", "")).strip()
    if short_title and not re.fullmatch(r"第?[0-9一二三四五六七八九十百]+巻", short_title):
        return short_title
    title = str(work.get("title", "")).strip()
    match = re.search(r"第[一二三四五六七八九十百0-9]+巻[　 ]+(.+)$", title)
    if match:
        return match.group(1).strip()
    canonical = str(work.get("canonical_title", "")).strip()
    return canonical or short_title or title


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def load_video_rows() -> list[dict[str, str]]:
    with ALL_VIDEOS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_seed_rows() -> list[dict[str, Any]]:
    payload = load_catalog()
    works = payload.get("works", [])
    name_map: dict[str, dict[str, Any]] = {}
    for work in works:
        for name in candidate_names(work):
            name_map.setdefault(name, work)

    results: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for row in load_video_rows():
        title = str(row.get("title", "")).strip()
        if "七之助" not in title:
            continue
        if any(marker in title for marker in EXCLUDE_MARKERS):
            continue
        duration_seconds = parse_int(row.get("duration_seconds"))
        if duration_seconds <= 180 or duration_seconds > 5400:
            continue
        normalized = normalize_title(title)
        if not normalized:
            continue
        matched_work = None
        for key, work in name_map.items():
            if key and (key in normalized or normalized in key):
                matched_work = work
                break
        if not matched_work:
            continue
        work_key = str(matched_work.get("key", "")).strip()
        if not work_key or work_key in seen_keys:
            continue
        views = parse_int(row.get("views"))
        estimated_minutes_watched = parse_int(row.get("estimatedMinutesWatched"))
        average_view_duration_seconds = parse_int(row.get("averageViewDuration"))
        score = (
            views * 0.45
            + estimated_minutes_watched * 0.08
            + average_view_duration_seconds * 1.2
        )
        results.append(
            {
                "work_key": work_key,
                "seed_title": preferred_seed_title(matched_work),
                "title": str(matched_work.get("title", "")).strip(),
                "short_title": preferred_seed_title(matched_work),
                "published_at": str(row.get("publishedAt", "")).strip(),
                "channel_title": title,
                "duration_seconds": duration_seconds,
                "views": views,
                "estimated_minutes_watched": estimated_minutes_watched,
                "average_view_duration_seconds": average_view_duration_seconds,
                "score": round(score, 3),
                "major_category": str(matched_work.get("major_category", "")).strip(),
                "has_text": "yes" if matched_work.get("text_paths") else "no",
                "has_audio": "yes" if matched_work.get("audio_paths") else "no",
                "privacy": (
                    "public"
                    if str(row.get("is_public", "")).strip().lower() == "true"
                    else "private"
                    if str(row.get("is_private", "")).strip().lower() == "true"
                    else "other"
                ),
            }
        )
        seen_keys.add(work_key)

    results.sort(
        key=lambda item: (
            -float(item["score"]),
            -int(item["views"]),
            str(item["short_title"]),
        )
    )
    for index, item in enumerate(results, start=1):
        item["rank"] = index
    return results


def write_outputs(rows: list[dict[str, Any]]) -> None:
    with OUT_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# 七之助 Seed Shortworks",
        "",
        "- source: old channel report",
        "- scope: shortworks only (`180 < duration_seconds <= 5400`) excluding compilations, songs, sleep/work, highlights, and intro videos",
        f"- seeds: {len(rows)}",
        "",
        "| rank | seed | score | views | avg_view | watch_minutes | category | text | audio |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows[:20]:
        lines.append(
            f"| {row['rank']} | {row['seed_title']} | {row['score']} | {row['views']} | {row['average_view_duration_seconds']} | {row['estimated_minutes_watched']} | {row['major_category']} | {row['has_text']} | {row['has_audio']} |"
        )
    OUT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_seed_rows()
    write_outputs(rows)
    print(f"Wrote: {OUT_CSV_PATH}")
    print(f"Wrote: {OUT_MD_PATH}")
    print(f"Seeds: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
