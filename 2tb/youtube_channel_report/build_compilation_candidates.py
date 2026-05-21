#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compilation candidates from daily growth signals.")
    parser.add_argument("--growth-input", default="daily_growth_signals.csv")
    parser.add_argument("--series-name", default="銭形平次捕物控")
    parser.add_argument("--csv-output", default="zenigata_compilation_candidates.csv")
    parser.add_argument("--md-output", default="zenigata_compilation_candidates.md")
    return parser.parse_args()


def parse_float(value: str | None) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def parse_int(value: str | None) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(value))
    except ValueError:
        return 0


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


def infer_compilation_type(video_format: str, title: str) -> str:
    if video_format == "第一集":
        return "第一集続編"
    if video_format == "総集編/傑作選":
        return "完全版/続編総集編"
    if video_format == "睡眠・作業用":
        return "睡眠長尺総集編"
    if video_format == "聴くドラマ/一人でドラマ":
        return "ドラマ長尺総集編"
    if "長編" in title:
        return "長編拡張版"
    return "三作まとめ候補"


def infer_candidate_lane(age_days: int, growth_rate: float, video_format: str) -> str:
    if age_days <= 10:
        return "new_hot_seed"
    if growth_rate >= 0.10:
        return "revival_seed"
    if video_format == "総集編/傑作選":
        return "bundle_extension"
    if video_format in {"睡眠・作業用", "聴くドラマ/一人でドラマ"}:
        return "format_expansion"
    return "library_pick"


def build_note(row: Dict[str, str]) -> str:
    growth = parse_float(row.get("impression_growth_rate_7d"))
    last_7d_impr = parse_int(row.get("last_7d_impressions"))
    ctr = parse_float(row.get("last_7d_ctr")) * 100
    watch_impr = parse_float(row.get("last_7d_watch_time_minutes_per_impression"))
    video_format = row.get("video_format", "")

    notes = []
    if last_7d_impr >= 9000:
        notes.append("直近露出が非常に強い")
    elif last_7d_impr >= 3000:
        notes.append("直近露出が強い")
    if growth >= 0.10:
        notes.append("前7日比で再加速")
    elif growth <= -0.50:
        notes.append("初速後の減衰局面")
    if ctr >= 7.0:
        notes.append("CTRが高い")
    elif ctr >= 5.5:
        notes.append("CTRが安定")
    if watch_impr >= 6.0:
        notes.append("露出あたり視聴時間が強い")
    elif watch_impr >= 3.0:
        notes.append("長尺化適性あり")
    if video_format == "総集編/傑作選":
        notes.append("既に総集編型で実績あり")
    elif video_format == "第一集":
        notes.append("第一集の続編設計向き")
    elif video_format == "睡眠・作業用":
        notes.append("睡眠導線に乗せやすい")
    elif video_format == "聴くドラマ/一人でドラマ":
        notes.append("ドラマ演出枠で横展開しやすい")
    return " / ".join(notes)


def build_rows(growth_rows: List[Dict[str, str]], target_series: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for row in growth_rows:
        if row.get("series_name") != target_series:
            continue
        title = row.get("title", "")
        video_format = row.get("video_format", "")
        age_days = parse_int(row.get("age_days"))
        signal_score = parse_float(row.get("signal_score"))
        last_7d_impressions = parse_int(row.get("last_7d_impressions"))
        prev_7d_impressions = parse_int(row.get("prev_7d_impressions"))
        growth_rate = parse_float(row.get("impression_growth_rate_7d"))
        last_7d_ctr = parse_float(row.get("last_7d_ctr")) * 100
        watch_impr = parse_float(row.get("last_7d_watch_time_minutes_per_impression"))
        compile_priority_score = round(signal_score + (last_7d_ctr * 25) + (watch_impr * 60) + min(last_7d_impressions, 12000) * 0.08, 2)
        rows.append({
            "channel_scope": "current_channel",
            "series_name": row.get("series_name", ""),
            "series_sub": row.get("series_sub", ""),
            "video_id": row.get("video_id", ""),
            "title": title,
            "publishedAt": row.get("publishedAt", ""),
            "age_days": age_days,
            "video_format": video_format,
            "candidate_lane": infer_candidate_lane(age_days, growth_rate, video_format),
            "recommended_compilation_type": infer_compilation_type(video_format, title),
            "same_line_key": f"{row.get('series_name','')}::{video_format or 'unknown'}",
            "compile_priority_score": compile_priority_score,
            "signal_score": round(signal_score, 2),
            "last_7d_impressions": last_7d_impressions,
            "prev_7d_impressions": prev_7d_impressions,
            "impression_growth_rate_7d_pct": round(growth_rate * 100, 1) if row.get("impression_growth_rate_7d") not in (None, "") else "",
            "last_7d_ctr_pct": round(last_7d_ctr, 2),
            "last_7d_watch_time_minutes_per_impression": round(watch_impr, 3),
            "selection_note": build_note(row),
        })
    rows.sort(key=lambda row: row["compile_priority_score"], reverse=True)
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


def write_md(path: Path, rows: List[Dict[str, object]], growth_input_label: str, target_series: str) -> None:
    lines = [f"# {target_series} 総集編候補", ""]
    lines.append(f"- 対象シリーズ: {target_series}")
    lines.append(f"- 元データ: {growth_input_label}")
    lines.append("")
    lines.append("## 優先候補トップ20")
    lines.append("")
    lines.append("| 順位 | タイトル | 形式 | lane | compile_score | last_7d_impr | growth_7d | ctr | watch/impr |")
    lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |")
    for idx, row in enumerate(rows[:20], start=1):
        growth = row["impression_growth_rate_7d_pct"]
        growth_label = "" if growth == "" else f"{growth:.1f}%"
        lines.append(
            f"| {idx} | {escape_md(row['title'])} | {escape_md(row['recommended_compilation_type'])} | {escape_md(row['candidate_lane'])} | {row['compile_priority_score']:.2f} | {row['last_7d_impressions']} | {growth_label} | {row['last_7d_ctr_pct']:.2f}% | {row['last_7d_watch_time_minutes_per_impression']:.3f} |"
        )
    lines.append("")
    lines.append("## 制作メモ")
    lines.append("")
    for idx, row in enumerate(rows[:10], start=1):
        lines.append(f"### {idx}. {row['title']}")
        lines.append("")
        lines.append(f"- video_id: `{row['video_id']}`")
        lines.append(f"- 公開日: {row['publishedAt']}")
        lines.append(f"- 推奨総集編タイプ: {row['recommended_compilation_type']}")
        lines.append(f"- 同系統キー: `{row['same_line_key']}`")
        lines.append(f"- 判定メモ: {row['selection_note']}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    growth_path = (base_dir / args.growth_input).resolve()
    rows = build_rows(load_csv(growth_path), args.series_name)
    csv_path = (base_dir / args.csv_output).resolve()
    md_path = (base_dir / args.md_output).resolve()
    write_csv(csv_path, rows)
    write_md(md_path, rows, growth_path.name, args.series_name)
    print(f"Compilation CSV: {csv_path}")
    print(f"Compilation report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
