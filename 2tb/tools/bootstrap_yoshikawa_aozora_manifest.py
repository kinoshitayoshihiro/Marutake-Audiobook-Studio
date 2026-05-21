#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG_CSV = ROOT / "reports" / "yoshikawa_works_catalog.csv"
MANIFEST_PATH = ROOT / "reports" / "yoshikawa_aozora_manifest.json"


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
    if bool_field(row, "has_local_text"):
        return (
            "local_text_present",
            "手持ち本文あり。青空文庫は補完または全文再取得の確認対象。",
        )
    return (
        "needs_lookup",
        "手持ち本文なし。青空文庫照合と取得対象。",
    )


def merge_entry(row: dict[str, str], existing: dict[str, Any] | None) -> dict[str, Any]:
    title = str(row.get("title", "")).strip()
    status, notes = default_status(row)
    item = {
        "title": title,
        "normalized_title": title,
        "work_type": str(row.get("work_type", "")).strip(),
        "video_count": int(str(row.get("video_count", "0") or "0")),
        "report_priority": str(row.get("report_priority", "")).strip(),
        "has_local_text": bool_field(row, "has_local_text"),
        "local_text_count": int(str(row.get("local_text_count", "0") or "0")),
        "local_text_paths": str(row.get("local_text_paths", "")).strip(),
        "aozora_card_url": "",
        "aozora_text_url": "",
        "aozora_matches": [],
        "status": status,
        "notes": notes,
    }
    if not existing:
        return item

    item["normalized_title"] = str(existing.get("normalized_title", title)).strip() or title
    item["aozora_card_url"] = str(existing.get("aozora_card_url", "")).strip()
    item["aozora_text_url"] = str(existing.get("aozora_text_url", "")).strip()
    item["status"] = str(existing.get("status", status)).strip() or status
    item["notes"] = str(existing.get("notes", notes)).strip() or notes
    matches = existing.get("aozora_matches", [])
    item["aozora_matches"] = matches if isinstance(matches, list) else []
    return item


def main() -> int:
    rows = load_catalog()
    existing = load_existing_manifest()
    items = [
        merge_entry(row, existing.get(str(row.get("title", "")).strip()))
        for row in rows
    ]
    payload = {
        "description": "吉川英治作品の青空文庫照合用 manifest。作品単位で複数分冊を保持する。",
        "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }
    MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Items: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())