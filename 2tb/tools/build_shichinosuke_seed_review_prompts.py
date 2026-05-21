#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from shichinosuke_catalog_builder_impl import CATALOG_JSON_PATH, ROOT

DEFAULT_OUTPUT_DIR = ROOT / "reports" / "shichinosuke_seed_review_prompts_selected"
DEFAULT_INDEX_PATH = ROOT / "reports" / "shichinosuke_seed_review_prompts_selected.md"
DEFAULT_JSONL_PATH = ROOT / "reports" / "shichinosuke_seed_review_prompts_selected.jsonl"
DEFAULT_FEEDBACK_LOG_PATH = ROOT / "reports" / "shichinosuke_seed_feedback_log.csv"

FEEDBACK_LOG_HEADERS = [
    "seed_title",
    "candidate_title",
    "decision",
    "fit_score",
    "reason_short",
    "reviewer",
    "reviewed_at",
    "candidate_rank",
    "candidate_score",
    "shared_minor",
    "shared_themes",
    "shared_keywords",
    "shared_characters",
    "has_text",
    "has_audio",
    "has_video",
]


def resolve_report_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="七之助の核作品レビュー prompt を生成する"
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=CATALOG_JSON_PATH,
        help="works catalog JSON のパス",
    )
    parser.add_argument(
        "--seed-key",
        action="append",
        default=[],
        help="対象 seed の work key（複数指定可）",
    )
    parser.add_argument(
        "--seed-title",
        action="append",
        default=[],
        help="対象 seed のタイトルまたは短縮タイトル（複数指定可）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="seed ごとの候補件数",
    )
    parser.add_argument(
        "--include-adopted",
        action="store_true",
        help="採用済み総集編の収録作も候補に含める",
    )
    parser.add_argument(
        "--recorded-only",
        action="store_true",
        help="MP3確認済み作品だけを候補にする",
    )
    parser.add_argument(
        "--include-no-text",
        action="store_true",
        help="本文なし作品も候補に含める",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="個別 prompt を書くディレクトリ",
    )
    parser.add_argument(
        "--index-path",
        type=Path,
        default=DEFAULT_INDEX_PATH,
        help="生成一覧 Markdown の出力先",
    )
    parser.add_argument(
        "--jsonl-path",
        type=Path,
        default=DEFAULT_JSONL_PATH,
        help="LLM 連携向け JSONL の出力先",
    )
    parser.add_argument(
        "--feedback-log-path",
        type=Path,
        default=DEFAULT_FEEDBACK_LOG_PATH,
        help="フィードバックログ CSV の出力先",
    )
    return parser.parse_args()


def load_catalog(path: Path) -> dict[str, Any]:
    return json.loads(resolve_report_path(path).read_text(encoding="utf-8"))


def normalize_text(value: str) -> str:
    return "".join(str(value or "").lower().split())


def sanitize_filename(value: str) -> str:
    invalid = str.maketrans(
        {
            "/": "_",
            "\\": "_",
            ":": "_",
            "*": "_",
            "?": "_",
            '"': "_",
            "<": "_",
            ">": "_",
            "|": "_",
            " ": "_",
        }
    )
    return value.translate(invalid)


def uniq_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        ordered.append(cleaned)
    return ordered


def format_list(items: list[str], fallback: str = "なし") -> str:
    cleaned = uniq_strings([str(item).strip() for item in items if str(item).strip()])
    return " / ".join(cleaned) if cleaned else fallback


def work_tag_values(work: dict[str, Any]) -> list[str]:
    return uniq_strings(
        [
            str(work.get("major_category", "")).strip(),
            *[str(item).strip() for item in work.get("minor_categories", [])],
            *[str(item).strip() for item in work.get("themes", [])],
            *[str(item).strip() for item in work.get("keywords", [])[:12]],
        ]
    )


def work_character_values(work: dict[str, Any]) -> list[str]:
    return uniq_strings([str(item).strip() for item in work.get("characters", [])])


def intersection_values(left: list[str], right: list[str]) -> list[str]:
    right_set = {str(item).strip() for item in right if str(item).strip()}
    return uniq_strings([item for item in left if item in right_set])


def build_adopted_title_set(catalog: dict[str, Any]) -> set[str]:
    adopted: set[str] = set()
    works_by_key = {
        str(work.get("key", "")): work for work in catalog.get("works", []) if work.get("key")
    }
    for bundle in catalog.get("adopted_bundles", []):
        for entry in bundle.get("works", []):
            work = works_by_key.get(str(entry.get("key", "")), {})
            candidates = [
                entry.get("title", ""),
                entry.get("short_title", ""),
                work.get("title", ""),
                work.get("short_title", ""),
                work.get("canonical_title", ""),
            ]
            for value in candidates:
                normalized = normalize_text(str(value))
                if normalized:
                    adopted.add(normalized)
    return adopted


def resolve_seed_targets(catalog: dict[str, Any], seed_keys: list[str], seed_titles: list[str]) -> list[dict[str, Any]]:
    works = catalog.get("works", [])
    works_by_key = {str(work.get("key", "")): work for work in works if work.get("key")}
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    for seed_key in seed_keys:
        work = works_by_key.get(seed_key)
        if work and seed_key not in seen:
            selected.append(work)
            seen.add(seed_key)

    normalized_title_queries = [normalize_text(value) for value in seed_titles if normalize_text(value)]
    for query in normalized_title_queries:
        for work in works:
            candidates = [
                work.get("title", ""),
                work.get("short_title", ""),
                work.get("canonical_title", ""),
            ]
            if any(query == normalize_text(candidate) for candidate in candidates):
                key = str(work.get("key", ""))
                if key and key not in seen:
                    selected.append(work)
                    seen.add(key)
                break
        else:
            for work in works:
                candidates = [
                    work.get("title", ""),
                    work.get("short_title", ""),
                    work.get("canonical_title", ""),
                ]
                if any(query in normalize_text(candidate) for candidate in candidates):
                    key = str(work.get("key", ""))
                    if key and key not in seen:
                        selected.append(work)
                        seen.add(key)
                    break
    return selected


def score_seed_candidate(seed: dict[str, Any], work: dict[str, Any]) -> dict[str, Any]:
    shared_minor = intersection_values(
        [str(item).strip() for item in seed.get("minor_categories", [])],
        [str(item).strip() for item in work.get("minor_categories", [])],
    )
    shared_themes = intersection_values(
        [str(item).strip() for item in seed.get("themes", [])],
        [str(item).strip() for item in work.get("themes", [])],
    )
    shared_keywords = [
        item
        for item in intersection_values(work_tag_values(seed), work_tag_values(work))
        if item not in shared_themes and item != seed.get("major_category")
    ]
    shared_characters = intersection_values(
        work_character_values(seed),
        work_character_values(work),
    )
    chapter_gap = abs(int(seed.get("chapter_count") or 0) - int(work.get("chapter_count") or 0))
    reasons: list[str] = []
    score = 0

    if seed.get("major_category") and seed.get("major_category") == work.get("major_category"):
        score += 28
        reasons.append(f"主分類一致: {seed.get('major_category')}")
    if shared_minor:
        score += min(24, len(shared_minor) * 8)
        reasons.append(f"小分類一致: {format_list(shared_minor)}")
    if shared_themes:
        score += min(24, len(shared_themes) * 6)
        reasons.append(f"themes一致: {format_list(shared_themes)}")
    if shared_keywords:
        score += min(16, len(shared_keywords) * 4)
        reasons.append(f"語彙接点: {format_list(shared_keywords[:4])}")
    if shared_characters:
        score += min(12, len(shared_characters) * 4)
        reasons.append(f"人物接点: {format_list(shared_characters)}")
    if chapter_gap <= 1:
        score += 6
        reasons.append("章立ての重さが近い")
    if work.get("audio_paths"):
        score += 8
        reasons.append("MP3確認済み")
    if work.get("video_paths"):
        score += 3
    if work.get("text_paths"):
        score += 6
        reasons.append("本文あり")

    return {
        "work": work,
        "score": score,
        "shared_minor": shared_minor,
        "shared_themes": shared_themes,
        "shared_keywords": shared_keywords,
        "shared_characters": shared_characters,
        "reasons": reasons,
    }


def build_seed_candidates(
    catalog: dict[str, Any],
    seed: dict[str, Any],
    *,
    limit: int,
    include_adopted: bool,
    recorded_only: bool,
    include_no_text: bool,
) -> list[dict[str, Any]]:
    works = catalog.get("works", [])
    adopted_titles = build_adopted_title_set(catalog)
    seed_key = str(seed.get("key", ""))
    candidates: list[dict[str, Any]] = []

    for work in works:
        if str(work.get("key", "")) == seed_key:
            continue
        if not include_adopted:
            normalized_titles = [
                normalize_text(work.get("title", "")),
                normalize_text(work.get("short_title", "")),
                normalize_text(work.get("canonical_title", "")),
            ]
            if any(title in adopted_titles for title in normalized_titles if title):
                continue
        if recorded_only and not work.get("audio_paths"):
            continue
        if not include_no_text and not work.get("text_paths"):
            continue
        scored = score_seed_candidate(seed, work)
        if scored["score"] <= 0:
            continue
        candidates.append(scored)

    candidates.sort(
        key=lambda entry: (
            -int(entry["score"]),
            -(len(entry["work"].get("audio_paths", []))),
            int(entry["work"].get("sort_order") or 0),
        )
    )
    return candidates[:limit]


def build_prompt_text(
    seed: dict[str, Any],
    candidates: list[dict[str, Any]],
    *,
    feedback_log_path: Path,
) -> str:
    candidate_sections: list[str] = []
    for index, entry in enumerate(candidates, start=1):
        work = entry["work"]
        candidate_sections.extend(
            [
                f"### 候補{index}",
                f"- タイトル: {work.get('title', '')}",
                f"- 短縮タイトル: {work.get('short_title', '')}",
                f"- 大分類: {work.get('major_category', '')}",
                f"- 小分類: {format_list(work.get('minor_categories', []), 'なし')}",
                f"- themes: {format_list(work.get('themes', []), 'なし')}",
                f"- characters: {format_list(work.get('characters', []), 'なし')}",
                f"- 一致スコア: {entry.get('score', 0)}",
                f"- 一致理由: {format_list(entry.get('reasons', []), '補助根拠なし')}",
                f"- 本文参照: {format_list(work.get('text_paths', []), '本文パスなし')}",
                f"- 音声参照: {format_list(work.get('audio_paths', [])[:3], 'MP3なし')}",
                f"- synopsis: {work.get('synopsis', '') or '要約未整備'}",
                "",
            ]
        )

    return "\n".join(
        [
            f"# 七之助 核作品レビュー: {seed.get('short_title') or seed.get('title', '')}",
            "",
            "## 役割",
            "あなたは七之助捕物帳シリーズの編集者です。",
            "核作品を中心に、総集編として相性の良い相方候補を見極めてください。",
            "",
            "## 核作品",
            f"- タイトル: {seed.get('title', '')}",
            f"- 短縮タイトル: {seed.get('short_title', '')}",
            f"- 大分類: {seed.get('major_category', '')}",
            f"- 小分類: {format_list(seed.get('minor_categories', []), 'なし')}",
            f"- themes: {format_list(seed.get('themes', []), 'なし')}",
            f"- characters: {format_list(seed.get('characters', []), 'なし')}",
            f"- 本文参照: {format_list(seed.get('text_paths', []), '本文パスなし')}",
            f"- 音声参照: {format_list(seed.get('audio_paths', [])[:3], 'MP3なし')}",
            f"- synopsis: {seed.get('synopsis', '') or '要約未整備'}",
            "",
            "## 審査ルール",
            "- 単なる類似度ではなく、総集編としての流れとバランスを重視する。",
            "- 事件の型、空気感、人物の重なり、結末の後味、並び順の自然さを見る。",
            "- 核作品のテーマをぼかさない構成を優先する。",
            "- 不採用候補がある場合は理由を短く残す。",
            "",
            "## 出力してほしいこと",
            "- 最適な3本構成",
            "- 次点2〜3本",
            "- 不採用寄り候補と理由",
            "- 並び順案",
            "- 総集編タイトル案を3案",
            "- 採否結果は feedback_log に追記する",
            f"- feedback_log: {feedback_log_path}",
            "",
            "## 出力形式",
            "以下のJSONだけを返してください。",
            "",
            "```json",
            "{",
            f'  "seed_title": "{seed.get("short_title") or seed.get("title", "")}",',
            '  "decision": "approve | revise",',
            '  "top_three": ["...", "...", "..."],',
            '  "runner_up": ["...", "..."],',
            '  "rejects": [{"title": "...", "reason": "..."}],',
            '  "ordering": ["...", "...", "..."],',
            '  "title_ideas": ["...", "...", "..."],',
            '  "summary": "2〜5文で総評",',
            '  "feedback_log_updates": [',
            '    {"candidate_title": "...", "decision": "採用 | 次点 | 不採用", "fit_score": 1, "reason_short": "..."}',
            "  ]",
            "}",
            "```",
            "",
            "## 候補一覧",
            *candidate_sections,
        ]
    )


def build_jsonl_record(
    seed: dict[str, Any],
    candidates: list[dict[str, Any]],
    prompt_text: str,
) -> dict[str, Any]:
    return {
        "seed_key": seed.get("key", ""),
        "seed_title": seed.get("title", ""),
        "seed_short_title": seed.get("short_title", ""),
        "candidate_count": len(candidates),
        "prompt": prompt_text,
    }


def ensure_feedback_log(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_rows: list[dict[str, str]] = []
    existing_pairs: set[tuple[str, str]] = set()
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                existing_rows.append(row)
                existing_pairs.add(
                    (
                        str(row.get("seed_title", "")).strip(),
                        str(row.get("candidate_title", "")).strip(),
                    )
                )

    for item in items:
        seed = item["seed"]
        seed_title = str(seed.get("short_title") or seed.get("title", "")).strip()
        for rank, candidate in enumerate(item["candidates"], start=1):
            work = candidate["work"]
            candidate_title = str(
                work.get("short_title") or work.get("title", "")
            ).strip()
            pair = (seed_title, candidate_title)
            if pair in existing_pairs:
                continue
            existing_pairs.add(pair)
            existing_rows.append(
                {
                    "seed_title": seed_title,
                    "candidate_title": candidate_title,
                    "decision": "",
                    "fit_score": "",
                    "reason_short": "",
                    "reviewer": "",
                    "reviewed_at": "",
                    "candidate_rank": str(rank),
                    "candidate_score": str(candidate.get("score", 0)),
                    "shared_minor": "|".join(candidate.get("shared_minor", [])),
                    "shared_themes": "|".join(candidate.get("shared_themes", [])),
                    "shared_keywords": "|".join(candidate.get("shared_keywords", [])),
                    "shared_characters": "|".join(candidate.get("shared_characters", [])),
                    "has_text": str(int(bool(work.get("text_paths")))),
                    "has_audio": str(int(bool(work.get("audio_paths")))),
                    "has_video": str(int(bool(work.get("video_paths")))),
                }
            )

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FEEDBACK_LOG_HEADERS)
        writer.writeheader()
        writer.writerows(existing_rows)


def write_outputs(
    items: list[dict[str, Any]],
    *,
    output_dir: Path,
    index_path: Path,
    jsonl_path: Path,
    feedback_log_path: Path,
) -> None:
    output_dir = resolve_report_path(output_dir)
    index_path = resolve_report_path(index_path)
    jsonl_path = resolve_report_path(jsonl_path)
    feedback_log_path = resolve_report_path(feedback_log_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    index_lines = [
        "# 七之助 核作品レビュー prompt 一覧",
        "",
        f"- 件数: {len(items)}",
        f"- 出力ディレクトリ: {output_dir.relative_to(ROOT).as_posix()}",
        f"- feedback_log: {feedback_log_path.relative_to(ROOT).as_posix()}",
        "",
    ]
    jsonl_lines: list[str] = []

    for item in items:
        seed = item["seed"]
        candidates = item["candidates"]
        file_name = sanitize_filename(
            f"seed_{seed.get('short_title') or seed.get('title') or seed.get('key')}"
        )
        prompt_path = output_dir / f"{file_name}.md"
        prompt_text = build_prompt_text(
            seed,
            candidates,
            feedback_log_path=feedback_log_path,
        )
        prompt_path.write_text(prompt_text, encoding="utf-8")
        index_lines.extend(
            [
                f"## {seed.get('short_title') or seed.get('title', '')}",
                "",
                f"- seed_key: {seed.get('key', '')}",
                f"- 候補件数: {len(candidates)}",
                f"- ファイル: {prompt_path.relative_to(ROOT).as_posix()}",
                "",
            ]
        )
        jsonl_lines.append(
            json.dumps(
                build_jsonl_record(seed, candidates, prompt_text),
                ensure_ascii=False,
            )
        )

    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    jsonl_path.write_text("\n".join(jsonl_lines), encoding="utf-8")
    ensure_feedback_log(feedback_log_path, items)


def main() -> int:
    args = parse_args()
    catalog = load_catalog(args.catalog)
    seeds = resolve_seed_targets(catalog, args.seed_key, args.seed_title)
    if not seeds:
        raise SystemExit("No matching seeds found. Use --seed-key or --seed-title.")

    output_items: list[dict[str, Any]] = []
    for seed in seeds:
        candidates = build_seed_candidates(
            catalog,
            seed,
            limit=max(1, int(args.limit)),
            include_adopted=args.include_adopted,
            recorded_only=args.recorded_only,
            include_no_text=args.include_no_text,
        )
        output_items.append({"seed": seed, "candidates": candidates})

    write_outputs(
        output_items,
        output_dir=args.output_dir,
        index_path=args.index_path,
        jsonl_path=args.jsonl_path,
        feedback_log_path=args.feedback_log_path,
    )

    print(f"Wrote: {resolve_report_path(args.index_path).relative_to(ROOT)}")
    print(f"Wrote: {resolve_report_path(args.jsonl_path).relative_to(ROOT)}")
    print(f"Wrote dir: {resolve_report_path(args.output_dir).relative_to(ROOT)}")
    print(
        f"Feedback log: {resolve_report_path(args.feedback_log_path).relative_to(ROOT)}"
    )
    print(f"Prompts: {len(output_items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
