#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


GENERIC_THEMES = ["justice", "deduction", "edo_culture", "honor"]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def dump_json(path: Path, data: Any) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    path.write_text(text + "\n", encoding="utf-8")


def extract_episode_title(full_title: str) -> str:
    m = re.search(r"【([^】]+)】", full_title)
    if m:
        return m.group(1).strip()

    # Fallback: last token after whitespace
    parts = re.split(r"[\s　/]+", full_title.strip())
    return parts[-1].strip() if parts else full_title.strip()


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def ensure_backup(path: Path) -> Path:
    base = Path(str(path) + ".bak.meta")
    if not base.exists():
        base.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        return base

    # Don't overwrite; add numeric suffix.
    i = 2
    while True:
        cand = Path(str(path) + f".bak.meta{i}")
        if not cand.exists():
            cand.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            return cand
        i += 1


def normalize_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for x in value:
        if isinstance(x, str):
            s = x.strip()
            if s:
                out.append(s)
        else:
            s = str(x).strip()
            if s:
                out.append(s)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clean bookdata metadata for better theme classification (remove cross-title keywords, clear generic themes)"
    )
    parser.add_argument(
        "--bookdata-dir",
        default="bookdata",
        help="Directory containing bookdata JSON files (default: bookdata)",
    )
    parser.add_argument(
        "--glob",
        default="七之助捕物帳_*.json",
        help='Filename glob inside bookdata-dir (default: "七之助捕物帳_*.json")',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not write files; only print planned changes",
    )
    parser.add_argument(
        "--clear-generic-themes",
        action="store_true",
        help=f"If themes exactly equal {GENERIC_THEMES}, replace with []",
    )

    args = parser.parse_args()

    bookdata_dir = Path(args.bookdata_dir)
    files = sorted(bookdata_dir.glob(args.glob))
    if not files:
        raise SystemExit(f"No files matched: {bookdata_dir / args.glob}")

    # Build episode title set across the corpus
    episode_titles: dict[Path, str] = {}
    all_episode_titles: set[str] = set()
    for path in files:
        book = load_json(path)
        if not isinstance(book, dict):
            continue
        title = str(book.get("title", path.stem))
        ep = extract_episode_title(title)
        episode_titles[path] = ep
        if ep:
            all_episode_titles.add(ep)

    changed = 0
    removed_cross_total = 0
    cleared_themes = 0

    for path in files:
        book = load_json(path)
        if not isinstance(book, dict):
            continue

        ep = episode_titles.get(path, "")

        keywords_before = normalize_str_list(book.get("keywords"))
        themes_before = normalize_str_list(book.get("themes"))

        keywords_after: list[str] = []
        removed_cross: list[str] = []
        for kw in keywords_before:
            if kw in all_episode_titles and kw != ep:
                removed_cross.append(kw)
                continue
            keywords_after.append(kw)
        keywords_after = dedupe_preserve_order(keywords_after)

        themes_after = themes_before
        if args.clear_generic_themes:
            if [t.strip() for t in themes_before] == GENERIC_THEMES:
                themes_after = []

        will_change = (keywords_after != keywords_before) or (
            themes_after != themes_before
        )
        if not will_change:
            continue

        changed += 1
        removed_cross_total += len(set(removed_cross))
        if themes_after != themes_before:
            cleared_themes += 1

        if args.dry_run:
            print(f"DRY: {path}")
            if keywords_after != keywords_before:
                print(
                    f"  keywords: {len(keywords_before)} -> {len(keywords_after)} (removed_cross={sorted(set(removed_cross))[:8]})"
                )
            if themes_after != themes_before:
                print(f"  themes cleared: {themes_before} -> {themes_after}")
            continue

        ensure_backup(path)
        book["keywords"] = keywords_after
        book["themes"] = themes_after
        dump_json(path, book)

    print(f"Files matched: {len(files)}")
    print(f"Files changed: {changed}")
    print(
        f"Cross-title keywords removed (unique per file, summed): {removed_cross_total}"
    )
    print(f"Themes cleared: {cleared_themes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
