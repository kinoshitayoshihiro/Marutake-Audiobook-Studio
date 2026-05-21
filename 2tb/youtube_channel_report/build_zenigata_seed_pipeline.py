#!/usr/bin/env python3

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = BASE_DIR / "reports"
CURRENT_ALL_VIDEOS_PATH = Path(__file__).resolve().parent / "youtube_video_report_last_90_days_all_videos.csv"
CURRENT_GROWTH_PATH = Path(__file__).resolve().parent / "daily_growth_signals.csv"
SEARCH_BUILDER_PATH = BASE_DIR / "tools" / "zenigata_search_page_builder_impl.py"
SHORTWORKS_HELPER_PATH = Path(__file__).resolve().parent / "build_zenigata_shortworks_catalog.py"
SEED_SUMMARY_CSV_PATH = REPORTS_DIR / "zenigata_seed_shortworks.csv"
SEED_SUMMARY_MD_PATH = REPORTS_DIR / "zenigata_seed_shortworks.md"
FEEDBACK_LOG_PATH = REPORTS_DIR / "zenigata_bundle_feedback_log.csv"
CURRENT_CHANNEL_ID = "UC2UJSjh_A_Erfoj7bD2drzA"
OLD_CHANNEL_ID = "UCeTnkaLU8_MAMSdMFVrf1dw"

CURRENT_TITLE_EXCLUDE_MARKERS = (
    "総集編",
    "第一集",
    "第二集",
    "各巻",
    "第三集",
    "五作集",
    "三作集",
    "完全版",
    "まとめ",
    "連載",
    "第一巻",
    "第二巻",
    "第三巻",
    "第四巻",
    "第五巻",
    "前編",
    "後編",
    "中篇",
    "長編",
    "長篇",
    "全編",
    "主題歌",
    "睡眠",
    "作業用",
    "傑作選",
    "朗読ライブ",
    "冒頭を紹介",
)

FEEDBACK_LOG_FIELDS = [
    "logged_at",
    "seed_title",
    "candidate_title",
    "pipeline_score",
    "shared_theme_count",
    "shared_tag_count",
    "shared_character_count",
    "lineage_bonus",
    "has_local_text_bonus",
    "old_only_bonus",
    "adoption_status",
    "story_lineage",
    "has_local_text",
    "decision",
    "fit_score",
    "reason_short",
    "reviewer",
    "reviewed_at",
]

CANDIDATE_FIELDS = [
    "seed_title",
    "score",
    "shared_theme_count",
    "shared_tag_count",
    "shared_character_count",
    "lineage_bonus",
    "has_local_text_bonus",
    "old_only_bonus",
    "title",
    "adoption_status",
    "story_lineage",
    "shared_themes",
    "shared_tags",
    "shared_characters",
    "has_local_text",
    "publication_years",
    "synopsis",
    "score_reason",
]


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SEARCH_BUILDER = load_module(SEARCH_BUILDER_PATH, "zenigata_search_builder")
SHORTWORKS_HELPER = load_module(SHORTWORKS_HELPER_PATH, "zenigata_shortworks_helper")


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


def as_float(value: Any) -> float:
    try:
        return float(str(value or "0").strip())
    except (TypeError, ValueError):
        return 0.0


def sanitize_filename(title: str) -> str:
    safe = []
    for ch in str(title):
        if ch.isalnum() or ch in {"_", "-", " "}:
            safe.append(ch)
        elif "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
            safe.append(ch)
        else:
            safe.append("_")
    return "".join(safe).strip().replace(" ", "_")


def ensure_feedback_log() -> None:
    existing_rows = load_csv_rows(FEEDBACK_LOG_PATH)
    with FEEDBACK_LOG_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FEEDBACK_LOG_FIELDS)
        writer.writeheader()
        for row in existing_rows:
            normalized = {field: str(row.get(field, "")).strip() for field in FEEDBACK_LOG_FIELDS}
            writer.writerow(normalized)


def load_catalog_maps() -> tuple[dict[str, dict[str, str]], dict[str, dict[str, str]], list[tuple[str, dict[str, str]]]]:
    catalog_rows = load_csv_rows(REPORTS_DIR / "zenigata_heiji_works_catalog.csv")
    return SHORTWORKS_HELPER.build_catalog_maps(catalog_rows)


def build_growth_map() -> dict[str, dict[str, str]]:
    return {
        str(row.get("video_id", "")).strip(): row
        for row in load_csv_rows(CURRENT_GROWTH_PATH)
        if str(row.get("video_id", "")).strip()
    }


def pick_seed_rows(limit: int = 10) -> list[dict[str, Any]]:
    exact_map, normalized_map, normalized_keys = load_catalog_maps()
    growth_map = build_growth_map()
    search_rows = SEARCH_BUILDER.load_rows(
        SEARCH_BUILDER.load_recording_state(),
        SEARCH_BUILDER.load_aozora_manifest(),
    )
    items_by_title = {str(row["title"]): row for row in search_rows}

    seeds: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for row in load_csv_rows(CURRENT_ALL_VIDEOS_PATH):
        video_id = str(row.get("videoId", "")).strip()
        title = str(row.get("title", "")).strip()
        if not title or "銭形平次" not in title:
            continue
        if any(marker in title for marker in CURRENT_TITLE_EXCLUDE_MARKERS):
            continue
        if str(row.get("is_private", "")).strip().lower() == "true":
            continue
        if str(row.get("is_public", "")).strip().lower() != "true":
            continue
        duration_seconds = as_int(row.get("duration_seconds"))
        if duration_seconds <= 180 or duration_seconds > 5400:
            continue
        matched_title, _catalog_row = SHORTWORKS_HELPER.match_catalog_row(
            title, exact_map, normalized_map, normalized_keys
        )
        if not matched_title or matched_title in seen_titles:
            continue
        search_item = items_by_title.get(matched_title)
        if not search_item or not bool(search_item.get("has_local_text")):
            continue
        growth = growth_map.get(video_id, {})
        signal_score = as_float(growth.get("signal_score"))
        last_7d_impressions = as_float(growth.get("last_7d_impressions"))
        last_7d_ctr = as_float(growth.get("last_7d_ctr"))
        views = as_float(row.get("views"))
        impressions = as_float(row.get("impressions"))
        average_view_duration = as_float(row.get("averageViewDuration"))
        seed_score = (
            signal_score
            + last_7d_impressions * 0.08
            + last_7d_ctr * 1000
            + views * 0.2
            + impressions * 0.01
            + average_view_duration * 0.05
        )
        seeds.append(
            {
                "seed_title": matched_title,
                "video_id": video_id,
                "channel_title": title,
                "published_at": str(row.get("publishedAt", "")).strip(),
                "duration_seconds": duration_seconds,
                "views": as_int(row.get("views")),
                "impressions": as_int(row.get("impressions")),
                "impression_ctr": as_float(row.get("impressionCtr")),
                "average_view_duration_seconds": as_int(row.get("averageViewDuration")),
                "signal_score": round(signal_score, 3),
                "last_7d_impressions": round(last_7d_impressions, 3),
                "last_7d_ctr": round(last_7d_ctr, 6),
                "seed_score": round(seed_score, 3),
                "adoption_status": str(search_item.get("adoption_status", "")).strip(),
                "story_lineage": str(search_item.get("story_lineage", "")).strip(),
                "theme_secondary": " / ".join(search_item.get("theme_secondary", [])),
                "tags": " / ".join(search_item.get("tags", [])),
                "characters": " / ".join(search_item.get("characters", [])),
                "publication_years": str(search_item.get("publication_years", "")).strip(),
                "has_local_text": "yes" if bool(search_item.get("has_local_text")) else "no",
                "preferred_text_path": str(search_item.get("preferred_text_path", "")).strip(),
            }
        )
        seen_titles.add(matched_title)

    seeds.sort(key=lambda item: (-float(item["seed_score"]), item["seed_title"]))
    return seeds[:limit]


def score_candidate(seed: dict[str, Any], row: dict[str, Any]) -> dict[str, Any] | None:
    seed_themes = set(seed.get("theme_secondary", []))
    seed_tags = set(seed.get("tags", []))
    seed_characters = set(seed.get("characters", []))
    shared_themes = sorted(seed_themes & set(row.get("theme_secondary", [])))
    shared_tags = sorted(seed_tags & set(row.get("tags", [])))
    shared_characters = sorted(seed_characters & set(row.get("characters", [])))
    lineage_bonus = 3 if row.get("story_lineage") == seed.get("story_lineage") else 0
    has_local_text_bonus = 1 if row.get("has_local_text") else 0
    old_only_bonus = 2 if row.get("adoption_status") == "旧実績のみ" else 0
    score = (
        len(shared_themes) * 5
        + len(shared_tags) * 3
        + len(shared_characters)
        + lineage_bonus
        + has_local_text_bonus
        + old_only_bonus
    )
    if score <= 0:
        return None
    reason_parts: list[str] = []
    if shared_themes:
        reason_parts.append(f"themes:{' / '.join(shared_themes)}")
    if shared_tags:
        reason_parts.append(f"tags:{' / '.join(shared_tags)}")
    if shared_characters:
        reason_parts.append(f"characters:{' / '.join(shared_characters)}")
    if lineage_bonus:
        reason_parts.append("lineage")
    if has_local_text_bonus:
        reason_parts.append("local_text")
    if old_only_bonus:
        reason_parts.append("old_only")
    return {
        "seed_title": str(seed.get("title", "")).strip(),
        "score": score,
        "shared_theme_count": len(shared_themes),
        "shared_tag_count": len(shared_tags),
        "shared_character_count": len(shared_characters),
        "lineage_bonus": lineage_bonus,
        "has_local_text_bonus": has_local_text_bonus,
        "old_only_bonus": old_only_bonus,
        "title": str(row.get("title", "")).strip(),
        "adoption_status": str(row.get("adoption_status", "")).strip(),
        "story_lineage": str(row.get("story_lineage", "")).strip(),
        "shared_themes": " / ".join(shared_themes),
        "shared_tags": " / ".join(shared_tags),
        "shared_characters": " / ".join(shared_characters),
        "has_local_text": "yes" if row.get("has_local_text") else "no",
        "publication_years": str(row.get("publication_years", "")).strip(),
        "synopsis": str(row.get("synopsis") or row.get("summary") or "").strip(),
        "score_reason": " | ".join(reason_parts),
    }


def build_seed_candidates(seed_title: str, limit: int = 10) -> list[dict[str, Any]]:
    rows = SEARCH_BUILDER.load_rows(
        SEARCH_BUILDER.load_recording_state(),
        SEARCH_BUILDER.load_aozora_manifest(),
    )
    seed = next((row for row in rows if str(row.get("title")) == seed_title), None)
    if not seed:
        return []

    candidates: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("title")) == seed_title:
            continue
        if str(row.get("adoption_status", "")).strip() == "採用済み":
            continue
        if not bool(row.get("has_local_text")):
            continue
        latest_title = str(row.get("latest_channel_title", "") or "").strip()
        if latest_title and any(marker in latest_title for marker in CURRENT_TITLE_EXCLUDE_MARKERS):
            continue
        latest_duration = as_int(row.get("latest_duration_seconds"))
        if latest_duration and latest_duration > 5400:
            continue
        scored = score_candidate(seed, row)
        if scored:
            candidates.append(scored)
    candidates.sort(
        key=lambda item: (
            -int(item["score"]),
            item["adoption_status"] != "旧実績のみ",
            str(item["title"]),
        )
    )
    return candidates[:limit]


def write_seed_candidate_files(seed_row: dict[str, Any], candidates: list[dict[str, Any]]) -> tuple[Path, Path]:
    slug = sanitize_filename(str(seed_row["seed_title"]))
    csv_path = REPORTS_DIR / f"zenigata_seed_{slug}_candidates.csv"
    md_path = REPORTS_DIR / f"zenigata_seed_{slug}_review.md"

    if candidates:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CANDIDATE_FIELDS)
            writer.writeheader()
            writer.writerows(candidates)
    else:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CANDIDATE_FIELDS)
            writer.writeheader()

    md_lines = [
        f"# {seed_row['seed_title']} 総集編レビュー",
        "",
        f"- 核作品: {seed_row['seed_title']}",
        f"- 現行チャンネル: {CURRENT_CHANNEL_ID}",
        f"- 旧チャンネル: {OLD_CHANNEL_ID}",
        f"- 公開タイトル: {seed_row['channel_title']}",
        f"- 公開日: {seed_row['published_at']}",
        f"- 実績: views {seed_row['views']} / impressions {seed_row['impressions']} / CTR {seed_row['impression_ctr']} / signal {seed_row['signal_score']}",
        f"- 作品属性: lineage {seed_row['story_lineage']} / themes {seed_row['theme_secondary'] or '-'} / tags {seed_row['tags'] or '-'} / characters {seed_row['characters'] or '-'}",
        f"- 本文: {seed_row['has_local_text']} / {seed_row['preferred_text_path'] or 'path不明'}",
        "- 目的: 採用済みを除いた候補から、本文比較で総集編3本を決める",
        f"- 候補CSV: reports/{csv_path.name}",
        "",
        "## 候補上位",
        "",
    ]
    if not candidates:
        md_lines.append("- 候補がありません。")
    else:
        for index, row in enumerate(candidates[:10], start=1):
            md_lines.append(
                f"- {index}. {row['title']} / score {row['score']} / {row['adoption_status']} / {row['score_reason'] or '近接要素なし'}"
            )
    md_lines.extend(
        [
            "",
            "## スコア内訳",
            "",
            "- shared themes: 1件につき +5",
            "- shared tags: 1件につき +3",
            "- shared characters: 1件につき +1",
            "- same lineage: +3",
            "- has local text: +1",
            "- old-only bonus: +2",
            "",
            "## 本文比較プロンプト",
            "",
            f"{seed_row['seed_title']}を核作品として、候補作品の本文を比較してください。",
            "判定基準は次の順です。",
            "1. 同じ総集編に入れたとき、聴感上の空気感が揃うか",
            "2. 事件の型が近いか",
            "3. 結末の後味がぶつからないか",
            "4. 八五郎・平次の出方が揃うか",
            "5. 3本の並び順として自然か",
            "",
            "出力形式:",
            "- 最適な3本",
            "- 次点3本",
            "- 除外した方がよい作品",
            "- 理由を作品ごとに1-3行",
            "- 総集編タイトル案を3案",
            "- 並び順案を1案",
            "",
            "## 使い方メモ",
            "",
            "- 検索アプリは粗い候補出し",
            "- 本文比較は最終審査",
            "- 採否結果は feedback_log に追記する",
        ]
    )
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return csv_path, md_path


def append_feedback_log(seed_row: dict[str, Any], candidates: list[dict[str, Any]]) -> None:
    existing = load_csv_rows(FEEDBACK_LOG_PATH)
    existing_pairs = {
        (str(row.get("seed_title", "")).strip(), str(row.get("candidate_title", "")).strip())
        for row in existing
    }
    logged_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    appended = False
    with FEEDBACK_LOG_PATH.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FEEDBACK_LOG_FIELDS)
        for row in candidates:
            pair = (str(seed_row["seed_title"]), str(row["title"]))
            if pair in existing_pairs:
                continue
            writer.writerow(
                {
                    "logged_at": logged_at,
                    "seed_title": seed_row["seed_title"],
                    "candidate_title": row["title"],
                    "pipeline_score": row["score"],
                    "shared_theme_count": row["shared_theme_count"],
                    "shared_tag_count": row["shared_tag_count"],
                    "shared_character_count": row["shared_character_count"],
                    "lineage_bonus": row["lineage_bonus"],
                    "has_local_text_bonus": row["has_local_text_bonus"],
                    "old_only_bonus": row["old_only_bonus"],
                    "adoption_status": row["adoption_status"],
                    "story_lineage": row["story_lineage"],
                    "has_local_text": row["has_local_text"],
                    "decision": "",
                    "fit_score": "",
                    "reason_short": "",
                    "reviewer": "",
                    "reviewed_at": "",
                }
            )
            appended = True
    if appended:
        return


def write_seed_summary(seed_rows: list[dict[str, Any]], seed_outputs: dict[str, tuple[Path, Path]]) -> None:
    if seed_rows:
        with SEED_SUMMARY_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(seed_rows[0].keys()))
            writer.writeheader()
            writer.writerows(seed_rows)
    else:
        SEED_SUMMARY_CSV_PATH.write_text("", encoding="utf-8")

    lines = [
        "# Zenigata Seed Shortworks",
        "",
        "- source: current channel report",
        f"- current channel id: `{CURRENT_CHANNEL_ID}`",
        f"- old channel id: `{OLD_CHANNEL_ID}`",
        "- scope: short stories only (`180 < duration_seconds <= 5400`), excluding long/mid, compilations, songs, sleep/work, and aggregated titles",
        "- next step: run LLM本文比較 on each seed review markdown",
        "",
        f"- seeds: {len(seed_rows)}",
        "",
        "| seed | seed_score | views | impressions | signal_score | adoption_status | candidate_csv | review_md |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in seed_rows:
        seed_title = str(row["seed_title"])
        candidate_csv, review_md = seed_outputs[seed_title]
        lines.append(
            f"| {seed_title} | {row['seed_score']} | {row['views']} | {row['impressions']} | {row['signal_score']} | {row['adoption_status']} | {candidate_csv.name} | {review_md.name} |"
        )
    SEED_SUMMARY_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_feedback_log()
    seed_rows = pick_seed_rows(limit=10)
    seed_outputs: dict[str, tuple[Path, Path]] = {}
    for seed_row in seed_rows:
        candidates = build_seed_candidates(str(seed_row["seed_title"]), limit=10)
        append_feedback_log(seed_row, candidates)
        seed_outputs[str(seed_row["seed_title"])] = write_seed_candidate_files(
            seed_row, candidates
        )
    write_seed_summary(seed_rows, seed_outputs)

    print(SEED_SUMMARY_CSV_PATH)
    print(SEED_SUMMARY_MD_PATH)
    for seed_title, (csv_path, md_path) in seed_outputs.items():
        print(f"{seed_title}: {csv_path.name} / {md_path.name}")
    print(f"seed_shortworks={len(seed_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
