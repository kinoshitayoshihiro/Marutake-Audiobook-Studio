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
MANIFEST_PATH = ROOT / "reports" / "yoshikawa_aozora_manifest.json"
REPORT_PATH = ROOT / "reports" / "yoshikawa_aozora_resolution_report.json"

AOZORA_CSV_URL = "https://www.aozora.gr.jp/index_pages/list_person_all_extended_utf8.zip"
AOZORA_AUTHOR_ID = "001562"

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
        "鬪": "闘",
        "麥": "麦",
        "鐵": "鉄",
        "郞": "郎",
        "櫻": "桜",
    }
)
PUNCT_RE = re.compile(
    r"[\s\u3000・･\-―‐ー\(\)（）\[\]【】〔〕「」『』〈〉《》＜＞"
    r"、。,.!！?？:：;；/／\\]"
)

TITLE_ALIASES = {
    "しんだ千鳥": ["死んだ千鳥"],
    "次郎吉格子": ["治郎吉格子"],
    "田崎早雲とその子": ["田崎草雲とその子"],
    "細川ガラシャ夫人": ["細川ガラシヤ夫人"],
    "洟かみ浪人": ["濞かみ浪人"],
}


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
    return normalized.strip().lower()


def normalize_author_id(value: str) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits.zfill(6)


def download_aozora_rows() -> list[dict[str, str]]:
    request = urllib.request.Request(
        AOZORA_CSV_URL,
        headers={"User-Agent": "GitHub-Copilot/yoshikawa-aozora-resolver"},
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


def sort_key(row: dict[str, str]) -> tuple[Any, ...]:
    subtitle = str(row.get("副題", "")).strip()
    number_match = re.match(r"^(\d+)", subtitle)
    number = int(number_match.group(1)) if number_match else 9999
    return (
        number,
        orthography_rank(row),
        str(row.get("作品ID", "")).strip(),
    )


def extract_candidates(row: dict[str, str]) -> list[str]:
    title = str(row.get("作品名", "")).strip()
    subtitle = str(row.get("副題", "")).strip()
    values = [title]
    if subtitle:
        values.append(f"{title} {subtitle}")
        values.append(f"{title}　{subtitle}")
        values.append(subtitle)
    return [value for value in values if value]


def build_indexes(rows: list[dict[str, str]]) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    exact: dict[str, list[dict[str, str]]] = defaultdict(list)
    normalized: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if normalize_author_id(row.get("人物ID", "")) != AOZORA_AUTHOR_ID:
            continue
        for candidate in extract_candidates(row):
            exact[candidate].append(row)
            normalized[normalize_title(candidate)].append(row)
    return exact, normalized


def row_match_score(item_title: str, row: dict[str, str]) -> tuple[int, int, int]:
    title = str(row.get("作品名", "")).strip()
    subtitle = str(row.get("副題", "")).strip()
    item_norm = normalize_title(item_title)
    title_norm = normalize_title(title)
    subtitle_norm = normalize_title(subtitle)
    combined_norm = normalize_title(f"{title} {subtitle}")
    direct = 0 if item_norm == title_norm or item_norm == combined_norm else 1
    contains = 0 if subtitle_norm and subtitle_norm in item_norm else 1
    return (direct, contains, sort_key(row)[0])


def pick_candidates(item_title: str, exact_index: dict[str, list[dict[str, str]]], normalized_index: dict[str, list[dict[str, str]]]) -> tuple[list[dict[str, str]], str]:
    exact = exact_index.get(item_title, [])
    if exact:
        return sorted(exact, key=sort_key), "exact"

    normalized = normalized_index.get(normalize_title(item_title), [])
    if normalized:
        return sorted(normalized, key=sort_key), "normalized"

    for alias in TITLE_ALIASES.get(item_title, []):
        exact = exact_index.get(alias, [])
        if exact:
            return sorted(exact, key=sort_key), "alias-exact"

        normalized = normalized_index.get(normalize_title(alias), [])
        if normalized:
            return sorted(normalized, key=sort_key), "alias-normalized"

    title_only_matches = normalized_index.get(normalize_title(item_title.split()[0]), [])
    if title_only_matches:
        ranked = sorted(title_only_matches, key=lambda row: row_match_score(item_title, row))
        best_prefix = str(ranked[0].get("作品名", "")).strip()
        filtered = [row for row in ranked if str(row.get("作品名", "")).strip() == best_prefix]
        suffix = item_title.replace(best_prefix, "", 1).strip()
        if suffix:
            suffix_norm = normalize_title(suffix)
            narrowed = [
                row
                for row in filtered
                if suffix_norm and suffix_norm in normalize_title(str(row.get("副題", "")).strip())
            ]
            if narrowed:
                filtered = narrowed
        return sorted(filtered, key=sort_key), "series-prefix"

    return [], "unmatched"


def build_match_payload(row: dict[str, str]) -> dict[str, str]:
    return {
        "work_id": str(row.get("作品ID", "")).strip(),
        "title": str(row.get("作品名", "")).strip(),
        "subtitle": str(row.get("副題", "")).strip(),
        "card_url": str(row.get("図書カードURL", "")).strip(),
        "text_url": str(row.get("テキストファイルURL", "")).strip(),
        "html_url": str(row.get("XHTML/HTMLファイルURL", "")).strip(),
        "orthography": str(row.get("文字遣い種別", "")).strip(),
    }


def resolve_item(item: dict[str, Any], exact_index: dict[str, list[dict[str, str]]], normalized_index: dict[str, list[dict[str, str]]]) -> tuple[dict[str, Any], dict[str, Any]]:
    title = str(item.get("title", "")).strip()
    candidates, match_type = pick_candidates(title, exact_index, normalized_index)

    if not candidates:
        item["aozora_matches"] = []
        item["aozora_card_url"] = ""
        item["aozora_text_url"] = ""
        item["status"] = "unresolved"
        item["notes"] = "青空文庫CSVで一致候補を確認できず。個別表記で再照合が必要。"
        return item, {
            "title": title,
            "matched": False,
            "match_type": match_type,
            "candidate_count": 0,
        }

    matches = [build_match_payload(row) for row in candidates]
    item["aozora_matches"] = matches
    item["aozora_card_url"] = matches[0]["card_url"]
    item["aozora_text_url"] = matches[0]["text_url"]
    item["normalized_title"] = matches[0]["title"]
    item["status"] = "resolved_series" if len(matches) > 1 else "resolved_single"

    note_parts = [f"青空文庫CSV照合済み（{match_type}）", f"候補数: {len(matches)}"]
    if len(matches) > 1:
        note_parts.append("分冊作品として取得可能")
    if any(match["text_url"] for match in matches):
        note_parts.append("テキストURLあり")
    item["notes"] = "。".join(note_parts) + "。"

    return item, {
        "title": title,
        "matched": True,
        "match_type": match_type,
        "candidate_count": len(matches),
        "first_work_id": matches[0]["work_id"],
    }


def main() -> int:
    manifest = load_manifest()
    rows = download_aozora_rows()
    exact_index, normalized_index = build_indexes(rows)

    results: list[dict[str, Any]] = []
    resolved_items: list[dict[str, Any]] = []
    for item in manifest.get("items", []):
        resolved_item, result = resolve_item(item, exact_index, normalized_index)
        resolved_items.append(resolved_item)
        results.append(result)

    manifest["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    manifest["items"] = resolved_items
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "author_id": AOZORA_AUTHOR_ID,
        "resolved": sum(1 for item in resolved_items if str(item.get("status", "")).startswith("resolved")),
        "unresolved": sum(1 for item in resolved_items if item.get("status") == "unresolved"),
        "results": results,
    }
    REPORT_PATH.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote: {MANIFEST_PATH.relative_to(ROOT)}")
    print(f"Report: {REPORT_PATH.relative_to(ROOT)}")
    print(f"Resolved: {summary['resolved']}")
    print(f"Unresolved: {summary['unresolved']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())