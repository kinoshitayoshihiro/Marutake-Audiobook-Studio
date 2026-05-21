#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path


def try_read(path: Path, enc: str) -> str | None:
    try:
        return path.read_text(encoding=enc)
    except UnicodeDecodeError:
        return None


def score_japanese(text: str) -> int:
    # Simple heuristic: count Hiragana/Katakana/CJK chars in first 2000 chars
    sample = text[:2000]
    score = 0
    for ch in sample:
        o = ord(ch)
        if 0x3040 <= o <= 0x30FF or 0x4E00 <= o <= 0x9FFF:
            score += 1
    return score


def main() -> None:
    workspace = Path(__file__).resolve().parents[1]
    path = (
        workspace
        / "Reading_library"
        / "納言恭平著"
        / "納言恭平　七之助捕物帳　第三巻.txt"
    )

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp932",
        "shift_jis",
        "euc_jp",
        "iso2022_jp",
        "utf-16",
        "utf-16-le",
        "utf-16-be",
    ]

    best = None
    results = []
    for enc in encodings:
        txt = try_read(path, enc)
        if txt is None:
            continue
        s = score_japanese(txt)
        results.append((s, enc, txt))
        if best is None or s > best[0]:
            best = (s, enc, txt)

    results.sort(reverse=True)
    print(f"file: {path}")
    for s, enc, _ in results[:5]:
        print(f"candidate: {enc} score={s}")

    if best is None:
        print("no readable encoding candidates")
        return

    _, enc, txt = best
    print(f"BEST: {enc}")
    # print first non-empty lines
    lines = [
        ln
        for ln in txt.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if ln.strip()
    ]
    for ln in lines[:15]:
        print(ln)


if __name__ == "__main__":
    main()
