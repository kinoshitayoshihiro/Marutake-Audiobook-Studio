#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path


def main() -> None:
    workspace = Path(__file__).resolve().parents[1]
    path = (
        workspace
        / "Reading_library"
        / "納言恭平著"
        / "納言恭平　七之助捕物帳　第三巻.txt"
    )
    txt = path.read_text(encoding="cp932")
    lines = [
        ln.rstrip() for ln in txt.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]

    nonempty = [ln for ln in lines if ln.strip()]
    print(f"file: {path}")
    print("--- last 60 non-empty lines ---")
    for ln in nonempty[-60:]:
        print(ln)


if __name__ == "__main__":
    main()
