#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import re
import sys
from pathlib import Path


EXPECTED_KEYS = [
    "title",
    "author",
    "genre",
    "japanese_genre",
    "sub_genre",
    "setting",
    "location",
    "time_period",
    "keywords",
    "themes",
    "emotions",
    "synopsis",
    "highlights",
    "characters",
    "glossary",
    "authorProfile",
    "chapters",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON: {path} ({exc})")


def reorder_top_level(data: dict) -> dict:
    missing = [k for k in EXPECTED_KEYS if k not in data]
    extra = [k for k in data.keys() if k not in EXPECTED_KEYS]
    if missing:
        fail(f"missing keys: {missing}")
    if extra:
        fail(f"extra keys: {extra}")

    return {k: data[k] for k in EXPECTED_KEYS}


def normalize_newlines(text: str) -> str:
    # Handle Windows CRLF and classic Mac CR.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def find_heading(text: str, title: str, start: int) -> re.Match:
    # Allow both ASCII space and Japanese full-width space.
    # Some sources prefix headings with markers like "■".
    title = title.strip()
    pattern = re.compile(rf"(?m)^[ \t　]*■?[ \t　]*{re.escape(title)}[ \t　]*$")
    return pattern.search(text, pos=start)


def slice_chapters_by_titles(text: str, titles: list[str]) -> list[str]:
    text = normalize_newlines(text)

    matches: list[re.Match] = []
    cursor = 0
    for i, title in enumerate(titles):
        m = find_heading(text, title, cursor)
        if not m and i == 0:
            # Some sources (often OCR) omit the first heading line.
            # Treat the beginning of the text as the first chapter boundary.
            m = re.compile(r"\A").search(text)
        if not m:
            # Provide a small hint for debugging.
            preview = text[cursor : cursor + 500]
            preview = preview.replace("\n", "\\n")
            fail(
                f"heading not found: {title} (search start={cursor}). preview={preview[:300]}"
            )
        matches.append(m)
        cursor = m.end()

    contents: list[str] = []
    for i, m in enumerate(matches):
        # Start after the heading line.
        start = m.end()
        # Skip immediate blank lines.
        while start < len(text) and text[start] == "\n":
            start += 1

        end = len(text) if i == len(matches) - 1 else matches[i + 1].start()
        chunk = text[start:end]
        chunk = chunk.strip("\n")
        chunk = chunk.rstrip()
        contents.append(chunk)

    return contents


def detect_chapter_titles(text: str, heading_regex: str | None) -> list[str]:
    text = normalize_newlines(text)

    # Default: lines that consist of only Japanese kanji numerals (common Aozora-like style).
    # Examples: "一" / "　　二" / "三".
    pattern = (
        re.compile(heading_regex, flags=re.MULTILINE)
        if heading_regex
        else re.compile(r"(?m)^[ \t　]*([一二三四五六七八九十]+)[ \t　]*$")
    )

    titles: list[str] = []
    seen: set[str] = set()
    for m in pattern.finditer(text):
        # Prefer capture group 1 when present; otherwise the full match.
        t = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
        # Strip all whitespace (including newlines) to avoid accidental "\n一" titles.
        t = t.strip()
        if not t:
            continue
        if t in seen:
            continue
        seen.add(t)
        titles.append(t)

    return titles


def cmd_make_base(args: argparse.Namespace) -> None:
    src_path = Path(args.src)
    out_path = Path(args.out)

    data = load_json(src_path)
    if not isinstance(data, dict):
        fail("top-level must be an object")

    data = reorder_top_level(data)
    chapters = data.get("chapters")
    if not isinstance(chapters, list):
        fail("chapters must be list")
    for chap in chapters:
        if not isinstance(chap, dict):
            fail("chapters must be list[dict]")
        if set(chap.keys()) != {"title", "content"}:
            fail("each chapter must have keys: title, content")
        chap["content"] = ""

    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {out_path}")


def cmd_inject(args: argparse.Namespace) -> None:
    base_path = Path(args.base)
    text_path = Path(args.text)
    out_path = Path(args.out)

    base = load_json(base_path)
    if not isinstance(base, dict):
        fail("base top-level must be an object")
    base = reorder_top_level(base)

    chapters = base.get("chapters")
    if not isinstance(chapters, list) or not all(isinstance(x, dict) for x in chapters):
        fail("chapters must be list[dict]")
    titles: list[str] = []
    for i, chap in enumerate(chapters):
        if set(chap.keys()) != {"title", "content"}:
            fail(f"chapters[{i}] must have keys: title, content")
        title = chap.get("title")
        if not isinstance(title, str) or not title.strip():
            fail(f"chapters[{i}].title must be non-empty str")
        titles.append(title)

    try:
        raw_text = text_path.read_text(encoding=args.encoding)
    except Exception as exc:
        fail(f"failed to read text: {text_path} ({exc})")

    contents = slice_chapters_by_titles(raw_text, titles)
    if len(contents) != len(chapters):
        fail("internal error: content count mismatch")

    for chap, content in zip(chapters, contents):
        chap["content"] = content

    out_path.write_text(
        json.dumps(base, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {out_path}")


def cmd_make_base_from_text(args: argparse.Namespace) -> None:
    src_path = Path(args.src)
    text_path = Path(args.text)
    out_path = Path(args.out)

    data = load_json(src_path)
    if not isinstance(data, dict):
        fail("top-level must be an object")
    data = reorder_top_level(data)

    try:
        raw_text = text_path.read_text(encoding=args.encoding)
    except Exception as exc:
        fail(f"failed to read text: {text_path} ({exc})")

    titles = detect_chapter_titles(raw_text, args.heading_regex)
    if not titles:
        fail(
            "no chapter headings detected. Provide --heading-regex or adjust the source text."
        )

    data["chapters"] = [{"title": t, "content": ""} for t in titles]

    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"WROTE: {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a base bookdata JSON (empty chapters) and inject full text into chapters by heading titles."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_base = sub.add_parser(
        "make-base", help="Create a base JSON where all chapters[].content are emptied"
    )
    p_base.add_argument(
        "--src", required=True, help="Source bookdata JSON (may contain summaries)"
    )
    p_base.add_argument("--out", required=True, help="Output base JSON path")
    p_base.set_defaults(func=cmd_make_base)

    p_base2 = sub.add_parser(
        "make-base-from-text",
        help="Create a base JSON by detecting chapter headings from a .txt (chapters[].content are emptied)",
    )
    p_base2.add_argument(
        "--src",
        required=True,
        help="Source bookdata JSON (metadata is kept; chapters will be replaced)",
    )
    p_base2.add_argument("--text", required=True, help="Source text (.txt) path")
    p_base2.add_argument("--out", required=True, help="Output base JSON path")
    p_base2.add_argument(
        "--encoding", default="utf-8", help="Text file encoding (default: utf-8)"
    )
    p_base2.add_argument(
        "--heading-regex",
        default=None,
        help=(
            "Regex to detect chapter headings. If it has a capture group, group(1) is used as the title; otherwise the full match. "
            "Default detects lines that contain only kanji numerals (一二三四...)."
        ),
    )
    p_base2.set_defaults(func=cmd_make_base_from_text)

    p_inj = sub.add_parser(
        "inject", help="Inject full text from a .txt file into a base JSON"
    )
    p_inj.add_argument(
        "--base",
        required=True,
        help="Base bookdata JSON path (chapters titles define split points)",
    )
    p_inj.add_argument("--text", required=True, help="Source text (.txt) path")
    p_inj.add_argument(
        "--out", required=True, help="Output fulltext bookdata JSON path"
    )
    p_inj.add_argument(
        "--encoding", default="utf-8", help="Text file encoding (default: utf-8)"
    )
    p_inj.set_defaults(func=cmd_inject)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
