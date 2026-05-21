#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from string import Template
from typing import Any

from zenigata_search_page_builder_impl import (
    CSV_PATH,
    ROOT,
    SYNOPSIS_LLM_JSON_PATH,
    build_extractive_synopsis,
    clean_character_names,
    has_synopsis_placeholder,
    load_text_override_map,
    needs_summary_refresh,
    normalize_theme_list,
    preferred_local_text_path,
    read_text_best_effort,
    split_pipe,
    split_slash,
    strip_aozora_text,
)

DEFAULT_OUTPUT_DIR = ROOT / "reports" / "zenigata_synopsis_prompts"
DEFAULT_INDEX_PATH = ROOT / "reports" / "zenigata_synopsis_prompts.md"
DEFAULT_JSONL_PATH = ROOT / "reports" / "zenigata_synopsis_prompts.jsonl"
DEFAULT_TEMPLATE_PATH = ROOT / "prompts" / "zenigata_synopsis_enrichment_prompt_ja.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="銭形平次 synopsis 補筆用の LLM prompt / JSONL を生成する"
    )
    parser.add_argument("--catalog", type=Path, default=CSV_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--jsonl-path", type=Path, default=DEFAULT_JSONL_PATH)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE_PATH)
    parser.add_argument("--llm-json", type=Path, default=SYNOPSIS_LLM_JSON_PATH)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--title", action="append", default=[])
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_existing_titles(path: Path) -> set[str]:
    target = resolve_path(path)
    if not target.exists():
        return set()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    source = raw.get("items", []) if isinstance(raw, dict) else raw
    if not isinstance(source, list):
        return set()
    titles: set[str] = set()
    for entry in source:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "") or "").strip()
        synopsis = str(entry.get("synopsis", "") or "").strip()
        if title and synopsis:
            titles.add(title)
    return titles


def needs_enrichment(row: dict[str, str], existing_titles: set[str]) -> bool:
    title = str(row.get("title", "") or "").strip()
    if not title or title in existing_titles:
        return False
    synopsis = str(row.get("synopsis", "") or "").strip()
    summary = str(row.get("summary", "") or "").strip()
    return has_synopsis_placeholder(synopsis) or needs_summary_refresh(summary)


def build_excerpt(text_path: str) -> tuple[str, dict[str, Any]]:
    if not text_path:
        return "", {}
    raw = read_text_best_effort(text_path)
    if not raw:
        return "", {}
    title = Path(text_path).stem.replace("銭形平次捕物控_", "")
    cleaned = strip_aozora_text(raw, title)
    filtered_lines: list[str] = []
    for line in cleaned.splitlines():
        compact = re.sub(r"\s+", " ", line).strip()
        if not compact:
            continue
        if any(marker in compact for marker in ("初出", "底本", "入力", "校正")):
            continue
        if re.search(r"(出版社|文藝春秋|潮出版社|発行)", compact):
            continue
        if re.search(r"^[0-9０-９]{4}.*年.*月.*日", compact):
            continue
        filtered_lines.append(line.rstrip())
    excerpt = "\n".join(filtered_lines).strip()[:12000].strip()
    if not excerpt:
        excerpt = cleaned[:12000].strip()
    if len(cleaned) > 12000:
        excerpt += "\n\n[...以下省略... ]"
    draft = build_extractive_synopsis(title, cleaned)
    return excerpt, draft


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


def prompt_payload(
    row: dict[str, str],
    text_override_map: dict[str, dict[str, Any]],
) -> dict[str, str]:
    source_paths = split_pipe(row.get("source_paths", ""))
    title = str(row.get("title", "") or "").strip()
    text_path = preferred_local_text_path(title, source_paths, text_override_map)
    override = text_override_map.get(title, {})
    excerpt, draft = build_excerpt(text_path)
    return {
        "title": title,
        "publication_years": str(row.get("publication_years", "") or "").strip(),
        "magazines": str(row.get("magazines", "") or "").strip(),
        "story_lineage": str(row.get("story_lineage", "") or "").strip(),
        "theme_secondary": " / ".join(
            normalize_theme_list(split_slash(row.get("theme_secondary", "")))
        )
        or "未整理",
        "tags": " / ".join(split_slash(row.get("tags", ""))[:10]) or "未整理",
        "characters": " / ".join(
            clean_character_names(split_slash(row.get("characters", "")))[:8]
        )
        or "未整理",
        "current_synopsis": str(row.get("synopsis", "") or "").strip() or "未設定",
        "current_summary": str(row.get("summary", "") or "").strip() or "未設定",
        "draft_synopsis": str(draft.get("synopsis", "") or "").strip() or "なし",
        "draft_summary": str(draft.get("summary", "") or "").strip() or "なし",
        "text_path": text_path or "なし",
        "text_source": str(override.get("source", "catalog") or "catalog"),
        "editorial_notes": (
            " / ".join(override.get("editorial_notes", []))
            if isinstance(override.get("editorial_notes"), list)
            else "なし"
        ),
        "bookdata_path": next(
            (path for path in source_paths if str(path).startswith("bookdata/")),
            "",
        )
        or "なし",
        "excerpt": excerpt or "本文抜粋を取得できませんでした。",
    }


def load_rows(catalog_path: Path) -> list[dict[str, str]]:
    with resolve_path(catalog_path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_prompt_text(template_text: str, payload: dict[str, str]) -> str:
    return Template(template_text).safe_substitute(payload)


def build_jsonl_record(payload: dict[str, str], prompt_text: str) -> dict[str, Any]:
    title = payload["title"]
    return {
        "custom_id": f"zenigata-synopsis-{sanitize_filename(title)}",
        "title": title,
        "publication_years": payload["publication_years"],
        "magazines": payload["magazines"],
        "text_path": payload["text_path"],
        "prompt": prompt_text,
    }


def main() -> int:
    args = parse_args()
    output_dir = resolve_path(args.output_dir)
    index_path = resolve_path(args.index_path)
    jsonl_path = resolve_path(args.jsonl_path)
    template_path = resolve_path(args.template)
    output_dir.mkdir(parents=True, exist_ok=True)

    template_text = template_path.read_text(encoding="utf-8")
    existing_titles = load_existing_titles(args.llm_json)
    text_override_map = load_text_override_map()
    selected_titles = {str(title).strip() for title in args.title if str(title).strip()}

    rows = []
    for row in load_rows(args.catalog):
        if selected_titles and str(row.get("title", "")).strip() not in selected_titles:
            continue
        if needs_enrichment(row, existing_titles):
            rows.append(row)
    if args.limit > 0:
        rows = rows[: args.limit]

    index_lines = [
        "# 銭形平次 synopsis 補筆 prompt 一覧",
        "",
        f"- 件数: {len(rows)}",
        f"- 出力先: {output_dir.relative_to(ROOT).as_posix()}",
        f"- JSONL: {jsonl_path.relative_to(ROOT).as_posix()}",
        "",
    ]
    jsonl_lines: list[str] = []

    for row in rows:
        payload = prompt_payload(row, text_override_map)
        prompt_text = build_prompt_text(template_text, payload)
        file_name = sanitize_filename(payload["title"])
        prompt_path = output_dir / f"{file_name}.md"
        prompt_path.write_text(prompt_text, encoding="utf-8")
        index_lines.extend(
            [
                f"## {payload['title']}",
                "",
                f"- 年代: {payload['publication_years']}",
                f"- 掲載誌: {payload['magazines']}",
                f"- 系統: {payload['story_lineage']}",
                f"- prompt: {prompt_path.relative_to(ROOT).as_posix()}",
                "",
            ]
        )
        jsonl_lines.append(
            json.dumps(build_jsonl_record(payload, prompt_text), ensure_ascii=False)
        )

    index_path.write_text("\n".join(index_lines), encoding="utf-8")
    jsonl_path.write_text("\n".join(jsonl_lines), encoding="utf-8")
    print(f"Wrote: {index_path.relative_to(ROOT)}")
    print(f"Wrote: {jsonl_path.relative_to(ROOT)}")
    print(f"Wrote dir: {output_dir.relative_to(ROOT)}")
    print(f"Prompts: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
