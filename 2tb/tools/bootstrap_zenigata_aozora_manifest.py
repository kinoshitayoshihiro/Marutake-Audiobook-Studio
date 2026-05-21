#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_CSV = ROOT / "reports" / "zenigata_heiji_works_catalog.csv"
MANIFEST_PATH = ROOT / "reports" / "zenigata_aozora_manifest.json"


def load_catalog() -> list[dict[str, str]]:
    with CATALOG_CSV.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_existing_manifest() -> dict[str, dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        return {}
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    items = data.get("items", []) if isinstance(data, dict) else []
    manifest: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if title:
            manifest[title] = item
    return manifest


def bool_field(row: dict[str, str], field: str) -> bool:
    return str(row.get(field, "")).strip().lower() == "yes"


def default_status(row: dict[str, str]) -> tuple[str, str]:
    has_local_text = bool_field(row, "has_local_text")
    has_bookdata = bool_field(row, "has_bookdata")
    if has_local_text and has_bookdata:
        return (
            "local_bookdata_ready",
            "手持ち本文とbookdataあり。青空本文が必要ならURL解決のみ追加。",
        )
    if has_local_text:
        return (
            "local_text_present",
            "手持ち本文あり。青空照合は任意、bookdata草案生成対象。",
        )
    return (
        "needs_lookup",
        "手持ち本文なし。青空文庫→国会図書館→外部公開テキストの順に照合。",
    )


def merge_entry(row: dict[str, str], existing: dict[str, Any] | None) -> dict[str, Any]:
    title = str(row.get("title", "")).strip()
    status, notes = default_status(row)
    item = {
        "title": title,
        "normalized_title": title,
        "aozora_card_url": "",
        "aozora_text_url": "",
        "status": status,
        "notes": notes,
        "publication_years": str(row.get("publication_years", "")).strip(),
        "magazines": str(row.get("magazines", "")).strip(),
        "has_local_text": bool_field(row, "has_local_text"),
        "has_bookdata": bool_field(row, "has_bookdata"),
    }
    if not existing:
        return item
    item["aozora_card_url"] = str(existing.get("aozora_card_url", "")).strip()
    item["aozora_text_url"] = str(existing.get("aozora_text_url", "")).strip()
    item["status"] = str(existing.get("status", status)).strip() or status
    item["notes"] = str(existing.get("notes", notes)).strip() or notes
    return item


def main() -> int:
    rows = load_catalog()
    existing = load_existing_manifest()
    items = [
        merge_entry(row, existing.get(str(row.get("title", "")).strip()))
        for row in rows
    ]
    items.sort(
        key=lambda item: (str(item.get("publication_years", "")), str(item["title"]))
    )
    payload = {
        "description": "青空文庫本文補完用 manifest。381件の全タイトルを収録し、照合状態を管理する。",
        "generated_at": __import__("datetime")
        .datetime.now()
        .strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }
    MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    unresolved = sum(
        1 for item in items if item["status"] in {"needs_lookup", "unresolved"}
    )
    with_text = sum(1 for item in items if item["has_local_text"])
    with_bookdata = sum(1 for item in items if item["has_bookdata"])
    print(f"Wrote: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Items: {len(items)}")
    print(f"Local text present: {with_text}")
    print(f"Bookdata present: {with_bookdata}")
    print(f"Needs Aozora lookup: {unresolved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
