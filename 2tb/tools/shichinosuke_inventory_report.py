#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict

from shichinosuke_catalog_builder_impl import (
    AUDIO_ROOT,
    BOOKDATA_DIR,
    TEXT_DIR,
    VIDEO_ROOT,
    MEDIA_AUDIO_EXTS,
    MEDIA_VIDEO_EXTS,
    TEXT_EXTS,
    canonical_title,
    extract_short_title,
    normalize_text,
)

SOURCE_ROOTS = [
    (TEXT_DIR, TEXT_EXTS),
    (AUDIO_ROOT, MEDIA_AUDIO_EXTS),
    (VIDEO_ROOT, MEDIA_VIDEO_EXTS | TEXT_EXTS),
]

IGNORE_KEYWORDS = {
    "openingcredit",
    "endingcredit",
    "credit",
    "op",
    "ed",
    "sample",
}

GENERIC_CONTAINER_NAMES = {
    "第一巻",
    "第二巻",
    "第三巻",
    "第四巻",
    "第五巻",
    "第六巻",
    "再録",
    "七之助捕物帳",
}


class BookdataEntry(TypedDict):
    title: str
    source: str


class SourceEntry(TypedDict):
    title: str
    paths: list[str]


def collect_bookdata() -> dict[str, BookdataEntry]:
    records: dict[str, BookdataEntry] = {}
    for path in sorted(BOOKDATA_DIR.glob("七之助捕物帳*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        title = str(data.get("title", "")).strip() or path.stem
        short_title = extract_short_title(title, path)
        canonical = canonical_title(short_title)
        key = normalize_text(canonical)
        records[key] = {
            "title": canonical,
            "source": path.name,
        }
    return records


def path_title(path: Path) -> str:
    for parent in path.parents:
        name = parent.name.strip()
        if not name or name in GENERIC_CONTAINER_NAMES:
            continue
        match = re.match(r"^\d+\.\s*(.+)$", name)
        if match:
            return canonical_title(match.group(1).strip())

    stem = path.stem
    stem = stem.replace("納言恭平著", "").replace("納言恭平", "")
    stem = stem.replace("七之助捕物帳", "").strip(" _-　")
    if not stem:
        stem = path.stem
    return canonical_title(stem)


def should_skip(path: Path) -> bool:
    name = normalize_text(path.name)
    return any(keyword in name for keyword in IGNORE_KEYWORDS)


def collect_sources() -> dict[str, SourceEntry]:
    records: dict[str, SourceEntry] = {}
    for root, extensions in SOURCE_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            if path.name.startswith(".") or should_skip(path):
                continue
            title = path_title(path)
            key = normalize_text(title)
            if not key:
                continue
            entry = records.setdefault(key, {"title": title, "paths": []})
            entry["paths"].append(str(path))
    return records


def main() -> int:
    bookdata = collect_bookdata()
    sources = collect_sources()

    only_sources = sorted(set(sources) - set(bookdata))
    only_bookdata = sorted(set(bookdata) - set(sources))
    all_titles = sorted(set(bookdata) | set(sources))

    print(f"bookdata_count: {len(bookdata)}")
    print(f"source_count: {len(sources)}")
    print(f"union_count: {len(all_titles)}")
    print()

    print("[source_only]")
    for key in only_sources:
        info = sources[key]
        print(f"- {info['title']}")
        for path in info["paths"][:5]:
            print(f"    {path}")
    if not only_sources:
        print("- なし")
    print()

    print("[bookdata_only]")
    for key in only_bookdata:
        book_entry = bookdata[key]
        print(f"- {book_entry['title']} :: {book_entry['source']}")
    if not only_bookdata:
        print("- なし")
    print()

    print("[all_titles]")
    for key in all_titles:
        if key in bookdata:
            title = bookdata[key]["title"]
        else:
            title = sources[key]["title"]
        flags: list[str] = []
        if key in bookdata:
            flags.append("bookdata")
        if key in sources:
            flags.append("source")
        print(f"- {title} ({', '.join(flags)})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
