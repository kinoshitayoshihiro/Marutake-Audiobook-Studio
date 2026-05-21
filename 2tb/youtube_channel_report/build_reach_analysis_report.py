#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from statistics import median
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build reach analysis markdown and opportunity CSV from enriched video CSVs.")
    parser.add_argument("--all-input", default="youtube_video_report_last_90_days_all_videos.csv")
    parser.add_argument("--normal-input", default="youtube_video_report_last_90_days_normal_video.csv")
    parser.add_argument("--report-output", default="reach_analysis_report.md")
    parser.add_argument("--opportunities-output", default="reach_analysis_opportunities.csv")
    return parser.parse_args()


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def normalize_number(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def escape_md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def load_rows(path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            impressions = parse_float(row.get("impressions"))
            ctr = parse_float(row.get("impressionCtr"))
            views = parse_float(row.get("views")) or 0.0
            watch_minutes = parse_float(row.get("estimatedMinutesWatched")) or 0.0
            avg_view_duration = parse_float(row.get("averageViewDuration")) or 0.0
            duration_seconds = parse_int(row.get("duration_seconds"))
            retention_ratio = avg_view_duration / duration_seconds if duration_seconds and duration_seconds > 0 else None
            rows.append({
                **row,
                "impressions_num": impressions,
                "ctr_num": ctr,
                "views_num": views,
                "watch_minutes_num": watch_minutes,
                "avg_view_duration_num": avg_view_duration,
                "duration_seconds_num": duration_seconds,
                "retention_ratio": retention_ratio,
                "views_per_impression": views / impressions if impressions and impressions > 0 else None,
                "watch_minutes_per_impression": watch_minutes / impressions if impressions and impressions > 0 else None,
            })
    return rows


def top_rows(rows: List[Dict[str, object]], *, metric: str, limit: int = 10, min_impressions: float = 0) -> List[Dict[str, object]]:
    filtered = [row for row in rows if row.get(metric) is not None and (row.get("impressions_num") or 0) >= min_impressions]
    return sorted(filtered, key=lambda row: row[metric], reverse=True)[:limit]


def build_opportunity_rows(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    eligible = [row for row in rows if (row.get("impressions_num") or 0) >= 1500]
    if not eligible:
        return []
    ctr_values = [row["ctr_num"] for row in eligible if row.get("ctr_num") is not None]
    impression_values = [row["impressions_num"] for row in eligible if row.get("impressions_num") is not None]
    if not ctr_values or not impression_values:
        return []
    median_ctr = median(ctr_values)
    median_impressions = median(impression_values)
    opportunities: List[Dict[str, object]] = []
    for row in eligible:
        ctr = row.get("ctr_num")
        impressions = row.get("impressions_num")
        if ctr is None or impressions is None:
            continue
        if ctr < median_ctr * 1.2:
            continue
        if impressions >= median_impressions:
            continue
        opportunities.append({
            "videoId": row["videoId"],
            "title": row["title"],
            "content_type_bucket": row["content_type_bucket"],
            "publishedAt": row["publishedAt"],
            "views": row["views_num"],
            "estimatedMinutesWatched": row["watch_minutes_num"],
            "impressions": impressions,
            "impressionCtr": ctr,
            "views_per_impression": row["views_per_impression"],
            "watch_minutes_per_impression": row["watch_minutes_per_impression"],
            "retention_ratio": row["retention_ratio"],
        })
    opportunities.sort(key=lambda row: (row["impressionCtr"], row["watch_minutes_per_impression"] or 0), reverse=True)
    return opportunities


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_number(row.get(key)) for key in fieldnames})


def add_table(lines: List[str], rows: List[Dict[str, object]], *, title: str) -> None:
    lines.append(f"## {title}")
    lines.append("")
    if not rows:
        lines.append("該当データなし。")
        lines.append("")
        return
    lines.append("| title | impressions | CTR% | views | watch_min | watch/impr | bucket |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for row in rows:
        lines.append(
            "| "
            f"{escape_md(row['title'])} | "
            f"{int(row.get('impressions_num') or row.get('impressions') or 0)} | "
            f"{((row.get('ctr_num') or row.get('impressionCtr') or 0) * 100):.2f} | "
            f"{int(row.get('views_num') or row.get('views') or 0)} | "
            f"{int(row.get('watch_minutes_num') or row.get('estimatedMinutesWatched') or 0)} | "
            f"{(row.get('watch_minutes_per_impression') or 0):.3f} | "
            f"{escape_md(row.get('content_type_bucket', ''))} |"
        )
    lines.append("")


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    all_csv = (base_dir / args.all_input).resolve()
    normal_csv = (base_dir / args.normal_input).resolve()
    report_path = (base_dir / args.report_output).resolve()
    opportunities_path = (base_dir / args.opportunities_output).resolve()

    all_rows = load_rows(all_csv)
    normal_rows = load_rows(normal_csv)
    all_with_reach = [row for row in all_rows if row.get("impressions_num") is not None]
    normal_with_reach = [row for row in normal_rows if row.get("impressions_num") is not None]
    all_impressions = [row["impressions_num"] for row in all_with_reach]
    normal_impressions = [row["impressions_num"] for row in normal_with_reach]
    all_ctr = [row["ctr_num"] for row in all_with_reach if row.get("ctr_num") is not None]
    normal_ctr = [row["ctr_num"] for row in normal_with_reach if row.get("ctr_num") is not None]
    top_impressions = top_rows(normal_with_reach, metric="impressions_num", limit=10)
    top_ctr = top_rows(normal_with_reach, metric="ctr_num", limit=10, min_impressions=2000)
    top_watch_per_impression = top_rows(normal_with_reach, metric="watch_minutes_per_impression", limit=10, min_impressions=3000)
    opportunities = build_opportunity_rows(normal_with_reach)[:15]
    write_csv(opportunities_path, opportunities)

    lines: List[str] = []
    lines.append("# Reach Analysis Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- all_videos: {len(all_rows)} rows, reach filled {len(all_with_reach)} rows")
    lines.append(f"- normal_video: {len(normal_rows)} rows, reach filled {len(normal_with_reach)} rows")
    if all_impressions and all_ctr:
        lines.append(f"- all_videos median impressions: {median(all_impressions):.1f}, median CTR: {median(all_ctr) * 100:.2f}%")
    if normal_impressions and normal_ctr:
        lines.append(f"- normal_video median impressions: {median(normal_impressions):.1f}, median CTR: {median(normal_ctr) * 100:.2f}%")
    lines.append("")
    add_table(lines, top_impressions, title="Top Impressions Normal Video")
    add_table(lines, top_ctr, title="Top CTR Normal Video (min 2,000 impressions)")
    add_table(lines, top_watch_per_impression, title="Top Watch Minutes Per Impression (min 3,000 impressions)")
    add_table(lines, opportunities, title="Underexposed High-CTR Opportunities")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Report written: {report_path}")
    print(f"Opportunities written: {opportunities_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
