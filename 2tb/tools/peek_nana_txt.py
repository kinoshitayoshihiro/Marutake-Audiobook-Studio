#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import re
from pathlib import Path


def read_text_guess_encoding(path: Path) -> tuple[str, str]:
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis"):
        try:
            return path.read_text(encoding=enc), enc
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace"), "utf-8?"


def is_blank(line: str) -> bool:
    return line.strip() == ""


def extract_headings(lines: list[str]) -> tuple[str, list[tuple[int, str]]]:
    nonempty = [i for i, l in enumerate(lines) if not is_blank(l)]
    if not nonempty:
        return "", []

    main_title_index = nonempty[0]
    main_title = lines[main_title_index].strip()
    headings: list[tuple[int, str]] = []

    # Special-case: 2nd non-empty line as a heading if it is isolated by blank lines
    if len(nonempty) >= 2:
        i = nonempty[1]
        cand = lines[i].strip()
        looks_like_heading = (
            i > main_title_index
            and len(cand) <= 12
            and not cand.startswith("「")
            and i - 1 >= 0
            and is_blank(lines[i - 1])
            and i + 1 < len(lines)
            and is_blank(lines[i + 1])
        )
        if looks_like_heading:
            headings.append((i, cand))

    def indented_heading_at(i: int) -> str | None:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            return None
        if i <= main_title_index:
            return None
        if i - 1 >= 0 and not is_blank(lines[i - 1]):
            return None
        if i + 1 < len(lines) and not is_blank(lines[i + 1]):
            return None

        lead = 0
        for ch in raw:
            if ch == "\u3000":
                lead += 1
            else:
                break
        if lead < 1:
            return None
        if stripped.startswith("「"):
            return None
        if len(stripped) > 40:
            return None
        return stripped

    for i in range(len(lines)):
        h = indented_heading_at(i)
        if h:
            headings.append((i, h))

    # Section headings like: "■　　一、夏草" (common in some Nana volumes)
    section_re = re.compile(r"^\s*■\s*(?P<title>.+?)\s*$")
    for i, raw in enumerate(lines):
        if i <= main_title_index:
            continue
        m = section_re.match(raw)
        if not m:
            continue
        title = m.group("title").strip()
        # avoid catching decorative lines
        if not title or title.startswith("「"):
            continue
        # prefer titles that look like numbered sections, e.g. "一、xxx"
        if re.match(r"^[一二三四五六七八九十百千]+、", title) or re.match(
            r"^\d+\s*[、\.]", title
        ):
            headings.append((i, title))

    # De-dup and sort
    uniq: dict[int, str] = {i: h for i, h in headings}
    headings2 = sorted(uniq.items(), key=lambda x: x[0])
    return main_title, headings2


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: peek_nana_txt.py <path-to-txt>")
        raise SystemExit(2)

    path = Path(sys.argv[1])
    text, enc = read_text_guess_encoding(path)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    main_title, headings = extract_headings(lines)
    print(f"file: {path}")
    print(f"encoding: {enc}")
    print(f"main_title: {main_title}")
    print(f"chapter_count: {len(headings)}")
    print("chapter_titles:")
    for _, h in headings:
        print(f"- {h}")

    # Preview each chapter head
    if headings:
        print("\npreviews:")
        for idx, (start_i, title) in enumerate(headings, 1):
            end_i = headings[idx][0] if idx < len(headings) else len(lines)
            content = lines[start_i + 1 : end_i]
            while content and is_blank(content[0]):
                content.pop(0)
            while content and is_blank(content[-1]):
                content.pop()
            head = " ".join(l.strip() for l in content[:6] if l.strip())
            print(f"[{idx}] {title}: {head[:180]}")


if __name__ == "__main__":
    main()
