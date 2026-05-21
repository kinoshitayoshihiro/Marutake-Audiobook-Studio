#!/usr/bin/env python3

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"
CATALOG_PATH = REPORTS_DIR / "yoshikawa_works_catalog.csv"
SEED_SUMMARY_CSV_PATH = REPORTS_DIR / "yoshikawa_seed_shortworks.csv"
SEED_SUMMARY_MD_PATH = REPORTS_DIR / "yoshikawa_seed_shortworks.md"


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_int(value: Any) -> int:
    try:
        return int(float(str(value or "0").strip()))
    except (TypeError, ValueError):
        return 0


def sanitize_filename(title: str) -> str:
    safe: list[str] = []
    for ch in str(title):
        if ch.isalnum() or ch in {"_", "-", " "}:
            safe.append(ch)
        elif "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe).strip().replace(" ", "_")


def parse_date(date_text: str) -> datetime | None:
    text = str(date_text or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        return None


def recency_bonus(last_published: str) -> float:
    dt = parse_date(last_published)
    if dt is None:
        return 0.0
    if dt.year >= 2025:
        return 4.0
    if dt.year == 2024:
        return 3.0
    if dt.year == 2023:
        return 2.0
    if dt.year == 2022:
        return 1.0
    return 0.0


def bool_flag(row: dict[str, str], field: str) -> bool:
    return str(row.get(field, "")).strip().lower() == "yes"


def pick_seed_rows(limit: int = 10) -> list[dict[str, Any]]:
    rows = load_csv_rows(CATALOG_PATH)
    seeds: list[dict[str, Any]] = []
    for row in rows:
        video_count = as_int(row.get("video_count"))
        report_priority = bool_flag(row, "report_priority")
        has_local_text = bool_flag(row, "has_local_text")
        work_type = str(row.get("work_type", "")).strip()
        if video_count < 2 and not report_priority and not has_local_text:
            continue
        seed_score = (
            video_count * 1.2
            + (24 if report_priority else 0)
            + (12 if has_local_text else 0)
            + (8 if work_type == "シリーズ" else 0)
            + recency_bonus(str(row.get("last_published", "")))
        )
        seeds.append(
            {
                "seed_title": str(row.get("title", "")).strip(),
                "seed_score": round(seed_score, 3),
                "video_count": video_count,
                "work_type": work_type,
                "primary_genre": str(row.get("primary_genre", "")).strip(),
                "primary_era": str(row.get("primary_era", "")).strip(),
                "report_priority": str(row.get("report_priority", "")).strip(),
                "has_local_text": str(row.get("has_local_text", "")).strip(),
                "local_text_count": as_int(row.get("local_text_count")),
                "local_text_paths": str(row.get("local_text_paths", "")).strip(),
                "first_published": str(row.get("first_published", "")).strip(),
                "last_published": str(row.get("last_published", "")).strip(),
                "representative_clean_titles": str(row.get("representative_clean_titles", "")).strip(),
                "normalization_note": str(row.get("normalization_note", "")).strip(),
            }
        )
    seeds.sort(key=lambda item: (-float(item["seed_score"]), str(item["seed_title"])))
    for rank, item in enumerate(seeds[:limit], start=1):
        item["rank"] = rank
    return seeds[:limit]


def score_candidate(seed: dict[str, Any], row: dict[str, str]) -> dict[str, Any] | None:
    candidate_title = str(row.get("title", "")).strip()
    if not candidate_title or candidate_title == str(seed["seed_title"]):
        return None
    shared: list[str] = []
    score = 0.0
    if str(row.get("primary_genre", "")).strip() == str(seed.get("primary_genre", "")).strip() and str(seed.get("primary_genre", "")).strip():
        score += 5
        shared.append(f"genre:{seed['primary_genre']}")
    if str(row.get("primary_era", "")).strip() == str(seed.get("primary_era", "")).strip() and str(seed.get("primary_era", "")).strip():
        score += 3
        shared.append(f"era:{seed['primary_era']}")
    if str(row.get("work_type", "")).strip() == str(seed.get("work_type", "")).strip() and str(seed.get("work_type", "")).strip():
        score += 2
        shared.append(f"type:{seed['work_type']}")
    if bool_flag(row, "report_priority"):
        score += 4
        shared.append("report_priority")
    if bool_flag(row, "has_local_text"):
        score += 3
        shared.append("local_text")
    if as_int(row.get("video_count")) >= 10:
        score += 2
    elif as_int(row.get("video_count")) >= 5:
        score += 1
    seed_video_count = as_int(seed.get("video_count"))
    candidate_video_count = as_int(row.get("video_count"))
    diff = abs(seed_video_count - candidate_video_count)
    if diff <= 3:
        score += 2
    elif diff <= 10:
        score += 1
    if score <= 0:
        return None
    return {
        "seed_title": str(seed["seed_title"]),
        "candidate_title": candidate_title,
        "score": round(score, 3),
        "shared_signals": " / ".join(shared),
        "candidate_video_count": candidate_video_count,
        "candidate_work_type": str(row.get("work_type", "")).strip(),
        "candidate_primary_genre": str(row.get("primary_genre", "")).strip(),
        "candidate_primary_era": str(row.get("primary_era", "")).strip(),
        "candidate_report_priority": str(row.get("report_priority", "")).strip(),
        "candidate_has_local_text": str(row.get("has_local_text", "")).strip(),
        "candidate_local_text_paths": str(row.get("local_text_paths", "")).strip(),
        "candidate_last_published": str(row.get("last_published", "")).strip(),
        "candidate_representative_titles": str(row.get("representative_clean_titles", "")).strip(),
        "candidate_normalization_note": str(row.get("normalization_note", "")).strip(),
    }


def build_seed_candidates(seed_title: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = load_csv_rows(CATALOG_PATH)
    seed_row = next((row for row in rows if str(row.get("title", "")).strip() == seed_title), None)
    if seed_row is None:
        return []
    seed = {
        "seed_title": seed_title,
        "video_count": as_int(seed_row.get("video_count")),
        "work_type": str(seed_row.get("work_type", "")).strip(),
        "primary_genre": str(seed_row.get("primary_genre", "")).strip(),
        "primary_era": str(seed_row.get("primary_era", "")).strip(),
    }
    candidates: list[dict[str, Any]] = []
    for row in rows:
        scored = score_candidate(seed, row)
        if scored is not None:
            candidates.append(scored)
    candidates.sort(key=lambda item: (-float(item["score"]), str(item["candidate_title"])))
    return candidates[:limit]


def write_seed_candidate_files(seed_row: dict[str, Any], candidates: list[dict[str, Any]]) -> tuple[Path, Path]:
    slug = sanitize_filename(str(seed_row["seed_title"]))
    csv_path = REPORTS_DIR / f"yoshikawa_seed_{slug}_candidates.csv"
    md_path = REPORTS_DIR / f"yoshikawa_seed_{slug}_review.md"
    fieldnames = [
        "seed_title",
        "candidate_title",
        "score",
        "shared_signals",
        "candidate_video_count",
        "candidate_work_type",
        "candidate_primary_genre",
        "candidate_primary_era",
        "candidate_report_priority",
        "candidate_has_local_text",
        "candidate_local_text_paths",
        "candidate_last_published",
        "candidate_representative_titles",
        "candidate_normalization_note",
    ]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)

    lines = [
        f"# {seed_row['seed_title']} Seed Review",
        "",
        f"- 核作品: {seed_row['seed_title']}",
        f"- score: {seed_row['seed_score']}",
        f"- 動画数: {seed_row['video_count']}",
        f"- 種別: {seed_row['work_type']}",
        f"- 主ジャンル: {seed_row['primary_genre'] or '不明'}",
        f"- 主時代: {seed_row['primary_era'] or '不明'}",
        f"- 本文: {seed_row['has_local_text']} / {seed_row['local_text_paths'] or '-'}",
        f"- 公開範囲: {seed_row['first_published']} - {seed_row['last_published']}",
        "",
        "## 候補一覧",
        "",
        "| rank | candidate | score | signals | videos | text | last_published |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for rank, row in enumerate(candidates, start=1):
        lines.append(
            f"| {rank} | {row['candidate_title']} | {row['score']} | {row['shared_signals'] or '-'} | {row['candidate_video_count']} | {row['candidate_has_local_text']} | {row['candidate_last_published'] or '-'} |"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def write_seed_summary(seed_rows: list[dict[str, Any]], seed_outputs: dict[str, tuple[Path, Path]]) -> None:
    fieldnames = [
        "rank",
        "seed_title",
        "seed_score",
        "video_count",
        "work_type",
        "primary_genre",
        "primary_era",
        "report_priority",
        "has_local_text",
        "local_text_count",
        "first_published",
        "last_published",
        "candidate_csv",
        "review_md",
    ]
    normalized_rows: list[dict[str, Any]] = []
    for row in seed_rows:
        candidate_csv, review_md = seed_outputs[str(row["seed_title"])]
        normalized_rows.append(
            {
                "rank": row["rank"],
                "seed_title": row["seed_title"],
                "seed_score": row["seed_score"],
                "video_count": row["video_count"],
                "work_type": row["work_type"],
                "primary_genre": row["primary_genre"],
                "primary_era": row["primary_era"],
                "report_priority": row["report_priority"],
                "has_local_text": row["has_local_text"],
                "local_text_count": row["local_text_count"],
                "first_published": row["first_published"],
                "last_published": row["last_published"],
                "candidate_csv": candidate_csv.name,
                "review_md": review_md.name,
            }
        )
    with SEED_SUMMARY_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(normalized_rows)

    lines = [
        "# Yoshikawa Seed Shortworks",
        "",
        "- source: yoshikawa_works_catalog.csv",
        "- rule: report_priority / local_text / video_count / recency を加点して seed を選定",
        f"- seeds: {len(normalized_rows)}",
        "",
        "| rank | seed | score | videos | type | genre | era | text | review |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in normalized_rows:
        lines.append(
            f"| {row['rank']} | {row['seed_title']} | {row['seed_score']} | {row['video_count']} | {row['work_type']} | {row['primary_genre'] or '-'} | {row['primary_era'] or '-'} | {row['has_local_text']} | {row['review_md']} |"
        )
    SEED_SUMMARY_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    seed_rows = pick_seed_rows(limit=10)
    seed_outputs: dict[str, tuple[Path, Path]] = {}
    for row in seed_rows:
        candidates = build_seed_candidates(str(row["seed_title"]), limit=10)
        seed_outputs[str(row["seed_title"])] = write_seed_candidate_files(row, candidates)
    write_seed_summary(seed_rows, seed_outputs)
    print(SEED_SUMMARY_CSV_PATH)
    print(SEED_SUMMARY_MD_PATH)
    for seed_title, (csv_path, md_path) in seed_outputs.items():
        print(f"{seed_title}: {csv_path.name} / {md_path.name}")
    print(f"seed_shortworks={len(seed_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())