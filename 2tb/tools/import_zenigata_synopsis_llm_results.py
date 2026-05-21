#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from zenigata_search_page_builder_impl import ROOT, SYNOPSIS_LLM_JSON_PATH


JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="銭形平次 synopsis 補筆の LLM 結果を正規化して保存する"
    )
    parser.add_argument("input", type=Path, help="LLM 結果の JSON / JSONL / TXT")
    parser.add_argument("--output", type=Path, default=SYNOPSIS_LLM_JSON_PATH)
    parser.add_argument("--model", default="")
    parser.add_argument("--source", default="llm")
    return parser.parse_args()


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def parse_possible_json(text: str) -> Any:
    clean = text.strip()
    if not clean:
        return None
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    block = JSON_BLOCK_RE.search(clean)
    if block:
        try:
            return json.loads(block.group(1))
        except json.JSONDecodeError:
            return None
    return None


def extract_payload(record: Any) -> list[dict[str, Any]]:
    if isinstance(record, list):
        items: list[dict[str, Any]] = []
        for entry in record:
            items.extend(extract_payload(entry))
        return items
    if not isinstance(record, dict):
        return []
    if "title" in record and "synopsis" in record:
        return [record]
    for key in ("response", "output", "result", "content", "text", "output_text"):
        value = record.get(key)
        if isinstance(value, dict):
            return extract_payload(value)
        if isinstance(value, list):
            return extract_payload(value)
        if isinstance(value, str):
            parsed = parse_possible_json(value)
            if parsed is not None:
                return extract_payload(parsed)
    if "choices" in record and isinstance(record["choices"], list):
        return extract_payload(record["choices"])
    if "message" in record:
        return extract_payload(record["message"])
    return []


def normalize_item(
    item: dict[str, Any], *, model: str, source: str
) -> dict[str, Any] | None:
    title = str(item.get("title", "") or "").strip()
    synopsis = str(item.get("synopsis", "") or "").strip()
    summary = str(item.get("summary", "") or "").strip()
    if not title or not synopsis:
        return None
    if not summary:
        base = synopsis[:90].rstrip("。")
        summary = f"{base}。" if base and not base.endswith("。") else base
    return {
        "title": title,
        "synopsis": synopsis,
        "summary": summary,
        "confidence": str(item.get("confidence", "") or "").strip(),
        "notes": (
            [str(note).strip() for note in item.get("notes", []) if str(note).strip()]
            if isinstance(item.get("notes"), list)
            else []
        ),
        "quality": str(item.get("quality", "") or "").strip(),
        "model": model or str(item.get("model", "") or "").strip(),
        "source": source or str(item.get("source", "llm") or "").strip(),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }


def load_input(path: Path) -> list[dict[str, Any]]:
    text = resolve_path(path).read_text(encoding="utf-8")
    parsed = parse_possible_json(text)
    if parsed is not None:
        return extract_payload(parsed)
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        try:
            parsed_line = json.loads(clean)
        except json.JSONDecodeError:
            continue
        items.extend(extract_payload(parsed_line))
    return items


def load_existing(path: Path) -> dict[str, dict[str, Any]]:
    target = resolve_path(path)
    if not target.exists():
        return {}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    source = raw.get("items", []) if isinstance(raw, dict) else raw
    if not isinstance(source, list):
        return {}
    items: dict[str, dict[str, Any]] = {}
    for entry in source:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "") or "").strip()
        if title:
            items[title] = entry
    return items


def main() -> int:
    args = parse_args()
    items = load_existing(args.output)
    for item in load_input(args.input):
        normalized = normalize_item(item, model=args.model, source=args.source)
        if normalized is None:
            continue
        items[normalized["title"]] = normalized
    output_path = resolve_path(args.output)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": [items[title] for title in sorted(items)],
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote: {display_path(output_path)}")
    print(f"Items: {len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
