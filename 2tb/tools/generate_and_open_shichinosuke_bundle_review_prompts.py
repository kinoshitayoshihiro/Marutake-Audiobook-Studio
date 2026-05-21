#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import cast

from build_shichinosuke_bundle_review_prompts import (
    load_review_queue,
    select_items,
    write_outputs,
)
from shichinosuke_catalog_builder_impl import BUNDLE_REVIEW_QUEUE_PATH, ROOT

DEFAULT_OUTPUT_DIR = ROOT / "reports" / "shichinosuke_bundle_review_prompts_selected"
DEFAULT_INDEX_PATH = ROOT / "reports" / "shichinosuke_bundle_review_prompts_selected.md"
DEFAULT_JSONL_PATH = (
    ROOT / "reports" / "shichinosuke_bundle_review_prompts_selected.jsonl"
)


def resolve_report_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="選択した七之助 bundle の審査 prompt を生成して結果を開く"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=BUNDLE_REVIEW_QUEUE_PATH,
        help="bundle review queue JSON のパス",
    )
    parser.add_argument(
        "--bundle-id",
        action="append",
        default=[],
        help="対象 bundle_id（複数指定可）",
    )
    parser.add_argument(
        "--bundle-ids-text",
        default="",
        help="bundle_id 一覧の生テキスト。JSON配列/改行/カンマ区切り対応",
    )
    parser.add_argument(
        "--bundle-group",
        choices=["classification", "sequential", "all"],
        default="all",
        help="対象 bundle group",
    )
    parser.add_argument(
        "--tier",
        choices=["primary", "alternate", "all"],
        default="all",
        help="対象 candidate tier",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="先頭から何件生成するか。0 は無制限",
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
        "--no-open",
        action="store_true",
        help="生成後に Finder / 既定アプリで開かない",
    )
    return parser.parse_args()


def open_path(path: Path) -> None:
    if path.suffix.lower() in {".md", ".jsonl", ".txt", ".json"}:
        subprocess.run(["open", "-a", "TextEdit", str(path)], check=False)
        return
    subprocess.run(["open", str(path)], check=False)


def parse_bundle_ids_text(raw: str) -> list[str]:
    text = raw.strip()
    if not text:
        return []
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        value = None
    if isinstance(value, list):
        parsed_ids: list[str] = []
        value_list = cast(list[object], value)
        for item in value_list:
            candidate = str(item).strip()
            if candidate:
                parsed_ids.append(candidate)
        return parsed_ids

    normalized = (
        text.replace("\r", "\n")
        .replace("[", " ")
        .replace("]", " ")
        .replace('"', " ")
        .replace("'", " ")
        .replace(",", "\n")
    )
    return [item.strip() for item in normalized.splitlines() if item.strip()]


def main() -> int:
    args = parse_args()
    items = load_review_queue(args.input)
    output_dir = resolve_report_path(args.output_dir)
    index_path = resolve_report_path(args.index_path)
    jsonl_path = resolve_report_path(args.jsonl_path)
    bundle_ids: list[str] = [
        *args.bundle_id,
        *parse_bundle_ids_text(args.bundle_ids_text),
    ]
    selected = select_items(
        items,
        bundle_ids=bundle_ids,
        bundle_group=args.bundle_group,
        tier=args.tier,
        limit=args.limit,
    )
    write_outputs(
        selected,
        output_dir=output_dir,
        index_path=index_path,
        jsonl_path=jsonl_path,
    )
    print(f"Wrote: {index_path.relative_to(ROOT)}")
    print(f"Wrote: {jsonl_path.relative_to(ROOT)}")
    print(f"Wrote dir: {output_dir.relative_to(ROOT)}")
    print(f"Prompts: {len(selected)}")

    if not args.no_open:
        for path in [index_path, jsonl_path, output_dir]:
            open_path(path)
        print("Opened: index / jsonl / dir")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
