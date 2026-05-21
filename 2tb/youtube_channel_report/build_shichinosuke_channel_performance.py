#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"
OLD_REPORT_DIR = Path(__file__).resolve().parent / "old_channel_report"

CATALOG_PATH = REPORTS_DIR / "shichinosuke_works_catalog.json"
ALL_VIDEOS_PATH = OLD_REPORT_DIR / "youtube_video_report_last_90_days_all_videos.csv"
MASTER_PATH = OLD_REPORT_DIR / "video_master_enriched.csv"
DAILY_ANALYTICS_PATH = OLD_REPORT_DIR / "video_daily_analytics.csv"
PLANNING_PATH = OLD_REPORT_DIR / "content_planning_normal_video.csv"

OUT_CSV_PATH = REPORTS_DIR / "shichinosuke_channel_performance.csv"
OUT_MD_PATH = REPORTS_DIR / "shichinosuke_channel_performance.md"

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
    "serial_number",
    "seed_title",
    "title",
    "matched_video_count",
    "latest_video_id",
    "latest_channel_title",
    "latest_published_at",
    "latest_privacy",
    "latest_duration_seconds",
    "views",
    "estimated_minutes_watched",
    "average_view_duration_seconds",
    "average_view_duration_ratio",
    "average_view_duration_percentage",
    "retention_source",
    "impressions",
    "impression_ctr",
    "views_per_impression",
    "watch_time_minutes_per_impression",
    "description_length",
    "has_description_synopsis",
    "has_description_characters",
    "has_description_glossary",
    "major_category",
    "has_text",
    "has_audio",
]


def parse_int(value: Any) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return 0


def parse_float(value: Any) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return 0.0


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


def preferred_title(work: dict[str, Any]) -> str:
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


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def merged_source_rows() -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}
    for path in (ALL_VIDEOS_PATH, MASTER_PATH):
        for row in load_csv_rows(path):
            video_id = str(row.get("videoId") or row.get("video_id") or "").strip()
            key = video_id or str(row.get("title", "")).strip()
            if not key:
                continue
            existing = merged.get(key, {})
            combined = dict(existing)
            combined.update({k: v for k, v in row.items() if str(v or "").strip() != ""})
            merged[key] = combined
    return list(merged.values())


def classify_privacy(row: dict[str, Any]) -> str:
    if str(row.get("is_public", "")).strip().lower() == "true":
        return "public"
    if str(row.get("is_private", "")).strip().lower() == "true":
        return "private"
    if str(row.get("is_unlisted", "")).strip().lower() == "true":
        return "unlisted"
    status = str(row.get("status.privacyStatus", "")).strip().lower()
    return status or "other"


def latest_daily_metrics() -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for path in (PLANNING_PATH, DAILY_ANALYTICS_PATH):
        for row in load_csv_rows(path):
            video_id = str(row.get("video_id") or row.get("videoId") or "").strip()
            if not video_id:
                continue
            date = str(row.get("date", "")).strip()
            existing = latest.get(video_id)
            if existing and str(existing.get("date", "")) >= date:
                continue
            latest[video_id] = row
    return latest


def build_rows() -> list[dict[str, Any]]:
    payload = load_catalog()
    works = payload.get("works", [])
    name_map: dict[str, dict[str, Any]] = {}
    for work in works:
        for name in candidate_names(work):
            name_map.setdefault(name, work)

    latest_daily = latest_daily_metrics()
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    source_rows = merged_source_rows()
    for row in source_rows:
        title = str(row.get("title", "")).strip()
        if "七之助" not in title:
            continue
        if any(marker in title for marker in EXCLUDE_MARKERS):
            continue
        duration_seconds = parse_int(row.get("duration_seconds"))
        if duration_seconds <= 0:
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

        video_id = str(row.get("videoId") or row.get("video_id") or "").strip()
        daily = latest_daily.get(video_id, {})
        avg_view_duration = parse_int(row.get("averageViewDuration")) or parse_int(
            daily.get("average_view_duration_seconds")
        )
        avg_view_percentage = parse_float(
            daily.get("average_view_duration_percentage")
        )
        retention_ratio = 0.0
        retention_source = ""
        if avg_view_percentage > 0:
            retention_ratio = avg_view_percentage / 100.0
            retention_source = "daily_analytics"
        elif duration_seconds > 0 and avg_view_duration > 0:
            retention_ratio = avg_view_duration / duration_seconds
            retention_source = "derived_from_duration"

        grouped[str(matched_work.get("key", "")).strip()].append(
            {
                "work": matched_work,
                "video_id": video_id,
                "channel_title": title,
                "published_at": str(row.get("publishedAt", "")).strip(),
                "privacy": classify_privacy(row),
                "duration_seconds": duration_seconds,
                "views": parse_int(row.get("views")),
                "estimated_minutes_watched": parse_int(
                    row.get("estimatedMinutesWatched")
                ),
                "average_view_duration_seconds": avg_view_duration,
                "average_view_duration_percentage": avg_view_percentage,
                "average_view_duration_ratio": retention_ratio,
                "retention_source": retention_source,
                "impressions": parse_int(row.get("impressions"))
                or parse_int(daily.get("impressions")),
                "impression_ctr": parse_float(row.get("impressionCtr"))
                or parse_float(daily.get("impression_ctr")),
                "views_per_impression": parse_float(daily.get("views_per_impression")),
                "watch_time_minutes_per_impression": parse_float(
                    daily.get("watch_time_minutes_per_impression")
                ),
                "description_length": parse_int(row.get("description_length")),
                "has_description_synopsis": str(
                    row.get("has_description_synopsis", "")
                ).strip().lower()
                == "true",
                "has_description_characters": str(
                    row.get("has_description_characters", "")
                ).strip().lower()
                == "true",
                "has_description_glossary": str(
                    row.get("has_description_glossary", "")
                ).strip().lower()
                == "true",
            }
        )

    rows: list[dict[str, Any]] = []
    for work in works:
        work_key = str(work.get("key", "")).strip()
        matches = grouped.get(work_key, [])
        if not matches:
            continue
        matches.sort(
            key=lambda item: (
                str(item.get("published_at", "")),
                item.get("views", 0),
            ),
            reverse=True,
        )
        latest = matches[0]
        rows.append(
            {
                "work_key": work_key,
                "serial_number": parse_int(work.get("serial_number")),
                "seed_title": preferred_title(work),
                "title": str(work.get("title", "")).strip(),
                "matched_video_count": len(matches),
                "latest_video_id": latest["video_id"],
                "latest_channel_title": latest["channel_title"],
                "latest_published_at": latest["published_at"],
                "latest_privacy": latest["privacy"],
                "latest_duration_seconds": latest["duration_seconds"],
                "views": latest["views"],
                "estimated_minutes_watched": latest["estimated_minutes_watched"],
                "average_view_duration_seconds": latest[
                    "average_view_duration_seconds"
                ],
                "average_view_duration_ratio": round(
                    latest["average_view_duration_ratio"], 4
                ),
                "average_view_duration_percentage": round(
                    latest["average_view_duration_percentage"], 2
                )
                if latest["average_view_duration_percentage"] > 0
                else round(latest["average_view_duration_ratio"] * 100, 2)
                if latest["average_view_duration_ratio"] > 0
                else 0.0,
                "retention_source": latest["retention_source"] or "",
                "impressions": latest["impressions"],
                "impression_ctr": round(latest["impression_ctr"] * 100, 2)
                if latest["impression_ctr"] > 0
                else 0.0,
                "views_per_impression": round(latest["views_per_impression"], 4)
                if latest["views_per_impression"] > 0
                else 0.0,
                "watch_time_minutes_per_impression": round(
                    latest["watch_time_minutes_per_impression"], 4
                )
                if latest["watch_time_minutes_per_impression"] > 0
                else 0.0,
                "description_length": latest["description_length"],
                "has_description_synopsis": "yes"
                if latest["has_description_synopsis"]
                else "no",
                "has_description_characters": "yes"
                if latest["has_description_characters"]
                else "no",
                "has_description_glossary": "yes"
                if latest["has_description_glossary"]
                else "no",
                "major_category": str(work.get("major_category", "")).strip(),
                "has_text": "yes" if work.get("text_paths") else "no",
                "has_audio": "yes" if work.get("audio_paths") else "no",
            }
        )

    rows.sort(
        key=lambda item: (
            -int(item["views"]),
            -float(item["estimated_minutes_watched"]),
            str(item["seed_title"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def write_outputs(rows: list[dict[str, Any]]) -> None:
    with OUT_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    with_retention = sum(
        1 for row in rows if float(row.get("average_view_duration_percentage", 0) or 0) > 0
    )
    with_impressions = sum(1 for row in rows if int(row.get("impressions", 0) or 0) > 0)
    public_count = sum(1 for row in rows if row.get("latest_privacy") == "public")
    lines = [
        "# 七之助 Channel Performance",
        "",
        "- source: `youtube_channel_report/old_channel_report`",
        f"- matched works: {len(rows)}",
        f"- public works: {public_count}",
        f"- works with impressions: {with_impressions}",
        f"- works with retention: {with_retention}",
        "",
        "| rank | work | views | avg_view | retention% | impressions | CTR% | watch_min | privacy |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows[:25]:
        lines.append(
            f"| {row['rank']} | {row['seed_title']} | {row['views']} | {row['average_view_duration_seconds']} | {row['average_view_duration_percentage']} | {row['impressions']} | {row['impression_ctr']} | {row['estimated_minutes_watched']} | {row['latest_privacy']} |"
        )
    OUT_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = build_rows()
    write_outputs(rows)
    print(f"Wrote: {OUT_CSV_PATH}")
    print(f"Wrote: {OUT_MD_PATH}")
    print(f"Matched works: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
