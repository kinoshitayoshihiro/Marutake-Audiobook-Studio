#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build next-content idea CSV and markdown from planning and reach opportunities.")
    parser.add_argument("--planning-input", default="content_planning_normal_video.csv")
    parser.add_argument("--opportunities-input", default="reach_analysis_opportunities.csv")
    parser.add_argument("--csv-output", default="next_content_ideas.csv")
    parser.add_argument("--md-output", default="next_content_ideas.md")
    return parser.parse_args()


def parse_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def normalize_number(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def escape_md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_seed_map(planning_rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    return {row["videoId"]: row for row in planning_rows if (row.get("videoId") or "").strip()}


def format_label(video_format: str) -> str:
    mapping = {
        "単話": "単話",
        "第一集": "第一集",
        "三部作": "三部作",
        "総集編/傑作選": "総集編",
        "長編連載": "長編連載",
        "睡眠・作業用": "睡眠用長尺",
        "聴くドラマ/一人でドラマ": "聴くドラマ",
    }
    return mapping.get(video_format, video_format or "単話")


def idea_rows_for_seed(seed: Dict[str, str]) -> List[Dict[str, object]]:
    title = seed.get("title", "")
    series_name = seed.get("series_name", "")
    series_sub = seed.get("series_sub", "")
    video_format = seed.get("video_format", "単話")
    publish_strategy = seed.get("publish_strategy", "")
    title_pattern = seed.get("suggested_title_pattern", "")
    thumbnail_pattern = seed.get("suggested_thumbnail_pattern", "")
    ctr = parse_float(seed.get("impressionCtr"))
    watch_per_impr = parse_float(seed.get("watch_minutes_per_impression"))
    priority_score = round((ctr * 100) * max(watch_per_impr, 0.1), 2)
    focus = f"{series_name} / {series_sub}" if series_sub else series_name

    ideas: List[Dict[str, object]] = []
    if video_format == "単話":
        ideas.append({
            "priority_score": priority_score,
            "idea_type": "same_series_followup",
            "seed_videoId": seed["videoId"],
            "seed_title": title,
            "series_name": series_name,
            "series_sub": series_sub,
            "recommended_format": "単話",
            "candidate_focus": f"{focus} の近接テーマ単話を追加",
            "reason": "CTR と視聴時間効率の両方が高い。タイトル/サムネの勝ち筋を維持したまま同シリーズ単話を増やすのが最短。",
            "publish_strategy": publish_strategy or "単話主軸で継続",
            "suggested_title_pattern": title_pattern,
            "suggested_thumbnail_pattern": thumbnail_pattern,
        })
        ideas.append({
            "priority_score": priority_score - 0.2,
            "idea_type": "same_series_bundle",
            "seed_videoId": seed["videoId"],
            "seed_title": title,
            "series_name": series_name,
            "series_sub": series_sub,
            "recommended_format": "総集編/傑作選",
            "candidate_focus": f"{focus} の高反応単話を束ねた再編集版",
            "reason": "単話で反応が取れているため、再生リスト化より前に総集編サムネで露出を取り直す価値がある。",
            "publish_strategy": "まとめ企画として定期投入",
            "suggested_title_pattern": "シリーズ名 総集編｜テーマ訴求｜七味春五郎",
            "suggested_thumbnail_pattern": "総集編/傑作選を大 + テーマ訴求",
        })
    elif video_format == "三部作":
        ideas.append({
            "priority_score": priority_score,
            "idea_type": "same_subseries_bundle",
            "seed_videoId": seed["videoId"],
            "seed_title": title,
            "series_name": series_name,
            "series_sub": series_sub,
            "recommended_format": "三部作",
            "candidate_focus": f"{focus} で別テーマの三部作を作る",
            "reason": "三部作のまま CTR と watch/impression が強い。束ね企画の再現性が高い。",
            "publish_strategy": "まとめ企画として定期投入",
            "suggested_title_pattern": "シリーズ名 三部作｜作品A・作品B・作品C｜七味春五郎",
            "suggested_thumbnail_pattern": "三部作を大文字 + 3作品名小",
        })
        ideas.append({
            "priority_score": priority_score - 0.2,
            "idea_type": "sleep_longform_extension",
            "seed_videoId": seed["videoId"],
            "seed_title": title,
            "series_name": series_name,
            "series_sub": series_sub,
            "recommended_format": "睡眠・作業用",
            "candidate_focus": f"{focus} を睡眠導線で長尺化",
            "reason": "長時間視聴効率が非常に高い。睡眠・作業用の訴求を前面に出すとさらなる視聴時間が見込める。",
            "publish_strategy": "睡眠・作業用の長尺枠で継続",
            "suggested_title_pattern": "【睡眠朗読】シリーズ名『作品名』｜睡眠・作業用｜七味春五郎",
            "suggested_thumbnail_pattern": "睡眠・作業用を大 + 作品名 + 落ち着いた配色",
        })
    else:
        ideas.append({
            "priority_score": priority_score,
            "idea_type": "same_format_expansion",
            "seed_videoId": seed["videoId"],
            "seed_title": title,
            "series_name": series_name,
            "series_sub": series_sub,
            "recommended_format": format_label(video_format),
            "candidate_focus": f"{focus} の同型フォーマット横展開",
            "reason": "既存フォーマットの反応が良いので、企画構造を変えずに作品だけ入れ替えるのが安全。",
            "publish_strategy": publish_strategy,
            "suggested_title_pattern": title_pattern,
            "suggested_thumbnail_pattern": thumbnail_pattern,
        })

    return ideas


def add_series_scale_ideas(planning_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    rows = []
    top_rows = sorted(planning_rows, key=lambda row: parse_float(row.get("estimatedMinutesWatched")), reverse=True)
    for row in top_rows[:2]:
        rows.append({
            "priority_score": round(parse_float(row.get("estimatedMinutesWatched")) / 10000, 2),
            "idea_type": "series_scale_up",
            "seed_videoId": row["videoId"],
            "seed_title": row["title"],
            "series_name": row.get("series_name", ""),
            "series_sub": row.get("series_sub", ""),
            "recommended_format": row.get("video_format", ""),
            "candidate_focus": f"{row.get('series_name','')} の主力勝ちパターンを継続投入",
            "reason": "既に視聴時間が大きく、チャンネルの主力ラインとして維持価値が高い。",
            "publish_strategy": row.get("publish_strategy", ""),
            "suggested_title_pattern": row.get("suggested_title_pattern", ""),
            "suggested_thumbnail_pattern": row.get("suggested_thumbnail_pattern", ""),
        })
    return rows


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_number(row.get(key)) for key in fieldnames})


def write_md(path: Path, rows: List[Dict[str, object]]) -> None:
    lines = ["# Next Content Ideas", ""]
    lines.append("## Priority List")
    lines.append("")
    lines.append("| priority_score | idea_type | series | format | candidate_focus | reason |")
    lines.append("|---:|---|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row['priority_score']:.2f} | {escape_md(row['idea_type'])} | {escape_md(row['series_name'])} | {escape_md(str(row['recommended_format']))} | {escape_md(row['candidate_focus'])} | {escape_md(row['reason'])} |"
        )
    lines.append("")
    lines.append("## Execution Notes")
    lines.append("")
    for idx, row in enumerate(rows[:10], start=1):
        lines.append(f"### {idx}. {row['candidate_focus']}")
        lines.append("")
        lines.append(f"- seed: `{row['seed_videoId']}` {row['seed_title']}")
        lines.append(f"- strategy: {row['publish_strategy']}")
        lines.append(f"- title pattern: {row['suggested_title_pattern']}")
        lines.append(f"- thumbnail pattern: {row['suggested_thumbnail_pattern']}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    planning_rows = load_csv((base_dir / args.planning_input).resolve())
    opportunities = load_csv((base_dir / args.opportunities_input).resolve())
    seed_map = build_seed_map(planning_rows)

    ideas: List[Dict[str, object]] = []
    for opportunity in opportunities:
        seed = seed_map.get(opportunity.get("videoId", ""))
        if not seed:
            continue
        seed = {**seed, **opportunity}
        ideas.extend(idea_rows_for_seed(seed))

    ideas.extend(add_series_scale_ideas(planning_rows))
    ideas.sort(key=lambda row: row["priority_score"], reverse=True)

    seen = set()
    deduped: List[Dict[str, object]] = []
    for row in ideas:
        key = (row["candidate_focus"], row["recommended_format"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)

    csv_path = (base_dir / args.csv_output).resolve()
    md_path = (base_dir / args.md_output).resolve()
    write_csv(csv_path, deduped[:12])
    write_md(md_path, deduped[:12])
    print(f"Ideas written: {csv_path}")
    print(f"Report written: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
