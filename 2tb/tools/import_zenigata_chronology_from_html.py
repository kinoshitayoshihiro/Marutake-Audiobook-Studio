#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML = ROOT / "reports" / "zenigata_gemini_dashboard.html"
DEFAULT_CSV = ROOT / "reports" / "zenigata_heiji_chronology.csv"
DEFAULT_URL = "https://unasaka.sakura.ne.jp/siryou/zenigata.html"


def extract_raw_data(html_text: str) -> list[dict[str, Any]]:
    match = re.search(r"rawData\s*=\s*(\[[\s\S]*?\])\s*;", html_text)
    if not match:
        raise ValueError("rawData 配列が見つかりませんでした")
    payload = match.group(1)
    try:
        parsed: Any = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"rawData の JSON 解析に失敗しました: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("rawData が配列ではありません")
    data = cast(list[Any], parsed)
    rows: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            rows.append(cast(dict[str, Any], item))
    return rows


def pick(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def load_text(source: str) -> tuple[str, str]:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source) as response:
            raw = response.read()
            content_type = response.headers.get_content_charset()
        for encoding in (content_type, "shift_jis", "cp932", "utf-8"):
            if not encoding:
                continue
            try:
                return raw.decode(encoding), source
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="ignore"), source

    path = Path(source).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"input not found: {path}")
    for encoding in ("utf-8", "utf-8-sig", "shift_jis", "cp932"):
        try:
            return path.read_text(encoding=encoding), path.name
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="ignore"), path.name


def extract_rows_from_chronology_page(html_text: str) -> list[dict[str, str]]:
    body_match = re.search(r"<BODY[\s\S]*?>([\s\S]*?)</BODY>", html_text, re.I)
    block = body_match.group(1) if body_match else html_text
    block = re.sub(r"<br\s*/?>", "\n", block, flags=re.IGNORECASE)
    block = re.sub(r"</p\s*>", "\n", block, flags=re.IGNORECASE)
    block = re.sub(r"</tr\s*>", "\n", block, flags=re.IGNORECASE)
    block = re.sub(r"</td\s*>", "\n", block, flags=re.IGNORECASE)
    block = re.sub(r"<script[\s\S]*?</script>", "", block, flags=re.IGNORECASE)
    block = re.sub(r"<style[\s\S]*?</style>", "", block, flags=re.IGNORECASE)
    block = re.sub(r"</?b[^>]*>", "", block, flags=re.IGNORECASE)
    block = re.sub(r"</?font[^>]*>", "", block, flags=re.IGNORECASE)
    block = re.sub(r"<[^>]+>", "", block)
    block = html.unescape(block)
    lines = [re.sub(r"\s+", " ", line).strip() for line in block.splitlines()]
    lines = [line for line in lines if line]

    rows: list[dict[str, str]] = []
    current_year = ""
    ordinal = 0
    entry_pattern = re.compile(r"「(?P<title>[^」]+)」\s*（(?P<magazine>[^）]+)）")
    for line in lines:
        if re.fullmatch(r"昭和\d+年", line):
            current_year = line
            continue
        if not current_year:
            continue
        for match in entry_pattern.finditer(line):
            ordinal += 1
            rows.append(
                {
                    "order_no": str(ordinal),
                    "publication_year": current_year,
                    "title": match.group("title"),
                    "magazine": match.group("magazine"),
                }
            )
    if not rows:
        raise ValueError("年表ページから作品行を抽出できませんでした")
    return rows


def extract_rows(text: str, source_name: str) -> list[dict[str, str]]:
    try:
        raw_rows = extract_raw_data(text)
    except ValueError:
        chronology_rows = extract_rows_from_chronology_page(text)
        for row in chronology_rows:
            row["source"] = source_name
        return chronology_rows

    rows: list[dict[str, str]] = []
    for row in raw_rows:
        rows.append(
            {
                "order_no": pick(row, "order", "order_no", "no", "番号", "通番"),
                "publication_year": pick(
                    row, "year", "publication_year", "発表年", "年"
                ),
                "title": pick(row, "title", "作品名", "name", "題名"),
                "magazine": pick(row, "magazine", "掲載誌", "雑誌", "初出"),
                "source": source_name,
            }
        )
    return rows


def main() -> int:
    source = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    csv_path = Path(sys.argv[2]).expanduser() if len(sys.argv) > 2 else DEFAULT_CSV

    try:
        html_text, source_name = load_text(source)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    rows = extract_rows(html_text, source_name)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_no", "publication_year", "title", "magazine", "source"])
        for row in rows:
            writer.writerow(
                [
                    row.get("order_no", ""),
                    row.get("publication_year", ""),
                    row.get("title", ""),
                    row.get("magazine", ""),
                    row.get("source", source_name),
                ]
            )

    print(f"Wrote: {csv_path}")
    print(f"Rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
