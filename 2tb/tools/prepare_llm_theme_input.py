#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


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
    parts = re.split(r"[\s　/]+", full_title.strip())
    return parts[-1].strip() if parts else full_title.strip()


def get_content_excerpt(book: dict[str, Any], max_chars: int) -> str:
    chapters = book.get("chapters")
    if not isinstance(chapters, list) or max_chars <= 0:
        return ""

    buf: list[str] = []
    remaining = max_chars
    for ch in chapters:
        if remaining <= 0:
            break
        if not isinstance(ch, dict):
            continue
        c = ch.get("content")
        if not isinstance(c, str) or not c:
            continue
        snippet = c[:remaining]
        buf.append(snippet)
        remaining -= len(snippet)

    text = "\n".join(buf)
    # Light cleanup: drop excessive whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def extract_candidate_terms(text: str, top_n: int) -> list[dict[str, Any]]:
    """Very lightweight Japanese term extraction.

    - Counts occurrences of Kanji sequences (2-6 chars)
    - Counts occurrences of some kana/kanji mixed keyphrases (2-8 chars) that look like nouns

    This is intentionally simple and offline (no tokenizer dependency).
    """

    if not text:
        return []

    # Normalize
    t = text

    # Kanji sequences
    kanji = re.findall(r"[\u4E00-\u9FFF]{2,6}", t)

    # Mixed (hiragana/katakana/kanji) sequences that avoid digits/punct
    mixed = re.findall(r"[\u3040-\u30FF\u4E00-\u9FFF]{2,8}", t)

    stop = {
        "七之助",
        "音吉",
        "茂平次",
        "浜中",
        "親分",
        "お雪",
        "お藤",
        "旦那",
        "御用聞",
        "江戸",
        "捕物帳",
    }

    counter: Counter[str] = Counter()
    for w in kanji:
        if w in stop:
            continue
        counter[w] += 1
    for w in mixed:
        if w in stop:
            continue
        # Filter too-generic kana chains
        if re.fullmatch(r"[\u3040-\u309F]{2,8}", w):
            continue
        counter[w] += 1

    # Prefer terms that appear at least twice
    items = [(w, c) for (w, c) in counter.items() if c >= 2]
    items.sort(key=lambda x: (-x[1], -len(x[0]), x[0]))

    result = []
    for w, c in items[:top_n]:
        result.append({"term": w, "count": c})
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare JSONL for LLM-based theme classification"
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
        "--out-jsonl",
        default="reports/llm_theme_input_七之助捕物帳.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument(
        "--excerpt-chars",
        type=int,
        default=8000,
        help="Max chars of chapter content excerpt per work (default: 8000)",
    )
    parser.add_argument(
        "--top-terms",
        type=int,
        default=30,
        help="Top extracted candidate terms to include (default: 30)",
    )
    args = parser.parse_args()

    bookdata_dir = Path(args.bookdata_dir)
    files = sorted(bookdata_dir.glob(args.glob))
    if not files:
        raise SystemExit(f"No files matched: {bookdata_dir / args.glob}")

    out_path = Path(args.out_jsonl)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w", encoding="utf-8") as out:
        for path in files:
            book = load_json(path)
            if not isinstance(book, dict):
                continue

            title = str(book.get("title", path.stem))
            episode_title = extract_episode_title(title)
            synopsis = book.get("synopsis")
            synopsis = synopsis if isinstance(synopsis, str) else ""

            excerpt = get_content_excerpt(book, int(args.excerpt_chars))
            terms = extract_candidate_terms(excerpt, int(args.top_terms))

            payload = {
                "path": str(path.as_posix()),
                "title": title,
                "episode_title": episode_title,
                "author": str(book.get("author", "")),
                "synopsis": synopsis,
                "keywords": safe_list_str(book.get("keywords")),
                "themes": safe_list_str(book.get("themes")),
                "emotions": safe_list_str(book.get("emotions")),
                "candidate_terms": terms,
                "content_excerpt": excerpt,
            }
            out.write(json.dumps(payload, ensure_ascii=False) + "\n")

    print(f"Wrote: {out_path}")
    print(f"Items: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
