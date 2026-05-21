#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
READING_DIR = ROOT / "Reading_library" / "銭形平次捕物控"
CATALOG_CSV = REPORTS_DIR / "zenigata_heiji_works_catalog.csv"
THEME_JSON = ROOT / "tools" / "zenigata_theme_profiles.json"
TEXT_OVERRIDE_PATH = REPORTS_DIR / "zenigata_text_overrides.json"
OUT_JSON = REPORTS_DIR / "zenigata_theme_match_scores.json"
OUT_CSV = REPORTS_DIR / "zenigata_theme_match_scores.csv"
OUT_MD = REPORTS_DIR / "zenigata_theme_match_report.md"


def load_theme_profiles() -> dict[str, Any]:
    return json.loads(THEME_JSON.read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    text = text or ""
    text = text.replace("\u3000", " ")
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def read_text_best_effort(path: Path) -> str:
    for encoding in ("utf-8", "cp932"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return ""
    return ""


def load_local_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    if not READING_DIR.exists():
        return texts
    for path in READING_DIR.glob("*.txt"):
        content = read_text_best_effort(path)
        if content:
            texts[path.stem] = normalize_text(content)
    return texts


def load_text_overrides() -> dict[str, str]:
    if not TEXT_OVERRIDE_PATH.exists():
        return {}
    try:
        data = json.loads(TEXT_OVERRIDE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    items = data.get("items", []) if isinstance(data, dict) else []
    overrides: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        title = normalize_text(str(item.get("title", "")))
        text_path_value = str(item.get("text_path", "")).strip()
        if not title or not text_path_value:
            continue
        path = Path(text_path_value)
        content = read_text_best_effort(path)
        if content:
            overrides[title] = normalize_text(content)
    return overrides


def find_local_text(
    title: str, texts: dict[str, str], override_texts: dict[str, str]
) -> str:
    normalized_title = normalize_text(title)
    if normalized_title in override_texts:
        return override_texts[normalized_title]
    for stem, content in texts.items():
        if normalized_title in stem:
            return content
    return ""


def count_keyword_hits(text: str, keywords: list[str]) -> tuple[int, list[str]]:
    hits: list[str] = []
    count = 0
    for keyword in keywords:
        if keyword and keyword in text:
            count += text.count(keyword)
            hits.append(keyword)
    return count, sorted(set(hits))


def has_cooccurrence(text: str, keyword_set: list[str]) -> bool:
    return all(keyword in text for keyword in keyword_set if keyword)


def capped_score(hit_count: int, max_score: int, saturate_at: int) -> int:
    if hit_count <= 0:
        return 0
    ratio = min(hit_count, saturate_at) / saturate_at
    return round(max_score * ratio)


def score_work(
    row: dict[str, str], fulltext: str, theme: dict[str, Any], weights: dict[str, int]
) -> dict[str, Any]:
    lineage_text = normalize_text(row.get("story_lineage", ""))
    secondary_text = normalize_text(row.get("theme_secondary", ""))
    tags_text = normalize_text(row.get("tags", ""))
    char_text = normalize_text(row.get("characters", ""))
    synopsis_text = normalize_text(row.get("synopsis", ""))
    summary_text = normalize_text(row.get("summary", ""))

    breakdown: dict[str, int] = {
        "lineage": 0,
        "secondary": 0,
        "tags": 0,
        "characters": 0,
        "synopsis": 0,
        "summary": 0,
        "fulltext_core": 0,
        "fulltext_related": 0,
        "cooccurrence": 0,
        "season": 0,
    }
    reasons: list[str] = []

    lineage_hits, lineage_hit_words = count_keyword_hits(
        lineage_text, theme.get("lineage_keywords", [])
    )
    breakdown["lineage"] = capped_score(lineage_hits, weights["lineage"], 2)
    if lineage_hit_words:
        reasons.append("lineage: " + ", ".join(lineage_hit_words))

    secondary_hits, secondary_hit_words = count_keyword_hits(
        secondary_text, theme.get("secondary_keywords", [])
    )
    breakdown["secondary"] = capped_score(secondary_hits, weights["secondary"], 2)
    if secondary_hit_words:
        reasons.append("secondary: " + ", ".join(secondary_hit_words))

    tag_hits, tag_hit_words = count_keyword_hits(
        tags_text, theme.get("tag_keywords", [])
    )
    breakdown["tags"] = capped_score(tag_hits, weights["tags"], 3)
    if tag_hit_words:
        reasons.append("tags: " + ", ".join(tag_hit_words))

    char_hits, char_hit_words = count_keyword_hits(
        char_text, theme.get("character_keywords", [])
    )
    breakdown["characters"] = capped_score(char_hits, weights["characters"], 2)
    if char_hit_words:
        reasons.append("characters: " + ", ".join(char_hit_words))

    synopsis_hits, synopsis_hit_words = count_keyword_hits(
        synopsis_text, theme.get("synopsis_keywords", [])
    )
    breakdown["synopsis"] = capped_score(synopsis_hits, weights["synopsis"], 4)
    if synopsis_hit_words:
        reasons.append("synopsis: " + ", ".join(synopsis_hit_words))

    summary_hits, summary_hit_words = count_keyword_hits(
        summary_text, theme.get("summary_keywords", [])
    )
    breakdown["summary"] = capped_score(summary_hits, weights["summary"], 3)
    if summary_hit_words:
        reasons.append("summary: " + ", ".join(summary_hit_words))

    if fulltext:
        fulltext_core_hits, core_hit_words = count_keyword_hits(
            fulltext, theme.get("fulltext_core_keywords", [])
        )
        breakdown["fulltext_core"] = capped_score(
            fulltext_core_hits, weights["fulltext_core"], 8
        )
        if core_hit_words:
            reasons.append("fulltext_core: " + ", ".join(core_hit_words))

        fulltext_related_hits, related_hit_words = count_keyword_hits(
            fulltext, theme.get("fulltext_related_keywords", [])
        )
        breakdown["fulltext_related"] = capped_score(
            fulltext_related_hits, weights["fulltext_related"], 6
        )
        if related_hit_words:
            reasons.append("fulltext_related: " + ", ".join(related_hit_words))

        cooccur_count = sum(
            1
            for keyword_set in theme.get("cooccurrence_sets", [])
            if has_cooccurrence(fulltext, keyword_set)
        )
        breakdown["cooccurrence"] = capped_score(
            cooccur_count, weights["cooccurrence"], 2
        )
        if cooccur_count:
            reasons.append(f"cooccurrence: {cooccur_count}組")

        season_hits, season_hit_words = count_keyword_hits(
            fulltext, theme.get("season_keywords", [])
        )
        breakdown["season"] = capped_score(season_hits, weights["season"], 4)
        if season_hit_words:
            reasons.append("season: " + ", ".join(season_hit_words))

    total = sum(breakdown.values())
    has_local_text = bool(fulltext)
    return {
        "title": row.get("title", ""),
        "theme": theme["name"],
        "score_percent": total,
        "score_total": total,
        "score_breakdown": breakdown,
        "reason_hits": reasons,
        "has_local_text": has_local_text,
        "needs_recording": (row.get("has_channel_entry", "") or "").strip().lower()
        != "yes",
        "recording_status": (
            "未朗読・要録音"
            if (row.get("has_channel_entry", "") or "").strip().lower() != "yes"
            else "朗読済み"
        ),
        "fulltext_used": has_local_text,
    }


def main() -> int:
    profiles = load_theme_profiles()
    weights = profiles["weights"]
    texts = load_local_texts()
    override_texts = load_text_overrides()

    results: list[dict[str, Any]] = []
    with CATALOG_CSV.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fulltext = find_local_text(
                row.get("title", ""),
                texts,
                override_texts,
            )
            for theme in profiles["themes"]:
                results.append(score_work(row, fulltext, theme, weights))

    results.sort(
        key=lambda item: (
            str(item["theme"]),
            -int(item["score_percent"]),
            str(item["title"]),
        )
    )

    OUT_JSON.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "theme",
                "title",
                "score_percent",
                "has_local_text",
                "fulltext_used",
                "needs_recording",
                "recording_status",
                "reason_hits",
            ]
        )
        for item in results:
            writer.writerow(
                [
                    item["theme"],
                    item["title"],
                    item["score_percent"],
                    item["has_local_text"],
                    item["fulltext_used"],
                    item["needs_recording"],
                    item["recording_status"],
                    " / ".join(item["reason_hits"]),
                ]
            )

    report_lines = [
        "# 銭形平次捕物控 テーマ一致率レポート",
        "",
        f"- 対象作品数: {len(results) // max(len(profiles['themes']), 1)}",
        f"- テーマ数: {len(profiles['themes'])}",
        f"- ローカル本文ファイル数: {len(texts)}",
        "",
    ]
    for theme in profiles["themes"]:
        theme_name = theme["name"]
        top_items = [item for item in results if item["theme"] == theme_name][:5]
        report_lines.append(f"## {theme_name}")
        report_lines.append("")
        for index, item in enumerate(top_items, start=1):
            report_lines.append(
                f"- {index}. {item['title']} ({item['score_percent']}%) / {item['recording_status']}"
            )
        report_lines.append("")

    OUT_MD.write_text("\n".join(report_lines), encoding="utf-8")

    print(f"Wrote: {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote: {OUT_CSV.relative_to(ROOT)}")
    print(f"Wrote: {OUT_MD.relative_to(ROOT)}")
    print(f"Themes: {len(profiles['themes'])}")
    print(f"Local texts indexed: {len(texts)}")
    print(f"Scores: {len(results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
