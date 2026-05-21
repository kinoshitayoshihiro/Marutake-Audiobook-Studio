#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
CATALOG_CSV = ROOT / "reports" / "zenigata_heiji_works_catalog.csv"
MANIFEST_PATH = ROOT / "reports" / "zenigata_aozora_manifest.json"
REPORT_JSON = ROOT / "reports" / "zenigata_unresolved_triage.json"
REPORT_MD = ROOT / "reports" / "zenigata_unresolved_triage.md"
REPORT_CSV = ROOT / "reports" / "zenigata_unresolved_triage.csv"

BUCKET_LABELS = {
    "ndl_candidate": "国会図書館候補",
    "external_public_candidate": "外部公開テキスト候補",
    "likely_text_missing": "本文不在濃厚",
}

SKIP_STATUSES = {"resolved", "local_text_present", "local_bookdata_ready"}


def load_catalog() -> dict[str, dict[str, str]]:
    with CATALOG_CSV.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {str(row.get("title", "")).strip(): row for row in rows}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def has_bibliography(row: dict[str, str]) -> bool:
    return any(
        str(row.get(field, "")).strip()
        for field in ("publication_years", "magazines", "chronology_ordinals")
    )


def has_external_trace(row: dict[str, str]) -> bool:
    if str(row.get("has_channel_entry", "")).strip().lower() == "yes":
        return True
    if str(row.get("has_audio_archive", "")).strip().lower() == "yes":
        return True
    source_paths = [
        part.strip() for part in str(row.get("source_paths", "")).split("|")
    ]
    interesting = [
        path
        for path in source_paths
        if path
        and not path.startswith("reports/")
        and not path.startswith("bookdata/")
        and "zenigata_heiji_chronology.csv" not in path
    ]
    return bool(interesting)


def ndl_search_url(title: str, row: dict[str, str]) -> str:
    query_parts = ["野村胡堂", title]
    magazine = str(row.get("magazines", "")).strip()
    year = str(row.get("publication_years", "")).strip()
    if magazine:
        query_parts.append(magazine)
    if year:
        query_parts.append(year)
    query = quote_plus(" ".join(query_parts))
    return "https://ndlsearch.ndl.go.jp/search?keyword=" + query


def external_search_query(title: str, row: dict[str, str]) -> str:
    bits = ["野村胡堂", title, "全文 OR 青空 OR テキスト OR PDF"]
    if str(row.get("magazines", "")).strip():
        bits.append(str(row.get("magazines", "")).strip())
    return " ".join(bits)


def classify(title: str, row: dict[str, str]) -> tuple[str, str]:
    if has_bibliography(row):
        return (
            "ndl_candidate",
            "初出誌・発表年などの書誌情報あり。まず国会図書館サーチで追跡するのが有力。",
        )
    if has_external_trace(row):
        return (
            "external_public_candidate",
            "書誌情報は弱いが、チャンネル・音声・外部由来の痕跡あり。公開テキストの外部探索候補。",
        )
    return (
        "likely_text_missing",
        "青空未収録で書誌・周辺痕跡も乏しいため、現時点では本文不在濃厚。",
    )


def write_csv(items: list[dict[str, Any]]) -> None:
    fieldnames = [
        "title",
        "bucket",
        "bucket_label",
        "reason",
        "publication_years",
        "magazines",
        "has_channel_entry",
        "has_audio_archive",
        "ndl_search_url",
        "external_search_query",
    ]
    with REPORT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in items:
            writer.writerow({key: item.get(key, "") for key in fieldnames})


def write_markdown(
    grouped: dict[str, list[dict[str, Any]]], counts: Counter[str]
) -> None:
    lines = [
        "# 銭形平次 未解決本文トリアージ",
        "",
        f"- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 未解決総数: {sum(counts.values())}",
        f"- 国会図書館候補: {counts['ndl_candidate']}",
        f"- 外部公開テキスト候補: {counts['external_public_candidate']}",
        f"- 本文不在濃厚: {counts['likely_text_missing']}",
        "",
    ]
    for bucket in (
        "ndl_candidate",
        "external_public_candidate",
        "likely_text_missing",
    ):
        lines.append(f"## {BUCKET_LABELS[bucket]} ({counts[bucket]})")
        lines.append("")
        for item in grouped[bucket]:
            meta = " / ".join(
                part
                for part in [
                    item.get("publication_years", ""),
                    item.get("magazines", ""),
                ]
                if part
            )
            suffix = f" — {meta}" if meta else ""
            lines.append(f"- {item['title']}{suffix} / {item['reason']}")
        lines.append("")
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    catalog = load_catalog()
    manifest = load_manifest()
    items = manifest.get("items", [])
    triage_items: list[dict[str, Any]] = []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    counts: Counter[str] = Counter()

    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).strip() in SKIP_STATUSES:
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        row = catalog.get(title, {})
        bucket, reason = classify(title, row)
        label = BUCKET_LABELS[bucket]
        item["status"] = bucket
        item["lookup_bucket"] = bucket
        item["lookup_label"] = label
        item["lookup_reason"] = reason
        item["ndl_search_url"] = ndl_search_url(title, row)
        item["external_search_query"] = external_search_query(title, row)
        item["notes"] = f"{label}: {reason}"
        triage_item = {
            "title": title,
            "bucket": bucket,
            "bucket_label": label,
            "reason": reason,
            "publication_years": str(row.get("publication_years", "")).strip(),
            "magazines": str(row.get("magazines", "")).strip(),
            "has_channel_entry": str(row.get("has_channel_entry", "")).strip(),
            "has_audio_archive": str(row.get("has_audio_archive", "")).strip(),
            "ndl_search_url": item["ndl_search_url"],
            "external_search_query": item["external_search_query"],
        }
        triage_items.append(triage_item)
        grouped[bucket].append(triage_item)
        counts[bucket] += 1

    manifest["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = {
        "generated_at": manifest["generated_at"],
        "total": sum(counts.values()),
        "counts": dict(counts),
        "items": triage_items,
    }
    REPORT_JSON.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(triage_items)
    write_markdown(grouped, counts)

    print(f"Wrote: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Wrote: {REPORT_JSON.relative_to(ROOT)}")
    print(f"Wrote: {REPORT_CSV.relative_to(ROOT)}")
    print(f"Wrote: {REPORT_MD.relative_to(ROOT)}")
    print(f"Unresolved total: {sum(counts.values())}")
    print(f"NDL candidates: {counts['ndl_candidate']}")
    print(f"External public candidates: {counts['external_public_candidate']}")
    print(f"Likely text missing: {counts['likely_text_missing']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
