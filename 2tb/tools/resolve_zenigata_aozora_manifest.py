#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import io
import json
import re
import unicodedata
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "reports" / "zenigata_aozora_manifest.json"
REPORT_PATH = ROOT / "reports" / "zenigata_aozora_resolution_report.json"

AOZORA_CSV_URL = (
    "https://www.aozora.gr.jp/index_pages/" "list_person_all_extended_utf8.zip"
)
AOZORA_AUTHOR_ID = "001670"

AUTO_STATUSES = {
    "needs_lookup",
    "unresolved",
    "resolved",
    "local_text_present",
    "local_bookdata_ready",
}

TITLE_TRANSLATION = str.maketrans(
    {
        "處": "処",
        "變": "変",
        "卷": "巻",
        "顏": "顔",
        "盜": "盗",
        "藝": "芸",
        "舖": "舗",
        "帶": "帯",
        "從": "従",
        "拜": "拝",
        "峯": "峰",
        "冩": "写",
        "戀": "恋",
        "兒": "児",
        "價": "価",
        "圓": "円",
        "錢": "銭",
        "傳": "伝",
        "靈": "霊",
        "龍": "竜",
        "龜": "亀",
        "學": "学",
        "壽": "寿",
        "淺": "浅",
        "德": "徳",
        "舊": "旧",
        "體": "体",
        "觸": "触",
        "國": "国",
        "寢": "寝",
        "廣": "広",
        "來": "来",
        "廢": "廃",
        "醉": "酔",
        "與": "与",
        "艷": "艶",
        "嶋": "島",
        "邊": "辺",
        "祕": "秘",
        "蠅": "蝿",
        "驛": "駅",
        "惡": "悪",
        "佛": "仏",
        "豫": "予",
        "碎": "砕",
        "燈": "灯",
        "曉": "暁",
        "舘": "館",
        "竊": "窃",
        "巖": "岩",
        "搜": "捜",
        "默": "黙",
        "舜": "舜",
        "龕": "龕",
        "澤": "沢",
        "驅": "駆",
        "獨": "独",
        "辯": "弁",
        "雙": "双",
        "惱": "悩",
        "寬": "寛",
        "寶": "宝",
        "儘": "尽",
        "鹽": "塩",
        "蟲": "虫",
        "實": "実",
        "艷": "艶",
        "鬪": "闘",
        "攷": "考",
        "麥": "麦",
        "鐵": "鉄",
        "郞": "郎",
        "龜": "亀",
        "櫻": "桜",
        "薔": "薔",
        "薇": "薇",
    }
)
PUNCT_RE = re.compile(
    r"[\s\u3000・･\-―‐ー\(\)（）\[\]【】〔〕「」『』〈〉《》＜＞"
    r"、。,.!！?？:：;；/／\\]"
)


def load_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    items = data.get("items", []) if isinstance(data, dict) else []
    if not isinstance(items, list):
        raise ValueError("manifest items is not a list")
    return data


def normalize_title(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = normalized.translate(TITLE_TRANSLATION)
    normalized = PUNCT_RE.sub("", normalized)
    return normalized.strip()


def normalize_author_id(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits.zfill(6)


def download_aozora_rows() -> list[dict[str, str]]:
    request = urllib.request.Request(
        AOZORA_CSV_URL,
        headers={"User-Agent": "GitHub-Copilot/zenigata-aozora-resolver"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        name = archive.namelist()[0]
        text = archive.read(name).decode("utf-8-sig", errors="replace")
    return list(csv.DictReader(io.StringIO(text)))


def orthography_rank(row: dict[str, str]) -> int:
    label = str(row.get("文字遣い種別", "")).strip()
    order = {
        "新字新仮名": 0,
        "新字旧仮名": 1,
        "旧字旧仮名": 2,
    }
    return order.get(label, 9)


def choose_best_candidate(candidates: list[dict[str, str]]) -> dict[str, str]:
    return sorted(
        candidates,
        key=lambda row: (
            0 if str(row.get("テキストファイルURL", "")).strip() else 1,
            orthography_rank(row),
            str(row.get("公開日", "")),
            str(row.get("作品ID", "")),
        ),
    )[0]


def clean_catalog_title(text: str) -> str:
    value = str(text or "").strip()
    value = re.sub(r"^\d+[\s　]+", "", value)
    return value.strip()


def extract_candidate_titles(row: dict[str, str]) -> list[str]:
    titles: list[str] = []
    for field in ("作品名", "副題"):
        clean = clean_catalog_title(row.get(field, ""))
        if clean and clean not in titles:
            titles.append(clean)
    return titles


def build_indexes(
    rows: list[dict[str, str]],
) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    exact: dict[str, list[dict[str, str]]] = defaultdict(list)
    normalized: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if normalize_author_id(row.get("人物ID", "")) != AOZORA_AUTHOR_ID:
            continue
        candidate_titles = extract_candidate_titles(row)
        if not candidate_titles:
            continue
        for title in candidate_titles:
            exact[title].append(row)
            normalized[normalize_title(title)].append(row)
    return exact, normalized


def default_local_note(has_local_text: bool, has_bookdata: bool) -> str:
    if has_local_text and has_bookdata:
        return "手持ち本文とbookdataあり。青空本文が必要ならURL解決のみ追加。"
    if has_local_text:
        return "手持ち本文あり。青空照合は任意、bookdata草案生成対象。"
    return "手持ち本文なし。青空文庫→国会図書館→外部公開テキストの順に照合。"


def resolve_item(
    item: dict[str, Any],
    exact_index: dict[str, list[dict[str, str]]],
    normalized_index: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    title = str(item.get("title", "")).strip()
    existing_status = str(item.get("status", "")).strip()
    existing_notes = str(item.get("notes", "")).strip()
    existing_card = str(item.get("aozora_card_url", "")).strip()
    existing_text = str(item.get("aozora_text_url", "")).strip()
    has_local_text = bool(item.get("has_local_text"))
    has_bookdata = bool(item.get("has_bookdata"))

    candidates = exact_index.get(title, [])
    match_type = "exact"
    if not candidates:
        candidates = normalized_index.get(normalize_title(title), [])
        match_type = "normalized"

    if candidates:
        row = choose_best_candidate(candidates)
        aozora_title = str(row.get("作品名", "")).strip()
        text_url = str(row.get("テキストファイルURL", "")).strip()
        html_url = str(row.get("XHTML/HTMLファイルURL", "")).strip()
        note_parts = [
            f"青空文庫CSV照合済み（{match_type}）",
            f"表記: {str(row.get('文字遣い種別', '')).strip() or '不明'}",
        ]
        if aozora_title and aozora_title != title:
            note_parts.append(f"青空題名: {aozora_title}")
        note_parts.append("テキストURLあり" if text_url else "テキストURLなし")
        if html_url:
            note_parts.append("HTML公開あり")
        item["normalized_title"] = aozora_title or title
        item["aozora_card_url"] = str(row.get("図書カードURL", "")).strip()
        item["aozora_text_url"] = text_url
        item["status"] = "resolved"
        item["notes"] = (
            "。".join(part for part in note_parts if part).strip("。") + "。"
        )
        return item, {
            "matched": True,
            "match_type": match_type,
            "candidate_count": len(candidates),
            "changed": (existing_card != item["aozora_card_url"])
            or (existing_text != item["aozora_text_url"])
            or (existing_status != "resolved"),
            "has_text_url": bool(text_url),
        }

    if existing_status and existing_status not in AUTO_STATUSES:
        return item, {
            "matched": False,
            "match_type": "manual",
            "candidate_count": 0,
            "changed": False,
            "has_text_url": bool(existing_text),
        }

    if existing_card or existing_text:
        return item, {
            "matched": False,
            "match_type": "preserved",
            "candidate_count": 0,
            "changed": False,
            "has_text_url": bool(existing_text),
        }

    if has_local_text and has_bookdata:
        item["status"] = "local_bookdata_ready"
        item["notes"] = existing_notes or default_local_note(True, True)
    elif has_local_text:
        item["status"] = "local_text_present"
        item["notes"] = existing_notes or default_local_note(True, False)
    else:
        item["status"] = "unresolved"
        item["notes"] = (
            "青空文庫CSV（野村胡堂）で未一致。国会図書館・外部公開テキスト要確認。"
        )
    return item, {
        "matched": False,
        "match_type": "none",
        "candidate_count": 0,
        "changed": (
            existing_status != item.get("status", "")
            or existing_notes != item.get("notes", "")
        ),
        "has_text_url": False,
    }


def main() -> int:
    manifest = load_manifest()
    items = manifest.get("items", [])
    rows = download_aozora_rows()
    exact_index, normalized_index = build_indexes(rows)

    resolved_count = 0
    unresolved_count = 0
    newly_resolved = 0
    resolved_with_text = 0
    resolved_missing_local = 0
    ambiguous_matches = 0
    unresolved_titles: list[str] = []

    for raw_item in items:
        if not isinstance(raw_item, dict):
            continue
        item, info = resolve_item(raw_item, exact_index, normalized_index)
        if item.get("status") == "resolved":
            resolved_count += 1
            if info.get("changed"):
                newly_resolved += 1
            if info.get("has_text_url"):
                resolved_with_text += 1
            if not bool(item.get("has_local_text")):
                resolved_missing_local += 1
        else:
            unresolved_count += 1
            unresolved_titles.append(str(item.get("title", "")).strip())
        if int(info.get("candidate_count", 0)) > 1:
            ambiguous_matches += 1

    manifest["generated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = {
        "generated_at": manifest["generated_at"],
        "source_url": AOZORA_CSV_URL,
        "aozora_author_id": AOZORA_AUTHOR_ID,
        "aozora_author_name": "野村胡堂",
        "aozora_catalog_rows": sum(
            1
            for row in rows
            if normalize_author_id(row.get("人物ID", "")) == AOZORA_AUTHOR_ID
        ),
        "aozora_catalog_titles_indexed": len(exact_index),
        "manifest_items": len(items),
        "resolved": resolved_count,
        "resolved_with_text_url": resolved_with_text,
        "resolved_without_local_text": resolved_missing_local,
        "unresolved": unresolved_count,
        "newly_resolved_or_updated": newly_resolved,
        "ambiguous_matches": ambiguous_matches,
        "sample_unresolved_titles": unresolved_titles[:100],
    }
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Wrote: {REPORT_PATH.relative_to(ROOT)}")
    print(f"Aozora rows indexed: {report['aozora_catalog_rows']}")
    print(f"Aozora titles indexed: {report['aozora_catalog_titles_indexed']}")
    print(f"Resolved: {resolved_count}")
    print(f"Resolved with text URL: {resolved_with_text}")
    print(f"Resolved without local text: {resolved_missing_local}")
    print(f"Unresolved: {unresolved_count}")
    print(f"Ambiguous matches: {ambiguous_matches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
