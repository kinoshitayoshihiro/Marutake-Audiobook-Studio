#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Rule:
    label: str
    patterns: list[str]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_list_str(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value]
    return []


def build_search_text(
    book: dict[str, Any], *, use_content: bool, content_max_chars: int
) -> str:
    """Build a conservative search text for theme classification.

    Note: Some datasets include a long list of *other volumes' titles* in `keywords`.
    Using that directly causes cascading false positives (e.g., matching "幽霊" everywhere).
    So we prioritize this work's own title and synopsis, and only keep short, generic keywords.
    """

    parts: list[str] = []

    title = book.get("title")
    episode_title: str | None = None
    if isinstance(title, str) and title.strip():
        parts.append(title)
        # Extract bracketed episode title: "【...】" if present.
        try:
            import re

            m = re.search(r"【([^】]+)】", title)
            if m:
                episode_title = m.group(1)
                parts.append(episode_title)
        except Exception:
            pass

    synopsis = book.get("synopsis")
    if isinstance(synopsis, str) and synopsis.strip():
        parts.append(synopsis)

    for key in ("sub_genre", "japanese_genre", "genre"):
        v = book.get(key)
        if isinstance(v, str) and v.strip():
            parts.append(v)

    # Keep only generic keywords (allowlist) and the current episode title.
    # Some datasets put many other volumes' titles into `keywords`, so we must avoid using them.
    generic_allow = {
        "捕物帳",
        "江戸",
        "推理",
        "時代劇",
        "人情",
        "怪談",
        "怪奇",
    }
    for kw in safe_list_str(book.get("keywords")):
        s = str(kw).strip()
        if not s:
            continue
        if s in generic_allow:
            parts.append(s)
        elif episode_title and s == episode_title:
            parts.append(s)

    for key in ("themes", "emotions"):
        parts.extend(safe_list_str(book.get(key)))

    if use_content and content_max_chars > 0:
        chapters = book.get("chapters")
        if isinstance(chapters, list):
            remaining = content_max_chars
            for ch in chapters:
                if remaining <= 0:
                    break
                if not isinstance(ch, dict):
                    continue
                c = ch.get("content")
                if not isinstance(c, str) or not c:
                    continue
                snippet = c[:remaining]
                parts.append(snippet)
                remaining -= len(snippet)

    # Normalize a bit: lowercase for latin words, keep Japanese as-is.
    return "\n".join(parts).lower()


def classify(
    book: dict[str, Any],
    rules: list[Rule],
    default_label: str,
    *,
    use_content: bool,
    content_max_chars: int,
) -> tuple[str, list[str]]:
    text = build_search_text(
        book, use_content=use_content, content_max_chars=content_max_chars
    )

    best_label = default_label
    best_score = 0
    best_hits: list[str] = []

    for rule in rules:
        hits = [p for p in rule.patterns if p and p.lower() in text]
        score = len(hits)
        if score > best_score:
            best_label = rule.label
            best_score = score
            best_hits = hits

    return best_label, best_hits


def load_rules(rules_path: Path) -> tuple[list[Rule], str]:
    raw = load_json(rules_path)
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid rules JSON (expected object): {rules_path}")

    default_label = raw.get("default_label", "その他")
    labels = raw.get("labels")
    if not isinstance(labels, list):
        raise ValueError(f"Invalid rules JSON (expected labels list): {rules_path}")

    rules: list[Rule] = []
    for item in labels:
        if not isinstance(item, dict):
            continue
        label = item.get("label")
        patterns = item.get("patterns")
        if not isinstance(label, str) or not label.strip():
            continue
        if not isinstance(patterns, list):
            patterns = []
        rules.append(
            Rule(label=label, patterns=[str(p) for p in patterns if str(p).strip()])
        )

    return rules, str(default_label)


def extract_sort_key(path: Path, title: str) -> tuple[int, str]:
    # Try to sort by volume number if present: "第20巻" etc.
    import re

    m = re.search(r"第\s*(\d+)\s*巻", title)
    if not m:
        m = re.search(r"第\s*(\d+)\s*巻", path.name)

    vol = int(m.group(1)) if m else 10**9
    return (vol, title)


def chunked(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def interleave_bundles(
    *,
    ordered_labels: list[str],
    by_label: dict[str, list[dict[str, Any]]],
    per_group: int,
) -> list[dict[str, Any]]:
    """Create bundles but interleave labels to avoid long runs of the same label."""

    chunks_by_label: dict[str, list[list[dict[str, Any]]]] = {}
    max_chunks = 0
    for label in ordered_labels:
        items = by_label.get(label, [])
        if not items:
            continue
        chunks = chunked(items, per_group)
        chunks_by_label[label] = chunks
        if len(chunks) > max_chunks:
            max_chunks = len(chunks)

    bundles: list[dict[str, Any]] = []
    for idx in range(1, max_chunks + 1):
        for label in ordered_labels:
            chunks = chunks_by_label.get(label)
            if not chunks:
                continue
            if idx - 1 >= len(chunks):
                continue
            bundles.append(
                {
                    "bundle_label": label,
                    "bundle_index": idx,
                    "works": chunks[idx - 1],
                }
            )

    return bundles


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Group bookdata JSON files into theme-based bundles (e.g., 3 works per theme)"
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
        "--rules",
        default="tools/theme_rules.json",
        help="Rules JSON path (default: tools/theme_rules.json)",
    )
    parser.add_argument(
        "--per-group",
        type=int,
        default=3,
        help="Works per bundle (default: 3)",
    )
    parser.add_argument(
        "--use-content",
        action="store_true",
        help="Include chapters[].content in matching (slower but more accurate when synopsis/themes are empty)",
    )
    parser.add_argument(
        "--content-max-chars",
        type=int,
        default=20000,
        help="Max total characters of content to include per work when --use-content is set (default: 20000)",
    )
    parser.add_argument(
        "--out-md",
        default="reports/theme_groups.md",
        help="Output Markdown path (default: reports/theme_groups.md)",
    )
    parser.add_argument(
        "--out-csv",
        default="reports/theme_groups.csv",
        help="Output CSV path (default: reports/theme_groups.csv)",
    )
    parser.add_argument(
        "--min-hits",
        type=int,
        default=1,
        help="Minimum number of matched patterns required to assign a non-default label (default: 1)",
    )

    args = parser.parse_args()

    bookdata_dir = Path(args.bookdata_dir)
    rules_path = Path(args.rules)
    out_md = Path(args.out_md)
    out_csv = Path(args.out_csv)

    if args.per_group <= 0:
        raise ValueError("--per-group must be >= 1")

    rules, default_label = load_rules(rules_path)
    min_hits = int(args.min_hits)
    if min_hits < 1:
        raise ValueError("--min-hits must be >= 1")

    files = sorted(bookdata_dir.glob(args.glob))
    if not files:
        raise SystemExit(f"No files matched: {bookdata_dir / args.glob}")

    records: list[dict[str, Any]] = []
    for path in files:
        book = load_json(path)
        if not isinstance(book, dict):
            continue
        title = str(book.get("title", path.stem))
        label, hits = classify(
            book,
            rules,
            default_label,
            use_content=bool(args.use_content),
            content_max_chars=int(args.content_max_chars),
        )

        if label != default_label and len(hits) < min_hits:
            label = default_label
            hits = []
        records.append(
            {
                "path": str(path.as_posix()),
                "title": title,
                "author": str(book.get("author", "")),
                "label": label,
                "hits": hits,
            }
        )

    # Group by label
    by_label: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_label.setdefault(r["label"], []).append(r)

    # Sort within label (volume-aware)
    for label, items in by_label.items():
        items.sort(key=lambda r: extract_sort_key(Path(r["path"]), r["title"]))

    # Stable order of labels: rules order first, then default/others
    ordered_labels = [rule.label for rule in rules]
    remaining = [l for l in by_label.keys() if l not in ordered_labels]
    ordered_labels.extend(sorted(remaining))

    # Bundles (interleaved across labels for readability)
    bundles = interleave_bundles(
        ordered_labels=ordered_labels,
        by_label=by_label,
        per_group=int(args.per_group),
    )

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_md.open("w", encoding="utf-8") as f:
        f.write("# テーマ別 3作セット一覧\n\n")
        f.write(f"対象: `{bookdata_dir / args.glob}`\n\n")
        f.write(f"ルール: `{rules_path}`\n\n")
        for b in bundles:
            f.write(f"## {b['bundle_label']}（{b['bundle_index']}）\n\n")
            for w in b["works"]:
                hits = ", ".join(w["hits"]) if w["hits"] else "-"
                f.write(
                    f"- {w['title']} / {w['author']}  ({w['path']})  [hit: {hits}]\n"
                )
            f.write("\n")

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "bundle_label",
                "bundle_index",
                "title",
                "author",
                "path",
                "hits",
            ],
        )
        writer.writeheader()
        for b in bundles:
            for w in b["works"]:
                writer.writerow(
                    {
                        "bundle_label": b["bundle_label"],
                        "bundle_index": b["bundle_index"],
                        "title": w["title"],
                        "author": w["author"],
                        "path": w["path"],
                        "hits": "|".join(w["hits"]),
                    }
                )

    print(f"Wrote: {out_md}")
    print(f"Wrote: {out_csv}")
    print(f"Works: {len(records)}  Bundles: {len(bundles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
