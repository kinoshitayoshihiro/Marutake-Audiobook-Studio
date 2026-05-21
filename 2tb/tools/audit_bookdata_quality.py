#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BookAudit:
    path: str
    title: str
    episode_title: str
    author: str
    synopsis_len: int
    keywords_count: int
    keywords_cross_title_count: int
    keywords_cross_title_examples: list[str]
    themes: list[str]
    emotions: list[str]
    chapters_count: int
    content_chars: int


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_list_str(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(x) for x in value if str(x).strip()]
    return []


def extract_episode_title(full_title: str) -> str:
    m = re.search(r"【([^】]+)】", full_title)
    if m:
        return m.group(1).strip()

    # Fallback: try to extract after last whitespace or slash-like separators
    # e.g., "七之助捕物帳　第05巻　さかさ天一坊" -> "さかさ天一坊"
    # Keep it conservative.
    parts = re.split(r"[\s　/]+", full_title.strip())
    if parts:
        return parts[-1].strip()
    return full_title.strip()


def summarize_list(values: list[int]) -> dict[str, float]:
    if not values:
        return {"min": 0, "p50": 0, "p90": 0, "max": 0, "avg": 0}
    values_sorted = sorted(values)
    n = len(values_sorted)

    def p(q: float) -> int:
        idx = int(round((n - 1) * q))
        return values_sorted[idx]

    return {
        "min": float(values_sorted[0]),
        "p50": float(p(0.50)),
        "p90": float(p(0.90)),
        "max": float(values_sorted[-1]),
        "avg": float(sum(values_sorted) / n),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit bookdata JSON quality for theme classification"
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
        "--out-md",
        default="reports/bookdata_quality_七之助捕物帳.md",
        help="Output Markdown path",
    )
    parser.add_argument(
        "--out-csv",
        default="reports/bookdata_quality_七之助捕物帳.csv",
        help="Output CSV path",
    )
    args = parser.parse_args()

    bookdata_dir = Path(args.bookdata_dir)
    files = sorted(bookdata_dir.glob(args.glob))
    if not files:
        raise SystemExit(f"No files matched: {bookdata_dir / args.glob}")

    raw_books: list[dict[str, Any]] = []
    episode_titles: list[str] = []
    for path in files:
        book = load_json(path)
        if not isinstance(book, dict):
            continue
        title = str(book.get("title", path.stem))
        ep = extract_episode_title(title)
        raw_books.append(
            {"path": path, "book": book, "title": title, "episode_title": ep}
        )
        if ep:
            episode_titles.append(ep)

    episode_title_set = {t for t in episode_titles if t}

    audits: list[BookAudit] = []
    themes_counter: Counter[tuple[str, ...]] = Counter()

    for item in raw_books:
        path: Path = item["path"]
        book: dict[str, Any] = item["book"]
        title: str = item["title"]
        ep: str = item["episode_title"]

        author = str(book.get("author", ""))
        synopsis = book.get("synopsis")
        synopsis_len = len(synopsis) if isinstance(synopsis, str) else 0

        keywords = safe_list_str(book.get("keywords"))
        keywords_count = len(keywords)

        # Count keywords that look like other episode titles.
        cross = []
        for kw in keywords:
            if kw in episode_title_set and kw != ep:
                cross.append(kw)
        cross_unique = sorted(set(cross))

        themes = safe_list_str(book.get("themes"))
        emotions = safe_list_str(book.get("emotions"))
        themes_counter[tuple(themes)] += 1

        chapters = book.get("chapters")
        chapters_count = len(chapters) if isinstance(chapters, list) else 0
        content_chars = 0
        if isinstance(chapters, list):
            for ch in chapters:
                if isinstance(ch, dict):
                    c = ch.get("content")
                    if isinstance(c, str):
                        content_chars += len(c)

        audits.append(
            BookAudit(
                path=str(path.as_posix()),
                title=title,
                episode_title=ep,
                author=author,
                synopsis_len=synopsis_len,
                keywords_count=keywords_count,
                keywords_cross_title_count=len(cross_unique),
                keywords_cross_title_examples=cross_unique[:8],
                themes=themes,
                emotions=emotions,
                chapters_count=chapters_count,
                content_chars=content_chars,
            )
        )

    synopsis_lens = [a.synopsis_len for a in audits]
    keywords_counts = [a.keywords_count for a in audits]
    cross_counts = [a.keywords_cross_title_count for a in audits]

    empty_synopsis = sum(1 for a in audits if a.synopsis_len == 0)
    have_cross_titles = sum(1 for a in audits if a.keywords_cross_title_count > 0)

    out_md = Path(args.out_md)
    out_csv = Path(args.out_csv)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "path",
                "title",
                "episode_title",
                "author",
                "synopsis_len",
                "keywords_count",
                "keywords_cross_title_count",
                "keywords_cross_title_examples",
                "themes",
                "emotions",
                "chapters_count",
                "content_chars",
            ],
        )
        writer.writeheader()
        for a in audits:
            writer.writerow(
                {
                    "path": a.path,
                    "title": a.title,
                    "episode_title": a.episode_title,
                    "author": a.author,
                    "synopsis_len": a.synopsis_len,
                    "keywords_count": a.keywords_count,
                    "keywords_cross_title_count": a.keywords_cross_title_count,
                    "keywords_cross_title_examples": "|".join(
                        a.keywords_cross_title_examples
                    ),
                    "themes": "|".join(a.themes),
                    "emotions": "|".join(a.emotions),
                    "chapters_count": a.chapters_count,
                    "content_chars": a.content_chars,
                }
            )

    top_themes = themes_counter.most_common(5)

    def fmt_stats(label: str, stats: dict[str, float]) -> str:
        return f"- {label}: min={int(stats['min'])} p50={int(stats['p50'])} p90={int(stats['p90'])} max={int(stats['max'])} avg={stats['avg']:.1f}"

    with out_md.open("w", encoding="utf-8") as f:
        f.write("# bookdata品質監査（七之助捕物帳）\n\n")
        f.write(f"対象: `{bookdata_dir / args.glob}`\n\n")
        f.write("## サマリ\n\n")
        f.write(f"- 作品数: {len(audits)}\n")
        f.write(f"- synopsisが空: {empty_synopsis} / {len(audits)}\n")
        f.write(
            f"- keywordsに他巻タイトルが混入: {have_cross_titles} / {len(audits)}\n\n"
        )

        f.write("## 分布\n\n")
        f.write(fmt_stats("synopsis_len", summarize_list(synopsis_lens)) + "\n")
        f.write(fmt_stats("keywords_count", summarize_list(keywords_counts)) + "\n")
        f.write(
            fmt_stats("keywords_cross_title_count", summarize_list(cross_counts))
            + "\n\n"
        )

        f.write("## themesの多様性（上位）\n\n")
        for themes, cnt in top_themes:
            f.write(f"- {cnt}件: {list(themes)}\n")
        if len(themes_counter) > 5:
            f.write(f"- …（ユニークthemes配列: {len(themes_counter)}種類）\n")
        f.write("\n")

        f.write("## 問題が大きい疑いのある作品（抜粋）\n\n")
        # Rank by cross-title contamination and empty synopsis.
        suspicious = sorted(
            audits,
            key=lambda a: (
                a.synopsis_len == 0,
                a.keywords_cross_title_count,
                a.keywords_count,
            ),
            reverse=True,
        )
        for a in suspicious[:15]:
            f.write(
                f"- {a.title} ({a.path}) synopsis_len={a.synopsis_len} keywords={a.keywords_count} cross_titles={a.keywords_cross_title_count} examples={a.keywords_cross_title_examples}\n"
            )

    print(f"Wrote: {out_md}")
    print(f"Wrote: {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
