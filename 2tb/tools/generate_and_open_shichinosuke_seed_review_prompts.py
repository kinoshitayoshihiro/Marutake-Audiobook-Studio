#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from build_shichinosuke_seed_review_prompts import (
    DEFAULT_FEEDBACK_LOG_PATH,
    DEFAULT_INDEX_PATH,
    DEFAULT_JSONL_PATH,
    DEFAULT_OUTPUT_DIR,
    build_seed_candidates,
    load_catalog,
    resolve_report_path,
    resolve_seed_targets,
    write_outputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="選択した七之助 seed のレビュー prompt を生成して開く"
    )
    parser.add_argument("--catalog", type=Path, default=None)
    parser.add_argument("--seed-key", action="append", default=[])
    parser.add_argument("--seed-title", action="append", default=[])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--include-adopted", action="store_true")
    parser.add_argument("--recorded-only", action="store_true")
    parser.add_argument("--include-no-text", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--index-path", type=Path, default=DEFAULT_INDEX_PATH)
    parser.add_argument("--jsonl-path", type=Path, default=DEFAULT_JSONL_PATH)
    parser.add_argument(
        "--feedback-log-path",
        type=Path,
        default=DEFAULT_FEEDBACK_LOG_PATH,
    )
    parser.add_argument("--no-open", action="store_true")
    return parser.parse_args()


def open_path(path: Path) -> None:
    if path.suffix.lower() in {".md", ".jsonl", ".txt", ".json", ".csv"}:
        subprocess.run(["open", "-a", "TextEdit", str(path)], check=False)
        return
    subprocess.run(["open", str(path)], check=False)


def main() -> int:
    args = parse_args()
    catalog_path = args.catalog
    if catalog_path is None:
        from shichinosuke_catalog_builder_impl import CATALOG_JSON_PATH

        catalog_path = CATALOG_JSON_PATH
    catalog = load_catalog(catalog_path)
    seeds = resolve_seed_targets(catalog, args.seed_key, args.seed_title)
    if not seeds:
        raise SystemExit("No matching seeds found. Use --seed-key or --seed-title.")

    items = []
    for seed in seeds:
        candidates = build_seed_candidates(
            catalog,
            seed,
            limit=max(1, int(args.limit)),
            include_adopted=args.include_adopted,
            recorded_only=args.recorded_only,
            include_no_text=args.include_no_text,
        )
        items.append({"seed": seed, "candidates": candidates})

    write_outputs(
        items,
        output_dir=args.output_dir,
        index_path=args.index_path,
        jsonl_path=args.jsonl_path,
        feedback_log_path=args.feedback_log_path,
    )

    index_path = resolve_report_path(args.index_path)
    jsonl_path = resolve_report_path(args.jsonl_path)
    output_dir = resolve_report_path(args.output_dir)
    feedback_log_path = resolve_report_path(args.feedback_log_path)
    print(f"Wrote: {index_path}")
    print(f"Wrote: {jsonl_path}")
    print(f"Wrote dir: {output_dir}")
    print(f"Feedback log: {feedback_log_path}")
    print(f"Prompts: {len(items)}")

    if not args.no_open:
        for path in [index_path, jsonl_path, feedback_log_path, output_dir]:
            open_path(path)
        print("Opened: index / jsonl / feedback_log / dir")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
