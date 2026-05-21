#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import io
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import vrew_subtitle_core as vrew_core

try:
    from pykakasi import kakasi  # type: ignore
except ImportError:
    kakasi = None

build_zenigata_catalog_maps = None
match_zenigata_catalog_row = None
try:
    import importlib.util
    _ZENIGATA_HELPER_PATH = Path(__file__).resolve().parents[1] / "youtube_channel_report" / "build_zenigata_shortworks_catalog.py"
    _ZENIGATA_HELPER_SPEC = importlib.util.spec_from_file_location("zenigata_shortworks_helper", _ZENIGATA_HELPER_PATH)
    if _ZENIGATA_HELPER_SPEC and _ZENIGATA_HELPER_SPEC.loader:
        _zenigata_helper = importlib.util.module_from_spec(_ZENIGATA_HELPER_SPEC)
        _ZENIGATA_HELPER_SPEC.loader.exec_module(_zenigata_helper)
        build_zenigata_catalog_maps = _zenigata_helper.build_catalog_maps
        match_zenigata_catalog_row = _zenigata_helper.match_catalog_row
except Exception:
    build_zenigata_catalog_maps = None
    match_zenigata_catalog_row = None

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
CSV_PATH = REPORTS_DIR / "zenigata_heiji_works_catalog.csv"
OUT_PATH = REPORTS_DIR / "zenigata_heiji_search.html"
STATE_PATH = REPORTS_DIR / "zenigata_heiji_compilation_state.json"
RECORDING_STATE_PATH = REPORTS_DIR / "zenigata_heiji_recording_state.json"
BUNDLE_REVIEW_QUEUE_PATH = REPORTS_DIR / "zenigata_bundle_review_queue.json"
COMPILATION_MD_PATH = REPORTS_DIR / "zenigata_heiji_compilation_candidates.md"
NEEDS_RECORDING_MD_PATH = REPORTS_DIR / "zenigata_heiji_needs_recording.md"
NEEDS_RECORDING_CSV_PATH = REPORTS_DIR / "zenigata_heiji_needs_recording.csv"
SYNOPSIS_GAPS_MD_PATH = REPORTS_DIR / "zenigata_heiji_synopsis_gaps.md"
SYNOPSIS_ENRICHMENT_JSON_PATH = REPORTS_DIR / "zenigata_heiji_synopsis_enrichment.json"
SYNOPSIS_LLM_JSON_PATH = REPORTS_DIR / "zenigata_heiji_synopsis_llm.json"
TEXT_OVERRIDE_PATH = REPORTS_DIR / "zenigata_text_overrides.json"
THEME_SCORE_PATH = REPORTS_DIR / "zenigata_theme_match_scores.json"
AOZORA_MANIFEST_PATH = REPORTS_DIR / "zenigata_aozora_manifest.json"
VREW_OUTPUT_DIR = REPORTS_DIR / "zenigata_vrew"
SEED_SHORTWORKS_PATH = REPORTS_DIR / "zenigata_seed_shortworks.csv"
RERECORDED_LATEST_PATH = ROOT / "youtube_channel_report" / "old_channel_report" / "zenigata_rerecorded_latest_only.csv"
CURRENT_CHANNEL_REPORT_PATH = ROOT / "youtube_channel_report" / "youtube_video_report_last_90_days_all_videos.csv"
OLD_CHANNEL_ZENIGATA_PATH = ROOT / "youtube_channel_report" / "old_channel_report" / "zenigata_upload_inventory.csv"
CURRENT_SOURCE_ROOT = Path("/Volumes/SSD-PUTA - Data/AudioBook/02_銭形平次捕物控")
READING_LIBRARY_ROOT = ROOT / "Reading_library" / "銭形平次捕物控"
MANUAL_TEXT_ROOTS = (CURRENT_SOURCE_ROOT, READING_LIBRARY_ROOT)

LOCAL_STORAGE_KEY = "zenigataHeijiCompilationStateV1"
BOOKDATA_DETAIL_CACHE: dict[str, dict[str, Any]] = {}
DITTO_MARKS = {"〃", "同上"}
TITLE_LINEAGE_OVERRIDES = {
    "金色の処女": "長編・冒険",
    "金色の乙女": "長編・冒険",
}
THEME_NORMALIZATION_MAP = {
    "八五郎活躍": "八五郎・ガラッ八篇",
    "八五郎篇": "八五郎・ガラッ八篇",
    "ガラッ八篇": "八五郎・ガラッ八篇",
    "八五郎活躍篇": "八五郎・ガラッ八篇",
    "恋愛・嫉妬": "恋愛・嫉妬篇",
    "恋愛・嫉妬篇": "恋愛・嫉妬篇",
    "人情・家族": "人情・家族篇",
    "人情・家族篇": "人情・家族篇",
}
CHARACTER_NOISE_WORDS = {
    "おります",
    "おりました",
    "おる",
    "いる",
    "あり",
    "あります",
    "でした",
    "という",
    "など",
    "もの",
    "こと",
    "それ",
    "これ",
}
SYNOPSIS_PLACEHOLDER_MARKERS = (
    "要補筆",
    "未取得",
    "要約未設定",
    "既存カタログから要約未取得",
)
GENERIC_SUMMARY_TEXTS = {
    "江戸を舞台にした捕物事件。",
    "要約未設定",
    "未設定",
}
INCIDENT_KEYWORDS = (
    "殺",
    "死",
    "盗",
    "奪",
    "消え",
    "縊",
    "絞",
    "首",
    "血",
    "骸",
    "怪",
    "不思議",
    "下手人",
    "事件",
)
ACTION_KEYWORDS = ("平次", "八五郎", "ガラッ八")
ACTION_VERBS = (
    "調べ",
    "追",
    "見張",
    "駆けつけ",
    "乗り出",
    "首を突っ込",
    "見破",
    "捕",
)
KANA_BUCKETS = [
    ("あ", "あ", tuple("あいうえおぁぃぅぇぉ")),
    ("か", "か", tuple("かきくけこがぎぐげご")),
    ("さ", "さ", tuple("さしすせそざじずぜぞ")),
    ("た", "た", tuple("たちつてとだぢづでど")),
    ("な", "な", tuple("なにぬねの")),
    ("は", "は", tuple("はひふへほばびぶべぼぱぴぷぺぽ")),
    ("ま", "ま", tuple("まみむめも")),
    ("や", "や", tuple("やゆよゃゅょ")),
    ("ら", "ら", tuple("らりるれろ")),
    ("わ", "わ", tuple("わをんゎ")),
]


def title_to_hiragana(text: str) -> str:
    if not text:
        return ""
    if kakasi is not None:
        try:
            converter = kakasi()
            return "".join(item["hira"] for item in converter.convert(text))
        except Exception:
            pass
    return text


def kana_bucket_for_title(title: str) -> str:
    reading = title_to_hiragana(title)
    for ch in reading:
        if not re.match(r"[ぁ-ん]", ch):
            continue
        for label, _display, chars in KANA_BUCKETS:
            if ch in chars:
                return label
        return "他"
    return "他"


def decade_label(year: int) -> str:
    if 1000 <= year < 3000:
        return f"{year // 10 * 10}年代"
    return "年不明"


def year_sort_key(publication_years: str) -> int:
    match = re.search(r"(1[0-9]{3}|20[0-9]{2})", str(publication_years or ""))
    if match:
        return int(match.group(1))
    return 9999


def choose_non_hachigoro_theme(themes: list[str]) -> str:
    for theme in themes:
        clean = str(theme).strip()
        if clean and clean not in {"八五郎", "ガラッ八", "八五郎活躍"}:
            return clean
    return "事件のどんでん返し"


def has_hachigoro_focus(*parts: Any) -> bool:
    text = " ".join(str(part or "") for part in parts)
    return "八五郎" in text or "ガラッ八" in text


def refine_story_lineage(
    title: str,
    story_lineage: str,
    theme_secondary: list[str],
    characters: list[str],
    synopsis: str,
    summary: str,
) -> str:
    if title in TITLE_LINEAGE_OVERRIDES:
        return TITLE_LINEAGE_OVERRIDES[title]
    if story_lineage == "八五郎活躍" and not has_hachigoro_focus(
        title,
        *theme_secondary,
        *characters,
        synopsis,
        summary,
    ):
        return choose_non_hachigoro_theme(theme_secondary)
    return story_lineage


def group_id(source_kind: str, theme: str) -> str:
    safe: list[str] = []
    for ch in f"{source_kind}-{theme}":
        if ch.isalnum():
            safe.append(ch.lower())
        elif ch in {"-", "_"}:
            safe.append(ch)
        else:
            safe.append("-")
    return "".join(safe).strip("-") or "group"


def normalize_theme_label(theme: Any) -> str:
    clean = str(theme or "").strip()
    if not clean:
        return ""
    return THEME_NORMALIZATION_MAP.get(clean, clean)


def normalize_theme_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        clean = normalize_theme_label(value)
        if clean and clean not in normalized:
            normalized.append(clean)
    return normalized


def is_character_noise(text: Any) -> bool:
    clean = str(text or "").strip()
    if not clean:
        return True
    if clean in CHARACTER_NOISE_WORDS:
        return True
    if len(clean) >= 10:
        return True
    if len(clean) >= 8 and re.fullmatch(r"[ぁ-んー]+", clean):
        return True
    if re.search(r"(という|している|された|される|だった|である|らしい)$", clean):
        return True
    if re.search(r"(という|している|でした|おります|おりました)$", clean):
        return True
    if re.search(
        r"(を殺し|が死ん|の死|が消え|が逃げ|を追い|を追う|が泊|は默|は黙|じゃ|で|と|に|を|が|は)$",
        clean,
    ):
        return True
    if re.search(r"[をがにはでとへの][一-龥々ヶぁ-ん]{2,}$", clean):
        return True
    if re.fullmatch(r"お前(?:さん)?", clean):
        return True
    if re.search(r"[、。.,/()（）\s]", clean):
        return True
    return False


def clean_character_names(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for value in values:
        candidate = str(value or "").strip()
        if is_character_noise(candidate):
            continue
        if candidate not in cleaned:
            cleaned.append(candidate)
    return cleaned


def should_fill_synopsis(row: dict[str, Any]) -> bool:
    synopsis = str(row.get("synopsis", "") or "").strip()
    summary = str(row.get("summary", "") or "").strip()
    combined = " ".join(part for part in [synopsis, summary] if part).strip()
    if not combined:
        return True
    return any(marker in combined for marker in SYNOPSIS_PLACEHOLDER_MARKERS)


def make_compilation_title(theme: str, source_kind: str) -> str:
    normalized = normalize_theme_label(theme)
    if normalized.endswith(("篇", "編")):
        return f"銭形平次捕物控 総集編『{normalized}』"
    if source_kind == "lineage":
        return f"銭形平次捕物控 総集編『{normalized}』"
    return f"銭形平次捕物控 総集編『{normalized}篇』"


def normalize_state(raw: Any) -> dict[str, Any]:
    adopted_candidates: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for entry in raw.get("adopted_candidates", []):
            if not isinstance(entry, dict):
                continue
            work_titles = [
                str(title).strip()
                for title in entry.get("work_titles", [])
                if str(title).strip()
            ]
            if not work_titles:
                continue
            adopted_candidates.append(
                {
                    "candidate_id": str(entry.get("candidate_id", "")).strip(),
                    "theme": normalize_theme_label(entry.get("theme", "")),
                    "title": str(entry.get("title", "")).strip(),
                    "work_titles": work_titles,
                    "needs_recording_titles": [
                        str(title).strip()
                        for title in entry.get("needs_recording_titles", [])
                        if str(title).strip()
                    ],
                    "adopted_at": str(entry.get("adopted_at", "")).strip(),
                }
            )
    return {"adopted_candidates": adopted_candidates}


def load_state() -> dict[str, Any]:
    if STATE_PATH.exists():
        try:
            state = normalize_state(json.loads(STATE_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            state = normalize_state({})
    else:
        state = normalize_state({})
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state


def normalize_recording_state(raw: Any) -> dict[str, Any]:
    recording_overrides: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for entry in raw.get("recording_overrides", []):
            if not isinstance(entry, dict):
                continue
            title = str(entry.get("title", "")).strip()
            if not title:
                continue
            recording_overrides.append(
                {
                    "title": title,
                    "is_recorded": bool(entry.get("is_recorded", False)),
                    "note": str(entry.get("note", "")).strip(),
                    "updated_at": str(entry.get("updated_at", "")).strip(),
                }
            )
    return {"recording_overrides": recording_overrides}


def load_recording_state() -> dict[str, Any]:
    if RECORDING_STATE_PATH.exists():
        try:
            state = normalize_recording_state(
                json.loads(RECORDING_STATE_PATH.read_text(encoding="utf-8"))
            )
        except json.JSONDecodeError:
            state = normalize_recording_state({})
    else:
        state = normalize_recording_state({})
    RECORDING_STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state


def recording_override_map(
    recording_state: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        str(entry.get("title", "")).strip(): entry
        for entry in recording_state.get("recording_overrides", [])
        if str(entry.get("title", "")).strip()
    }


def load_rerecorded_latest_map() -> dict[str, dict[str, str]]:
    if not RERECORDED_LATEST_PATH.exists():
        return {}
    try:
        with RERECORDED_LATEST_PATH.open(encoding="utf-8-sig", newline="") as handle:
            return {
                str(row.get("normalized_title", "")).strip(): row
                for row in csv.DictReader(handle)
                if str(row.get("normalized_title", "")).strip()
            }
    except OSError:
        return {}


def load_channel_presence_maps(catalog_rows: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    if build_zenigata_catalog_maps is None or match_zenigata_catalog_row is None:
        return {}, {}
    exact_map, normalized_map, normalized_keys = build_zenigata_catalog_maps(catalog_rows)

    def collect(path: Path, already_zenigata: bool = False) -> dict[str, list[dict[str, str]]]:
        if not path.exists():
            return {}
        try:
            with path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except OSError:
            return {}
        matched: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            title = str(row.get("title", "") or row.get("video_title", "") or "").strip()
            if not title:
                continue
            if not already_zenigata and "銭形平次" not in title:
                continue
            matched_title, _catalog_row = match_zenigata_catalog_row(title, exact_map, normalized_map, normalized_keys)
            if not matched_title:
                continue
            matched[matched_title].append({
                "video_id": str(row.get("videoId", row.get("video_id", "")) or "").strip(),
                "title": title,
                "published_at": str(row.get("publishedAt", row.get("published_at", "")) or "").strip(),
            })
        return matched

    return collect(CURRENT_CHANNEL_REPORT_PATH), collect(OLD_CHANNEL_ZENIGATA_PATH, already_zenigata=True)


CURRENT_SOURCE_ALIASES = {
    "鬼女": "鬼女",
    "井戸端の逢い引き": "井戸端の逢引",
    "お染の歎き": "お染の嘆き",
    "南蛮秘宝撰": "南蛮秘法箋",
    "復鬼喜の姿": "復讐鬼の姿",
    "金色の乙女": "金色の処女",
    "呪いの銀釵": "呪いの銀簪",
    "美しき鎌いたち": "美しき鎌鼬",
    "敵討設計書": "敵討設計図",
}
MANUAL_TEXT_SKIP_PARTS = {
    "青空文庫",
    "midjourney_session",
    "image",
    "imageイラスト",
    "済み",
    "まとめ版",
    "配信用",
}


def load_current_source_titles(catalog_rows: list[dict[str, Any]]) -> set[str]:
    if build_zenigata_catalog_maps is None or match_zenigata_catalog_row is None:
        return set()
    if not CURRENT_SOURCE_ROOT.exists():
        return set()
    exact_map, normalized_map, normalized_keys = build_zenigata_catalog_maps(catalog_rows)
    matched: set[str] = set()
    for path in sorted(CURRENT_SOURCE_ROOT.iterdir()):
        if path.name.startswith('.') or path.name in {"image", "名称未設定フォルダ"}:
            continue
        names = [path.stem if path.is_file() else path.name]
        if path.is_dir() and path.name.startswith("000_総集編"):
            for child in sorted(path.iterdir()):
                if child.name.startswith('.'):
                    continue
                names.append(child.stem if child.is_file() else child.name)
        for name in names:
            resolved_title, _catalog_row = match_zenigata_catalog_row(name, exact_map, normalized_map, normalized_keys)
            if resolved_title:
                matched.add(resolved_title)
                continue
            cleaned = clean_manual_text_title(name)
            alias_title = CURRENT_SOURCE_ALIASES.get(cleaned)
            if alias_title:
                matched.add(alias_title)
    return matched


def score_manual_text_candidate(path: Path, root: Path) -> int:
    score = 0
    name = path.name
    text = str(path)
    if root == CURRENT_SOURCE_ROOT:
        score += 80
    elif root == READING_LIBRARY_ROOT:
        score += 40
    if "青空文庫" in text:
        score -= 40
    if any(part in name for part in ("最終", "最終稿", "最終確認")):
        score += 30
    if any(part in name for part in ("下書き", "名称未設定")):
        score -= 25
    score -= len(path.parts)
    return score


def clean_manual_text_title(text: str) -> str:
    cleaned = re.sub(r"^[0-9]+[._]", "", str(text or "")).strip()
    cleaned = cleaned.replace("　前説", "").replace("前説", "").replace("_書き出し", "").strip()
    cleaned = re.sub(r"^野村胡堂\s*", "", cleaned).strip()
    cleaned = cleaned.replace("銭形平次捕物控", " ").replace("錢形平次捕物控", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def discover_manual_text_paths(catalog_rows: list[dict[str, Any]]) -> dict[str, str]:
    if build_zenigata_catalog_maps is None or match_zenigata_catalog_row is None:
        return {}
    exact_map, normalized_map, normalized_keys = build_zenigata_catalog_maps(catalog_rows)
    best: dict[str, tuple[int, str]] = {}
    for root in MANUAL_TEXT_ROOTS:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.txt")):
            if any(part.startswith(".") for part in path.parts):
                continue
            if any(skip in path.parts for skip in MANUAL_TEXT_SKIP_PARTS):
                continue
            resolved_title, _catalog_row = match_zenigata_catalog_row(
                path.stem,
                exact_map,
                normalized_map,
                normalized_keys,
            )
            if not resolved_title:
                cleaned = clean_manual_text_title(path.stem)
                alias_title = CURRENT_SOURCE_ALIASES.get(cleaned)
                if alias_title:
                    resolved_title = alias_title
            if not resolved_title:
                continue
            score = score_manual_text_candidate(path, root)
            path_text = str(path)
            previous = best.get(resolved_title)
            if previous is None or score > previous[0]:
                best[resolved_title] = (score, path_text)
    return {title: path_text for title, (_score, path_text) in best.items()}


def adoption_status_for(in_current_channel: bool, in_old_channel: bool, in_current_source: bool = False) -> tuple[str, str]:
    if in_current_channel:
        return "採用済み", "捕物帳チャンネル掲載済み"
    if in_current_source:
        return "採用済み", "捕物帳チャンネル採用ソースあり"
    if in_old_channel:
        return "旧実績のみ", "人情朗読の旧チャンネル実績あり"
    return "未採用", "現行チャンネル未掲載・旧チャンネル実績なし"


def normalize_review_queue(raw: Any) -> dict[str, Any]:
    source = raw.get("bundles", []) if isinstance(raw, dict) else raw
    bundles: list[dict[str, Any]] = []
    if not isinstance(source, list):
        source = []
    for entry in source:
        if not isinstance(entry, dict):
            continue
        works: list[dict[str, Any]] = []
        for work in entry.get("works", []):
            if not isinstance(work, dict):
                continue
            title = str(work.get("title", "")).strip()
            if not title:
                continue
            works.append(
                {
                    "title": title,
                    "synopsis": str(work.get("synopsis", "")).strip(),
                    "themes": normalize_string_list(work.get("themes", [])),
                    "tags": normalize_string_list(work.get("tags", [])),
                    "characters": normalize_string_list(work.get("characters", [])),
                    "story_lineage": str(work.get("story_lineage", "")).strip(),
                    "bookdata_path": str(work.get("bookdata_path", "")).strip(),
                    "has_local_text": bool(work.get("has_local_text")),
                    "is_recorded": bool(work.get("is_recorded")),
                }
            )
        if not works:
            continue
        bundles.append(
            {
                "bundle_id": str(entry.get("bundle_id", "")).strip(),
                "bundle_group": str(entry.get("bundle_group", "seeded")).strip()
                or "seeded",
                "source_title": str(entry.get("source_title", "")).strip(),
                "theme": normalize_theme_label(entry.get("theme", "")),
                "recommended_title": str(entry.get("recommended_title", "")).strip(),
                "thumbnail_text": str(entry.get("thumbnail_text", "")).strip(),
                "summary": str(entry.get("summary", "")).strip(),
                "review_prompt": str(entry.get("review_prompt", "")).strip(),
                "publication_priority": (
                    str(entry.get("publication_priority", "medium")).strip() or "medium"
                ),
                "review_reason": str(entry.get("review_reason", "")).strip(),
                "review_status": (
                    str(entry.get("review_status", "pending")).strip() or "pending"
                ),
                "estimated_minutes": int(entry.get("estimated_minutes", 0) or 0),
                "overlap_rate": int(entry.get("overlap_rate", 0) or 0),
                "needs_recording_titles": normalize_string_list(
                    entry.get("needs_recording_titles", [])
                ),
                "created_at": str(entry.get("created_at", "")).strip(),
                "works": works,
            }
        )
    return {"bundles": bundles}


def load_review_queue() -> dict[str, Any]:
    if BUNDLE_REVIEW_QUEUE_PATH.exists():
        try:
            state = normalize_review_queue(
                json.loads(BUNDLE_REVIEW_QUEUE_PATH.read_text(encoding="utf-8"))
            )
        except json.JSONDecodeError:
            state = normalize_review_queue({})
    else:
        state = normalize_review_queue({})
    BUNDLE_REVIEW_QUEUE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state


def split_pipe(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str):
        return []
    return [item.strip() for item in value.split("|") if item.strip()]


def split_slash(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not isinstance(value, str):
        return []
    return [item.strip() for item in re.split(r"[／/]", value) if item.strip()]


def normalize_bool(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on", "済", "あり"}


def first_matching_path(paths: list[str], prefix: str) -> str:
    for path in paths:
        clean = str(path).strip()
        if clean.startswith(prefix):
            return clean
    return ""


def report_href_for_path(path_text: str) -> str:
    clean = str(path_text).strip()
    if not clean:
        return ""
    target = ROOT / clean
    return Path(os.path.relpath(target, REPORTS_DIR)).as_posix()


def normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[／/|]\s*", value)
        return [item.strip() for item in parts if item.strip()]
    return []


def normalize_detail_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def normalize_synopsis_llm_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title", "") or "").strip()
    if not title:
        return None
    synopsis = str(raw.get("synopsis", "") or "").strip()
    summary = str(raw.get("summary", "") or "").strip()
    if has_synopsis_placeholder(synopsis):
        synopsis = ""
    if needs_summary_refresh(summary):
        summary = ""
    if not synopsis:
        return None
    if not summary:
        base = synopsis[:90].rstrip("。")
        summary = f"{base}。" if base and not base.endswith("。") else base
    return {
        "title": title,
        "synopsis": synopsis,
        "summary": summary,
        "updated_at": str(raw.get("updated_at", "") or "").strip(),
        "model": str(raw.get("model", "") or "").strip(),
        "source": str(raw.get("source", "llm") or "llm").strip() or "llm",
        "source_path": str(raw.get("source_path", "") or "").strip(),
        "quality": str(raw.get("quality", "") or "").strip(),
    }


def load_synopsis_llm_map() -> dict[str, dict[str, Any]]:
    if not SYNOPSIS_LLM_JSON_PATH.exists():
        return {}
    try:
        raw = json.loads(SYNOPSIS_LLM_JSON_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    source = raw.get("items", []) if isinstance(raw, dict) else raw
    if not isinstance(source, list):
        return {}
    items: dict[str, dict[str, Any]] = {}
    for entry in source:
        normalized = normalize_synopsis_llm_entry(entry)
        if normalized is None:
            continue
        items[str(normalized["title"])] = normalized
    return items


def normalize_text_override_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title", "") or "").strip()
    text_path = str(raw.get("text_path", "") or "").strip()
    if not title or not text_path:
        return None
    editorial_notes = raw.get("editorial_notes", [])
    return {
        "title": title,
        "text_path": text_path,
        "source": str(raw.get("source", "ocr") or "ocr").strip() or "ocr",
        "editorial_notes": (
            [str(note).strip() for note in editorial_notes if str(note).strip()]
            if isinstance(editorial_notes, list)
            else []
        ),
    }


def load_text_override_map() -> dict[str, dict[str, Any]]:
    if not TEXT_OVERRIDE_PATH.exists():
        return {}
    try:
        raw = json.loads(TEXT_OVERRIDE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    source = raw.get("items", []) if isinstance(raw, dict) else raw
    if not isinstance(source, list):
        return {}
    items: dict[str, dict[str, Any]] = {}
    for entry in source:
        normalized = normalize_text_override_entry(entry)
        if normalized is None:
            continue
        items[str(normalized["title"])] = normalized
    return items


def has_synopsis_placeholder(text: Any) -> bool:
    clean = str(text or "").strip()
    if not clean:
        return True
    return any(marker in clean for marker in SYNOPSIS_PLACEHOLDER_MARKERS)


def needs_summary_refresh(text: Any) -> bool:
    clean = str(text or "").strip()
    if not clean:
        return True
    if clean in GENERIC_SUMMARY_TEXTS:
        return True
    return has_synopsis_placeholder(clean)


def first_local_text_path(source_paths: list[str]) -> str:
    for path_text in source_paths:
        clean = str(path_text or "").strip()
        if not clean or not clean.startswith("Reading_library/"):
            continue
        if Path(clean).suffix.lower() in {".txt", ".text"}:
            return clean
    return ""


def preferred_local_text_path(
    title: str,
    source_paths: list[str],
    text_override_map: dict[str, dict[str, Any]],
    manual_text_map: dict[str, str] | None = None,
) -> str:
    override = text_override_map.get(title)
    if override:
        path_text = str(override.get("text_path", "") or "").strip()
        if path_text:
            return path_text
    manual_path = str((manual_text_map or {}).get(title, "") or "").strip()
    if manual_path:
        return manual_path
    return first_local_text_path(source_paths)


def read_text_best_effort(path_text: str) -> str:
    clean = str(path_text or "").strip()
    if not clean:
        return ""
    target = Path(clean)
    if not target.is_absolute():
        target = ROOT / clean
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16le", "utf-16be", "cp932", "shift_jis"):
        try:
            return target.read_text(encoding=encoding)
        except OSError:
            return ""
        except UnicodeDecodeError:
            continue
    try:
        return target.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def strip_aozora_text(text: str, title: str) -> str:
    clean = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    clean = re.sub(r"(?s)-{20,}\n.*?\n-{20,}", "", clean, count=1)
    clean = clean.replace("｜", "")
    clean = clean.replace("銭形平次捕物控", "")
    clean = clean.replace("錢形平次捕物控", "")
    clean = re.sub(r"《[^》]+》", "", clean)
    clean = re.sub(r"［＃[^\]]+］", "", clean)
    clean = re.split(r"(?m)^底本：", clean, maxsplit=1)[0]
    clean = re.split(r"(?m)^入力：", clean, maxsplit=1)[0]
    clean = re.split(r"入力、校正、制作にあたったのは", clean, maxsplit=1)[0]
    lines: list[str] = []
    for index, raw_line in enumerate(clean.split("\n")):
        line = raw_line.strip()
        if index < 8 and line in {"銭形平次捕物控", title, "野村胡堂"}:
            continue
        if re.fullmatch(r"【第[一二三四五六七八九十百]+回】", line):
            continue
        if re.fullmatch(r"[一二三四五六七八九十百]+", line):
            continue
        if line.startswith("青空文庫"):
            continue
        lines.append(raw_line)
    clean = "\n".join(lines)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def safe_filename(value: str, max_len: int = 80) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "_", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = "untitled"
    return text[:max_len].strip().replace(" ", "_")


DEFAULT_VREW_NO_BREAK_PHRASES = {
    "銭形平次",
    "錢形平次",
    "銭形の親分",
    "八五郎",
    "ガラッ八",
    "三輪の万七",
    "お静",
    "笹野新三郎",
    "平次親分",
    "親分",
    "岡っ引",
    "下っ引",
    "御用聞",
    "御用聞き",
}
TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES = {
    "敵討設計図": {
        "敵討設計図",
        "敵討設計書",
        "石原の利助",
        "石原のお品",
        "お品さん",
        "兩國橋",
        "小田原提灯",
    },
    "七人の花嫁": {
        "七人の花嫁",
        "お静",
        "ガラッ八",
        "銭形の平次",
    },
    "南蛮秘法箋": {
        "南蛮秘法箋",
        "田代屋又左衛門",
        "又左衛門",
        "倅の嫁",
        "お冬",
        "小石川水道端",
    },
    "呪いの銀簪": {
        "呪いの銀簪",
        "布袋屋",
        "石原の親分",
        "柳橋",
        "屋形船",
        "銀簪",
    },
    "十手の道": {
        "十手の道",
        "高力左近太夫",
        "志賀玄蕃",
        "志賀内匠",
        "島原",
        "加世",
        "関と申します",
    },
    "復讐鬼の姿": {
        "復讐鬼の姿",
        "笹野新三郎",
        "小田島伝蔵",
        "勇吉",
        "新太郎",
        "お国",
    },
    "遺書の罪": {
        "遺書の罪",
        "ガラツ八",
        "八五郎",
    },
    "飛ぶ若衆": {
        "飛ぶ若衆",
        "谷中",
        "お靜",
        "屠蘇臭い",
    },
    "恋をせぬ女": {
        "恋をせぬ女",
        "菊坂小町",
        "小森屋",
        "お通",
        "由松親分",
        "本郷",
        "向柳原",
    },
    "弱い浪人": {
        "弱い浪人",
        "増田屋金兵衞",
        "金兵衞",
        "明神下",
        "獨り月見",
    },
}
DEFAULT_VREW_FORBIDDEN_LINE_START = set("、。，．？！!)]）｝」』】〕〉》ぁぃぅぇぉゃゅょァィゥェォャュョッー")
DEFAULT_VREW_FORBIDDEN_LINE_END = set("([（｛「『【〔〈《")


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", str(text or "")))


def subtitle_phrase_pool(title: str = "") -> set[str]:
    pool = set(DEFAULT_VREW_NO_BREAK_PHRASES)
    if title:
        pool.update(TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES.get(str(title).strip(), set()))
    return pool


def breaks_no_break_phrase(text: str, break_index: int, phrases: set[str] | None = None) -> bool:
    source = str(text or "")
    if not source or break_index <= 0 or break_index >= len(source):
        return False
    pool = subtitle_phrase_pool()
    if phrases:
        pool.update(str(phrase).strip() for phrase in phrases if str(phrase).strip())
    for phrase in pool:
        start = 0
        while True:
            found = source.find(phrase, start)
            if found < 0:
                break
            if found < break_index < found + len(phrase):
                return True
            start = found + len(phrase)
    return False


def choose_subtitle_break(
    text: str,
    target: int,
    *,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> int:
    clean = str(text or "")
    if len(clean) <= target:
        return len(clean)
    lower = max(1, target - 10)
    upper = min(len(clean) - 1, target + 8)
    best_index = min(target, len(clean) - 1)
    best_score = -10**9
    for index in range(lower, upper + 1):
        left = clean[:index].rstrip()
        right = clean[index:].lstrip()
        if not left or not right:
            continue
        left_last = left[-1]
        right_first = right[0]
        score = -abs(len(left) - target) * 3
        if left_last in "。！？?!」』":
            score += 30
        elif left_last in "、，；：…":
            score += 24
        elif clean[index:index + 2] == "――":
            score += 20
        elif left_last in "）」』】":
            score += 12
        if right_first in DEFAULT_VREW_FORBIDDEN_LINE_START:
            score -= 35
        if left_last in DEFAULT_VREW_FORBIDDEN_LINE_END:
            score -= 30
        if breaks_no_break_phrase(clean, index, phrases):
            score -= 60
        if contains_cjk(left_last + right_first):
            if re.match(r"[ぁ-んァ-ヶー]", left_last) and re.match(r"[ぁ-んァ-ヶー]", right_first):
                score -= 18
            if re.match(r"[一-龠々]", left_last) and re.match(r"[一-龠々]", right_first):
                score -= 14
            if re.match(r"[一-龠々ぁ-んァ-ヶー]", left_last) and re.match(r"[一-龠々ぁ-んァ-ヶー]", right_first):
                score -= 8
        if prefer_dialogue:
            if left_last in "、，。！？?!」』":
                score += 16
            if right_first in "とがもはをにへで":
                score -= 6
        if score > best_score:
            best_score = score
            best_index = index
    return max(1, best_index)


def wrap_subtitle_line(
    text: str,
    width: int = 22,
    *,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    chunks: list[str] = []
    remaining = clean
    while remaining:
        if len(remaining) <= width:
            chunks.append(remaining)
            break
        split_at = choose_subtitle_break(
            remaining,
            width,
            phrases=phrases,
            prefer_dialogue=prefer_dialogue,
        )
        chunk = remaining[:split_at].rstrip()
        remaining = remaining[split_at:].lstrip()
        if not chunk:
            chunk = remaining[:width]
            remaining = remaining[width:]
        chunks.append(chunk)
    return chunks


def split_long_subtitle_fragment(
    text: str,
    target_chars: int,
    *,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    fragments: list[str] = []
    remaining = clean
    while remaining:
        if len(remaining) <= target_chars:
            fragments.append(remaining)
            break
        split_at = choose_subtitle_break(
            remaining,
            target_chars,
            phrases=phrases,
            prefer_dialogue=prefer_dialogue,
        )
        fragment = remaining[:split_at].rstrip()
        remaining = remaining[split_at:].lstrip()
        if not fragment:
            fragment = remaining[:target_chars]
            remaining = remaining[target_chars:]
        fragments.append(fragment)
    return fragments


def split_for_subtitle_blocks(
    sentence: str,
    target_chars: int,
    *,
    phrases: set[str] | None = None,
) -> list[str]:
    clean = re.sub(r"\s+", " ", str(sentence or "")).strip()
    if not clean:
        return []
    fragments: list[str] = []
    quote_pattern = re.compile(r"[「『][^」』]*[」』]?")
    cursor = 0
    for match in quote_pattern.finditer(clean):
        prefix = clean[cursor:match.start()].strip()
        if prefix:
            prefix_parts = [part.strip() for part in re.split(r"(?<=[、，。！？])", prefix) if part.strip()]
            for part in prefix_parts or [prefix]:
                fragments.extend(
                    split_long_subtitle_fragment(part, target_chars, phrases=phrases)
                )
        quoted = match.group(0).strip()
        if quoted:
            fragments.extend(
                split_long_subtitle_fragment(
                    quoted,
                    target_chars,
                    phrases=phrases,
                    prefer_dialogue=True,
                )
            )
        cursor = match.end()
    suffix = clean[cursor:].strip()
    if suffix:
        suffix_parts = [part.strip() for part in re.split(r"(?<=[、，。！？])", suffix) if part.strip()]
        for part in suffix_parts or [suffix]:
            fragments.extend(split_long_subtitle_fragment(part, target_chars, phrases=phrases))
    return [fragment for fragment in fragments if fragment]


def split_japanese_sentences(text: str) -> list[str]:
  normalized = re.sub(r"[ \t\u3000]+", " ", str(text or ""))
  normalized = re.sub(r"([」』])(?=[^\s」』、。，！？?!])", r"\1\n", normalized)
  chunks: list[str] = []
  current: list[str] = []
  index = 0
  quote_depth = 0

  while index < len(normalized):
    char = normalized[index]
    current.append(char)

    if char in "「『":
      quote_depth += 1

    if char in "。！？?!":
      if index + 1 < len(normalized) and normalized[index + 1] in "」』":
        index += 1
        current.append(normalized[index])
        if quote_depth > 0:
          quote_depth -= 1
        chunk = "".join(current).strip()
        if chunk:
          chunks.append(chunk)
        current = []
      elif quote_depth == 0:
        chunk = "".join(current).strip()
        if chunk:
          chunks.append(chunk)
        current = []
    elif char in "」』":
      if quote_depth > 0:
        quote_depth -= 1
      prev_char = normalized[index - 1] if index > 0 else ""
      next_char = normalized[index + 1] if index + 1 < len(normalized) else ""
      if prev_char not in "。！？?!" and (not next_char or next_char.isspace()):
        chunk = "".join(current).strip()
        if chunk:
          chunks.append(chunk)
        current = []

    index += 1

  tail = "".join(current).strip()
  if tail:
    chunks.append(tail)

  sentences: list[str] = []
  for chunk in chunks:
    clean = re.sub(r"\s+", " ", chunk).strip()
    clean = re.sub(r"^[一二三四五六七八九十百上中下]+\s+", "", clean)
    clean = clean.strip()
    if not clean:
      continue
    if any(
      marker in clean
      for marker in (
        "テキスト中に現れる記号",
        "入力者注",
        "青空文庫",
        "ボランティア",
        "底本",
        "入力、校正、制作",
      )
    ):
      continue
    if clean.startswith(("銭形平次捕物控", "錢形平次捕物控")):
      continue
    sentences.append(clean)

  return sentences


def postprocess_subtitle_blocks(
    blocks: list[str],
    *,
    width: int,
    max_lines: int,
    phrases: set[str] | None = None,
) -> list[str]:
    if not blocks:
        return []
    terminals = set("。！？?!」』）】")
    openers = set("「『（【")
    processed = [block.strip() for block in blocks if block and block.strip()]
    changed = True
    while changed:
        changed = False
        merged: list[str] = []
        index = 0
        while index < len(processed):
            current = processed[index]
            if index + 1 < len(processed):
                nxt = processed[index + 1]
                current_plain = current.replace("\n", "")
                next_plain = nxt.replace("\n", "")
                can_merge_short_tail = (
                    len(nxt.splitlines()) == 1
                    and len(next_plain) <= 12
                    and current_plain
                    and next_plain
                    and current_plain[-1] not in terminals
                    and next_plain[0] not in openers
                )
                if can_merge_short_tail:
                    combined = f"{current_plain}{next_plain}"
                    wrapped = wrap_subtitle_line(
                        combined,
                        width=width,
                        phrases=phrases,
                        prefer_dialogue=combined.startswith(("「", "『")),
                    )
                    if 1 <= len(wrapped) <= max_lines:
                        merged.append("\n".join(wrapped))
                        index += 2
                        changed = True
                        continue
            merged.append(current)
            index += 1
        processed = merged
    return processed


def build_vrew_subtitle_text(
    text: str,
    line_width: int = 22,
    max_lines: int = 2,
    *,
    title: str = "",
) -> str:
    sentences = split_japanese_sentences(text)
    blocks: list[str] = []
    target_chars = line_width * max_lines
    phrase_pool = subtitle_phrase_pool(title)
    for sentence in sentences:
        pending = ""
        source_parts = split_for_subtitle_blocks(
            sentence,
            target_chars,
            phrases=phrase_pool,
        ) or [sentence]
        for fragment in source_parts:
            proposal = f"{pending}{fragment}" if pending else fragment
            wrapped = wrap_subtitle_line(
                proposal,
                width=line_width,
                phrases=phrase_pool,
                prefer_dialogue=proposal.startswith(("「", "『")),
            )
            if len(wrapped) <= max_lines:
                pending = proposal
                continue
            if pending:
                cue_lines = wrap_subtitle_line(
                    pending,
                    width=line_width,
                    phrases=phrase_pool,
                    prefer_dialogue=pending.startswith(("「", "『")),
                )
                if cue_lines:
                    blocks.append("\n".join(cue_lines[:max_lines]))
                pending = fragment
            else:
                hard_wrapped = wrap_subtitle_line(
                    fragment,
                    width=line_width,
                    phrases=phrase_pool,
                    prefer_dialogue=fragment.startswith(("「", "『")),
                )
                while hard_wrapped:
                    blocks.append("\n".join(hard_wrapped[:max_lines]))
                    hard_wrapped = hard_wrapped[max_lines:]
                pending = ""
        if pending:
            cue_lines = wrap_subtitle_line(
                pending,
                width=line_width,
                phrases=phrase_pool,
                prefer_dialogue=pending.startswith(("「", "『")),
            )
            while cue_lines:
                blocks.append("\n".join(cue_lines[:max_lines]))
                cue_lines = cue_lines[max_lines:]
    blocks = postprocess_subtitle_blocks(
        blocks,
        width=line_width,
        max_lines=max_lines,
        phrases=phrase_pool,
    )
    return "\n\n".join(block for block in blocks if block.strip()).strip()


vrew_core.DEFAULT_VREW_NO_BREAK_PHRASES.update(DEFAULT_VREW_NO_BREAK_PHRASES)
for _title, _phrases in TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES.items():
  existing = vrew_core.TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES.setdefault(_title, set())
  existing.update(_phrases)


def read_text_best_effort(path_text: str) -> str:
  return vrew_core.read_text_best_effort(path_text)


def strip_aozora_text(text: str, title: str) -> str:
  return vrew_core.strip_aozora_text(
    text,
    title,
    author_names=("野村胡堂",),
    series_titles=("銭形平次捕物控", "錢形平次捕物控"),
  )


def build_text_preview(path_text: str, title: str, limit: int = 420) -> str:
  if not path_text:
    return ""
  try:
    raw = read_text_best_effort(path_text)
  except Exception:
    return ""
  if not raw:
    return ""
  cleaned = strip_aozora_text(raw, title)
  cleaned = re.sub(r"\s+", " ", cleaned).strip()
  if not cleaned:
    return ""
  if len(cleaned) <= limit:
    return cleaned
  return cleaned[:limit].rstrip() + "..."


def safe_filename(value: str, max_len: int = 80) -> str:
  return vrew_core.safe_filename(value, max_len=max_len)


def build_vrew_subtitle_text(
  text: str,
  line_width: int = 22,
  max_lines: int = 2,
  *,
  title: str = "",
) -> str:
  return vrew_core.build_vrew_subtitle_text(
    text,
    line_width=line_width,
    max_lines=max_lines,
    title=title,
  )


def build_subtitle_cues(subtitle_text: str) -> list[dict[str, Any]]:
    blocks = [block.strip() for block in subtitle_text.split("\n\n") if block.strip()]
    cues: list[dict[str, Any]] = []
    cursor = 0.0
    for index, block in enumerate(blocks, start=1):
        plain = block.replace("\n", "")
        char_count = max(1, len(plain))
        duration = min(7.0, max(2.0, char_count / 5.5))
        cues.append({
            "index": index,
            "start_seconds": cursor,
            "end_seconds": cursor + duration,
            "text": block,
        })
        cursor += duration + 0.15
    return cues


def format_srt_timestamp(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours = total_ms // 3_600_000
    minutes = (total_ms % 3_600_000) // 60_000
    secs = (total_ms % 60_000) // 1000
    millis = total_ms % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def build_subtitle_csv(cues: list[dict[str, Any]]) -> str:
    rows = ["index,start_seconds,end_seconds,text"]
    for cue in cues:
        text = str(cue["text"]).replace('"', '""').replace("\n", "\\n")
        rows.append(
            f'{cue["index"]},{cue["start_seconds"]:.2f},{cue["end_seconds"]:.2f},"{text}"'
        )
    return "\n".join(rows) + "\n"


def build_subtitle_srt(cues: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for cue in cues:
        blocks.append(
            f'{cue["index"]}\n'
            f'{format_srt_timestamp(float(cue["start_seconds"]))} --> {format_srt_timestamp(float(cue["end_seconds"]))}\n'
            f'{cue["text"]}\n'
        )
    return "\n".join(blocks).strip() + "\n"


def ensure_vrew_assets(title: str, text_path: str) -> dict[str, str]:
  clean_path = str(text_path or "").strip()
  if not clean_path:
    return {}

  VREW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
  base_name = safe_filename(title)
  txt_path = VREW_OUTPUT_DIR / f"{base_name}.txt"
  csv_path = VREW_OUTPUT_DIR / f"{base_name}.csv"
  srt_path = VREW_OUTPUT_DIR / f"{base_name}.srt"

  if txt_path.exists():
    rel_txt = txt_path.relative_to(ROOT).as_posix()
    rel_csv = csv_path.relative_to(ROOT).as_posix() if csv_path.exists() else ""
    rel_srt = srt_path.relative_to(ROOT).as_posix() if srt_path.exists() else ""
    return {
      "vrew_text_path": rel_txt,
      "vrew_text_href": report_href_for_path(rel_txt),
      "vrew_csv_path": rel_csv,
      "vrew_csv_href": report_href_for_path(rel_csv) if rel_csv else "",
      "vrew_srt_path": rel_srt,
      "vrew_srt_href": report_href_for_path(rel_srt) if rel_srt else "",
    }

  source_text = read_text_best_effort(clean_path)
  if not source_text:
    return {}
  cleaned = strip_aozora_text(source_text, title)
  if not cleaned:
    return {}
  subtitle_text = build_vrew_subtitle_text(cleaned, title=title)
  if not subtitle_text:
    return {}

  txt_path.write_text(subtitle_text, encoding="utf-8")
  rel_txt = txt_path.relative_to(ROOT).as_posix()
  return {
    "vrew_text_path": rel_txt,
    "vrew_text_href": report_href_for_path(rel_txt),
    "vrew_csv_path": "",
    "vrew_csv_href": "",
    "vrew_srt_path": "",
    "vrew_srt_href": "",
  }


def score_synopsis_sentence(sentence: str, index: int) -> int:
    score = max(0, 28 - index)
    if any(keyword in sentence for keyword in INCIDENT_KEYWORDS):
        score += 12
    if any(keyword in sentence for keyword in ACTION_KEYWORDS):
        score += 6
    if any(keyword in sentence for keyword in ACTION_VERBS):
        score += 6
    if sentence.startswith(("「", "『")):
        score -= 3
    if "――" in sentence:
        score -= 2
    if len(sentence) > 90:
        score -= 3
    if len(sentence) < 16:
        score -= 5
    return score


def build_extractive_synopsis(title: str, text: str) -> dict[str, Any]:
    cleaned = strip_aozora_text(text, title)
    chapter_parts = [
        part.strip()
        for part in re.split(r"(?m)^\s*[一二三四五六七八九十百]+\s*$", cleaned)
        if part.strip()
    ]
    window_text = "\n".join(chapter_parts[:2]) if chapter_parts else cleaned
    sentences = split_japanese_sentences(window_text)
    if not sentences:
        return {}
    ranked = [
        (score_synopsis_sentence(sentence, index), index, sentence)
        for index, sentence in enumerate(sentences[:40])
    ]
    selected_indexes: list[int] = []

    def pick_first(predicate: Any) -> None:
        for _score, index, sentence in ranked:
            if index in selected_indexes:
                continue
            if predicate(index, sentence):
                selected_indexes.append(index)
                return

    pick_first(
        lambda index, sentence: index < 18
        and score_synopsis_sentence(sentence, index) >= 10
    )
    pick_first(
        lambda index, sentence: index < 25
        and any(keyword in sentence for keyword in INCIDENT_KEYWORDS)
    )
    pick_first(
        lambda index, sentence: index < 30
        and any(keyword in sentence for keyword in ACTION_KEYWORDS)
        and any(keyword in sentence for keyword in ACTION_VERBS)
    )
    for score, index, _sentence in sorted(
        ranked,
        key=lambda item: (-item[0], item[1]),
    ):
        if score < 8 or index in selected_indexes:
            continue
        selected_indexes.append(index)
        if len(selected_indexes) >= 3:
            break
    selected_indexes = sorted(selected_indexes)[:3]
    if not selected_indexes:
        return {}
    synopsis = "".join(sentences[index] for index in selected_indexes).strip()
    if len(synopsis) > 220:
        synopsis = "".join(sentences[index] for index in selected_indexes[:2]).strip()
    summary = "".join(sentences[index] for index in selected_indexes[:2]).strip()
    if len(summary) > 100:
        summary = sentences[selected_indexes[0]].strip()
    return {
        "synopsis": synopsis,
        "summary": summary,
        "sentence_count": len(sentences),
        "picked_indexes": selected_indexes,
    }


def enrich_row_synopsis(
    title: str,
    synopsis: str,
    summary: str,
    source_paths: list[str],
    bookdata_detail: dict[str, Any],
    synopsis_llm_map: dict[str, dict[str, Any]],
    text_override_map: dict[str, dict[str, Any]],
    manual_text_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    result = {
        "synopsis": synopsis,
        "summary": summary,
        "source": "catalog",
        "source_path": "",
        "sentence_count": 0,
    }
    bookdata_synopsis = str(bookdata_detail.get("synopsis", "") or "").strip()
    if (
        has_synopsis_placeholder(synopsis)
        and bookdata_synopsis
        and not has_synopsis_placeholder(bookdata_synopsis)
    ):
        result["synopsis"] = bookdata_synopsis
        result["source"] = "bookdata"
    if (
        needs_summary_refresh(summary)
        and result["synopsis"]
        and not has_synopsis_placeholder(result["synopsis"])
    ):
        base = str(result["synopsis"]).strip()
        result["summary"] = base[:90].rstrip("。") + (
            "。" if base and not base.endswith("。") else ""
        )
    if not has_synopsis_placeholder(result["synopsis"]):
        return result
    llm_entry = synopsis_llm_map.get(title)
    if llm_entry:
        result["synopsis"] = str(llm_entry.get("synopsis", "") or "").strip()
        result["summary"] = str(llm_entry.get("summary", "") or "").strip()
        result["source"] = str(llm_entry.get("source", "llm") or "llm")
        result["source_path"] = str(
            llm_entry.get("source_path", SYNOPSIS_LLM_JSON_PATH.as_posix()) or ""
        )
        return result
    text_path = preferred_local_text_path(title, source_paths, text_override_map, manual_text_map)
    if not text_path:
        return result
    text = read_text_best_effort(text_path)
    if not text:
        return result
    enriched = build_extractive_synopsis(title, text)
    if not enriched:
        return result
    result["draft_synopsis"] = str(enriched.get("synopsis", "") or "").strip()
    result["draft_summary"] = str(enriched.get("summary", "") or "").strip()
    result["draft_source"] = "aozora-extractive"
    result["draft_source_path"] = text_path
    result["sentence_count"] = int(enriched.get("sentence_count", 0) or 0)
    return result


def load_bookdata_detail(bookdata_path: str) -> dict[str, Any]:
    clean = str(bookdata_path or "").strip()
    if not clean:
        return {}
    cached = BOOKDATA_DETAIL_CACHE.get(clean)
    if cached is not None:
        return cached

    target = ROOT / clean
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        BOOKDATA_DETAIL_CACHE[clean] = {}
        return {}
    if not isinstance(data, dict):
        BOOKDATA_DETAIL_CACHE[clean] = {}
        return {}

    characters: list[dict[str, str]] = []
    for entry in data.get("characters", []):
        if not isinstance(entry, dict):
            continue
        name = normalize_detail_text(entry.get("name") or entry.get("term"))
        desc = normalize_detail_text(
            entry.get("description") or entry.get("desc") or entry.get("profile")
        )
        if (name and not is_character_noise(name)) or desc:
            characters.append({"name": name, "description": desc})

    glossary: list[dict[str, str]] = []
    for entry in data.get("glossary", []):
        if not isinstance(entry, dict):
            continue
        term = normalize_detail_text(entry.get("term") or entry.get("name"))
        reading = normalize_detail_text(entry.get("reading"))
        desc = normalize_detail_text(
            entry.get("description") or entry.get("desc") or entry.get("meaning")
        )
        if term or reading or desc:
            glossary.append({"term": term, "reading": reading, "description": desc})

    author_profile_raw = data.get("authorProfile") or data.get("author_profile")
    author_profile = ""
    if isinstance(author_profile_raw, dict):
        author_profile = normalize_detail_text(
            author_profile_raw.get("biography")
            or author_profile_raw.get("profile")
            or author_profile_raw.get("description")
            or author_profile_raw.get("summary")
        )
    else:
        author_profile = normalize_detail_text(author_profile_raw)

    highlights = normalize_string_list(data.get("highlights", []))
    keywords = normalize_string_list(data.get("keywords", []))
    themes = normalize_string_list(data.get("themes", []))
    emotions = normalize_string_list(data.get("emotions", []))
    chapter_titles: list[str] = []
    for chapter in data.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        title = normalize_detail_text(chapter.get("title") or chapter.get("name"))
        if title:
            chapter_titles.append(title)

    detail = {
        "title": normalize_detail_text(data.get("title")),
        "author": normalize_detail_text(data.get("author")),
        "genre": normalize_detail_text(data.get("genre")),
        "japanese_genre": normalize_detail_text(data.get("japanese_genre")),
        "sub_genre": normalize_detail_text(data.get("sub_genre")),
        "year": normalize_detail_text(data.get("year")),
        "era": normalize_detail_text(data.get("era")),
        "setting": normalize_detail_text(data.get("setting")),
        "location": normalize_detail_text(data.get("location")),
        "time_period": normalize_detail_text(data.get("time_period")),
        "synopsis": normalize_detail_text(data.get("synopsis")),
        "keywords": keywords,
        "themes": themes,
        "emotions": emotions,
        "highlights": highlights,
        "characters": characters,
        "glossary": glossary,
        "author_profile": author_profile,
        "chapter_titles": chapter_titles[:12],
        "chapter_count": len(chapter_titles),
    }
    has_content = any(
        [
            detail["synopsis"],
            detail["author_profile"],
            detail["characters"],
            detail["glossary"],
            detail["highlights"],
            keywords,
            themes,
            emotions,
            detail["setting"],
            detail["location"],
            detail["time_period"],
        ]
    )
    detail["available"] = has_content
    search_parts = [
        str(detail["author"]),
        str(detail["genre"]),
        str(detail["japanese_genre"]),
        str(detail["sub_genre"]),
        str(detail["setting"]),
        str(detail["location"]),
        str(detail["time_period"]),
        str(detail["synopsis"]),
        str(detail["author_profile"]),
        " / ".join(keywords),
        " / ".join(themes),
        " / ".join(emotions),
        " / ".join(item.get("name", "") for item in characters),
        " / ".join(item.get("term", "") for item in glossary),
        " / ".join(highlights),
    ]
    detail["search_text"] = " ".join(
        str(part) for part in search_parts if str(part).strip()
    ).strip()
    BOOKDATA_DETAIL_CACHE[clean] = detail
    return detail


def load_rows(
    recording_state: dict[str, Any] | None = None,
    aozora_manifest: dict[str, dict[str, str]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    last_magazines = ""
    overrides = recording_override_map(recording_state or {})
    synopsis_llm_map = load_synopsis_llm_map()
    text_override_map = load_text_override_map()
    aozora_lookup = aozora_manifest or {}
    rerecorded_latest_map = load_rerecorded_latest_map()
    raw_csv = CSV_PATH.read_bytes()
    csv_text = ""
    used_encoding = "utf-8"
    for encoding in ("utf-8", "utf-8-sig", "cp932", "shift_jis", "euc_jp"):
        try:
            csv_text = raw_csv.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if not csv_text:
        csv_text = raw_csv.decode("utf-8", errors="replace")
        used_encoding = "utf-8-replace"
    nul_count = csv_text.count("\x00")
    if nul_count:
        csv_text = csv_text.replace("\x00", "")
        print(f"Warning: {CSV_PATH.name} contained {nul_count} NUL bytes; removed during load")
    if "�" in csv_text:
        print(f"Warning: {CSV_PATH.name} decoded with replacement characters via {used_encoding}")
    catalog_rows = list(csv.DictReader(io.StringIO(csv_text, newline="")))
    current_channel_map, old_channel_map = load_channel_presence_maps(catalog_rows)
    current_source_titles = load_current_source_titles(catalog_rows)
    manual_text_map = discover_manual_text_paths(catalog_rows)
    for row in catalog_rows:
            title = row.get("title", "").strip()
            aozora = aozora_lookup.get(title, {})
            theme_secondary = normalize_theme_list(
                split_slash(row.get("theme_secondary", ""))
            )
            tags = split_slash(row.get("tags", ""))
            characters = clean_character_names(split_slash(row.get("characters", "")))
            source_paths = split_pipe(row.get("source_paths", ""))
            published_dates = split_pipe(row.get("published_dates", ""))
            channel_titles = split_pipe(row.get("channel_titles", ""))
            rerecorded_latest = rerecorded_latest_map.get(title, {})
            latest_video_id = str(rerecorded_latest.get("video_id", "") or "").strip()
            latest_published_year = str(rerecorded_latest.get("published_year", "") or "").strip()
            latest_published_at = str(rerecorded_latest.get("published_at", "") or "").strip()
            latest_title = str(rerecorded_latest.get("title", "") or "").strip()
            latest_views = str(rerecorded_latest.get("views", "") or "").strip()
            latest_views_per_day = str(rerecorded_latest.get("views_per_day", "") or "").strip()
            rerecorded_years_seen = split_pipe(str(rerecorded_latest.get("years_seen", "") or "").replace(",", "|"))
            rerecorded_selection_reason = str(rerecorded_latest.get("selection_reason", "") or "").strip()
            current_entries = current_channel_map.get(title, [])
            old_entries = old_channel_map.get(title, [])
            in_current_channel = bool(current_entries)
            in_current_source = title in current_source_titles
            in_old_channel = bool(old_entries)
            adoption_status, adoption_note = adoption_status_for(in_current_channel, in_old_channel, in_current_source)
            if latest_title:
                channel_titles = [latest_title]
            if latest_published_at:
                published_dates = [latest_published_at]
            publication_years = row.get("publication_years", "").strip()
            magazines = row.get("magazines", "").strip()
            if magazines in DITTO_MARKS and last_magazines:
                magazines = last_magazines
            elif magazines and magazines not in DITTO_MARKS:
                last_magazines = magazines

            has_channel_entry = normalize_bool(row.get("has_channel_entry", ""))
            has_audio_archive = normalize_bool(row.get("has_audio_archive", ""))
            has_local_text = normalize_bool(row.get("has_local_text", ""))
            has_bookdata = normalize_bool(row.get("has_bookdata", ""))
            has_meta = normalize_bool(row.get("has_meta", ""))
            override = overrides.get(title)
            override_value = (
                None if override is None else bool(override.get("is_recorded"))
            )
            override_note = (
                "" if override is None else str(override.get("note", "")).strip()
            )
            is_recorded = (
                has_channel_entry if override_value is None else override_value
            )
            needs_recording = not is_recorded
            if override_value is None:
                recording_status = "未朗読・要録音" if needs_recording else "朗読済み"
                recording_note = (
                    "チャンネル掲載履歴がないため録音候補"
                    if needs_recording
                    else "既に朗読公開済み"
                )
                recording_source = "catalog"
            elif is_recorded:
                recording_status = "手動更新・朗読済み"
                recording_note = override_note or "録音状態ファイルで朗読済みに更新"
                recording_source = "manual"
            else:
                recording_status = "手動更新・未朗読・要録音"
                recording_note = override_note or "録音状態ファイルで未朗読に更新"
                recording_source = "manual"
            if latest_video_id:
                recording_note = f"{recording_note} / 再録あり・検索アプリでは最新版を採用"
            synopsis = row.get("synopsis", "").strip()
            summary = row.get("summary", "").strip()
            story_lineage = refine_story_lineage(
                title,
                row.get("story_lineage", "").strip() or "未分類",
                theme_secondary,
                characters,
                synopsis,
                summary,
            )
            story_lineage = normalize_theme_label(story_lineage)

            tags = [tag for tag in tags if tag not in {"八五郎活躍", "未分類"}]
            tags = normalize_theme_list(tags)
            if story_lineage and story_lineage not in tags:
                tags.insert(0, story_lineage)

            title_bucket = kana_bucket_for_title(title)
            magazine_list = split_pipe(magazines)
            year_sort = year_sort_key(publication_years)
            bookdata_path = first_matching_path(source_paths, "bookdata/")
            bookdata_href = report_href_for_path(bookdata_path)
            bookdata_abs_path = (
                str((ROOT / bookdata_path).resolve()) if bookdata_path else ""
            )
            bookdata_file_uri = (
                (ROOT / bookdata_path).resolve().as_uri() if bookdata_path else ""
            )
            bookdata_dir_abs_path = (
                str((ROOT / bookdata_path).resolve().parent) if bookdata_path else ""
            )
            bookdata_dir_uri = (
                (ROOT / bookdata_path).resolve().parent.as_uri()
                if bookdata_path
                else ""
            )
            bookdata_detail = load_bookdata_detail(bookdata_path)
            synopsis_info = enrich_row_synopsis(
                title,
                synopsis,
                summary,
                source_paths,
                bookdata_detail,
                synopsis_llm_map,
                text_override_map,
                manual_text_map,
            )
            preferred_text_path = preferred_local_text_path(
                title,
                source_paths,
                text_override_map,
                manual_text_map,
            )
            preferred_text_href = report_href_for_path(preferred_text_path)
            preferred_text_abs_path = ""
            preferred_text_file_uri = ""
            if preferred_text_path:
              preferred_target = Path(preferred_text_path)
              if not preferred_target.is_absolute():
                preferred_target = ROOT / preferred_target
              preferred_target = preferred_target.resolve()
              preferred_text_abs_path = str(preferred_target)
              preferred_text_file_uri = preferred_target.as_uri()
              audio_archive_dirs = split_pipe(str(row.get("audio_archive_dirs", "")))
              audio_archive_dir_uris = []
              for audio_dir in audio_archive_dirs:
                try:
                  audio_archive_dir_uris.append(Path(audio_dir).resolve().as_uri())
                except Exception:
                  audio_archive_dir_uris.append("")
            preferred_text_preview = build_text_preview(preferred_text_path, title)
            vrew_assets = ensure_vrew_assets(title, preferred_text_path)
            has_local_text = has_local_text or bool(preferred_text_path)
            text_override = text_override_map.get(title, {})
            synopsis = str(synopsis_info.get("synopsis", "") or "").strip()
            summary = str(synopsis_info.get("summary", "") or "").strip()
            if synopsis and has_synopsis_placeholder(
                str(bookdata_detail.get("synopsis", "") or "")
            ):
                bookdata_detail = dict(bookdata_detail)
                bookdata_detail["synopsis"] = synopsis
                bookdata_detail["available"] = True
                bookdata_detail["search_text"] = " ".join(
                    part
                    for part in [
                        bookdata_detail.get("search_text", ""),
                        synopsis,
                        summary,
                    ]
                    if str(part).strip()
                ).strip()

            rows.append(
                {
                    "title": title,
                    "story_lineage": story_lineage,
                    "theme_secondary": theme_secondary,
                    "tags": tags,
                    "characters": characters,
                    "synopsis": synopsis,
                    "summary": summary,
                    "synopsis_source": str(synopsis_info.get("source", "catalog")),
                    "synopsis_source_path": str(synopsis_info.get("source_path", "")),
                    "preferred_text_path": preferred_text_path,
                    "preferred_text_href": preferred_text_href,
                    "preferred_text_abs_path": preferred_text_abs_path,
                    "preferred_text_file_uri": preferred_text_file_uri,
                    "preferred_text_preview": preferred_text_preview,
                    "vrew_text_path": str(vrew_assets.get("vrew_text_path", "")),
                    "vrew_text_href": str(vrew_assets.get("vrew_text_href", "")),
                    "vrew_csv_path": str(vrew_assets.get("vrew_csv_path", "")),
                    "vrew_csv_href": str(vrew_assets.get("vrew_csv_href", "")),
                    "vrew_srt_path": str(vrew_assets.get("vrew_srt_path", "")),
                    "vrew_srt_href": str(vrew_assets.get("vrew_srt_href", "")),
                    "has_vrew_assets": bool(vrew_assets),
                    "preferred_text_source": (
                        str(text_override.get("source", "catalog") or "catalog")
                        if text_override
                        else ("manual-library" if manual_text_map.get(title) else "catalog")
                    ),
                    "editorial_notes": (
                        list(text_override.get("editorial_notes", []))
                        if isinstance(text_override.get("editorial_notes"), list)
                        else []
                    ),
                    "synopsis_draft": str(synopsis_info.get("draft_synopsis", "")),
                    "summary_draft": str(synopsis_info.get("draft_summary", "")),
                    "synopsis_draft_source": str(synopsis_info.get("draft_source", "")),
                    "synopsis_draft_source_path": str(
                        synopsis_info.get("draft_source_path", "")
                    ),
                    "synopsis_sentence_count": int(
                        synopsis_info.get("sentence_count", 0) or 0
                    ),
                    "has_local_text": has_local_text,
                    "has_bookdata": has_bookdata,
                    "has_meta": has_meta,
                    "has_channel_entry": has_channel_entry,
                    "has_audio_archive": has_audio_archive,
                    "audio_file_count": int(row.get("audio_file_count", 0) or 0),
                    "audio_segment_count": int(row.get("audio_segment_count", 0) or 0),
                    "audio_recording_years": split_pipe(str(row.get("audio_recording_years", ""))),
                    "audio_archive_dirs": audio_archive_dirs,
                    "audio_archive_dir_uris": audio_archive_dir_uris,
                    "audio_derivative_count": int(
                        row.get("audio_derivative_count", 0) or 0
                    ),
                    "audio_duplicate_candidates": int(
                        row.get("audio_duplicate_candidates", 0) or 0
                    ),
                    "publication_years": publication_years,
                    "magazines": magazines,
                    "magazine_list": magazine_list,
                    "chronology_ordinals": row.get("chronology_ordinals", "").strip(),
                    "source_paths": source_paths,
                    "bookdata_path": bookdata_path,
                    "bookdata_href": bookdata_href,
                    "bookdata_abs_path": bookdata_abs_path,
                    "bookdata_file_uri": bookdata_file_uri,
                    "bookdata_dir_abs_path": bookdata_dir_abs_path,
                    "bookdata_dir_uri": bookdata_dir_uri,
                    "bookdata_detail": bookdata_detail,
                    "published_dates": published_dates,
                    "channel_titles": channel_titles,
                    "in_current_channel": in_current_channel,
                    "in_current_source": in_current_source,
                    "in_old_channel": in_old_channel,
                    "adoption_status": adoption_status,
                    "adoption_note": adoption_note,
                    "current_channel_titles": [entry.get("title", "") for entry in current_entries[:3] if entry.get("title")],
                    "old_channel_titles": [entry.get("title", "") for entry in old_entries[:3] if entry.get("title")],
                    "rerecorded_latest_only": bool(latest_video_id),
                    "latest_video_id": latest_video_id,
                    "latest_published_year": latest_published_year,
                    "latest_published_at": latest_published_at,
                    "latest_channel_title": latest_title,
                    "latest_views": latest_views,
                    "latest_views_per_day": latest_views_per_day,
                    "rerecorded_years_seen": rerecorded_years_seen,
                    "rerecorded_selection_reason": rerecorded_selection_reason,
                    "year_sort": year_sort,
                    "decade_label": decade_label(year_sort),
                    "title_bucket": title_bucket,
                    "base_is_recorded": has_channel_entry,
                    "is_recorded": is_recorded,
                    "needs_recording": needs_recording,
                    "recording_status": recording_status,
                    "recording_note": recording_note,
                    "recording_source": recording_source,
                    "recording_override": override_value,
                    "aozora_status": str(aozora.get("status", "unchecked")).strip(),
                    "aozora_notes": str(aozora.get("notes", "")).strip(),
                    "aozora_card_url": str(aozora.get("card_url", "")).strip(),
                    "aozora_text_url": str(aozora.get("text_url", "")).strip(),
                    "search_text": " ".join(
                        [
                            title,
                            story_lineage,
                            " / ".join(theme_secondary),
                            " / ".join(tags),
                            " / ".join(characters),
                            synopsis,
                            summary,
                            bookdata_detail.get("search_text", ""),
                            publication_years,
                            magazines,
                            " / ".join(channel_titles),
                            latest_video_id,
                            latest_published_year,
                            latest_views_per_day,
                            " / ".join(rerecorded_years_seen),
                            rerecorded_selection_reason,
                            adoption_status,
                            adoption_note,
                            recording_status,
                            str(aozora.get("status", "")).strip(),
                            str(aozora.get("notes", "")).strip(),
                        ]
                    ).strip(),
                }
            )
    return rows


def build_index(rows: list[dict[str, Any]]) -> dict[str, Any]:
    lineage_counts = Counter(str(row["story_lineage"]) for row in rows)
    kana_counts = Counter(str(row["title_bucket"]) for row in rows)
    year_counts = Counter(
        str(row["decade_label"])
        for row in rows
        if str(row["decade_label"]) and str(row["decade_label"]) != "年不明"
    )
    magazine_counts = Counter(
        magazine
        for row in rows
        for magazine in row.get("magazine_list", [])
        if str(magazine).strip()
    )
    lineages = [
        {"name": name, "count": count}
        for name, count in sorted(
            lineage_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]
    kana_groups = [
        {
            "name": label,
            "display": label,
            "count": kana_counts.get(label, 0),
        }
        for label, _display, _chars in KANA_BUCKETS
        if kana_counts.get(label, 0)
    ]
    if kana_counts.get("他", 0):
        kana_groups.append({"name": "他", "display": "他", "count": kana_counts["他"]})
    year_groups = [
        {"name": name, "count": count}
        for name, count in sorted(year_counts.items(), key=lambda item: item[0])
    ]
    magazine_groups = [
        {"name": name, "count": count}
        for name, count in sorted(
            magazine_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]
    stats = {
        "works": len(rows),
        "with_local_text": sum(1 for row in rows if row["has_local_text"]),
        "with_bookdata": sum(1 for row in rows if row["has_bookdata"]),
        "with_channel": sum(1 for row in rows if row["has_channel_entry"]),
        "with_audio": sum(1 for row in rows if row["has_audio_archive"]),
        "with_chronology": sum(1 for row in rows if row["publication_years"]),
        "needs_recording": sum(1 for row in rows if row["needs_recording"]),
        "recorded": sum(1 for row in rows if row["is_recorded"]),
        "adopted": sum(1 for row in rows if row.get("adoption_status") == "採用済み"),
        "legacy_only": sum(1 for row in rows if row.get("adoption_status") == "旧実績のみ"),
        "unadopted": sum(1 for row in rows if row.get("adoption_status") == "未採用"),
    }
    return {
        "lineages": lineages,
        "kana_groups": kana_groups,
        "year_groups": year_groups,
        "magazine_groups": magazine_groups,
        "stats": stats,
        "items": rows,
    }


def build_needs_recording_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    needs = [row for row in rows if row.get("needs_recording")]
    needs.sort(
        key=lambda row: (int(row.get("year_sort", 9999)), str(row.get("title", "")))
    )
    return needs


def write_needs_recording_reports(rows: list[dict[str, Any]]) -> None:
    needs = build_needs_recording_rows(rows)
    fieldnames = [
        "title",
        "publication_years",
        "magazines",
        "story_lineage",
        "recording_status",
        "recording_note",
        "recording_source",
        "has_local_text",
        "has_bookdata",
        "channel_titles",
        "source_paths",
    ]
    with NEEDS_RECORDING_CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in needs:
            writer.writerow(
                {
                    "title": row.get("title", ""),
                    "publication_years": row.get("publication_years", ""),
                    "magazines": row.get("magazines", ""),
                    "story_lineage": row.get("story_lineage", ""),
                    "recording_status": row.get("recording_status", ""),
                    "recording_note": row.get("recording_note", ""),
                    "recording_source": row.get("recording_source", ""),
                    "has_local_text": "yes" if row.get("has_local_text") else "no",
                    "has_bookdata": "yes" if row.get("has_bookdata") else "no",
                    "channel_titles": " / ".join(row.get("channel_titles", [])[:3]),
                    "source_paths": " / ".join(row.get("source_paths", [])[:4]),
                }
            )

    lines = [
        "# 銭形平次捕物控 要録音一覧",
        "",
        (
            "- 運用メモ: "
            "[zenigata_recording_workflow.md](zenigata_recording_workflow.md)"
        ),
        f"- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 要録音作品数: {len(needs)}",
        "",
    ]
    if not needs:
        lines.append("- 要録音作品はありません。")
    else:
        for index, row in enumerate(needs, start=1):
            meta = " / ".join(
                part
                for part in [
                    str(row.get("publication_years", "")),
                    str(row.get("magazines", "")),
                    str(row.get("story_lineage", "")),
                ]
                if str(part).strip()
            )
            lines.append(f"{index}. {row.get('title', '')} — {meta}")
            lines.append(f"   - 状態: {row.get('recording_status', '')}")
            lines.append(f"   - メモ: {row.get('recording_note', '')}")
    NEEDS_RECORDING_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_synopsis_gap_report(rows: list[dict[str, Any]]) -> None:
    enriched = [
        row
        for row in rows
        if str(row.get("synopsis_source", "")) == "aozora-extractive"
    ]
    gaps = [row for row in rows if should_fill_synopsis(row)]
    gaps.sort(
        key=lambda row: (int(row.get("year_sort", 9999)), str(row.get("title", "")))
    )
    enriched.sort(
        key=lambda row: (int(row.get("year_sort", 9999)), str(row.get("title", "")))
    )
    lines = [
        "# 銭形平次捕物控 synopsis 補筆候補",
        "",
        f"- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 本文から自動補筆: {len(enriched)}",
        f"- 補筆候補数: {len(gaps)}",
        "",
    ]
    if enriched:
        lines.extend(["## 本文から自動補筆した作品", ""])
        for index, row in enumerate(enriched[:80], start=1):
            lines.append(f"{index}. {row.get('title', '')}")
            lines.append(f"   - synopsis: {row.get('synopsis', '') or '未設定'}")
            lines.append(
                f"   - source: {row.get('synopsis_source_path', '') or 'Reading_library'}"
            )
        lines.append("")
    if not gaps:
        lines.append("- synopsis 補筆候補はありません。")
    else:
        for index, row in enumerate(gaps, start=1):
            lines.append(f"## {index}. {row.get('title', '')}")
            lines.append("")
            lines.append(
                "- 年代・掲載: "
                + " / ".join(
                    part
                    for part in [
                        str(row.get("publication_years", "")),
                        str(row.get("magazines", "")),
                    ]
                    if part.strip()
                )
            )
            lines.append(
                f"- 系統: {row.get('story_lineage', '') or '未分類'} / 登場人物: "
                f"{' / '.join(row.get('characters', [])[:5]) or '未整理'}"
            )
            lines.append(f"- 現在の synopsis: {row.get('synopsis', '') or '未設定'}")
            lines.append(f"- 現在の summary: {row.get('summary', '') or '未設定'}")
            lines.append("")
    SYNOPSIS_GAPS_MD_PATH.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "auto_filled": [
            {
                "title": str(row.get("title", "")),
                "publication_years": str(row.get("publication_years", "")),
                "magazines": str(row.get("magazines", "")),
                "synopsis": str(row.get("synopsis", "")),
                "summary": str(row.get("summary", "")),
                "source_path": str(row.get("synopsis_source_path", "")),
            }
            for row in enriched
        ],
        "remaining_gaps": [
            {
                "title": str(row.get("title", "")),
                "publication_years": str(row.get("publication_years", "")),
                "magazines": str(row.get("magazines", "")),
                "story_lineage": str(row.get("story_lineage", "")),
            }
            for row in gaps
        ],
    }
    SYNOPSIS_ENRICHMENT_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_theme_scores() -> list[dict[str, Any]]:
    if not THEME_SCORE_PATH.exists():
        return []
    try:
        data = json.loads(THEME_SCORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def parse_int(value: Any) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return 0


def parse_float(value: Any) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return 0.0


def load_seed_shortworks_report() -> dict[str, Any]:
    if not SEED_SHORTWORKS_PATH.exists():
        return {"generated_at": "", "seeds": []}
    with SEED_SHORTWORKS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        seeds: list[dict[str, Any]] = []
        for index, raw_row in enumerate(reader, start=1):
            row = {
                str(key).replace("\ufeff", "").strip(): value
                for key, value in raw_row.items()
            }
            seed_title = str(row.get("seed_title", "")).strip()
            if not seed_title:
                continue
            seeds.append(
                {
                    "rank": index,
                    "seed_title": seed_title,
                    "video_id": str(row.get("video_id", "")).strip(),
                    "channel_title": str(row.get("channel_title", "")).strip(),
                    "published_at": str(row.get("published_at", "")).strip(),
                    "duration_seconds": parse_int(row.get("duration_seconds")),
                    "views": parse_int(row.get("views")),
                    "impressions": parse_int(row.get("impressions")),
                    "impression_ctr": parse_float(row.get("impression_ctr")),
                    "average_view_duration_seconds": parse_int(
                        row.get("average_view_duration_seconds")
                    ),
                    "signal_score": parse_float(row.get("signal_score")),
                    "last_7d_impressions": parse_float(row.get("last_7d_impressions")),
                    "last_7d_ctr": parse_float(row.get("last_7d_ctr")),
                    "seed_score": parse_float(row.get("seed_score")),
                    "adoption_status": str(row.get("adoption_status", "")).strip(),
                    "story_lineage": str(row.get("story_lineage", "")).strip(),
                    "theme_secondary": split_slash(str(row.get("theme_secondary", ""))),
                    "tags": split_slash(str(row.get("tags", ""))),
                    "characters": clean_character_names(
                        split_slash(str(row.get("characters", "")))
                    ),
                    "publication_years": str(row.get("publication_years", "")).strip(),
                    "has_local_text": str(row.get("has_local_text", "")).strip()
                    in {"yes", "true", "1"},
                    "preferred_text_path": str(
                        row.get("preferred_text_path", "")
                    ).strip(),
                    "has_vrew_assets": bool(row.get("has_vrew_assets")),
                    "vrew_text_href": str(row.get("vrew_text_href", "")).strip(),
                    "vrew_csv_href": str(row.get("vrew_csv_href", "")).strip(),
                    "vrew_srt_href": str(row.get("vrew_srt_href", "")).strip(),
                }
            )
    return {
        "generated_at": datetime.fromtimestamp(
            SEED_SHORTWORKS_PATH.stat().st_mtime
        ).isoformat(timespec="seconds"),
        "seeds": seeds,
    }


def load_aozora_manifest() -> dict[str, dict[str, str]]:
    if not AOZORA_MANIFEST_PATH.exists():
        return {}
    try:
        data = json.loads(AOZORA_MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    items = data.get("items", []) if isinstance(data, dict) else []
    manifest: dict[str, dict[str, str]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        normalized_title = str(item.get("normalized_title", "")).strip()
        payload = {
            "status": str(item.get("status", "")).strip(),
            "notes": str(item.get("notes", "")).strip(),
            "card_url": str(item.get("aozora_card_url", "")).strip(),
            "text_url": str(item.get("aozora_text_url", "")).strip(),
        }
        for key in {title, normalized_title}:
            if key:
                manifest[key] = payload
    return manifest


def build_gap_payload(
    rows: list[dict[str, Any]], aozora_manifest: dict[str, dict[str, str]]
) -> dict[str, Any]:
    local_text_titles = {
        str(row.get("title", "")) for row in rows if bool(row.get("has_local_text"))
    }

    def item_payload(row: dict[str, Any]) -> dict[str, Any]:
        aozora = aozora_manifest.get(str(row.get("title", "")), {})
        return {
            "title": str(row.get("title", "")),
            "publication_years": str(row.get("publication_years", "")),
            "magazines": str(row.get("magazines", "")),
            "recording_status": str(row.get("recording_status", "")),
            "has_local_text": bool(row.get("has_local_text")),
            "has_bookdata": bool(row.get("has_bookdata")),
            "synopsis": str(row.get("synopsis", "") or row.get("summary", "")),
            "aozora_status": str(aozora.get("status", "unchecked")),
            "aozora_notes": str(aozora.get("notes", "")),
        }

    missing_bookdata = [
        item_payload(row) for row in rows if not bool(row.get("has_bookdata"))
    ]
    missing_text = [
        item_payload(row) for row in rows if not bool(row.get("has_local_text"))
    ]
    unresolved_aozora = sorted(
        [
            {
                "title": title,
                "status": payload.get("status", "unchecked"),
                "notes": payload.get("notes", ""),
            }
            for title, payload in aozora_manifest.items()
            if title not in local_text_titles
            if payload.get("status")
            and payload.get("status")
            not in {"resolved", "local_text_present", "local_bookdata_ready"}
        ],
        key=lambda item: str(item["title"]),
    )
    unresolved_buckets = {
        "ndl_candidate": sum(
            1 for item in unresolved_aozora if item.get("status") == "ndl_candidate"
        ),
        "external_public_candidate": sum(
            1
            for item in unresolved_aozora
            if item.get("status") == "external_public_candidate"
        ),
        "likely_text_missing": sum(
            1
            for item in unresolved_aozora
            if item.get("status") == "likely_text_missing"
        ),
    }
    missing_bookdata.sort(
        key=lambda item: (item["publication_years"] or "", item["title"])
    )
    missing_text.sort(key=lambda item: (item["publication_years"] or "", item["title"]))
    return {
        "missing_bookdata": missing_bookdata,
        "missing_text": missing_text,
        "unresolved_aozora": unresolved_aozora,
        "unresolved_buckets": unresolved_buckets,
    }


def build_theme_match_payload(scores: list[dict[str, Any]]) -> dict[str, Any]:
    themes = sorted(
        {
            str(item.get("theme", "")).strip()
            for item in scores
            if str(item.get("theme", "")).strip()
        }
    )
    return {
        "themes": themes,
        "scores": scores,
    }


def work_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        0 if row["is_recorded"] else 1,
        0 if row["has_bookdata"] else 1,
        row["year_sort"],
        str(row["title"]),
    )


def build_compilation_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[("lineage", str(row["story_lineage"]))].append(row)
        for theme in row["theme_secondary"]:
            grouped[("secondary", str(theme))].append(row)

    groups: list[dict[str, Any]] = []
    for (source_kind, theme), items in grouped.items():
        unique_items = {str(item["title"]): item for item in items}
        sorted_items = sorted(unique_items.values(), key=work_sort_key)
        if len(sorted_items) < 3:
            continue
        groups.append(
            {
                "id": group_id(source_kind, theme),
                "source_kind": source_kind,
                "theme": theme,
                "description": (
                    "物語の系統から組む総集編候補"
                    if source_kind == "lineage"
                    else "副系統テーマから組む総集編候補"
                ),
                "suggested_title": make_compilation_title(theme, source_kind),
                "total_works": len(sorted_items),
                "recorded_works": sum(
                    1 for item in sorted_items if item["is_recorded"]
                ),
                "needs_recording_works": sum(
                    1 for item in sorted_items if item["needs_recording"]
                ),
                "work_titles": [str(item["title"]) for item in sorted_items],
            }
        )

    source_rank = {"lineage": 0, "secondary": 1}
    groups.sort(
        key=lambda group: (
            source_rank.get(str(group["source_kind"]), 99),
            -int(group["recorded_works"]),
            -int(group["total_works"]),
            str(group["theme"]),
        )
    )
    return groups


def adopted_work_titles(state: dict[str, Any]) -> set[str]:
    titles: set[str] = set()
    for entry in state.get("adopted_candidates", []):
        for title in entry.get("work_titles", []):
            titles.add(str(title))
    return titles


def build_compilation_candidates(
    groups: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    items_by_title = {str(row["title"]): row for row in rows}
    excluded_titles = adopted_work_titles(state)
    seen_signatures: set[str] = set()
    candidates: list[dict[str, Any]] = []

    for group in groups:
        available = [
            items_by_title[title]
            for title in group["work_titles"]
            if title in items_by_title and title not in excluded_titles
        ]
        if len(available) < 3:
            continue
        trio = available[:3]
        signature = "||".join(sorted(str(item["title"]) for item in trio))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        needs_recording_titles = [
            str(item["title"]) for item in trio if item["needs_recording"]
        ]
        recorded_count = len(trio) - len(needs_recording_titles)
        candidates.append(
            {
                "candidate_id": (
                    f"{group['id']}::{'||'.join(str(item['title']) for item in trio)}"
                ),
                "theme": group["theme"],
                "title": group["suggested_title"],
                "source_kind": group["source_kind"],
                "description": group["description"],
                "work_titles": [str(item["title"]) for item in trio],
                "needs_recording_titles": needs_recording_titles,
                "recorded_count": recorded_count,
                "needs_recording_count": len(needs_recording_titles),
                "group_total_works": group["total_works"],
                "remaining_pool": len(available),
            }
        )

    candidates.sort(
        key=lambda item: (
            item["needs_recording_count"],
            -item["recorded_count"],
            -item["remaining_pool"],
            str(item["theme"]),
            str(item["title"]),
        )
    )
    return candidates


def render_compilation_markdown(
    rows: list[dict[str, Any]],
    state: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    adopted_titles = adopted_work_titles(state)
    lines = [
        "# 銭形平次捕物控 総集編候補一覧",
        "",
        f"- 生成日時: {generated_at}",
        f"- 総作品数: {len(rows)}",
        f"- 朗読済み: {sum(1 for row in rows if row['is_recorded'])}",
        f"- 未朗読・要録音: {sum(1 for row in rows if row['needs_recording'])}",
        f"- 採用済み作品数: {len(adopted_titles)}",
        f"- 候補数: {len(candidates)}",
        "",
        "## 先頭候補",
        "",
    ]

    for index, candidate in enumerate(candidates[:20], start=1):
        lines.append(f"### {index}. {candidate['title']}")
        lines.append("")
        lines.append(f"- テーマ: {candidate['theme']}")
        lines.append(f"- 種別: {candidate['description']}")
        lines.append(f"- 候補三本: {' / '.join(candidate['work_titles'])}")
        if candidate["needs_recording_titles"]:
            lines.append("- 要録音: " + " / ".join(candidate["needs_recording_titles"]))
        else:
            lines.append("- 要録音: なし（3本とも朗読済み）")
        lines.append(f"- 残り候補プール: {candidate['remaining_pool']}本")
        lines.append("")

    lines.extend(["## 採用済み", ""])
    adopted_candidates = state.get("adopted_candidates", [])
    if not adopted_candidates:
        lines.append("- まだ採用済みの総集編はありません。")
    else:
        for entry in adopted_candidates:
            lines.append(f"- {entry['title']} :: {' / '.join(entry['work_titles'])}")
    lines.append("")
    return "\n".join(lines)


def render_html(payload: dict[str, Any]) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = """<!doctype html>
<html lang=\"ja\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>銭形平次捕物控 作品検索</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8f4e6;
      --panel: rgba(255,252,245,0.9);
      --paper: #fffdf8;
      --ink: #333333;
      --muted: #6e6254;
      --line: #d9cfbf;
      --accent: #1c305c;
      --accent-soft: #e8ecf3;
      --accent-strong: #132342;
      --accent-2: #4a593d;
      --accent-3: #8d3447;
      --badge: #f2ede3;
      --good: #4a593d;
      --good-bg: #e7eee0;
      --warn: #8a5a22;
      --warn-bg: #f8ebd7;
      --shadow: 0 10px 26px rgba(61, 42, 24, 0.14);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(28, 48, 92, 0.08), transparent 28%),
        radial-gradient(circle at top right, rgba(141, 52, 71, 0.08), transparent 24%),
        linear-gradient(180deg, #fbf8ef 0%, var(--bg) 260px);
      color: var(--ink);
      font-family: \"Noto Serif JP\", \"Yu Mincho\", \"Hiragino Mincho ProN\", \"MS Mincho\", serif;
      line-height: 1.6;
      letter-spacing: 0.02em;
    }}
    .wrap {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
    .hero, .sidebar, .main-panel {{
      background: var(--panel);
      border: 1px solid rgba(217,207,191,0.92);
      backdrop-filter: blur(14px);
      box-shadow: var(--shadow);
      border-radius: 24px;
    }}
    .hero {{ padding: 28px; margin-bottom: 20px; }}
    .hero h1 {{ margin: 0 0 8px; font-size: clamp(26px, 3vw, 38px); }}
    .hero p {{ margin: 0; color: var(--muted); }}
    .hero-meta {{ display: grid; gap: 16px; margin-top: 18px; }}
    .stats {{ overflow-x: auto; }}
    .stats-card {{
      background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(250,246,238,0.96));
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
    }}
    .stats-table {{ width: 100%; border-collapse: collapse; min-width: 680px; }}
    .stats-table th,
    .stats-table td {{ border-bottom: 1px solid var(--line); padding: 10px 12px; text-align: left; }}
    .stats-table th {{ font-size: 12px; color: var(--muted); font-weight: 700; letter-spacing: 0.04em; }}
    .stats-table td strong {{ font-size: 18px; color: var(--accent-strong); }}
    .stats-table tr:last-child th,
    .stats-table tr:last-child td {{ border-bottom: none; }}
    .nav-tabs {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .nav-tab {{
      border: 1px solid var(--line);
      background: rgba(255,251,244,0.88);
      color: var(--muted);
      padding: 10px 14px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: 0.16s ease;
    }}
    .nav-tab:hover {{ border-color: var(--accent); color: var(--accent-strong); }}
    .nav-tab.active {{ background: var(--accent); color: #fff; border-color: var(--accent); box-shadow: 0 6px 14px rgba(28,48,92,0.18); }}
    .toolbar {{
      display: grid;
      grid-template-columns: minmax(0, 1.5fr) 220px;
      gap: 12px;
      margin-top: 18px;
    }}
    .input, .select, .button {{
      width: 100%;
      border: none;
      border-bottom: 2px solid var(--accent);
      border-radius: 14px;
      padding: 13px 14px 10px;
      background: transparent;
      color: var(--ink);
      font-size: 15px;
      font-family: inherit;
    }}
    .input:focus, .select:focus {{ outline: none; border-bottom-color: var(--accent-3); box-shadow: 0 6px 18px rgba(28,48,92,0.08); }}
    .button {{ cursor: pointer; }}
    .button.primary {{
      background: linear-gradient(135deg, var(--accent), var(--accent-3));
      color: #fff;
      border-color: transparent;
      border-bottom: none;
      box-shadow: 0 8px 18px rgba(28,48,92,0.2);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 300px 1fr;
      gap: 20px;
      align-items: start;
    }}
    .sidebar {{ padding: 20px; position: sticky; top: 20px; }}
    .main-panel {{ padding: 18px; }}
    .section-title {{ margin: 0 0 12px; font-size: 14px; color: var(--muted); font-weight: 700; }}
    .facet-summary {{ margin-bottom: 12px; color: var(--muted); font-size: 13px; }}
    .chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .chip {{
      border: 1px solid var(--line);
      background: rgba(255,251,244,0.94);
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 13px;
      cursor: pointer;
      transition: 0.15s ease;
    }}
    .chip:hover {{ border-color: var(--accent); color: var(--accent-strong); }}
    .chip.active {{ background: var(--accent-2); border-color: var(--accent-2); color: #fff; }}
    .checks {{ display: grid; gap: 10px; margin-top: 12px; }}
    .check {{ display: flex; align-items: center; gap: 10px; font-size: 14px; color: var(--ink); }}
    .panel-head {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 14px;
    }}
    .view-switch {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .view-button {{
      width: auto;
      padding: 10px 14px;
      border: 1px solid var(--line);
      border-bottom: 2px solid var(--accent);
      border-radius: 999px;
      background: rgba(255,251,244,0.94);
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}
    .view-button.active {{
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
      box-shadow: 0 6px 14px rgba(28,48,92,0.18);
    }}
    .mode-switch {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
    .mode-button {{
      width: auto;
      padding: 10px 14px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,251,244,0.94);
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}
    .mode-button.active {{
      background: linear-gradient(135deg, var(--accent), var(--accent-3));
      color: #fff;
      border-color: transparent;
      box-shadow: 0 8px 18px rgba(28,48,92,0.2);
    }}
    .mode-summary {{ margin-top: 10px; color: var(--muted); font-size: 14px; }}
    .mode-section {{ display: none; margin-top: 18px; }}
    .mode-section.active {{ display: block; }}
    .result-meta {{ color: var(--muted); font-size: 14px; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }}
    .work-table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.96);
      box-shadow: 0 2px 6px rgba(61,42,24,0.1);
    }}
    .work-table {{ width: 100%; border-collapse: collapse; min-width: 980px; }}
    .work-table th,
    .work-table td {{ padding: 12px 14px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    .work-table th {{
      position: sticky;
      top: 0;
      background: #f6efe2;
      color: var(--accent-strong);
      font-size: 12px;
      letter-spacing: 0.04em;
      z-index: 1;
    }}
    .work-table tr:hover td {{ background: rgba(232,236,243,0.28); }}
    .work-table tr:last-child td {{ border-bottom: none; }}
    .work-title-cell {{ min-width: 180px; }}
    .work-title-main {{ font-weight: 700; color: var(--accent-strong); }}
    .work-title-sub {{ margin-top: 4px; font-size: 12px; color: var(--muted); }}
    .work-tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .work-synopsis {{ min-width: 260px; color: var(--ink); }}
    .simple-list {{ display: grid; gap: 10px; }}
    .simple-row {{
      display: grid;
      grid-template-columns: minmax(180px, 220px) 120px 1fr;
      gap: 12px;
      padding: 12px 14px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.94);
      box-shadow: 0 2px 6px rgba(61,42,24,0.08);
      align-items: start;
    }}
    .simple-title {{ font-weight: 700; color: var(--accent-strong); }}
    .simple-meta {{ color: var(--muted); font-size: 12px; }}
    .gap-panel {{ display: grid; gap: 14px; margin-bottom: 20px; }}
    .gap-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .gap-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 2px 6px rgba(61,42,24,0.1);
      border-left: 6px solid var(--accent);
    }}
    .gap-list {{ margin: 0; padding-left: 18px; display: grid; gap: 8px; }}
    .gap-list li {{ color: var(--ink); }}
    .gap-note {{ color: var(--muted); font-size: 13px; }}
    .card, .comp-card, .adopted-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      transition: transform 0.16s ease, box-shadow 0.16s ease;
      box-shadow: 0 2px 6px rgba(61,42,24,0.12);
      border-left: 6px solid var(--accent-2);
    }}
    .card:hover, .comp-card:hover, .adopted-card:hover, .theme-card:hover {{ transform: translateY(-2px); box-shadow: 0 12px 24px rgba(61,42,24,0.16); }}
    .card h2, .comp-card h3, .adopted-card h3 {{ margin: 0; line-height: 1.35; }}
    .subline {{ color: var(--muted); font-size: 13px; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--badge);
      border-radius: 999px;
      padding: 5px 10px;
      font-size: 12px;
      color: var(--accent-strong);
      border: 1px solid rgba(217,207,191,0.9);
    }}
    .badge.good {{ background: var(--good-bg); color: var(--good); }}
    .badge.warn {{ background: var(--warn-bg); color: var(--warn); }}
    .chips-mini {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip-mini {{
      background: #f6efe2;
      border: 1px solid #e5d8c0;
      color: #614c31;
      border-radius: 10px;
      padding: 4px 8px;
      font-size: 12px;
    }}
    .desc {{ font-size: 14px; color: var(--ink); margin: 0; }}
    .empty {{
      padding: 40px 16px;
      text-align: center;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 18px;
      background: rgba(255,255,255,0.95);
    }}
    details {{ border-top: 1px dashed var(--line); padding-top: 10px; }}
    summary {{ cursor: pointer; color: var(--accent-strong); font-size: 13px; font-weight: 600; }}
    .detail-block {{ margin-top: 8px; display: grid; gap: 8px; font-size: 13px; }}
    .detail-label {{ color: var(--muted); font-weight: 700; margin-right: 6px; }}
    .comp-wrap {{ display: grid; gap: 14px; margin-bottom: 20px; }}
    .comp-toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .comp-grid, .adopted-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }}
    .theme-panel {{ display: grid; gap: 14px; margin-bottom: 20px; }}
    .theme-toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
    .theme-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }}
    .seed-layout {{
      display: grid;
      grid-template-columns: 300px minmax(0, 1.1fr) minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }}
    .seed-sidebar, .seed-panel {{
      background: var(--panel);
      border: 1px solid rgba(217,207,191,0.92);
      border-radius: 20px;
      padding: 18px;
      box-shadow: 0 2px 6px rgba(61,42,24,0.1);
    }}
    .seed-sidebar {{ position: sticky; top: 20px; display: grid; gap: 14px; }}
    .seed-column {{ display: grid; gap: 14px; }}
    .youtube-seed-list {{ display: grid; gap: 10px; }}
    .youtube-seed-card {{
      background: rgba(255,255,255,0.96);
      border: 1px solid var(--line);
      border-left: 5px solid var(--accent-3);
      border-radius: 16px;
      padding: 14px;
      display: grid;
      gap: 8px;
      box-shadow: 0 2px 6px rgba(61,42,24,0.08);
    }}
    .youtube-seed-head {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: flex-start;
    }}
    .youtube-seed-rank {{
      font-size: 24px;
      font-weight: 700;
      color: var(--accent-strong);
      line-height: 1;
    }}
    .youtube-seed-score {{
      font-size: 12px;
      color: var(--muted);
      text-align: right;
      white-space: nowrap;
    }}
    .youtube-seed-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
    }}
    .youtube-seed-metric {{
      border: 1px solid var(--line);
      background: rgba(248,242,230,0.85);
      border-radius: 12px;
      padding: 8px 10px;
      font-size: 12px;
    }}
    .youtube-seed-metric strong {{
      display: block;
      color: var(--accent-strong);
      margin-bottom: 4px;
    }}
    .youtube-seed-note {{ color: var(--muted); font-size: 13px; }}
    .seed-focus-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.96);
      padding: 14px;
      display: grid;
      gap: 8px;
    }}
    .seed-list, .seed-bundle-list {{ display: grid; gap: 12px; }}
    .seed-candidate-card, .seed-bundle-card, .queue-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-left: 6px solid var(--accent-3);
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 2px 6px rgba(61,42,24,0.12);
      display: grid;
      gap: 10px;
    }}
    .seed-candidate-card.good {{ border-left-color: var(--accent-2); }}
    .seed-score {{ font-size: 26px; font-weight: 700; color: var(--accent-strong); }}
    .seed-grid-meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 8px;
    }}
    .seed-meta-card {{
      border: 1px solid var(--line);
      background: rgba(248,242,230,0.85);
      border-radius: 14px;
      padding: 10px 12px;
      font-size: 12px;
    }}
    .seed-meta-card strong {{ display: block; color: var(--accent-strong); margin-bottom: 4px; }}
    .seed-reason-list {{ margin: 0; padding-left: 18px; display: grid; gap: 4px; }}
    .seed-work-list {{ margin: 0; padding-left: 18px; display: grid; gap: 6px; }}
    .planner-toolbar {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 12px; }}
    .score-breakdown {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: 8px; }}
    .score-chip {{ border: 1px solid var(--line); background: rgba(255,255,255,0.92); border-radius: 12px; padding: 8px 10px; font-size: 12px; }}
    .score-chip strong {{ display: block; color: var(--accent-strong); margin-bottom: 4px; }}
    .planner-note {{ color: var(--muted); font-size: 13px; line-height: 1.7; }}
    .bundle-title-box {{ background: linear-gradient(135deg, rgba(28,48,92,0.1), rgba(141,52,71,0.08)); border: 1px solid rgba(28,48,92,0.12); border-radius: 14px; padding: 12px 14px; }}
    .seed-card-section {{ display: grid; gap: 6px; }}
    .queue-list { display: grid; gap: 10px; }
    .queue-card { border-left-color: var(--accent); }
    .queue-editor { display: grid; gap: 8px; margin-top: 10px; }
    .queue-editor label { display: grid; gap: 4px; color: var(--muted); font-size: 12px; }
    .queue-editor input, .queue-editor textarea, .queue-editor select { width: 100%; font: inherit; border: 1px solid var(--line); border-radius: 12px; background: rgba(255,255,255,0.95); color: var(--ink); padding: 10px 12px; }
    .queue-editor textarea { min-height: 84px; resize: vertical; }
    .queue-card h4, .seed-candidate-card h3, .seed-bundle-card h3 {{ margin: 0; }}
    .thumbnail-copy {{
      font-size: 18px;
      font-weight: 700;
      color: var(--accent-strong);
      background: rgba(232,236,243,0.45);
      border-radius: 14px;
      padding: 10px 12px;
    }}
    .theme-card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      box-shadow: 0 2px 6px rgba(61,42,24,0.12);
      border-left: 6px solid var(--accent-3);
    }}
    .work-list {{ margin: 0; padding-left: 20px; display: grid; gap: 6px; }}
    .work-line {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .comp-note {{ color: var(--muted); font-size: 13px; }}
    .inline-actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .resource-actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .resource-actions.compact {{ margin-top: 10px; }}
    .button.small {{ padding: 6px 10px; font-size: 12px; }}
    .reason-list {{ margin: 0; padding-left: 18px; display: grid; gap: 4px; }}
    .split {{ height: 1px; background: var(--line); margin: 6px 0; }}
    .bookdata-inline {{ margin-top: 10px; }}
    .bookdata-inline > summary {{
      list-style: none;
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,251,244,0.94);
    }}
    .bookdata-inline > summary::-webkit-details-marker {{ display: none; }}
    .bookdata-inline[open] > summary {{
      background: var(--accent-soft);
      border-color: rgba(28,48,92,0.18);
    }}
    .bookdata-layout {{ display: grid; gap: 16px; }}
    .bookdata-section {{
      background: rgba(255,255,255,0.9);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 16px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.8);
    }}
    .bookdata-section h3 {{
      margin: 0 0 10px;
      color: var(--accent-strong);
      font-size: 16px;
    }}
    .bookdata-section p {{ margin: 0; }}
    .bookdata-meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
    }}
    .bookdata-meta-item {{
      background: #f8f2e6;
      border: 1px solid #e4d8c4;
      border-radius: 14px;
      padding: 10px 12px;
    }}
    .bookdata-meta-item strong {{
      display: block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .bookdata-chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .bookdata-card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }}
    .bookdata-mini-card {{
      background: #fcf8f0;
      border: 1px solid #e8dcc7;
      border-radius: 16px;
      padding: 12px;
    }}
    .bookdata-mini-card h4 {{
      margin: 0 0 6px;
      color: var(--accent-strong);
      font-size: 14px;
    }}
    .bookdata-mini-card p {{ margin: 0; font-size: 13px; color: var(--ink); }}
    .bookdata-list {{ margin: 0; padding-left: 18px; display: grid; gap: 8px; }}
    .bookdata-list li {{ color: var(--ink); }}
    .bookdata-inline-note {{ color: var(--muted); font-size: 12px; }}
    .filter-group {{ margin-top: 14px; border-top: 1px solid var(--line); padding-top: 14px; }}
    .filter-group:first-of-type {{ margin-top: 0; border-top: none; padding-top: 0; }}
    .mode-grid {{ display: grid; gap: 18px; }}
    .highlight-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 16px; }}
    .highlight-card {{
      background: rgba(255,255,255,0.96);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      box-shadow: 0 2px 6px rgba(61,42,24,0.1);
    }}
    .highlight-card h3 {{ margin: 0 0 8px; color: var(--accent-strong); font-size: 15px; }}
    .highlight-card p {{ margin: 0; color: var(--ink); font-size: 13px; line-height: 1.6; }}
    .hero-lead {{ margin: 14px 0 0; color: var(--muted); font-size: 14px; line-height: 1.8; }}
    .planner-pulse {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-top: 18px; }}
    .pulse-card {{ background: rgba(255,255,255,0.94); border: 1px solid rgba(217,207,191,0.9); border-radius: 18px; padding: 14px 16px; box-shadow: 0 2px 8px rgba(61,42,24,0.08); }}
    .pulse-card strong {{ display: block; color: var(--accent-strong); font-size: 15px; margin-bottom: 4px; }}
    .pulse-card span {{ display: block; color: var(--muted); font-size: 13px; line-height: 1.6; }}
    .resource-strip {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 0; }}
    .resource-pill {{ display: inline-flex; align-items: center; gap: 6px; border: 1px solid #dfd1bf; background: #f8f2e7; color: var(--ink); border-radius: 999px; padding: 6px 10px; font-size: 12px; }}
    .resource-pill strong {{ color: var(--accent-strong); font-weight: 700; }}
    .evidence-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; margin-top: 12px; }}
    .evidence-card {{ background: rgba(255,255,255,0.92); border: 1px solid #e4d8c4; border-radius: 16px; padding: 12px; }}
    .evidence-card strong {{ display: block; color: var(--accent-strong); font-size: 13px; margin-bottom: 6px; }}
    .evidence-card p {{ margin: 0; color: var(--ink); font-size: 12px; line-height: 1.7; }}
    .work-evidence-list {{ display: grid; gap: 10px; margin-top: 14px; }}
    .work-evidence-item {{ background: rgba(255,255,255,0.92); border: 1px solid #e3d6c1; border-radius: 16px; padding: 12px 14px; }}
    .work-evidence-item h4 {{ margin: 0 0 4px; color: var(--accent-strong); font-size: 14px; }}
    .work-evidence-item p {{ margin: 8px 0 0; color: var(--ink); font-size: 13px; line-height: 1.7; }}
    .work-evidence-meta {{ color: var(--muted); font-size: 12px; }}
    .reason-pill-list {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    .reason-pill {{ display: inline-flex; align-items: center; border-radius: 999px; background: var(--accent-soft); color: var(--accent-strong); padding: 6px 10px; font-size: 12px; border: 1px solid rgba(28,48,92,0.12); }}
    .ordering-box {{ margin-top: 12px; padding: 12px 14px; border-radius: 16px; border: 1px solid #ded1be; background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(248,242,231,0.96)); color: var(--ink); font-size: 13px; line-height: 1.7; }}
    footer {{ color: var(--muted); font-size: 12px; text-align: right; padding: 18px 4px 0; }}
    @media (max-width: 1080px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; }}
    }}
    @media (max-width: 760px) {{
      .wrap {{ padding: 14px; }}
      .hero, .sidebar, .main-panel {{ border-radius: 18px; }}
      .toolbar {{ grid-template-columns: 1fr; }}
      .cards, .comp-grid, .adopted-grid, .gap-grid {{ grid-template-columns: 1fr; }}
      .seed-layout {{ grid-template-columns: 1fr; }}
      .seed-sidebar {{ position: static; }}
      .simple-row {{ grid-template-columns: 1fr; }}
      .hero h1 {{ font-size: 28px; }}
      .stats-table {{ min-width: 560px; }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <section class=\"hero\">
      <div class=\"toolbar\">
        <input id=\"q\" class=\"input\" type=\"search\" placeholder=\"検索：作品名 / あらすじ / 登場人物 / タグ / 掲載誌 / 動画題名 など\" />
        <select id=\"sort\" class=\"select\">
          <option value=\"title\">タイトル順</option>
          <option value=\"year\">発表年順</option>
          <option value=\"audio\">音源数が多い順</option>
        </select>
      </div>
      <div class="mode-switch" id="modeSwitch">
        <button class="button mode-button active" type="button" data-mode="compilation">総集編作成</button>
        <button class="button mode-button" type="button" data-mode="seed">作品から総集編</button>
        <button class="button mode-button" type="button" data-mode="search">作品を探す</button>
        <button class="button mode-button" type="button" data-mode="recording">録音管理</button>
        <button class="button mode-button" type="button" data-mode="missing">不足管理</button>
      </div>
      <div class="mode-summary" id="modeSummary">今日は何を進めるかで画面を切り替えます。初期表示は総集編作成です。</div>
      <p class="hero-lead">銭形平次の総集編企画、核作品からの bundle 設計、録音不足の洗い出し、bookdata と青空の確認までを一つの導線で回せるようにしています。</p>
      <div class="planner-pulse" id="plannerPulse"></div>
      <div id="stats"></div>
    </section>

      <section class="mode-section active" data-mode-panel="compilation">
        <div class="mode-grid">
          <div class="theme-panel">
            <div>
              <div class="panel-head">
                <div>
                  <h2 style="margin:0;">テーマ一致率</h2>
                  <div class="result-meta" id="themeSummary"></div>
                </div>
                <div class="theme-toolbar">
                  <select id="themeSelect" class="select">
                    <option value="">テーマを選択してください</option>
                  </select>
                  <label class="check"><input id="themeRecordedOnly" type="checkbox" /> 朗読済みのみで見る</label>
                </div>
              </div>
              <div class="result-meta">本文・あらすじ・タグなどから算出した一致率の上位3本を表示します。採用済み作品は自動除外します。</div>
            </div>
            <div id="themeList" class="theme-grid"></div>
          </div>

          <div class="comp-wrap">
            <div>
              <div class="panel-head">
                <div>
                  <h2 style="margin:0;">総集編作成</h2>
                  <div class="result-meta" id="compSummary"></div>
                </div>
                <div class="comp-toolbar">
                  <label class="check"><input id="compReadyOnly" type="checkbox" /> 3本とも朗読済みのみ</label>
                  <button id="exportState" class="button" type="button">採用状態をJSONでコピー</button>
                  <button id="resetState" class="button" type="button">採用状態を初期化</button>
                </div>
              </div>
              <div class="result-meta">採用済み作品は候補から自動除外します。採用状態はこのブラウザのローカル保存に保持されます。</div>
            </div>
            <div id="compHighlights" class="highlight-grid"></div>
            <div id="compList" class="comp-grid"></div>
            <div class="split"></div>
            <div>
              <h2 style="margin:0 0 8px;">採用済み総集編</h2>
              <div class="result-meta" id="adoptedSummary"></div>
            </div>
            <div id="adoptedList" class="adopted-grid"></div>
          </div>
        </div>
      </section>

      <section class="mode-section" data-mode-panel="seed">
        <div class="seed-layout">
          <aside class="seed-sidebar">
            <div class="filter-group">
              <h2 class="section-title">YouTube核候補</h2>
              <div id="youtubeSeedSummary" class="result-meta">channel report から短編の強い作品を表示します。</div>
              <div class="checks">
                <label class="check"><input id="youtubeSeedPreferBacklog" type="checkbox" checked /> 未採用・旧実績のみを優先表示</label>
              </div>
              <div id="youtubeSeedList" class="youtube-seed-list"></div>
            </div>

            <div class="filter-group">
              <h2 class="section-title">核作品</h2>
              <div id="seedSelectionSummary" class="result-meta">作品カードの「この作品から候補を探す」から開始します。</div>
              <div id="seedFocusCard" class="seed-focus-card">
                <div class="gap-note">まだ核作品が選ばれていません。</div>
              </div>
              <div class="inline-actions">
                <button id="clearSeedSelection" class="button small" type="button">選択解除</button>
              </div>
            </div>

            <div class="filter-group">
              <h2 class="section-title">企画条件</h2>
              <div class="planner-toolbar">
                <select id="seedPlanSize" class="select">
                  <option value="3">3本セット</option>
                  <option value="5">5本セット</option>
                </select>
                <select id="seedTone" class="select">
                  <option value="incident">事件性重視</option>
                  <option value="emotion">情緒重視</option>
                </select>
              </div>
              <div class="checks">
                <label class="check"><input id="seedExcludeAdopted" type="checkbox" checked /> 採用済み作品を除外</label>
                <label class="check"><input id="seedExcludeUnrecorded" type="checkbox" /> 未朗読を除外</label>
                <label class="check"><input id="seedExcludeNoText" type="checkbox" /> 本文なしを除外</label>
                <label class="check"><input id="seedExcludeExistingTheme" type="checkbox" /> 既出テーマを除外</label>
              </div>
            </div>

            <div class="filter-group">
              <h2 class="section-title">review queue</h2>
              <div id="reviewQueueSummary" class="result-meta">まだ bundle は入っていません。</div>
              <div class="inline-actions">
                <button id="exportReviewQueue" class="button small" type="button">review queue をJSONでコピー</button>
                <button id="loadReviewQueueJson" class="button small" type="button">現在JSONを表示</button>
                <button id="importReviewQueueJson" class="button small" type="button">JSONを取り込む</button>
                <button id="resetReviewQueue" class="button small" type="button">review queue を初期化</button>
              </div>
              <textarea id="reviewQueueEditor" class="input" rows="10" style="margin-top:10px;font-family:ui-monospace, SFMono-Regular, Menlo, monospace;line-height:1.6;">{
  "bundles": []
}</textarea>
              <div id="reviewQueueList" class="queue-list"></div>
            </div>
          </aside>

          <section class="seed-panel seed-column">
            <div class="panel-head">
              <div>
                <h2 style="margin:0;">相方候補</h2>
                <div class="result-meta" id="seedCandidateSummary"></div>
              </div>
            </div>
            <div id="seedCandidateList" class="seed-list"></div>
          </section>

          <section class="seed-panel seed-column">
            <div class="panel-head">
              <div>
                <h2 style="margin:0;">総集編企画案</h2>
                <div class="result-meta" id="seedBundleSummary"></div>
              </div>
            </div>
            <div id="seedBundleList" class="seed-bundle-list"></div>
          </section>
        </div>
      </section>

      <section class="mode-section" data-mode-panel="search">
        <div class="layout">
          <aside class="sidebar">
            <div class="filter-group">
              <h2 class="section-title">一覧ナビ</h2>
              <div class="nav-tabs" id="facetTabs">
                <button class="nav-tab active" type="button" data-tab="lineage">系統</button>
                <button class="nav-tab" type="button" data-tab="kana">50音</button>
                <button class="nav-tab" type="button" data-tab="year">年代</button>
                <button class="nav-tab" type="button" data-tab="magazine">掲載誌</button>
              </div>
              <div class="facet-summary" id="facetSummary">系統一覧から作品を絞り込めます。</div>
              <div class="chip-row" id="facetChips"></div>
            </div>

            <div class="filter-group">
              <h2 class="section-title">基本フィルタ</h2>
              <div class="checks">
                <label class="check"><input id="filterNeedsRecording" type="checkbox" /> 未朗読・要録音のみ</label>
                <label class="check"><input id="filterLocal" type="checkbox" /> ローカル本文あり</label>
                <label class="check"><input id="filterBookdata" type="checkbox" /> 詳細bookdataあり</label>
              </div>
            </div>

            <div class="filter-group">
              <h2 class="section-title">高度なフィルタ</h2>
              <div class="checks">
                <label class="check"><input id="filterChannel" type="checkbox" /> チャンネル掲載履歴あり</label>
                <label class="check"><input id="filterAudio" type="checkbox" /> 外部音声アーカイブあり</label>
                <label class="check"><input id="filterChronology" type="checkbox" /> 年表データあり</label>
              </div>
            </div>
          </aside>

          <section class="main-panel">
            <div class="panel-head">
              <div class="result-meta" id="count"></div>
              <div class="view-switch" id="viewSwitch">
                <button class="button view-button" type="button" data-view="cards">カード表示</button>
                <button class="button view-button" type="button" data-view="works">作品一覧</button>
                <button class="button view-button active" type="button" data-view="simple">簡潔一覧</button>
              </div>
              <div class="result-meta">普段は簡潔一覧、比較は作品一覧、深掘り確認だけカード表示に切り替えます。</div>
            </div>
            <div class="cards" id="list"></div>
          </section>
        </div>
      </section>

      <section class="mode-section" data-mode-panel="recording">
        <div class="gap-panel">
          <div>
            <div class="panel-head">
              <div>
                <h2 style="margin:0;">要録音一覧</h2>
                <div class="result-meta" id="needsRecordingPanelSummary"></div>
              </div>
              <div class="comp-toolbar">
                <button id="exportRecordingState" class="button" type="button">録音状態をJSONでコピー</button>
                <button id="resetRecordingState" class="button" type="button">録音状態を初期化</button>
              </div>
            </div>
            <div class="result-meta">ここで更新した録音状態はこのブラウザに保存されます。固定したい場合は書き出したJSONを保存して再ビルドしてください。</div>
          </div>
          <div class="gap-grid">
            <article class="gap-card">
              <h3 style="margin:0 0 8px;">要録音作品</h3>
              <div class="gap-note" id="needsRecordingSummary"></div>
              <ol class="gap-list" id="needsRecordingList"></ol>
            </article>
            <article class="gap-card">
              <h3 style="margin:0 0 8px;">手動更新済み</h3>
              <div class="gap-note" id="recordingOverrideSummary"></div>
              <ol class="gap-list" id="recordingOverrideList"></ol>
            </article>
          </div>
        </div>
      </section>

      <section class="mode-section" data-mode-panel="missing">
        <div class="gap-panel">
          <div>
            <div class="panel-head">
              <div>
                <h2 style="margin:0;">bookdata / 本文の不足一覧</h2>
                <div class="result-meta" id="gapSummary"></div>
              </div>
            </div>
            <div class="result-meta">青空文庫照合はまだ全件解決ではないため、まずは現手持ちベースの不足を表示します。</div>
          </div>
          <div class="gap-grid">
            <article class="gap-card">
              <h3 style="margin:0 0 8px;">bookdata未作成</h3>
              <div class="gap-note" id="missingBookdataSummary"></div>
              <ol class="gap-list" id="missingBookdataList"></ol>
            </article>
            <article class="gap-card">
              <h3 style="margin:0 0 8px;">本文未所持</h3>
              <div class="gap-note" id="missingTextSummary"></div>
              <ol class="gap-list" id="missingTextList"></ol>
            </article>
            <article class="gap-card">
              <h3 style="margin:0 0 8px;">青空照合未解決</h3>
              <div class="gap-note" id="aozoraSummary"></div>
              <ol class="gap-list" id="aozoraList"></ol>
            </article>
          </div>
        </div>
      </section>
    </div>

  <script id=\"index-data\" type=\"application/json\">__DATA_JSON__</script>
  <script>
    const payload = JSON.parse(document.getElementById('index-data').textContent);
    const items = payload.items;
    const lineages = payload.lineages;
    const kanaGroups = payload.kana_groups || [];
    const yearGroups = payload.year_groups || [];
    const magazineGroups = payload.magazine_groups || [];
    let stats = { ...(payload.stats || {}) };
    const compilation = payload.compilation;
    const recording = payload.recording || { state: { recording_overrides: [] } };
    const reviewQueue = payload.review_queue || { state: { bundles: [] } };
    const themeMatch = payload.theme_match || { themes: [], scores: [] };
    const youtubeSeedReport = payload.youtube_seed_report || { generated_at: '', seeds: [] };
    const gaps = payload.gaps || {
      missing_bookdata: [],
      missing_text: [],
      unresolved_aozora: [],
    };
    const RECORDING_LOCAL_STORAGE_KEY = 'zenigataHeijiRecordingStateV1';
    const REVIEW_QUEUE_LOCAL_STORAGE_KEY = 'zenigataHeijiBundleReviewQueueV1';
    const itemMap = new Map(items.map(item => [item.title, item]));
    const themeScoreMap = new Map();
    themeMatch.scores.forEach(score => {
      const theme = String(score.theme || '');
      if (!theme) return;
      if (!themeScoreMap.has(theme)) {
        themeScoreMap.set(theme, new Map());
      }
      themeScoreMap.get(theme).set(String(score.title || ''), score);
    });

    const els = {
      q: document.getElementById('q'),
      sort: document.getElementById('sort'),
      modeSwitch: document.getElementById('modeSwitch'),
      modeSummary: document.getElementById('modeSummary'),
      facetTabs: document.getElementById('facetTabs'),
      facetSummary: document.getElementById('facetSummary'),
      facetChips: document.getElementById('facetChips'),
      filterLocal: document.getElementById('filterLocal'),
      filterBookdata: document.getElementById('filterBookdata'),
      filterChannel: document.getElementById('filterChannel'),
      filterAudio: document.getElementById('filterAudio'),
      filterChronology: document.getElementById('filterChronology'),
      filterNeedsRecording: document.getElementById('filterNeedsRecording'),
      stats: document.getElementById('stats'),
      count: document.getElementById('count'),
      list: document.getElementById('list'),
      viewSwitch: document.getElementById('viewSwitch'),
      gapSummary: document.getElementById('gapSummary'),
      missingBookdataSummary: document.getElementById('missingBookdataSummary'),
      missingBookdataList: document.getElementById('missingBookdataList'),
      missingTextSummary: document.getElementById('missingTextSummary'),
      missingTextList: document.getElementById('missingTextList'),
      aozoraSummary: document.getElementById('aozoraSummary'),
      aozoraList: document.getElementById('aozoraList'),
      themeSelect: document.getElementById('themeSelect'),
      themeRecordedOnly: document.getElementById('themeRecordedOnly'),
      themeSummary: document.getElementById('themeSummary'),
      themeList: document.getElementById('themeList'),
      compSummary: document.getElementById('compSummary'),
      compHighlights: document.getElementById('compHighlights'),
      compList: document.getElementById('compList'),
      compReadyOnly: document.getElementById('compReadyOnly'),
      adoptedSummary: document.getElementById('adoptedSummary'),
      adoptedList: document.getElementById('adoptedList'),
      youtubeSeedSummary: document.getElementById('youtubeSeedSummary'),
      youtubeSeedPreferBacklog: document.getElementById('youtubeSeedPreferBacklog'),
      youtubeSeedList: document.getElementById('youtubeSeedList'),
      seedSelectionSummary: document.getElementById('seedSelectionSummary'),
      seedFocusCard: document.getElementById('seedFocusCard'),
      clearSeedSelection: document.getElementById('clearSeedSelection'),
      seedPlanSize: document.getElementById('seedPlanSize'),
      seedTone: document.getElementById('seedTone'),
      seedExcludeAdopted: document.getElementById('seedExcludeAdopted'),
      seedExcludeUnrecorded: document.getElementById('seedExcludeUnrecorded'),
      seedExcludeNoText: document.getElementById('seedExcludeNoText'),
      seedExcludeExistingTheme: document.getElementById('seedExcludeExistingTheme'),
      seedCandidateSummary: document.getElementById('seedCandidateSummary'),
      seedCandidateList: document.getElementById('seedCandidateList'),
      seedBundleSummary: document.getElementById('seedBundleSummary'),
      seedBundleList: document.getElementById('seedBundleList'),
      plannerPulse: document.getElementById('plannerPulse'),
      reviewQueueSummary: document.getElementById('reviewQueueSummary'),
      reviewQueueList: document.getElementById('reviewQueueList'),
      exportReviewQueue: document.getElementById('exportReviewQueue'),
      loadReviewQueueJson: document.getElementById('loadReviewQueueJson'),
      importReviewQueueJson: document.getElementById('importReviewQueueJson'),
      reviewQueueEditor: document.getElementById('reviewQueueEditor'),
      resetReviewQueue: document.getElementById('resetReviewQueue'),
      needsRecordingPanelSummary: document.getElementById('needsRecordingPanelSummary'),
      needsRecordingSummary: document.getElementById('needsRecordingSummary'),
      needsRecordingList: document.getElementById('needsRecordingList'),
      recordingOverrideSummary: document.getElementById('recordingOverrideSummary'),
      recordingOverrideList: document.getElementById('recordingOverrideList'),
      exportRecordingState: document.getElementById('exportRecordingState'),
      resetRecordingState: document.getElementById('resetRecordingState'),
      exportState: document.getElementById('exportState'),
      resetState: document.getElementById('resetState'),
    };

    let activeFacetTab = 'lineage';
    let activeLineage = 'all';
    let activeKana = 'all';
    let activeYear = 'all';
    let activeMagazine = 'all';
    let activeView = 'simple';
    let activeMode = 'compilation';
    let seedTitle = '';
    let compilationState = loadCompilationState();
    let recordingState = loadRecordingState();
    let reviewQueueState = loadReviewQueueState();

    function clone(value) {
      return JSON.parse(JSON.stringify(value));
    }

    function normalizeState(raw) {
      const base = { adopted_candidates: [] };
      if (!raw || typeof raw !== 'object') return base;
      const adopted = Array.isArray(raw.adopted_candidates)
        ? raw.adopted_candidates
            .filter(entry => entry && typeof entry === 'object')
            .map(entry => ({
              candidate_id: String(entry.candidate_id || '').trim(),
              theme: String(entry.theme || '').trim(),
              title: String(entry.title || '').trim(),
              note: String(entry.note || '').trim(),
              work_titles: Array.isArray(entry.work_titles)
                ? entry.work_titles.map(title => String(title).trim()).filter(Boolean)
                : [],
              needs_recording_titles: Array.isArray(entry.needs_recording_titles)
                ? entry.needs_recording_titles.map(title => String(title).trim()).filter(Boolean)
                : [],
              adopted_at: String(entry.adopted_at || '').trim(),
            }))
            .filter(entry => entry.work_titles.length)
        : [];
      return { adopted_candidates: adopted };
    }

    function normalizeRecordingState(raw) {
      const base = { recording_overrides: [] };
      if (!raw || typeof raw !== 'object') return base;
      const overrides = Array.isArray(raw.recording_overrides)
        ? raw.recording_overrides
            .filter(entry => entry && typeof entry === 'object')
            .map(entry => ({
              title: String(entry.title || '').trim(),
              is_recorded: Boolean(entry.is_recorded),
              note: String(entry.note || '').trim(),
              updated_at: String(entry.updated_at || '').trim(),
            }))
            .filter(entry => entry.title)
        : [];
      return { recording_overrides: overrides };
    }

    function normalizeReviewQueueState(raw) {
      const base = { bundles: [] };
      if (!raw || typeof raw !== 'object') return base;
      const bundles = Array.isArray(raw.bundles)
        ? raw.bundles
            .filter(entry => entry && typeof entry === 'object')
            .map(entry => ({
              bundle_id: String(entry.bundle_id || '').trim(),
              bundle_group: String(entry.bundle_group || 'seeded').trim() || 'seeded',
              source_title: String(entry.source_title || '').trim(),
              theme: String(entry.theme || '').trim(),
              recommended_title: String(entry.recommended_title || '').trim(),
              thumbnail_text: String(entry.thumbnail_text || '').trim(),
              summary: String(entry.summary || '').trim(),
              review_prompt: String(entry.review_prompt || '').trim(),
              publication_priority: String(entry.publication_priority || 'medium').trim() || 'medium',
              review_reason: String(entry.review_reason || '').trim(),
              review_status: String(entry.review_status || 'pending').trim() || 'pending',
              estimated_minutes: Number(entry.estimated_minutes || 0) || 0,
              overlap_rate: Number(entry.overlap_rate || 0) || 0,
              needs_recording_titles: Array.isArray(entry.needs_recording_titles)
                ? entry.needs_recording_titles.map(title => String(title || '').trim()).filter(Boolean)
                : [],
              created_at: String(entry.created_at || '').trim(),
              works: Array.isArray(entry.works)
                ? entry.works
                    .filter(work => work && typeof work === 'object')
                    .map(work => ({
                      title: String(work.title || '').trim(),
                      synopsis: String(work.synopsis || '').trim(),
                      themes: Array.isArray(work.themes)
                        ? work.themes.map(value => String(value || '').trim()).filter(Boolean)
                        : [],
                      tags: Array.isArray(work.tags)
                        ? work.tags.map(value => String(value || '').trim()).filter(Boolean)
                        : [],
                      characters: Array.isArray(work.characters)
                        ? work.characters.map(value => String(value || '').trim()).filter(Boolean)
                        : [],
                      story_lineage: String(work.story_lineage || '').trim(),
                      bookdata_path: String(work.bookdata_path || '').trim(),
                      has_local_text: Boolean(work.has_local_text),
                      is_recorded: Boolean(work.is_recorded),
                    }))
                    .filter(work => work.title)
                : [],
            }))
            .filter(entry => entry.bundle_id && entry.works.length)
        : [];
      return { bundles };
    }

    function loadCompilationState() {
      const seed = normalizeState(compilation.state || {});
      try {
        const stored = localStorage.getItem('zenigataHeijiCompilationStateV1');
        if (!stored) return seed;
        return normalizeState(JSON.parse(stored));
      } catch (_error) {
        return seed;
      }
    }

    function saveCompilationState() {
      localStorage.setItem(
        'zenigataHeijiCompilationStateV1',
        JSON.stringify(compilationState, null, 2)
      );
    }

    function loadRecordingState() {
      const seed = normalizeRecordingState(recording.state || {});
      try {
        const stored = localStorage.getItem(RECORDING_LOCAL_STORAGE_KEY);
        if (!stored) return seed;
        return normalizeRecordingState(JSON.parse(stored));
      } catch (_error) {
        return seed;
      }
    }

    function saveRecordingState() {
      localStorage.setItem(
        RECORDING_LOCAL_STORAGE_KEY,
        JSON.stringify(recordingState, null, 2)
      );
    }

    function loadReviewQueueState() {
      const seed = normalizeReviewQueueState(reviewQueue.state || {});
      try {
        const stored = localStorage.getItem(REVIEW_QUEUE_LOCAL_STORAGE_KEY);
        if (!stored) return seed;
        return normalizeReviewQueueState(JSON.parse(stored));
      } catch (_error) {
        return seed;
      }
    }

    function saveReviewQueueState() {
      localStorage.setItem(
        REVIEW_QUEUE_LOCAL_STORAGE_KEY,
        JSON.stringify(reviewQueueState, null, 2)
      );
    }

    function recordingOverrideMap() {
      return new Map(
        (recordingState.recording_overrides || []).map(entry => [entry.title, entry])
      );
    }

    function refreshRecordingDerivedFields() {
      const overrides = recordingOverrideMap();
      items.forEach(item => {
        const override = overrides.get(item.title) || null;
        const baseRecorded = Boolean(item.base_is_recorded);
        const isRecorded = override ? Boolean(override.is_recorded) : baseRecorded;
        item.base_is_recorded = baseRecorded;
        item.recording_override = override ? isRecorded : null;
        item.is_recorded = isRecorded;
        item.needs_recording = !isRecorded;
        if (override) {
          item.recording_source = 'manual';
          item.recording_status = isRecorded ? '手動更新・朗読済み' : '手動更新・未朗読・要録音';
          item.recording_note = override.note || (isRecorded ? '録音状態を手動更新' : '録音待ちとして手動更新');
        } else {
          item.recording_source = 'catalog';
          item.recording_status = isRecorded ? '朗読済み' : '未朗読・要録音';
          item.recording_note = isRecorded ? '既に朗読公開済み' : 'チャンネル掲載履歴がないため録音候補';
        }
        item.search_text_base = item.search_text_base || item.search_text || '';
        item.search_text = `${item.search_text_base} ${item.recording_status} ${item.recording_note}`.trim();
      });
      stats = {
        ...(payload.stats || {}),
        recorded: items.filter(item => item.is_recorded).length,
        needs_recording: items.filter(item => item.needs_recording).length,
      };
    }

    function setRecordingOverride(title, isRecorded) {
      const item = itemMap.get(String(title || ''));
      if (!item) return;
      const baseRecorded = Boolean(item.base_is_recorded);
      const next = (recordingState.recording_overrides || [])
        .filter(entry => entry.title !== item.title);
      if (isRecorded !== baseRecorded) {
        next.push({
          title: item.title,
          is_recorded: isRecorded,
          note: isRecorded ? '録音完了として手動更新' : '未録音として手動更新',
          updated_at: new Date().toLocaleString('ja-JP'),
        });
      }
      recordingState = { recording_overrides: next };
      saveRecordingState();
      refreshRecordingDerivedFields();
      renderStats();
      renderRecordingPanel();
      renderCompilation();
      renderSeedExplorer();
      render();
    }

    function clearRecordingOverride(title) {
      recordingState = {
        recording_overrides: (recordingState.recording_overrides || [])
          .filter(entry => entry.title !== title),
      };
      saveRecordingState();
      refreshRecordingDerivedFields();
      renderStats();
      renderRecordingPanel();
      renderCompilation();
      renderSeedExplorer();
      render();
    }

    function adoptedTitlesSet() {
      const adopted = new Set();
      compilationState.adopted_candidates.forEach(entry => {
        entry.work_titles.forEach(title => adopted.add(title));
      });
      return adopted;
    }

    function youtubeSeedEntries() {
      return Array.isArray(youtubeSeedReport.seeds) ? youtubeSeedReport.seeds : [];
    }

    function youtubeSeedPriority(entry) {
      const status = String((entry && entry.adoption_status) || '').trim();
      if (status === '未採用') return 0;
      if (status === '旧実績のみ') return 1;
      if (status === '採用済み') return 2;
      return 3;
    }

    function youtubeSeedMap() {
      return new Map(youtubeSeedEntries().map(entry => [String(entry.seed_title || ''), entry]));
    }

    function formatNumber(value) {
      const numeric = Number(value || 0);
      return Number.isFinite(numeric) ? numeric.toLocaleString('ja-JP') : '0';
    }

    function formatPercent(value) {
      const numeric = Number(value || 0);
      return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(1)}%` : '0.0%';
    }

    function formatDurationSeconds(value) {
      const total = Math.max(0, Number(value || 0));
      const minutes = Math.floor(total / 60);
      const seconds = Math.floor(total % 60);
      return `${minutes}分${String(seconds).padStart(2, '0')}秒`;
    }

    function renderStats() {
      const seedCount = youtubeSeedEntries().length;
      els.stats.innerHTML = `
        <table class=\"stats-table\">
          <thead>
            <tr>
              <th>項目</th>
              <th>件数</th>
              <th>項目</th>
              <th>件数</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th>作品数</th>
              <td><strong>${stats.works}</strong></td>
              <th>朗読済み</th>
              <td><strong>${stats.recorded}</strong></td>
            </tr>
            <tr>
              <th>要録音</th>
              <td><strong>${stats.needs_recording}</strong></td>
              <th>本文あり</th>
              <td><strong>${stats.with_local_text}</strong></td>
            </tr>
            <tr>
              <th>bookdata</th>
              <td><strong>${stats.with_bookdata}</strong></td>
              <th>年表データ</th>
              <td><strong>${stats.with_chronology}</strong></td>
            </tr>
            <tr>
              <th>チャンネル履歴</th>
              <td><strong>${stats.with_channel}</strong></td>
              <th>音声アーカイブ</th>
              <td><strong>${stats.with_audio}</strong></td>
            </tr>
            <tr>
              <th>YouTube核候補</th>
              <td><strong>${seedCount}</strong></td>
              <th>採用済み</th>
              <td><strong>${stats.adopted}</strong></td>
            </tr>
          </tbody>
        </table>
      `;
    }

    function escapeHtml(text) {
      return String(text || '')
        .split('&').join('&amp;')
        .split('<').join('&lt;')
        .split('>').join('&gt;')
        .split('"').join('&quot;');
    }

    function badge(label, type = '') {
      return `<span class=\"badge ${type}\">${escapeHtml(label)}</span>`;
    }

    async function copyText(text) {
      const value = String(text || '').trim();
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
      } catch (_error) {
        window.prompt('コピーできないため、ここからコピーしてください', value);
      }
    }

    function miniChips(values, limit = 8) {
      if (!values || !values.length) return '';
      return values.slice(0, limit).map(value => (
        `<span class="chip-mini">${escapeHtml(value)}</span>`
      )).join('');
    }

    function aozoraStatusLabel(item) {
      const mapping = {
        resolved: '青空解決',
        local_text_present: '手持ち本文あり',
        local_bookdata_ready: '本文・bookdataあり',
        needs_lookup: '青空未照合',
        unresolved: '青空未解決',
        ndl_candidate: '国会図書館候補',
        external_public_candidate: '外部公開候補',
        likely_text_missing: '本文不在濃厚',
        unchecked: '青空未確認',
      };
      const key = String((item && item.aozora_status) || 'unchecked').trim();
      return mapping[key] || key || '青空未確認';
    }

    function resolveWorkItem(workLike) {
      if (!workLike) return null;
      const title = typeof workLike === 'string' ? workLike : String(workLike.title || '');
      return itemMap.get(title) || workLike;
    }

    function bundleResourceSummary(works) {
      const resolvedWorks = (works || []).map(resolveWorkItem).filter(Boolean);
      const summary = { total: resolvedWorks.length, recorded: 0, localText: 0, bookdata: 0, audio: 0, aozoraReady: 0 };
      resolvedWorks.forEach(item => {
        if (item.is_recorded) summary.recorded += 1;
        if (item.has_local_text) summary.localText += 1;
        if (item.has_bookdata) summary.bookdata += 1;
        if (item.has_audio_archive) summary.audio += 1;
        if (['resolved', 'local_text_present', 'local_bookdata_ready'].includes(String(item.aozora_status || ''))) {
          summary.aozoraReady += 1;
        }
      });
      return summary;
    }

    function themeEvidenceForWorks(theme, works) {
      const map = theme ? themeScoreMap.get(String(theme || '')) : null;
      if (!map) return null;
      const scored = (works || []).map(work => map.get(String(work.title || ''))).filter(Boolean);
      if (!scored.length) return null;
      const average = Math.round(scored.reduce((sum, entry) => sum + Number(entry.score_percent || 0), 0) / scored.length);
      const reasons = uniqueValues(
        scored.reduce((acc, entry) => (
          acc.concat(Array.isArray(entry.reason_hits) ? entry.reason_hits : [])
        ), [])
      ).slice(0, 3);
      return { average, reasons, count: scored.length };
    }

    function renderResourceStrip(item) {
      const source = resolveWorkItem(item);
      if (!source) return '';
      const pills = [
        `<span class="resource-pill"><strong>朗読</strong>${escapeHtml(source.is_recorded ? '済' : '未')}</span>`,
        `<span class="resource-pill"><strong>本文</strong>${escapeHtml(source.has_local_text ? 'あり' : 'なし')}</span>`,
        `<span class="resource-pill"><strong>bookdata</strong>${escapeHtml(source.has_bookdata ? 'あり' : 'なし')}</span>`,
        `<span class="resource-pill"><strong>青空</strong>${escapeHtml(aozoraStatusLabel(source))}</span>`,
      ];
      if (source.has_vrew_assets) {
        pills.push(`<span class="resource-pill"><strong>Vrew</strong>素材あり</span>`);
      }
      if (source.has_audio_archive) {
        const audioYears = Array.isArray(source.audio_recording_years) && source.audio_recording_years.length
          ? ` / ${source.audio_recording_years.join('→')}`
          : '';
        pills.push(`<span class="resource-pill"><strong>音源</strong>${escapeHtml(source.audio_file_count || 0)}件${escapeHtml(audioYears)}</span>`);
      }
      return `<div class="resource-strip">${pills.join('')}</div>`;
    }

    function renderWorkEvidenceItem(workLike) {
      const item = resolveWorkItem(workLike);
      if (!item) return '';
      const chips = miniChips(uniqueValues([
        item.story_lineage,
        ...(item.theme_secondary || []),
        ...(item.tags || []).slice(0, 4),
      ]), 6);
      const meta = [item.publication_years || '年表未確認', item.magazines || '掲載誌未確認'].filter(Boolean).join(' / ');
      return `
        <article class="work-evidence-item">
          <h4>${escapeHtml(item.title)}</h4>
          <div class="work-evidence-meta">${escapeHtml(meta)}</div>
          ${renderResourceStrip(item)}
          ${chips ? `<div class="chips-mini">${chips}</div>` : ''}
          <p>${escapeHtml(item.synopsis || item.summary || '要約未設定')}</p>
        </article>
      `;
    }

    function renderPlannerPulse() {
      if (!els.plannerPulse) return;
      const compilationCandidates = buildCompilationCandidates();
      const readyCount = compilationCandidates.filter(item => item.ready).length;
      const queueCount = (reviewQueueState.bundles || []).length;
      const adoptedCount = (compilationState.adopted_candidates || []).length;
      const unresolvedAozora = (gaps.unresolved_aozora && gaps.unresolved_aozora.length) || 0;
      const topSeed = youtubeSeedEntries()[0] || null;
      const pulseBlocks = [
        { title: '総集編企画', body: `候補 ${compilationCandidates.length}件 / 今すぐ作れる ${readyCount}件` },
        { title: 'YouTube核候補', body: topSeed ? `首位 ${topSeed.seed_title} / score ${Math.round(Number(topSeed.seed_score || 0))}` : 'seed report 未生成' },
        { title: 'review queue', body: `審査待ち ${queueCount}件 / 採用済み ${adoptedCount}件` },
        { title: '録音状況', body: `要録音 ${stats.needs_recording || 0}本 / 朗読済み ${stats.recorded || 0}本` },
        { title: '資料補完', body: `bookdata不足 ${(gaps.missing_bookdata && gaps.missing_bookdata.length) || 0}本 / 青空未解決 ${unresolvedAozora}本` },
      ];
      els.plannerPulse.innerHTML = pulseBlocks.map(block => `
        <article class="pulse-card">
          <strong>${escapeHtml(block.title)}</strong>
          <span>${escapeHtml(block.body)}</span>
        </article>
      `).join('');
    }

    function renderBookdataLinkActions(item, className = 'resource-actions') {
      if (!item || !item.bookdata_href) return '';
      return `
        <div class="${escapeHtml(className)}">
          <a class="button small" href="${escapeHtml(item.bookdata_href)}" target="_blank" rel="noopener noreferrer">JSONを表示</a>
          ${item.bookdata_file_uri ? `<a class="button small" href="${escapeHtml(item.bookdata_file_uri)}" target="_blank" rel="noopener noreferrer">JSONを直開き</a>` : ''}
          ${item.bookdata_dir_uri ? `<a class="button small" href="${escapeHtml(item.bookdata_dir_uri)}" target="_blank" rel="noopener noreferrer">Finderで開く</a>` : ''}
          <button class="button small" type="button" data-copy-path="${escapeHtml(item.bookdata_abs_path || '')}">JSONパスをコピー</button>
          <button class="button small" type="button" data-copy-path="${escapeHtml(item.bookdata_dir_abs_path || '')}">Finder用フォルダパスをコピー</button>
        </div>
      `;
    }

    function renderVrewActions(item, className = 'resource-actions') {
      if (!item || !item.has_vrew_assets) return '';
      return `
        <div class="${escapeHtml(className)}">
          ${item.vrew_text_href ? `<a class="button small" href="${escapeHtml(item.vrew_text_href)}" target="_blank" rel="noopener noreferrer">Vrew TXT</a>` : ''}
        </div>
      `;
    }

    function renderPrimaryTextActions(item, className = 'resource-actions') {
      if (!item) return '';
      const actions = [];
      if (item.aozora_card_url) {
        actions.push(`<a class="button small" href="${escapeHtml(item.aozora_card_url)}" target="_blank" rel="noopener noreferrer">青空文庫ページ</a>`);
      }
      if (item.aozora_text_url) {
        actions.push(`<a class="button small" href="${escapeHtml(item.aozora_text_url)}" target="_blank" rel="noopener noreferrer">青空テキスト</a>`);
      }
      if (item.preferred_text_href) {
        actions.push(`<a class="button small" href="${escapeHtml(item.preferred_text_href)}" target="_blank" rel="noopener noreferrer">元text</a>`);
      } else if (item.preferred_text_file_uri) {
        actions.push(`<a class="button small" href="${escapeHtml(item.preferred_text_file_uri)}" target="_blank" rel="noopener noreferrer">元text</a>`);
      }
      return actions.length ? `<div class="${escapeHtml(className)}">${actions.join('')}</div>` : '';
    }

    function renderTextPreview(item) {
      if (!item || !item.preferred_text_preview) return '';
      return `
        <details>
          <summary>元textプレビュー</summary>
          <div class="detail-block">
            <div><span class="detail-label">本文抜粋</span>${escapeHtml(item.preferred_text_preview)}</div>
          </div>
        </details>
      `;
    }

    function renderPathLinkActions(paths, uris, limit = 4) {
      if (!Array.isArray(paths) || !paths.length) return '';
      return paths.slice(0, limit).map((path, index) => {
        const uri = Array.isArray(uris) ? (uris[index] || '') : '';
        const label = String(path || '').split('/').filter(Boolean).pop() || `フォルダ${index + 1}`;
        if (uri) {
          return `<a class="button small" href="${escapeHtml(uri)}" target="_blank" rel="noopener noreferrer" title="${escapeHtml(path)}">${escapeHtml(label)}</a>`;
        }
        return `<span title="${escapeHtml(path)}">${escapeHtml(label)}</span>`;
      }).join('');
    }

    function renderSeedAction(item) {
      if (!item) return '';
      return `
        <div class="inline-actions">
          <button class="button primary small" type="button" data-seed-title="${escapeHtml(item.title)}">この作品から候補を探す</button>
        </div>
      `;
    }

    function renderYoutubeSeedCard(entry) {
      const seedTitle = String(entry.seed_title || '');
      const item = itemMap.get(seedTitle) || null;
      const badges = [
        badge(`rank ${entry.rank || '-'}`, 'good'),
        entry.adoption_status ? badge(entry.adoption_status, entry.adoption_status === '採用済み' ? 'good' : '') : '',
        entry.has_local_text ? badge('本文あり', 'good') : badge('本文なし', 'warn'),
        item && item.is_recorded ? badge('朗読済み', 'good') : badge('要録音', 'warn'),
      ].filter(Boolean).join('');
      return `
        <article class="youtube-seed-card">
          <div class="youtube-seed-head">
            <div>
              <div class="youtube-seed-rank">#${escapeHtml(entry.rank || '-')}</div>
              <strong>${escapeHtml(seedTitle)}</strong>
              <div class="subline">${escapeHtml(entry.story_lineage || '未分類')} / ${escapeHtml(entry.publication_years || '年代未確認')}</div>
            </div>
            <div class="youtube-seed-score">seed score<br><strong>${escapeHtml(Math.round(Number(entry.seed_score || 0)))}</strong></div>
          </div>
          <div class="badges">${badges}</div>
          <div class="youtube-seed-grid">
            <div class="youtube-seed-metric"><strong>views</strong>${escapeHtml(formatNumber(entry.views))}</div>
            <div class="youtube-seed-metric"><strong>impressions</strong>${escapeHtml(formatNumber(entry.impressions))}</div>
            <div class="youtube-seed-metric"><strong>CTR</strong>${escapeHtml(formatPercent(entry.impression_ctr))}</div>
            <div class="youtube-seed-metric"><strong>直近7日impr</strong>${escapeHtml(formatNumber(entry.last_7d_impressions))}</div>
            <div class="youtube-seed-metric"><strong>signal</strong>${escapeHtml(Math.round(Number(entry.signal_score || 0)))}</div>
            <div class="youtube-seed-metric"><strong>尺</strong>${escapeHtml(formatDurationSeconds(entry.duration_seconds))}</div>
          </div>
          <div class="youtube-seed-note">${escapeHtml(entry.channel_title || '')}</div>
          <div class="inline-actions">
            <button class="button primary small" type="button" data-seed-title="${escapeHtml(seedTitle)}">この作品を核にする</button>
          </div>
        </article>
      `;
    }

    function renderYoutubeSeedPanel() {
      const preferBacklog = Boolean(els.youtubeSeedPreferBacklog && els.youtubeSeedPreferBacklog.checked);
      const entries = youtubeSeedEntries()
        .slice()
        .sort((left, right) => {
          if (preferBacklog) {
            const leftPriority = youtubeSeedPriority(left);
            const rightPriority = youtubeSeedPriority(right);
            if (leftPriority !== rightPriority) return leftPriority - rightPriority;
          }
          const leftScore = Number(left.seed_score || 0);
          const rightScore = Number(right.seed_score || 0);
          if (leftScore !== rightScore) return rightScore - leftScore;
          return String(left.seed_title || '').localeCompare(String(right.seed_title || ''), 'ja');
        })
        .slice(0, 6);
      if (!els.youtubeSeedSummary || !els.youtubeSeedList) return;
      if (!entries.length) {
        els.youtubeSeedSummary.textContent = 'reports/zenigata_seed_shortworks.csv がまだありません。channel report を更新すると表示されます。';
        els.youtubeSeedList.innerHTML = '<div class="gap-note">seed report 未生成です。</div>';
        return;
      }
      const generated = youtubeSeedReport.generated_at ? ` / 生成 ${youtubeSeedReport.generated_at}` : '';
      const top = entries[0];
      const modeLabel = preferBacklog ? '未採用・旧実績のみ優先' : '純粋な成績順';
      els.youtubeSeedSummary.textContent = `短編の成績上位 ${entries.length}本を表示中。表示順は ${modeLabel}。先頭は ${top.seed_title}、score ${Math.round(Number(top.seed_score || 0))}${generated}`;
      els.youtubeSeedList.innerHTML = entries.map(renderYoutubeSeedCard).join('');
    }

    function renderBookdataActions(item) {
      if (!item) return '';
      return `
        ${renderSeedAction(item)}
        ${renderPrimaryTextActions(item, 'inline-actions')}
        ${renderVrewActions(item, 'inline-actions')}
        ${renderBookdataInlineDetails(item)}
        ${item.bookdata_href ? renderBookdataLinkActions(item) : ''}
      `;
    }

    function getBookdataDetail(item) {
      if (!item || !item.bookdata_detail || !item.bookdata_detail.available) {
        return null;
      }
      return item.bookdata_detail;
    }

    function renderMetaGrid(entries) {
      if (!entries.length) return '';
      return `
        <div class="bookdata-meta-grid">
          ${entries.map(entry => `
            <div class="bookdata-meta-item">
              <strong>${escapeHtml(entry.label)}</strong>
              <div>${escapeHtml(entry.value)}</div>
            </div>
          `).join('')}
        </div>
      `;
    }

    function renderBulletSection(title, values) {
      if (!values || !values.length) return '';
      return `
        <section class="bookdata-section">
          <h3>${escapeHtml(title)}</h3>
          <ul class="bookdata-list">
            ${values.map(value => `<li>${escapeHtml(value)}</li>`).join('')}
          </ul>
        </section>
      `;
    }

    function renderCharacterSection(detail) {
      if (!detail.characters || !detail.characters.length) return '';
      return `
        <section class="bookdata-section">
          <h3>登場人物</h3>
          <div class="bookdata-card-grid">
            ${detail.characters.map(character => `
              <article class="bookdata-mini-card">
                <h4>${escapeHtml(character.name || '人物')}</h4>
                <p>${escapeHtml(character.description || '説明未設定')}</p>
              </article>
            `).join('')}
          </div>
        </section>
      `;
    }

    function renderGlossarySection(detail) {
      if (!detail.glossary || !detail.glossary.length) return '';
      return `
        <section class="bookdata-section">
          <h3>用語</h3>
          <div class="bookdata-card-grid">
            ${detail.glossary.map(entry => `
              <article class="bookdata-mini-card">
                <h4>${escapeHtml(entry.term || '用語')}</h4>
                ${entry.reading ? `<div class="bookdata-inline-note">${escapeHtml(entry.reading)}</div>` : ''}
                <p>${escapeHtml(entry.description || '説明未設定')}</p>
              </article>
            `).join('')}
          </div>
        </section>
      `;
    }

    function renderBookdataInlineContent(item) {
      const detail = getBookdataDetail(item);
      if (!detail) {
        return '<div class="bookdata-section"><p>表示できる詳細 bookdata がありません。</p></div>';
      }

      const metaEntries = [
        ['著者', detail.author],
        ['ジャンル', detail.japanese_genre || detail.genre],
        ['副ジャンル', detail.sub_genre],
        ['時代', detail.time_period || detail.era],
        ['舞台', detail.location || detail.setting],
        ['成立年', detail.year],
      ].filter(([, value]) => value).map(([label, value]) => ({ label, value }));

      const chipSections = [
        ['キーワード', detail.keywords],
        ['テーマ', detail.themes],
        ['感情', detail.emotions],
      ].filter(([, values]) => values && values.length).map(([title, values]) => `
        <section class="bookdata-section">
          <h3>${escapeHtml(title)}</h3>
          <div class="bookdata-chip-row">${miniChips(values, 24)}</div>
        </section>
      `);

      const chapterSection = detail.chapter_count
        ? `<section class="bookdata-section"><h3>章立て</h3><div class="bookdata-inline-note">全${escapeHtml(detail.chapter_count)}章</div><ul class="bookdata-list">${(detail.chapter_titles || []).map(title => `<li>${escapeHtml(title)}</li>`).join('')}</ul></section>`
        : '';

      return `
        <div class="bookdata-layout">
          ${metaEntries.length ? `<section class="bookdata-section"><h3>作品情報</h3>${renderMetaGrid(metaEntries)}</section>` : ''}
          ${detail.synopsis ? `<section class="bookdata-section"><h3>あらすじ</h3><p>${escapeHtml(detail.synopsis)}</p></section>` : ''}
          ${chipSections.join('')}
          ${renderBulletSection('見どころ', detail.highlights || [])}
          ${renderCharacterSection(detail)}
          ${renderGlossarySection(detail)}
          ${detail.author_profile ? `<section class="bookdata-section"><h3>作者紹介</h3><p>${escapeHtml(detail.author_profile)}</p></section>` : ''}
          ${chapterSection}
        </div>
      `;
    }

    function renderBookdataInlineDetails(item) {
      const detail = getBookdataDetail(item);
      if (!detail) return '';
      const summary = [
        '読書アプリ風で展開',
        item.publication_years || '',
        item.magazines || '',
      ].filter(Boolean).join(' / ');
      return `
        <details class="bookdata-inline">
          <summary>${escapeHtml(summary)}</summary>
          <div class="detail-block">
            ${renderBookdataInlineContent(item)}
          </div>
        </details>
      `;
    }

    function populateThemeSelect() {
      if (!themeMatch.themes || !themeMatch.themes.length) return;
      els.themeSelect.innerHTML = [
        '<option value="">テーマを選択してください</option>',
        ...themeMatch.themes.map(theme => (
          `<option value="${escapeHtml(theme)}">${escapeHtml(theme)}</option>`
        )),
      ].join('');
    }

    function facetGroups() {
      if (activeFacetTab === 'kana') return kanaGroups;
      if (activeFacetTab === 'year') return yearGroups;
      if (activeFacetTab === 'magazine') return magazineGroups;
      return lineages;
    }

    function currentFacetValue() {
      if (activeFacetTab === 'kana') return activeKana;
      if (activeFacetTab === 'year') return activeYear;
      if (activeFacetTab === 'magazine') return activeMagazine;
      return activeLineage;
    }

    function setFacetValue(value) {
      if (activeFacetTab === 'kana') activeKana = value;
      else if (activeFacetTab === 'year') activeYear = value;
      else if (activeFacetTab === 'magazine') activeMagazine = value;
      else activeLineage = value;
    }

    function facetSummaryText() {
      if (activeFacetTab === 'kana') return '50音ごとに作品を一覧できます。漢字題名もかな変換して振り分けます。';
      if (activeFacetTab === 'year') return '発表年代ごとに作品を探せます。';
      if (activeFacetTab === 'magazine') return '掲載誌ごとに作品を探せます。';
      return '物語の系統ごとに作品を一覧できます。';
    }

    function syncFacetTabs() {
      if (!els.facetTabs) return;
      [...els.facetTabs.querySelectorAll('.nav-tab')].forEach(button => {
        button.classList.toggle('active', button.dataset.tab === activeFacetTab);
      });
    }

    function modeSummaryText() {
      if (activeMode === 'seed') return '強い1本を核に、3本または5本の総集編企画案を組む画面です。';
      if (activeMode === 'search') return '作品検索と bookdata 確認に集中する画面です。';
      if (activeMode === 'recording') return '未朗読の確認と手動録音状態の更新だけを扱います。';
      if (activeMode === 'missing') return 'bookdata・本文・青空照合の不足だけを確認します。';
      return '総集編候補の比較と採用判断に集中するトップ画面です。';
    }

    function syncModeButtons() {
      if (!els.modeSwitch) return;
      [...els.modeSwitch.querySelectorAll('[data-mode]')].forEach(button => {
        button.classList.toggle('active', button.dataset.mode === activeMode);
      });
      if (els.modeSummary) {
        els.modeSummary.textContent = modeSummaryText();
      }
    }

    function syncModePanels() {
      document.querySelectorAll('[data-mode-panel]').forEach(panel => {
        panel.classList.toggle('active', panel.dataset.modePanel === activeMode);
      });
    }

    function renderFacetChips() {
      const value = currentFacetValue();
      const chips = [
        `<button class="chip ${value === 'all' ? 'active' : ''}" data-facet-value="all">すべて</button>`,
        ...facetGroups().map(item => (
          `<button class="chip ${value === String(item.name) ? 'active' : ''}" data-facet-value="${escapeHtml(item.name)}">${escapeHtml(item.name)} <small>(${item.count})</small></button>`
        )),
      ];
      els.facetSummary.textContent = facetSummaryText();
      els.facetChips.innerHTML = chips.join('');
    }

    function currentFilters() {
      return {
        query: els.q.value.trim().toLowerCase(),
        sort: els.sort.value,
        local: els.filterLocal.checked,
        bookdata: els.filterBookdata.checked,
        channel: els.filterChannel.checked,
        audio: els.filterAudio.checked,
        chronology: els.filterChronology.checked,
        needsRecording: els.filterNeedsRecording.checked,
      };
    }

    function applyFilters() {
      const filters = currentFilters();
      const adopted = adoptedTitlesSet();
      let filtered = items.filter(item => {
        if (activeFacetTab === 'lineage' && activeLineage !== 'all' && item.story_lineage !== activeLineage) return false;
        if (activeFacetTab === 'kana' && activeKana !== 'all' && item.title_bucket !== activeKana) return false;
        if (activeFacetTab === 'year' && activeYear !== 'all' && item.decade_label !== activeYear) return false;
        if (activeFacetTab === 'magazine' && activeMagazine !== 'all' && !(item.magazine_list || []).includes(activeMagazine)) return false;
        if (filters.local && !item.has_local_text) return false;
        if (filters.bookdata && !item.has_bookdata) return false;
        if (filters.channel && !item.has_channel_entry) return false;
        if (filters.audio && !item.has_audio_archive) return false;
        if (filters.chronology && !item.publication_years) return false;
        if (filters.needsRecording && !item.needs_recording) return false;
        if (filters.query && !String(item.search_text).toLowerCase().includes(filters.query)) return false;
        return true;
      });

      if (filters.sort === 'title') {
        filtered.sort((a, b) => String(a.title).localeCompare(String(b.title), 'ja'));
      } else if (filters.sort === 'year') {
        filtered.sort((a, b) => (a.year_sort - b.year_sort) || String(a.title).localeCompare(String(b.title), 'ja'));
      } else if (filters.sort === 'audio') {
        filtered.sort((a, b) => (b.audio_file_count - a.audio_file_count) || String(a.title).localeCompare(String(b.title), 'ja'));
      }

      return { filtered, adopted };
    }

    function buildCompilationCandidates() {
      const adopted = adoptedTitlesSet();
      const readyOnly = els.compReadyOnly.checked;
      const seen = new Set();
      const candidates = [];

      compilation.groups.forEach(group => {
        const availableWorks = group.work_titles
          .map(title => itemMap.get(title))
          .filter(Boolean)
          .filter(item => !adopted.has(item.title));

        if (availableWorks.length < 3) return;

        const trio = availableWorks.slice(0, 3);
        const signature = trio.map(item => item.title).sort().join('||');
        if (seen.has(signature)) return;
        seen.add(signature);

        const needsRecordingTitles = trio
          .filter(item => item.needs_recording)
          .map(item => item.title);
        const ready = needsRecordingTitles.length === 0;
        if (readyOnly && !ready) return;

        candidates.push({
          candidate_id: `${group.id}::${trio.map(item => item.title).join('||')}`,
          theme: group.theme,
          title: group.suggested_title,
          source_kind: group.source_kind,
          description: group.description,
          works: trio,
          remaining_pool: availableWorks.length,
          needs_recording_titles: needsRecordingTitles,
          ready,
        });
      });

      candidates.sort((a, b) => {
        if (a.ready !== b.ready) return a.ready ? -1 : 1;
        if (a.needs_recording_titles.length !== b.needs_recording_titles.length) {
          return a.needs_recording_titles.length - b.needs_recording_titles.length;
        }
        if (a.remaining_pool !== b.remaining_pool) return b.remaining_pool - a.remaining_pool;
        return String(a.title).localeCompare(String(b.title), 'ja');
      });
      return candidates;
    }

    function adoptedThemeSet() {
      return new Set(
        (compilationState.adopted_candidates || [])
          .map(entry => normalizeThemeLabel(entry.theme || ''))
          .filter(Boolean)
      );
    }

    function normalizeThemeLabel(theme) {
      const clean = String(theme || '').trim();
      if (!clean) return '';
      if (['八五郎活躍', '八五郎篇', 'ガラッ八篇', '八五郎活躍篇'].includes(clean)) {
        return '八五郎・ガラッ八篇';
      }
      if (['恋愛・嫉妬', '恋愛・嫉妬篇'].includes(clean)) {
        return '恋愛・嫉妬篇';
      }
      if (['人情・家族', '人情・家族篇'].includes(clean)) {
        return '人情・家族篇';
      }
      return clean;
    }

    function normalizeLabel(value) {
      return normalizeThemeLabel(String(value || '').trim());
    }

    function uniqueValues(values) {
      return [...new Set((values || []).map(normalizeLabel).filter(Boolean))];
    }

    function intersectionValues(left, right) {
      const rightSet = new Set(uniqueValues(right));
      return uniqueValues(left).filter(value => rightSet.has(value));
    }

    function extractSynopsisKeywords(item) {
      const detail = item.bookdata_detail || {};
      const source = [
        item.synopsis,
        item.summary,
        detail.synopsis,
        ...(detail.keywords || []),
      ].filter(Boolean).join(' ');
      const matches = source.match(/[一-龠ぁ-んァ-ヶA-Za-z0-9]{2,}/g) || [];
      const stopwords = new Set(['こと', 'もの', 'ため', 'よう', 'これ', 'それ', 'ある', 'いる', '事件', '捕物']);
      return uniqueValues(matches.filter(token => !stopwords.has(token)));
    }

    function itemThemeValues(item) {
      const detail = item.bookdata_detail || {};
      return uniqueValues([
        item.story_lineage,
        ...(item.theme_secondary || []),
        ...(detail.themes || []),
      ]);
    }

    function itemTagValues(item) {
      return uniqueValues(item.tags || []);
    }

    function itemEmotionValues(item) {
      const detail = item.bookdata_detail || {};
      return uniqueValues(detail.emotions || []);
    }

    function incidentProfile(item) {
      const source = [
        item.story_lineage,
        ...(item.theme_secondary || []),
        ...(item.tags || []),
        item.synopsis,
        item.summary,
        ...itemThemeValues(item),
      ].filter(Boolean).join(' ');
      const incidentHits = (source.match(/殺|死|盗|首|血|骸|怪|謎|罠|密室|下手人|捕物|探索|追跡|奪/g) || []).length;
      const emotionHits = (source.match(/恋|情|涙|親|子|夫婦|友情|哀|慈|義理|人情|切な|再会|家族/g) || []).length;
      return { incident: incidentHits, emotion: emotionHits };
    }

    function planToneLabel(value) {
      return value === 'emotion' ? '情緒重視' : '事件性重視';
    }

    function currentSeedPlanSize() {
      return Number((els.seedPlanSize && els.seedPlanSize.value) || 3) === 5 ? 5 : 3;
    }

    function currentSeedTone() {
      return String((els.seedTone && els.seedTone.value) || 'incident') === 'emotion' ? 'emotion' : 'incident';
    }

    function itemCharacterValues(item) {
      const detail = item.bookdata_detail || {};
      const detailNames = Array.isArray(detail.characters)
        ? detail.characters.map(entry => entry && entry.name)
        : [];
      return uniqueValues([...(item.characters || []), ...detailNames]);
    }

    function inferBundleTheme(works) {
      const counts = new Map();
      works.forEach(item => {
        uniqueValues([
          item.story_lineage,
          ...(item.theme_secondary || []),
          ...(item.tags || []).slice(0, 5),
          ...((item.bookdata_detail || {}).themes || []),
        ]).forEach(label => {
          counts.set(label, (counts.get(label) || 0) + 1);
        });
      });
      const ranked = [...counts.entries()]
        .sort((a, b) => (b[1] - a[1]) || a[0].localeCompare(b[0], 'ja'))
        .map(([label, count]) => ({ label, count }));
      const strong = ranked.filter(entry => entry.count >= 2).slice(0, 2);
      if (strong.length) return strong.map(entry => entry.label).join('・');
      return ranked.length ? ranked[0].label : '事件と因果';
    }

    function candidatePriority(score, item) {
      if (score >= 95 && item.is_recorded && item.has_local_text) return '高';
      if (score >= 70) return '中';
      return '低';
    }

    function publicationPriority(score, needsRecordingCount) {
      if (score >= 180 && needsRecordingCount === 0) return 'high';
      if (score >= 130 && needsRecordingCount <= 1) return 'medium';
      return 'low';
    }

    function buildReviewReason(seed, bundle, reasons) {
      const workTitles = (bundle.works || []).map(work => work.title).join(' / ');
      const parts = [
        `${seed.title} を核に ${bundle.bundle_size}本で組んだ企画案`,
        `テーマは ${bundle.theme}`,
        bundle.ordering_suggestion ? `並びは ${bundle.ordering_suggestion}` : '',
        reasons.slice(0, 3).join(' / '),
        workTitles,
      ].filter(Boolean);
      return parts.join('。');
    }

    function estimateWorkMinutes(item) {
      const detail = item.bookdata_detail || {};
      let minutes = 24;
      if (item.has_local_text) minutes += 3;
      if (item.has_bookdata) minutes += 2;
      if (detail.chapter_count) minutes += Math.min(Number(detail.chapter_count || 0), 4) * 2;
      if (item.audio_segment_count) minutes += Math.min(Number(item.audio_segment_count || 0), 3);
      return minutes;
    }

    function pairSimilarity(left, right) {
      const leftValues = new Set([
        ...itemThemeValues(left),
        ...itemTagValues(left),
      ]);
      const rightValues = new Set([
        ...itemThemeValues(right),
        ...itemTagValues(right),
      ]);
      const union = new Set([...leftValues, ...rightValues]);
      if (!union.size) return 0;
      let shared = 0;
      union.forEach(value => {
        if (leftValues.has(value) && rightValues.has(value)) shared += 1;
      });
      return shared / union.size;
    }

    function scoreSeedCandidate(seed, item) {
      const majorMatch = seed.story_lineage && seed.story_lineage === item.story_lineage;
      const minorOverlap = intersectionValues(seed.theme_secondary || [], item.theme_secondary || []);
      const themeOverlap = intersectionValues(itemThemeValues(seed), itemThemeValues(item))
        .filter(value => value !== seed.story_lineage);
      const keywordOverlap = intersectionValues(extractSynopsisKeywords(seed), extractSynopsisKeywords(item));
      const tagOverlap = intersectionValues(itemTagValues(seed), itemTagValues(item));
      const characterOverlap = intersectionValues(itemCharacterValues(seed), itemCharacterValues(item));
      const emotionOverlap = intersectionValues(itemEmotionValues(seed), itemEmotionValues(item));
      const reasons = [];
      const components = { heuristic: 0, production: 0, emotional: 0 };

      if (majorMatch) {
        components.heuristic += 30;
        reasons.push(`主系統一致: ${seed.story_lineage}`);
      }
      if (minorOverlap.length) {
        components.heuristic += Math.min(20, minorOverlap.length * 10);
        reasons.push(`副系統一致: ${minorOverlap.slice(0, 3).join(' / ')}`);
      }
      if (themeOverlap.length) {
        components.heuristic += Math.min(15, themeOverlap.length * 5);
        reasons.push(`想定テーマ一致: ${themeOverlap.slice(0, 3).join(' / ')}`);
      }
      if (keywordOverlap.length) {
        components.heuristic += Math.min(15, keywordOverlap.length * 5);
        reasons.push(`あらすじ語彙一致: ${keywordOverlap.slice(0, 3).join(' / ')}`);
      }
      if (tagOverlap.length) {
        components.heuristic += Math.min(10, tagOverlap.length * 5);
        reasons.push(`タグ一致: ${tagOverlap.slice(0, 3).join(' / ')}`);
      }
      if (characterOverlap.length) {
        components.heuristic += 5;
        reasons.push(`登場人物接点: ${characterOverlap.slice(0, 3).join(' / ')}`);
      }
      if (emotionOverlap.length) {
        components.emotional += Math.min(12, emotionOverlap.length * 4);
        reasons.push(`感情線の近さ: ${emotionOverlap.slice(0, 3).join(' / ')}`);
      }
      if (item.is_recorded) {
        components.production += 15;
        reasons.push('朗読済み');
      } else {
        components.production -= 5;
      }
      if (item.has_local_text) {
        components.production += 10;
        reasons.push('本文あり');
      }
      if (item.has_audio_archive) {
        components.production += 5;
        reasons.push(`音源あり ${item.audio_file_count || 0}件`);
      }

      const score = components.heuristic + components.production + components.emotional;
      const expectedTheme = inferBundleTheme([seed, item]);
      return {
        item,
        score,
        components,
        reasons,
        expected_theme: expectedTheme,
        priority: candidatePriority(score, item),
        review_reason: reasons[0] || `${expectedTheme} に近い相方候補`,
        shared_tags: tagOverlap,
        shared_keywords: keywordOverlap,
        shared_themes: themeOverlap,
        shared_characters: characterOverlap,
        shared_emotions: emotionOverlap,
      };
    }

    function currentSeedFilters() {
      return {
        excludeAdopted: Boolean(els.seedExcludeAdopted && els.seedExcludeAdopted.checked),
        excludeUnrecorded: Boolean(els.seedExcludeUnrecorded && els.seedExcludeUnrecorded.checked),
        excludeNoText: Boolean(els.seedExcludeNoText && els.seedExcludeNoText.checked),
        excludeExistingTheme: Boolean(els.seedExcludeExistingTheme && els.seedExcludeExistingTheme.checked),
      };
    }

    function selectedSeedItem() {
      return itemMap.get(seedTitle) || null;
    }

    function buildSeedCandidates() {
      const seed = selectedSeedItem();
      if (!seed) return [];
      const filters = currentSeedFilters();
      const adopted = adoptedTitlesSet();
      const adoptedThemes = adoptedThemeSet();
      return items
        .filter(item => item.title !== seed.title)
        .filter(item => !filters.excludeAdopted || (!adopted.has(item.title) && item.adoption_status !== '採用済み'))
        .filter(item => !filters.excludeUnrecorded || item.is_recorded)
        .filter(item => !filters.excludeNoText || item.has_local_text)
        .map(item => scoreSeedCandidate(seed, item))
        .filter(entry => entry.score > 0)
        .filter(entry => !filters.excludeExistingTheme || !adoptedThemes.has(entry.expected_theme))
        .sort((a, b) => {
          if (a.score !== b.score) return b.score - a.score;
          if (a.item.is_recorded !== b.item.is_recorded) return a.item.is_recorded ? -1 : 1;
          return String(a.item.title).localeCompare(String(b.item.title), 'ja');
        })
        .slice(0, 20);
    }

    function makeBundleId(seed, works, theme) {
      const slug = `${seed.title}-${theme}-${works.map(item => item.title).join('-')}`
        .toLowerCase()
        .replace(/[^一-龠ぁ-んァ-ヶA-Za-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
      return `seeded-${slug || 'bundle'}`;
    }

    function makeThumbnailText(theme, works, bundleSize) {
      const hooks = uniqueValues([
        theme,
        ...((((works[0] && works[0].tags) || []).slice(0, 1))),
        ...((((works[1] && works[1].tags) || []).slice(0, 1))),
      ]).slice(0, 2);
      return hooks.length >= 2 ? `${hooks[0]} × ${hooks[1]}` : `${theme} ${bundleSize}本企画`;
    }

    function combinationIndexes(length, choose) {
      const result = [];
      const stack = [];
      function walk(start) {
        if (stack.length === choose) {
          result.push([...stack]);
          return;
        }
        for (let index = start; index < length; index += 1) {
          stack.push(index);
          walk(index + 1);
          stack.pop();
        }
      }
      walk(0);
      return result;
    }

    function buildBundleTitle(seed, theme, bundleSize, tone) {
      const suffix = bundleSize === 5 ? '五作集' : '三作集';
      const accent = tone === 'emotion' ? '情の章' : '事件篇';
      const seedHook = seed.title.length <= 10 ? ` 核作品「${seed.title}」より` : '';
      return `銭形平次捕物控 総集編 ${theme} ${accent} ${suffix}${seedHook}`;
    }

    function buildOrderingSuggestion(works, tone) {
      const scored = works.map(work => {
        const profile = incidentProfile(itemMap.get(work.title) || work);
        return { work, profile };
      });
      const ordered = scored.sort((left, right) => {
        if (tone === 'emotion') {
          if (right.profile.emotion !== left.profile.emotion) return right.profile.emotion - left.profile.emotion;
          return right.profile.incident - left.profile.incident;
        }
        if (right.profile.incident !== left.profile.incident) return right.profile.incident - left.profile.incident;
        return right.profile.emotion - left.profile.emotion;
      }).map(entry => entry.work.title);
      return `${planToneLabel(tone)}で ${ordered.join(' → ')}`;
    }

    function buildSeedBundles() {
      const seed = selectedSeedItem();
      if (!seed) return [];
      const bundleSize = currentSeedPlanSize();
      const tone = currentSeedTone();
      const companionCount = bundleSize - 1;
      const candidates = buildSeedCandidates().slice(0, bundleSize === 5 ? 8 : 10);
      const bundles = [];
      combinationIndexes(candidates.length, companionCount).forEach(indexes => {
        const candidateEntries = indexes.map(index => candidates[index]);
        const companionWorks = candidateEntries.map(entry => entry.item);
        const works = [seed, ...companionWorks];
        const theme = inferBundleTheme(works);
        let similaritySum = 0;
        let similarityCount = 0;
        for (let left = 0; left < works.length; left += 1) {
          for (let right = left + 1; right < works.length; right += 1) {
            similaritySum += pairSimilarity(works[left], works[right]);
            similarityCount += 1;
          }
        }
        const overlapRate = similarityCount ? Math.round((similaritySum / similarityCount) * 100) : 0;
        const estimatedMinutes = works.reduce((sum, item) => sum + estimateWorkMinutes(item), 0);
        const needsRecordingTitles = works.filter(item => item.needs_recording).map(item => item.title);
        const incidentProfiles = works.map(item => incidentProfile(item));
        const toneScore = tone === 'emotion'
          ? incidentProfiles.reduce((sum, profile) => sum + profile.emotion, 0) * 4
          : incidentProfiles.reduce((sum, profile) => sum + profile.incident, 0) * 4;
        const heuristicScore = candidateEntries.reduce((sum, entry) => sum + Number((entry.components && entry.components.heuristic) || 0), 0) + overlapRate;
        const semanticScore = candidateEntries.reduce((sum, entry) => sum + Number((entry.components && entry.components.emotional) || 0), 0) + toneScore;
        const productionScore = candidateEntries.reduce((sum, entry) => sum + Number((entry.components && entry.components.production) || 0), 0) + (needsRecordingTitles.length === 0 ? 20 : 0) - (needsRecordingTitles.length * 12);
        const totalScore = heuristicScore + semanticScore + productionScore;
        const reasons = uniqueValues([
          ...candidateEntries.reduce((acc, entry) => acc.concat(entry.reasons || []), []),
          `${bundleSize}本の重なり率 ${overlapRate}%`,
          `${planToneLabel(tone)}のまとまり ${toneScore}`,
        ]).slice(0, 8);
        const orderingSuggestion = buildOrderingSuggestion(works.map(item => ({ title: item.title })), tone);
        const recommendedTitle = buildBundleTitle(seed, theme, bundleSize, tone);
        const bundleDraft = {
          bundle_id: makeBundleId(seed, companionWorks, theme),
          bundle_group: 'seeded',
          source_title: seed.title,
          theme,
          bundle_size: bundleSize,
          tone,
          ordering_suggestion: orderingSuggestion,
          recommended_title: recommendedTitle,
          thumbnail_text: makeThumbnailText(theme, works, bundleSize),
          summary: `${seed.title} を核に ${theme} で揃えた${bundleSize}本案`,
          review_prompt: '核作品との相性、並び順、YouTube総集編としての訴求力を確認してください。',
          estimated_minutes: estimatedMinutes,
          overlap_rate: overlapRate,
          needs_recording_titles: needsRecordingTitles,
          created_at: new Date().toLocaleString('ja-JP'),
          works: works.map(item => ({
              title: item.title,
              synopsis: item.synopsis || item.summary || '',
              themes: itemThemeValues(item),
              tags: itemTagValues(item),
              characters: itemCharacterValues(item),
              story_lineage: item.story_lineage,
              bookdata_path: item.bookdata_path || '',
              has_local_text: Boolean(item.has_local_text),
              is_recorded: Boolean(item.is_recorded),
            })),
          score: totalScore,
          reasons,
          score_breakdown: { heuristic: heuristicScore, semantic: semanticScore, production: productionScore, total: totalScore },
        };
        bundles.push({
          ...bundleDraft,
          publication_priority: publicationPriority(totalScore, needsRecordingTitles.length),
          review_reason: buildReviewReason(seed, bundleDraft, reasons),
          review_status: 'pending',
        });
      });
      return bundles
        .sort((a, b) => {
          if (a.needs_recording_titles.length !== b.needs_recording_titles.length) {
            return a.needs_recording_titles.length - b.needs_recording_titles.length;
          }
          if (a.score !== b.score) return b.score - a.score;
          return String(a.recommended_title).localeCompare(String(b.recommended_title), 'ja');
        })
        .slice(0, 10);
    }

    function renderSeedFocusCard(seed) {
      if (!seed) {
        return '<div class="gap-note">まだ核作品が選ばれていません。</div>';
      }
      const youtubeEntry = youtubeSeedMap().get(seed.title);
      const youtubeMetrics = youtubeEntry ? `
        <div class="seed-grid-meta">
          <div class="seed-meta-card"><strong>YouTube rank</strong>#${escapeHtml(youtubeEntry.rank || '-')}</div>
          <div class="seed-meta-card"><strong>seed score</strong>${escapeHtml(Math.round(Number(youtubeEntry.seed_score || 0)))}</div>
          <div class="seed-meta-card"><strong>CTR</strong>${escapeHtml(formatPercent(youtubeEntry.impression_ctr))}</div>
          <div class="seed-meta-card"><strong>7日impr</strong>${escapeHtml(formatNumber(youtubeEntry.last_7d_impressions))}</div>
        </div>
      ` : '';
      return `
        <div>
          <strong>${escapeHtml(seed.title)}</strong>
          <div class="subline">${escapeHtml(seed.publication_years || '年表未確認')} / ${escapeHtml(seed.story_lineage || '未分類')}</div>
        </div>
        <div class="badges">
          ${seed.is_recorded ? badge('朗読済み', 'good') : badge('要録音', 'warn')}
          ${seed.has_local_text ? badge('本文あり', 'good') : badge('本文なし', 'warn')}
          ${seed.has_bookdata ? badge('bookdata', 'good') : ''}
        </div>
        ${renderResourceStrip(seed)}
        ${youtubeMetrics}
        <div class="desc">${escapeHtml(seed.synopsis || seed.summary || '要約未設定')}</div>
      `;
    }

    function renderSeedCandidateCard(entry) {
      const item = entry.item;
      const breakdown = entry.components || {};
      const recommendation = ((entry.reasons && entry.reasons[0]) || entry.review_reason || 'テーマ近接');
      return `
        <article class="seed-candidate-card ${entry.priority === '高' ? 'good' : ''}">
          <div class="panel-head">
            <div>
              <h3>${escapeHtml(item.title)}</h3>
              <div class="subline">想定テーマ: ${escapeHtml(entry.expected_theme)} / 優先度 ${escapeHtml(entry.priority)}</div>
            </div>
            <div class="seed-score">${escapeHtml(entry.score)}</div>
          </div>
          <div class="score-breakdown">
            <div class="score-chip"><strong>Heuristic</strong>${escapeHtml(breakdown.heuristic || 0)}</div>
            <div class="score-chip"><strong>Production</strong>${escapeHtml(breakdown.production || 0)}</div>
            <div class="score-chip"><strong>Emotion</strong>${escapeHtml(breakdown.emotional || 0)}</div>
            <div class="score-chip"><strong>Total</strong>${escapeHtml(entry.score || 0)}</div>
          </div>
          ${renderResourceStrip(item)}
          <div class="seed-grid-meta">
            <div class="seed-meta-card"><strong>朗読</strong>${escapeHtml(item.is_recorded ? '済' : '未')}</div>
            <div class="seed-meta-card"><strong>本文</strong>${escapeHtml(item.has_local_text ? 'あり' : 'なし')}</div>
            <div class="seed-meta-card"><strong>要録音</strong>${escapeHtml(item.needs_recording ? 'あり' : 'なし')}</div>
            <div class="seed-meta-card"><strong>掲載</strong>${escapeHtml(item.magazines || '未確認')}</div>
          </div>
          <div class="evidence-grid">
            <article class="evidence-card">
              <strong>推薦理由</strong>
              <p>${escapeHtml(recommendation)}</p>
            </article>
            <article class="evidence-card">
              <strong>一致テーマ</strong>
              <p>${escapeHtml((entry.shared_themes || []).join(' / ') || entry.expected_theme || '未設定')}</p>
            </article>
            <article class="evidence-card">
              <strong>一致タグ</strong>
              <p>${escapeHtml((entry.shared_tags || []).join(' / ') || '該当なし')}</p>
            </article>
            <article class="evidence-card">
              <strong>制作メモ</strong>
              <p>${escapeHtml(item.has_local_text ? '本文ありで比較しやすい。' : '本文未所持のため要確認。')}${escapeHtml(item.needs_recording ? ' 録音前提。' : ' 朗読済み。')}</p>
            </article>
          </div>
          <div class="desc">${escapeHtml(item.synopsis || item.summary || '要約未設定')}</div>
          <div class="reason-pill-list">
            ${entry.reasons.slice(0, 6).map(reason => `<span class="reason-pill">${escapeHtml(reason)}</span>`).join('')}
          </div>
          <div class="inline-actions">
            <button class="button small" type="button" data-seed-title="${escapeHtml(item.title)}">この作品を核に切替</button>
          </div>
        </article>
      `;
    }

    function renderSeedBundleCard(bundle) {
      const works = bundle.works || [];
      const breakdown = bundle.score_breakdown || {};
      const resources = bundleResourceSummary(works);
      const themeEvidence = themeEvidenceForWorks(bundle.theme, works);
      return `
        <article class="seed-bundle-card">
          <div class="bundle-title-box">
            <h3>${escapeHtml(bundle.recommended_title)}</h3>
            <div class="subline">bundle_id: ${escapeHtml(bundle.bundle_id)} / テーマ: ${escapeHtml(bundle.theme)} / ${escapeHtml(bundle.bundle_size)}本 / ${escapeHtml(planToneLabel(bundle.tone))}</div>
          </div>
          <div class="thumbnail-copy">${escapeHtml(bundle.thumbnail_text || bundle.theme)}</div>
          <div class="score-breakdown">
            <div class="score-chip"><strong>Heuristic</strong>${escapeHtml(Math.round(breakdown.heuristic || 0))}</div>
            <div class="score-chip"><strong>Semantic</strong>${escapeHtml(Math.round(breakdown.semantic || 0))}</div>
            <div class="score-chip"><strong>Production</strong>${escapeHtml(Math.round(breakdown.production || 0))}</div>
            <div class="score-chip"><strong>Total</strong>${escapeHtml(Math.round(breakdown.total || bundle.score || 0))}</div>
          </div>
          <div class="resource-strip">
            <span class="resource-pill"><strong>朗読済み</strong>${escapeHtml(resources.recorded)} / ${escapeHtml(resources.total)}</span>
            <span class="resource-pill"><strong>本文</strong>${escapeHtml(resources.localText)} / ${escapeHtml(resources.total)}</span>
            <span class="resource-pill"><strong>bookdata</strong>${escapeHtml(resources.bookdata)} / ${escapeHtml(resources.total)}</span>
            <span class="resource-pill"><strong>青空</strong>${escapeHtml(resources.aozoraReady)} / ${escapeHtml(resources.total)}</span>
          </div>
          <div class="seed-grid-meta">
            <div class="seed-meta-card"><strong>想定尺</strong>${escapeHtml(bundle.estimated_minutes)}分</div>
            <div class="seed-meta-card"><strong>重複率</strong>${escapeHtml(bundle.overlap_rate)}%</div>
            <div class="seed-meta-card"><strong>要録音</strong>${escapeHtml(bundle.needs_recording_titles.length ? 'あり' : 'なし')}</div>
            <div class="seed-meta-card"><strong>優先度</strong>${escapeHtml(bundle.publication_priority || 'medium')}</div>
          </div>
          <div class="evidence-grid">
            <article class="evidence-card">
              <strong>総集編タイトル案</strong>
              <p>${escapeHtml(bundle.recommended_title || '未設定')}</p>
            </article>
            <article class="evidence-card">
              <strong>推薦理由</strong>
              <p>${escapeHtml(bundle.review_reason || bundle.summary || '')}</p>
            </article>
            <article class="evidence-card">
              <strong>テーマ根拠</strong>
              <p>${themeEvidence ? escapeHtml(`一致率平均 ${themeEvidence.average}% / ${themeEvidence.reasons.join(' / ') || '一致理由あり'}`) : 'テーマ一致率データはまだありません。'}</p>
            </article>
            <article class="evidence-card">
              <strong>制作メモ</strong>
              <p>${escapeHtml(bundle.review_prompt || '未設定')}</p>
            </article>
          </div>
          <div class="ordering-box">並び順提案: ${escapeHtml(bundle.ordering_suggestion || '未設定')}</div>
          <div class="work-evidence-list">
            ${works.map(work => renderWorkEvidenceItem(work)).join('')}
          </div>
          <div class="reason-pill-list">
            ${(bundle.reasons || []).map(reason => `<span class="reason-pill">${escapeHtml(reason)}</span>`).join('')}
          </div>
          <div class="inline-actions">
            <button class="button primary small" type="button" data-queue-add="${escapeHtml(bundle.bundle_id)}">review queue に送る</button>
            <button class="button small" type="button" data-copy-bundle-id="${escapeHtml(bundle.bundle_id)}">bundle_id をコピー</button>
          </div>
        </article>
      `;
    }

    function renderReviewQueue() {
      const bundles = (reviewQueueState.bundles || []).slice();
      els.reviewQueueSummary.textContent = bundles.length
        ? `review queue ${bundles.length}件 / JSON を保存して ${escapeHtml('__BUNDLE_REVIEW_QUEUE_FILE__')} に戻せます。`
        : 'まだ bundle は入っていません。';
      syncReviewQueueEditor();
      els.reviewQueueList.innerHTML = bundles.length
        ? bundles.map(bundle => `
            <article class="queue-card">
              <div>
                <h4>${escapeHtml(bundle.recommended_title || bundle.bundle_id)}</h4>
                <div class="subline">核作品: ${escapeHtml(bundle.source_title || '未設定')} / ${escapeHtml(bundle.bundle_id)}</div>
              </div>
              <div class="gap-note">優先度: ${escapeHtml(bundle.publication_priority || 'medium')} / 状態: ${escapeHtml(bundle.review_status || 'pending')}</div>
              <div class="gap-note">審査理由: ${escapeHtml(bundle.review_reason || bundle.summary || '')}</div>
              <div class="gap-note">${escapeHtml((bundle.works || []).map(work => work.title).join(' / '))}</div>
              <div class="queue-editor">
                <label>
                  <span>総集編タイトル案</span>
                  <input type="text" value="${escapeHtml(bundle.recommended_title || '')}" data-queue-edit="recommended_title" data-queue-id="${escapeHtml(bundle.bundle_id)}" />
                </label>
                <label>
                  <span>審査理由・メモ</span>
                  <textarea data-queue-edit="review_reason" data-queue-id="${escapeHtml(bundle.bundle_id)}">${escapeHtml(bundle.review_reason || bundle.summary || '')}</textarea>
                </label>
                <label>
                  <span>優先度</span>
                  <select data-queue-edit="publication_priority" data-queue-id="${escapeHtml(bundle.bundle_id)}">
                    <option value="high" ${bundle.publication_priority === 'high' ? 'selected' : ''}>high</option>
                    <option value="medium" ${(bundle.publication_priority || 'medium') === 'medium' ? 'selected' : ''}>medium</option>
                    <option value="low" ${bundle.publication_priority === 'low' ? 'selected' : ''}>low</option>
                  </select>
                </label>
                <label>
                  <span>審査状態</span>
                  <select data-queue-edit="review_status" data-queue-id="${escapeHtml(bundle.bundle_id)}">
                    <option value="pending" ${(bundle.review_status || 'pending') === 'pending' ? 'selected' : ''}>pending</option>
                    <option value="hold" ${bundle.review_status === 'hold' ? 'selected' : ''}>hold</option>
                    <option value="rejected" ${bundle.review_status === 'rejected' ? 'selected' : ''}>rejected</option>
                    <option value="adopted" ${bundle.review_status === 'adopted' ? 'selected' : ''}>adopted</option>
                  </select>
                </label>
              </div>
              <div class="inline-actions">
                <button class="button small" type="button" data-queue-status="adopted" data-queue-id="${escapeHtml(bundle.bundle_id)}">採用</button>
                <button class="button small" type="button" data-queue-status="hold" data-queue-id="${escapeHtml(bundle.bundle_id)}">保留</button>
                <button class="button small" type="button" data-queue-status="rejected" data-queue-id="${escapeHtml(bundle.bundle_id)}">却下</button>
                <button class="button small" type="button" data-copy-bundle-id="${escapeHtml(bundle.bundle_id)}">bundle_id をコピー</button>
                <button class="button small" type="button" data-queue-remove="${escapeHtml(bundle.bundle_id)}">queue から外す</button>
              </div>
            </article>
          `).join('')
        : '<div class="gap-note">review queue は空です。</div>';
    }

    function addBundleToReviewQueue(bundle) {
      const next = (reviewQueueState.bundles || [])
        .filter(entry => entry.bundle_id !== bundle.bundle_id);
      next.unshift(bundle);
      reviewQueueState = { bundles: next };
      saveReviewQueueState();
      renderReviewQueue();
    }

    function removeBundleFromReviewQueue(bundleId) {
      reviewQueueState = {
        bundles: (reviewQueueState.bundles || [])
          .filter(entry => entry.bundle_id !== bundleId),
      };
      saveReviewQueueState();
      renderReviewQueue();
    }

    function syncAdoptedEntryFromQueueBundle(bundle) {
      if (!bundle) return;
      let changed = false;
      compilationState = {
        adopted_candidates: (compilationState.adopted_candidates || []).map(entry => {
          if (entry.candidate_id !== bundle.bundle_id) return entry;
          changed = true;
          return {
            ...entry,
            title: String(bundle.recommended_title || entry.title || '').trim(),
            theme: String(bundle.theme || entry.theme || '').trim(),
            needs_recording_titles: Array.isArray(bundle.needs_recording_titles)
              ? bundle.needs_recording_titles.map(title => String(title || '').trim()).filter(Boolean)
              : entry.needs_recording_titles,
          };
        }),
      };
      if (changed) {
        saveCompilationState();
        renderCompilation();
      }
    }

    function updateBundleReviewStatus(bundleId, nextStatus) {
      reviewQueueState = {
        bundles: (reviewQueueState.bundles || []).map(entry => (
          entry.bundle_id === bundleId
            ? { ...entry, review_status: nextStatus }
            : entry
        )),
      };
      saveReviewQueueState();
      const bundle = (reviewQueueState.bundles || []).find(entry => entry.bundle_id === bundleId);
      syncAdoptedEntryFromQueueBundle(bundle);
      renderReviewQueue();
    }

    function updateQueueBundleField(bundleId, field, value) {
      reviewQueueState = {
        bundles: (reviewQueueState.bundles || []).map(entry => (
          entry.bundle_id === bundleId
            ? { ...entry, [field]: String(value || '').trim() }
            : entry
        )),
      };
      saveReviewQueueState();
      const bundle = (reviewQueueState.bundles || []).find(entry => entry.bundle_id === bundleId);
      syncAdoptedEntryFromQueueBundle(bundle);
      syncReviewQueueEditor();
    }

    function adoptQueueBundle(bundleId) {
      const bundle = (reviewQueueState.bundles || [])
        .find(entry => entry.bundle_id === bundleId);
      if (!bundle) return;
      if (!compilationState.adopted_candidates.some(entry => entry.candidate_id === bundleId)) {
        compilationState.adopted_candidates.push({
          candidate_id: bundle.bundle_id,
          theme: bundle.theme,
          title: bundle.recommended_title,
          work_titles: (bundle.works || []).map(work => work.title),
          needs_recording_titles: bundle.needs_recording_titles || [],
          adopted_at: new Date().toLocaleString('ja-JP'),
        });
        saveCompilationState();
        renderCompilation();
        renderSeedExplorer();
        render();
      }
      updateBundleReviewStatus(bundleId, 'adopted');
    }

    function syncReviewQueueEditor() {
      if (!els.reviewQueueEditor) return;
      els.reviewQueueEditor.value = JSON.stringify(reviewQueueState, null, 2);
    }

    async function exportReviewQueue() {
      const text = JSON.stringify(reviewQueueState, null, 2);
      syncReviewQueueEditor();
      try {
        await navigator.clipboard.writeText(text);
        els.reviewQueueSummary.textContent = 'review queue JSON をクリップボードにコピーしました';
      } catch (_error) {
        window.prompt('コピーできないため、ここから保存してください', text);
      }
    }

    function importReviewQueueFromEditor() {
      if (!els.reviewQueueEditor) return;
      const raw = String(els.reviewQueueEditor.value || '').trim();
      if (!raw) {
        els.reviewQueueSummary.textContent = 'review queue JSON が空です';
        return;
      }
      try {
        const parsed = JSON.parse(raw);
        reviewQueueState = normalizeReviewQueueState(parsed);
        saveReviewQueueState();
        renderReviewQueue();
        renderPlannerPulse();
        els.reviewQueueSummary.textContent = `review queue を ${reviewQueueState.bundles.length}件 取り込みました`;
      } catch (error) {
        window.alert(`review queue JSON を読めませんでした: ${error.message}`);
      }
    }

    function renderSeedExplorer() {
      renderYoutubeSeedPanel();
      const seed = selectedSeedItem();
      els.seedFocusCard.innerHTML = renderSeedFocusCard(seed);
      if (!seed) {
        els.seedSelectionSummary.textContent = '作品カードの「この作品から候補を探す」から開始します。';
        els.seedCandidateSummary.textContent = '核作品を選ぶと、相方候補を上位20件まで表示します。';
        els.seedBundleSummary.textContent = '核作品を中心に、3本または5本の総集編企画案を作ります。';
        els.seedCandidateList.innerHTML = '<div class="empty">まず核作品を1本選んでください。</div>';
        els.seedBundleList.innerHTML = '<div class="empty">核作品を選ぶと bundle 案を表示します。</div>';
        renderReviewQueue();
        return;
      }
      if (adoptedTitlesSet().has(seed.title) && currentSeedFilters().excludeAdopted) {
        els.seedSelectionSummary.textContent = `${seed.title} は採用済み総集編に含まれているため、除外設定では候補生成しません。`;
        els.seedCandidateList.innerHTML = '<div class="empty">採用済み除外を外すか、別の核作品を選んでください。</div>';
        els.seedBundleList.innerHTML = '<div class="empty">bundle 案を作るには未採用の核作品が必要です。</div>';
        renderReviewQueue();
        return;
      }
      const candidates = buildSeedCandidates();
      const bundles = buildSeedBundles();
      const youtubeEntry = youtubeSeedMap().get(seed.title);
      const youtubeNote = youtubeEntry
        ? ` YouTube成績は rank ${youtubeEntry.rank} / score ${Math.round(Number(youtubeEntry.seed_score || 0))} / CTR ${formatPercent(youtubeEntry.impression_ctr)} / 直近7日impr ${formatNumber(youtubeEntry.last_7d_impressions)}。`
        : '';
      els.seedSelectionSummary.textContent = `${seed.title} を核に、空気感と制作しやすさの両方で候補を並べています。${youtubeNote}`;
      els.seedCandidateSummary.textContent = `候補 ${candidates.length}件 / 上位20件まで表示`;
      els.seedBundleSummary.textContent = `${currentSeedPlanSize()}本案 ${bundles.length}件 / ${planToneLabel(currentSeedTone())} / 上位10件まで表示`;
      els.seedCandidateList.innerHTML = candidates.length
        ? candidates.map(renderSeedCandidateCard).join('')
        : '<div class="empty">条件に合う相方候補がありません。除外条件をゆるめてください。</div>';
      els.seedBundleList.innerHTML = bundles.length
        ? bundles.map(renderSeedBundleCard).join('')
        : '<div class="empty">総集編企画案を組めませんでした。候補条件を見直してください。</div>';
      renderReviewQueue();
      renderPlannerPulse();
    }

    function selectSeedWork(title) {
      const item = itemMap.get(String(title || ''));
      if (!item) return;
      seedTitle = item.title;
      activeMode = 'seed';
      syncModeButtons();
      syncModePanels();
      renderSeedExplorer();
    }

    function currentTheme() {
      return els.themeSelect ? String(els.themeSelect.value || '') : '';
    }

    function buildThemeRecommendations() {
      const theme = currentTheme();
      if (!theme || !themeScoreMap.has(theme)) return [];
      const adopted = adoptedTitlesSet();
      const recordedOnly = els.themeRecordedOnly.checked;
      const scores = [...themeScoreMap.get(theme).values()]
        .filter(score => !adopted.has(String(score.title || '')))
        .sort((a, b) => {
          if (a.score_percent !== b.score_percent) {
            return b.score_percent - a.score_percent;
          }
          return String(a.title).localeCompare(String(b.title), 'ja');
        });

      return scores
        .map(score => ({ score, item: itemMap.get(String(score.title || '')) }))
        .filter(entry => entry.item)
        .filter(entry => entry.item.adoption_status !== '採用済み')
        .filter(entry => !recordedOnly || entry.item.is_recorded)
        .slice(0, 3);
    }

    function renderThemeCard(entry) {
      const item = entry.item;
      const score = entry.score;
      const reasons = Array.isArray(score.reason_hits) ? score.reason_hits : [];
      const reasonList = reasons.length
        ? `<ul class="reason-list">${reasons.slice(0, 5).map(reason => `<li>${escapeHtml(reason)}</li>`).join('')}</ul>`
        : '<div class="comp-note">一致理由はまだありません。</div>';
      return `
        <article class="theme-card">
          <div>
            <h3>${escapeHtml(item.title)}</h3>
            <div class="subline">一致率 ${escapeHtml(score.score_percent)}% / ${escapeHtml(item.recording_status || '')}</div>
          </div>
          <div class="badges">
            ${badge(`${currentTheme()} ${score.score_percent}%`, 'good')}
            ${item.needs_recording ? badge('未朗読・要録音', 'warn') : badge('朗読済み', 'good')}
            ${item.has_local_text ? badge('本文あり', 'good') : ''}
          </div>
          <p class="desc">${escapeHtml(item.synopsis || item.summary || '要約未設定')}</p>
          ${reasonList}
        </article>
      `;
    }

    function renderThemeMatch() {
      const theme = currentTheme();
      if (!theme) {
        els.themeSummary.textContent = 'テーマを選ぶと一致率上位3本と一致理由を表示します。';
        els.themeList.innerHTML = '<div class="empty">テーマを選択してください。</div>';
        return;
      }

      const recommendations = buildThemeRecommendations();
      const adopted = adoptedTitlesSet();
      els.themeSummary.textContent = `${theme} / 上位${recommendations.length}本 / 採用済み除外 ${adopted.size}本`;

      if (!recommendations.length) {
        els.themeList.innerHTML = '<div class="empty">このテーマで表示できる候補がありません。採用済み除外や朗読済み限定を見直してください。</div>';
        return;
      }

      els.themeList.innerHTML = recommendations.map(renderThemeCard).join('');
    }

    function renderCompilationCard(candidate) {
      const resources = bundleResourceSummary(candidate.works || []);
      const themeEvidence = themeEvidenceForWorks(candidate.theme, candidate.works || []);
      const worksHtml = candidate.works.map(item => `
        <li>
          <div class="work-line">
            <strong>${escapeHtml(item.title)}</strong>
            ${item.needs_recording ? badge('未朗読・要録音', 'warn') : badge('朗読済み', 'good')}
            ${item.has_bookdata ? badge('bookdata', 'good') : ''}
            ${item.has_local_text ? badge('本文あり', 'good') : ''}
          </div>
          <div class="gap-note">${escapeHtml(item.synopsis || item.summary || '要約未設定')}</div>
        </li>
      `).join('');

      const recordingLine = candidate.needs_recording_titles.length
        ? `要録音: ${escapeHtml(candidate.needs_recording_titles.join(' / '))}`
        : '要録音: なし（3本とも朗読済み）';

      return `
        <article class="comp-card">
          <div>
            <h3>${escapeHtml(candidate.title)}</h3>
            <div class="subline">テーマ: ${escapeHtml(candidate.theme)} / ${escapeHtml(candidate.description)}</div>
          </div>
          <div class="badges">
            ${candidate.ready ? badge('今すぐ総集編化しやすい', 'good') : badge('要録音あり', 'warn')}
            ${badge(`残り候補${candidate.remaining_pool}本`)}
          </div>
          <div class="resource-strip">
            <span class="resource-pill"><strong>朗読済み</strong>${escapeHtml(resources.recorded)} / ${escapeHtml(resources.total)}</span>
            <span class="resource-pill"><strong>本文</strong>${escapeHtml(resources.localText)} / ${escapeHtml(resources.total)}</span>
            <span class="resource-pill"><strong>bookdata</strong>${escapeHtml(resources.bookdata)} / ${escapeHtml(resources.total)}</span>
            <span class="resource-pill"><strong>青空</strong>${escapeHtml(resources.aozoraReady)} / ${escapeHtml(resources.total)}</span>
          </div>
          <div class="evidence-grid">
            <article class="evidence-card">
              <strong>企画メモ</strong>
              <p>${escapeHtml(candidate.description)}</p>
            </article>
            <article class="evidence-card">
              <strong>テーマ根拠</strong>
              <p>${themeEvidence ? escapeHtml(`一致率平均 ${themeEvidence.average}% / ${themeEvidence.reasons.join(' / ') || '一致理由あり'}`) : 'テーマ一致率データはまだありません。'}</p>
            </article>
            <article class="evidence-card">
              <strong>録音メモ</strong>
              <p>${escapeHtml(recordingLine)}</p>
            </article>
          </div>
          <ol class="work-list">${worksHtml}</ol>
          <button class="button primary" type="button" data-adopt="${escapeHtml(candidate.candidate_id)}">この3本を採用</button>
        </article>
      `;
    }

    function renderAdoptedCard(entry) {
      const recordingLine = entry.needs_recording_titles.length
        ? `要録音: ${escapeHtml(entry.needs_recording_titles.join(' / '))}`
        : '要録音: なし';
      return `
        <article class="adopted-card">
          <div>
            <h3>${escapeHtml(entry.title || '採用済み総集編')}</h3>
            <div class="subline">テーマ: ${escapeHtml(entry.theme || '未設定')} / 採用日時: ${escapeHtml(entry.adopted_at || '不明')}</div>
          </div>
          <div class="comp-note">作品: ${escapeHtml(entry.work_titles.join(' / '))}</div>
          <div class="comp-note">${recordingLine}</div>
          <div class="queue-editor">
            <label>
              <span>採用済みタイトル</span>
              <input type="text" value="${escapeHtml(entry.title || '')}" data-adopted-edit="title" data-adopted-id="${escapeHtml(entry.candidate_id)}" />
            </label>
            <label>
              <span>採用済みテーマ</span>
              <input type="text" value="${escapeHtml(entry.theme || '')}" data-adopted-edit="theme" data-adopted-id="${escapeHtml(entry.candidate_id)}" />
            </label>
            <label>
              <span>メモ</span>
              <textarea data-adopted-edit="note" data-adopted-id="${escapeHtml(entry.candidate_id)}">${escapeHtml(entry.note || '')}</textarea>
            </label>
          </div>
          <button class="button" type="button" data-unadopt="${escapeHtml(entry.candidate_id)}">採用を取り消す</button>
        </article>
      `;
    }

    function renderCompilation() {
      const candidates = buildCompilationCandidates();
      const adoptedEntries = compilationState.adopted_candidates;
      const adoptedCount = adoptedTitlesSet().size;
      const ready = candidates.filter(item => item.ready);
      const oneRecordingAway = candidates.filter(item => item.needs_recording_titles.length === 1);
      const followups = candidates.filter(item => adoptedEntries.some(entry => entry.theme === item.theme));

      renderThemeMatch();

      els.compSummary.textContent = `候補${candidates.length}件 / 採用済み${adoptedEntries.length}件 / 除外済み作品${adoptedCount}本`;
      els.adoptedSummary.textContent = adoptedEntries.length
        ? '採用済みの3本セット。ここに含まれる作品は候補一覧から除外されています。'
        : 'まだ採用済みの総集編はありません。';
      els.compHighlights.innerHTML = [
        {
          title: '今日のおすすめ候補',
          body: candidates.slice(0, 3).map(item => item.title).join(' / ') || '候補がありません。'
        },
        {
          title: '今すぐ作れる候補',
          body: ready.slice(0, 3).map(item => item.title).join(' / ') || 'まだありません。'
        },
        {
          title: '要録音1本で作れる候補',
          body: oneRecordingAway.slice(0, 3).map(item => item.title).join(' / ') || 'まだありません。'
        },
        {
          title: '採用済みの続編候補',
          body: followups.slice(0, 3).map(item => item.title).join(' / ') || '続き候補はまだありません。'
        },
      ].map(block => `
        <article class="highlight-card">
          <h3>${escapeHtml(block.title)}</h3>
          <p>${escapeHtml(block.body)}</p>
        </article>
      `).join('');

      els.compList.innerHTML = candidates.length
        ? candidates.map(renderCompilationCard).join('')
        : '<div class=\"empty\">残っている作品では新しい3本候補がありません。採用状態を見直すか、条件をゆるめてください。</div>';

      els.adoptedList.innerHTML = adoptedEntries.length
        ? adoptedEntries.map(renderAdoptedCard).join('')
        : '<div class=\"empty\">採用済み総集編はまだありません。</div>';
      renderPlannerPulse();
    }

    function adoptCandidate(candidateId) {
      const candidate = buildCompilationCandidates().find(item => item.candidate_id === candidateId);
      if (!candidate) return;
      if (compilationState.adopted_candidates.some(entry => entry.candidate_id === candidateId)) return;
      compilationState.adopted_candidates.push({
        candidate_id: candidate.candidate_id,
        theme: candidate.theme,
        title: candidate.title,
        work_titles: candidate.works.map(item => item.title),
        needs_recording_titles: candidate.needs_recording_titles,
        adopted_at: new Date().toLocaleString('ja-JP'),
      });
      saveCompilationState();
      renderCompilation();
      renderSeedExplorer();
      render();
    }

    function unadoptCandidate(candidateId) {
      compilationState.adopted_candidates = compilationState.adopted_candidates
        .filter(entry => entry.candidate_id !== candidateId);
      saveCompilationState();
      renderCompilation();
      renderSeedExplorer();
      render();
    }

    function updateAdoptedField(candidateId, field, value) {
      compilationState = {
        adopted_candidates: (compilationState.adopted_candidates || []).map(entry => (
          entry.candidate_id === candidateId
            ? { ...entry, [field]: String(value || '').trim() }
            : entry
        )),
      };
      saveCompilationState();
      renderCompilation();
    }

    async function exportState() {
      const text = JSON.stringify(compilationState, null, 2);
      try {
        await navigator.clipboard.writeText(text);
        els.compSummary.textContent = `${els.compSummary.textContent} / JSONをクリップボードにコピーしました`;
      } catch (_error) {
        window.prompt('コピーできないため、ここから保存してください', text);
      }
    }

    async function exportRecordingState() {
      const text = JSON.stringify(recordingState, null, 2);
      try {
        await navigator.clipboard.writeText(text);
        els.needsRecordingPanelSummary.textContent = '録音状態JSONをクリップボードにコピーしました';
      } catch (_error) {
        window.prompt('コピーできないため、ここから保存してください', text);
      }
    }

    function renderNeedsRecordingEntry(item) {
      const meta = [item.publication_years, item.magazines, item.story_lineage]
        .filter(Boolean)
        .join(' / ');
      return `
        <li>
          <div><strong>${escapeHtml(item.title)}</strong>${meta ? ` / ${escapeHtml(meta)}` : ''}</div>
          <div class="gap-note">${escapeHtml(item.recording_status)} / ${escapeHtml(item.recording_note)}</div>
          <div class="inline-actions">
            <button class="button primary small" type="button" data-recording-mark="${escapeHtml(item.title)}" data-recording-value="true">録音済みにする</button>
            ${item.recording_source === 'manual' ? `<button class="button small" type="button" data-recording-clear="${escapeHtml(item.title)}">手動更新を解除</button>` : ''}
          </div>
        </li>
      `;
    }

    function renderRecordingOverrideEntry(entry) {
      const item = itemMap.get(entry.title);
      if (!item) return '';
      return `
        <li>
          <div><strong>${escapeHtml(item.title)}</strong> / ${escapeHtml(item.recording_status)}</div>
          <div class="gap-note">${escapeHtml(entry.updated_at || '更新日時なし')} / ${escapeHtml(entry.note || 'メモなし')}</div>
          <div class="inline-actions">
            <button class="button small" type="button" data-recording-mark="${escapeHtml(item.title)}" data-recording-value="${item.is_recorded ? 'false' : 'true'}">${item.is_recorded ? '未朗読に戻す' : '朗読済みにする'}</button>
            <button class="button small" type="button" data-recording-clear="${escapeHtml(item.title)}">手動更新を解除</button>
          </div>
        </li>
      `;
    }

    function renderRecordingPanel() {
      const needs = [...items]
        .filter(item => item.needs_recording)
        .sort((a, b) => (a.year_sort - b.year_sort) || String(a.title).localeCompare(String(b.title), 'ja'));
      const overrides = [...(recordingState.recording_overrides || [])]
        .sort((a, b) => String(a.title).localeCompare(String(b.title), 'ja'));

      els.needsRecordingPanelSummary.textContent = `要録音 ${needs.length}本 / 手動更新 ${overrides.length}本`;
      els.needsRecordingSummary.textContent = needs.length
        ? '録音済みに変更すると、この一覧から外れます。'
        : '要録音作品はありません。';
      els.recordingOverrideSummary.textContent = overrides.length
        ? '手動で変更した録音状態です。必要なら元に戻せます。'
        : '手動更新はまだありません。';

      els.needsRecordingList.innerHTML = needs.length
        ? needs.map(renderNeedsRecordingEntry).join('')
        : '<li class="gap-note">要録音作品はありません。</li>';
      els.recordingOverrideList.innerHTML = overrides.length
        ? overrides.map(renderRecordingOverrideEntry).join('')
        : '<li class="gap-note">手動更新はありません。</li>';
      renderPlannerPulse();
    }

    function renderCard(item, adopted) {
      const activeTheme = currentTheme();
      const themeScore = activeTheme && themeScoreMap.has(activeTheme)
        ? themeScoreMap.get(activeTheme).get(item.title)
        : null;
      const badges = [
        badge(item.story_lineage),
        item.publication_years ? badge(item.publication_years, 'good') : '',
        badge(item.adoption_status || '未採用', item.adoption_status === '採用済み' ? 'good' : item.adoption_status === '旧実績のみ' ? '' : 'warn'),
        adopted.has(item.title) ? badge('採用済み総集編に含む', 'warn') : '',
        themeScore ? badge(`${activeTheme}一致${themeScore.score_percent}%`, themeScore.score_percent >= 60 ? 'good' : '') : '',
        item.has_local_text ? badge('本文あり', 'good') : '',
        item.has_bookdata ? badge('bookdata', 'good') : '',
        item.has_channel_entry ? badge('チャンネル掲載', 'good') : '',
        item.has_audio_archive ? badge(`音源${item.audio_file_count}件`, 'good') : '',
        item.rerecorded_latest_only ? badge('再録整理済み', 'good') : '',
        item.aozora_status ? badge(aozoraStatusLabel(item), item.aozora_status === 'resolved' ? 'good' : '') : '',
      ].filter(Boolean).join('');

      const synopsis = item.synopsis || item.summary || '要約未設定';
      const detailTags = [];
      detailTags.push(`<div><span class=\"detail-label\">採用状況</span>${escapeHtml(item.adoption_status || '未採用')} / ${escapeHtml(item.adoption_note || '')}</div>`);
      detailTags.push(`<div><span class=\"detail-label\">録音状態</span>${escapeHtml(item.recording_status)} / ${escapeHtml(item.recording_note)}</div>`);
      if (item.magazines) detailTags.push(`<div><span class=\"detail-label\">掲載誌</span>${escapeHtml(item.magazines)}</div>`);
      if (item.theme_secondary && item.theme_secondary.length) detailTags.push(`<div><span class=\"detail-label\">副系統</span>${miniChips(item.theme_secondary, 10)}</div>`);
      if (item.tags && item.tags.length) detailTags.push(`<div><span class=\"detail-label\">タグ</span>${miniChips(item.tags, 12)}</div>`);
      if (item.characters && item.characters.length) detailTags.push(`<div><span class=\"detail-label\">登場人物</span>${miniChips(item.characters, 12)}</div>`);
      if (themeScore && Array.isArray(themeScore.reasons) && themeScore.reasons.length) detailTags.push(`<div><span class=\"detail-label\">${escapeHtml(activeTheme)}一致理由</span>${escapeHtml(themeScore.reasons.slice(0, 4).join(' / '))}</div>`);
      if (item.aozora_notes) detailTags.push(`<div><span class="detail-label">青空状況</span>${escapeHtml(aozoraStatusLabel(item))} / ${escapeHtml(item.aozora_notes)}</div>`);
      if (item.audio_recording_years && item.audio_recording_years.length) detailTags.push(`<div><span class="detail-label">朗読年度</span>${escapeHtml(item.audio_recording_years.join('→'))}</div>`);
      if (item.audio_archive_dirs && item.audio_archive_dirs.length) detailTags.push(`<div><span class="detail-label">音声フォルダ</span>${renderPathLinkActions(item.audio_archive_dirs, item.audio_archive_dir_uris, 4)}</div>`);
      if (item.source_paths && item.source_paths.length) detailTags.push(`<div><span class="detail-label">出典</span>${escapeHtml(item.source_paths.slice(0, 6).join(' / '))}</div>`);
      if (item.rerecorded_latest_only) detailTags.push(`<div><span class="detail-label">再録整理</span>${escapeHtml((item.rerecorded_selection_reason || '最新版を採用') + (item.rerecorded_years_seen && item.rerecorded_years_seen.length ? ` / 対象年 ${item.rerecorded_years_seen.join('→')}` : ''))}</div>`);
      if (item.latest_video_id || item.latest_published_year || item.latest_views_per_day) detailTags.push(`<div><span class="detail-label">採用版</span>${escapeHtml([item.latest_published_year || '', item.latest_video_id || '', item.latest_views_per_day ? `views/day ${item.latest_views_per_day}` : ''].filter(Boolean).join(' / '))}</div>`);
      if (item.channel_titles && item.channel_titles.length) detailTags.push(`<div><span class="detail-label">関連動画題名</span>${escapeHtml(item.channel_titles.slice(0, 3).join(' / '))}</div>`);

      return `
        <article class=\"card\">
          <div>
            <h2>${escapeHtml(item.title)}</h2>
            <div class=\"subline\">${escapeHtml(item.publication_years || '年表未確認')}${item.magazines ? ' / ' + escapeHtml(item.magazines) : ''}</div>
          </div>
          <div class=\"badges\">${badges}</div>
          ${renderResourceStrip(item)}
          <div class=\"chips-mini\">${miniChips(item.tags, 8)}</div>
          <p class=\"desc\">${escapeHtml(synopsis)}</p>
          ${renderBookdataActions(item)}
          ${renderTextPreview(item)}
          <details>
            <summary>詳細</summary>
            <div class=\"detail-block\">${detailTags.join('')}</div>
          </details>
        </article>
      `;
    }

    function renderWorkRow(item, adopted) {
      const activeTheme = currentTheme();
      const themeScore = activeTheme && themeScoreMap.has(activeTheme)
        ? themeScoreMap.get(activeTheme).get(item.title)
        : null;
      const tagChips = [
        `<span class=\"chip-mini\">${escapeHtml(item.story_lineage)}</span>`,
        ...(item.tags || []).slice(0, 5).map(
          tag => `<span class=\"chip-mini\">${escapeHtml(tag)}</span>`
        ),
      ].join('');
      const statusBadges = [
        badge(item.adoption_status || '未採用', item.adoption_status === '採用済み' ? 'good' : item.adoption_status === '旧実績のみ' ? '' : 'warn'),
        adopted.has(item.title) ? badge('採用済み', 'warn') : '',
        item.has_local_text ? badge('本文あり', 'good') : '',
        item.has_bookdata ? badge('bookdata', 'good') : '',
        item.has_audio_archive ? badge(`音源${item.audio_file_count}件`, 'good') : '',
        themeScore ? badge(`${activeTheme}${themeScore.score_percent}%`, themeScore.score_percent >= 60 ? 'good' : '') : '',
      ].filter(Boolean).join('');

      return `
        <tr>
          <td class=\"work-title-cell\">
            <div class=\"work-title-main\">${escapeHtml(item.title)}</div>
            <div class=\"work-title-sub\">${escapeHtml(item.publication_years || '年表未確認')}</div>
          </td>
          <td>${escapeHtml(item.magazines || '掲載誌未確認')}</td>
          <td>${statusBadges}</td>
          <td><div class=\"work-tags\">${tagChips}</div></td>
          <td>${escapeHtml((item.characters || []).slice(0, 5).join(' / ') || '登場人物情報なし')}</td>
          <td class="work-synopsis">${escapeHtml(item.synopsis || item.summary || '要約未設定')}${renderBookdataActions(item)}${renderTextPreview(item)}</td>
        </tr>
      `;
    }

    function renderWorkTable(filtered, adopted) {
      return `
        <div class=\"work-table-wrap\">
          <table class=\"work-table\">
            <thead>
              <tr>
                <th>作品</th>
                <th>掲載誌・年代</th>
                <th>状態</th>
                <th>系統・タグ</th>
                <th>登場人物</th>
                <th>あらすじ</th>
              </tr>
            </thead>
            <tbody>
              ${filtered.map(item => renderWorkRow(item, adopted)).join('')}
            </tbody>
          </table>
        </div>
      `;
    }

    function renderSimpleRow(item, adopted) {
      const status = item.is_recorded ? '朗読済み' : '未朗読・要録音';
      const tags = [item.story_lineage, ...(item.tags || []).slice(0, 3)]
        .filter(Boolean)
        .join(' / ');
      return `
        <div class="simple-row">
          <div>
            <div class="simple-title">${escapeHtml(item.title)}</div>
            <div class="simple-meta">${escapeHtml(item.publication_years || '年表未確認')}</div>
          </div>
          <div class="simple-meta">${escapeHtml(status)}</div>
          <div>
            <div class="simple-meta">${escapeHtml(item.magazines || '掲載誌未確認')}</div>
            <div>${escapeHtml(tags)}</div>
            ${renderBookdataActions(item)}
            <div class="simple-meta">${escapeHtml(item.synopsis || item.summary || '要約未設定')}</div>
            ${adopted.has(item.title) ? '<div class="simple-meta">採用済み総集編に含まれています</div>' : ''}
          </div>
        </div>
      `;
    }

    function renderSimpleList(filtered, adopted) {
      return `
        <div class="simple-list">
          ${filtered.map(item => renderSimpleRow(item, adopted)).join('')}
        </div>
      `;
    }

    function renderGapEntry(entry, kind) {
      const parts = [
        `<strong>${escapeHtml(entry.title || '')}</strong>`,
        entry.publication_years ? ` / ${escapeHtml(entry.publication_years)}` : '',
        entry.magazines ? ` / ${escapeHtml(entry.magazines)}` : '',
      ].join('');
      const note = kind === 'aozora'
        ? escapeHtml(entry.notes || entry.status || '未確認')
        : escapeHtml(entry.synopsis || entry.aozora_notes || entry.recording_status || '情報なし');
      return `<li><div>${parts}</div><div class="gap-note">${note}</div></li>`;
    }

    function renderGaps() {
      els.gapSummary.textContent = `bookdata不足 ${gaps.missing_bookdata.length}本 / 本文未所持 ${gaps.missing_text.length}本`;
      els.missingBookdataSummary.textContent = `現在のカタログ上で bookdata が未作成の作品です。`;
      els.missingTextSummary.textContent = `現手持ちの本文ファイルがない作品です。`;
      const aozoraBuckets = gaps.unresolved_buckets || {};
      els.aozoraSummary.textContent = `青空未解決 ${gaps.unresolved_aozora.length}本 / 国会図書館候補 ${aozoraBuckets.ndl_candidate || 0}本 / 外部公開候補 ${aozoraBuckets.external_public_candidate || 0}本 / 本文不在濃厚 ${aozoraBuckets.likely_text_missing || 0}本`;
      els.missingBookdataList.innerHTML = gaps.missing_bookdata.length
        ? gaps.missing_bookdata.slice(0, 30).map(entry => renderGapEntry(entry, 'bookdata')).join('')
        : '<li class="gap-note">bookdata未作成はありません。</li>';
      els.missingTextList.innerHTML = gaps.missing_text.length
        ? gaps.missing_text.slice(0, 30).map(entry => renderGapEntry(entry, 'text')).join('')
        : '<li class="gap-note">本文未所持はありません。</li>';
      els.aozoraList.innerHTML = gaps.unresolved_aozora.length
        ? gaps.unresolved_aozora.slice(0, 30).map(entry => renderGapEntry(entry, 'aozora')).join('')
        : '<li class="gap-note">青空照合未解決はありません。</li>';
      renderPlannerPulse();
    }

    function syncViewButtons() {
      [...els.viewSwitch.querySelectorAll('[data-view]')].forEach(button => {
        button.classList.toggle('active', button.dataset.view === activeView);
      });
    }

    function render() {
      const { filtered, adopted } = applyFilters();
      els.count.textContent = `${filtered.length}件表示 / 全${items.length}件 / 採用済み作品${adopted.size}本`;
      if (!filtered.length) {
        els.list.innerHTML = '<div class="empty">条件に一致する作品がありませんでした。検索語やフィルタを調整してください。</div>';
        return;
      }
      if (activeView === 'works') {
        els.list.className = '';
        els.list.innerHTML = renderWorkTable(filtered, adopted);
        return;
      }
      if (activeView === 'simple') {
        els.list.className = '';
        els.list.innerHTML = renderSimpleList(filtered, adopted);
        return;
      }
      els.list.className = 'cards';
      els.list.innerHTML = filtered.map(item => renderCard(item, adopted)).join('');
    }

    if (els.facetTabs) {
      els.facetTabs.addEventListener('click', event => {
        const button = event.target.closest('[data-tab]');
        if (!button) return;
        activeFacetTab = button.dataset.tab;
        syncFacetTabs();
        renderFacetChips();
        render();
      });
    }

    if (els.facetChips) {
      els.facetChips.addEventListener('click', event => {
        const button = event.target.closest('[data-facet-value]');
        if (!button) return;
        setFacetValue(String(button.dataset.facetValue || 'all'));
        renderFacetChips();
        render();
      });
    }

    if (els.modeSwitch) {
      els.modeSwitch.addEventListener('click', event => {
        const button = event.target.closest('[data-mode]');
        if (!button) return;
        activeMode = String(button.dataset.mode || 'compilation');
        syncModeButtons();
        syncModePanels();
      });
    }

    els.viewSwitch.addEventListener('click', event => {
      const button = event.target.closest('[data-view]');
      if (!button) return;
      activeView = String(button.dataset.view || 'cards');
      syncViewButtons();
      render();
    });

    els.list.addEventListener('click', event => {
      const seedButton = event.target.closest('[data-seed-title]');
      if (seedButton) {
        selectSeedWork(seedButton.dataset.seedTitle || '');
        return;
      }
      const button = event.target.closest('[data-copy-path]');
      if (!button) return;
      copyText(button.dataset.copyPath || '');
    });

    renderStats();
    renderGaps();
    populateThemeSelect();
    syncFacetTabs();
    syncModeButtons();
    syncModePanels();
    syncViewButtons();
    renderFacetChips();
    renderCompilation();
    renderRecordingPanel();
    renderSeedExplorer();
    render();

    [
      els.q,
      els.sort,
      els.filterLocal,
      els.filterBookdata,
      els.filterChannel,
      els.filterAudio,
      els.filterChronology,
      els.filterNeedsRecording,
    ].forEach(el => el.addEventListener('input', () => {
      render();
    }));

    [
      els.compReadyOnly,
      els.themeSelect,
      els.themeRecordedOnly,
    ].forEach(el => el.addEventListener('input', () => {
      renderCompilation();
    }));

    [
      els.seedPlanSize,
      els.seedTone,
      els.seedExcludeAdopted,
      els.seedExcludeUnrecorded,
      els.seedExcludeNoText,
      els.seedExcludeExistingTheme,
      els.youtubeSeedPreferBacklog,
    ].forEach(el => el.addEventListener('input', () => {
      renderSeedExplorer();
    }));

    els.compList.addEventListener('click', event => {
      const button = event.target.closest('[data-adopt]');
      if (!button) return;
      adoptCandidate(button.dataset.adopt);
    });

    els.adoptedList.addEventListener('click', event => {
      const button = event.target.closest('[data-unadopt]');
      if (!button) return;
      unadoptCandidate(button.dataset.unadopt);
    });

    els.adoptedList.addEventListener('input', event => {
      const field = event.target.closest('[data-adopted-edit]');
      if (!field) return;
      updateAdoptedField(field.dataset.adoptedId || '', field.dataset.adoptedEdit || '', field.value || '');
    });

    els.seedCandidateList.addEventListener('click', event => {
      const button = event.target.closest('[data-seed-title]');
      if (!button) return;
      selectSeedWork(button.dataset.seedTitle || '');
    });

    els.seedBundleList.addEventListener('click', event => {
      const addButton = event.target.closest('[data-queue-add]');
      if (addButton) {
        const bundleId = String(addButton.dataset.queueAdd || '');
        const bundle = buildSeedBundles().find(entry => entry.bundle_id === bundleId);
        if (bundle) addBundleToReviewQueue(bundle);
        return;
      }
      const copyButton = event.target.closest('[data-copy-bundle-id]');
      if (!copyButton) return;
      copyText(copyButton.dataset.copyBundleId || '');
    });

    els.reviewQueueList.addEventListener('click', event => {
      const statusButton = event.target.closest('[data-queue-status]');
      if (statusButton) {
        const bundleId = statusButton.dataset.queueId || '';
        const nextStatus = statusButton.dataset.queueStatus || 'pending';
        if (nextStatus === 'adopted') {
          adoptQueueBundle(bundleId);
        } else {
          updateBundleReviewStatus(bundleId, nextStatus);
        }
        return;
      }
      const removeButton = event.target.closest('[data-queue-remove]');
      if (removeButton) {
        removeBundleFromReviewQueue(removeButton.dataset.queueRemove || '');
        return;
      }
      const copyButton = event.target.closest('[data-copy-bundle-id]');
      if (!copyButton) return;
      copyText(copyButton.dataset.copyBundleId || '');
    });

    function handleReviewQueueFieldEdit(event) {
      const field = event.target.closest('[data-queue-edit]');
      if (!field) return;
      updateQueueBundleField(field.dataset.queueId || '', field.dataset.queueEdit || '', field.value || '');
    }

    els.reviewQueueList.addEventListener('input', handleReviewQueueFieldEdit);
    els.reviewQueueList.addEventListener('change', handleReviewQueueFieldEdit);

    els.needsRecordingList.addEventListener('click', event => {
      const markButton = event.target.closest('[data-recording-mark]');
      if (markButton) {
        setRecordingOverride(
          markButton.dataset.recordingMark,
          String(markButton.dataset.recordingValue) === 'true'
        );
        return;
      }
      const clearButton = event.target.closest('[data-recording-clear]');
      if (!clearButton) return;
      clearRecordingOverride(clearButton.dataset.recordingClear);
    });

    els.recordingOverrideList.addEventListener('click', event => {
      const markButton = event.target.closest('[data-recording-mark]');
      if (markButton) {
        setRecordingOverride(
          markButton.dataset.recordingMark,
          String(markButton.dataset.recordingValue) === 'true'
        );
        return;
      }
      const clearButton = event.target.closest('[data-recording-clear]');
      if (!clearButton) return;
      clearRecordingOverride(clearButton.dataset.recordingClear);
    });

    els.exportState.addEventListener('click', exportState);
    els.exportRecordingState.addEventListener('click', exportRecordingState);
    els.exportReviewQueue.addEventListener('click', exportReviewQueue);
    if (els.loadReviewQueueJson) {
      els.loadReviewQueueJson.addEventListener('click', () => {
        syncReviewQueueEditor();
        els.reviewQueueSummary.textContent = '現在の review queue JSON を表示しました';
      });
    }
    if (els.importReviewQueueJson) {
      els.importReviewQueueJson.addEventListener('click', importReviewQueueFromEditor);
    }
    els.clearSeedSelection.addEventListener('click', () => {
      seedTitle = '';
      renderSeedExplorer();
    });
    els.resetState.addEventListener('click', () => {
      if (!window.confirm('採用済み総集編をすべて解除しますか？')) return;
      compilationState = clone(compilation.state || { adopted_candidates: [] });
      saveCompilationState();
      renderCompilation();
      renderSeedExplorer();
      render();
    });
    els.resetRecordingState.addEventListener('click', () => {
      if (!window.confirm('手動更新した録音状態を初期化しますか？')) return;
      recordingState = clone(recording.state || { recording_overrides: [] });
      saveRecordingState();
      refreshRecordingDerivedFields();
      renderStats();
      renderRecordingPanel();
      renderCompilation();
      renderSeedExplorer();
      render();
    });
    els.resetReviewQueue.addEventListener('click', () => {
      if (!window.confirm('review queue を初期化しますか？')) return;
      reviewQueueState = clone(reviewQueue.state || { bundles: [] });
      saveReviewQueueState();
      renderReviewQueue();
    });

    refreshRecordingDerivedFields();
    renderSeedExplorer();
    render();
  </script>
</body>
</html>
  """
    return (
        html.replace("{{", "{")
        .replace("}}", "}")
        .replace("__GENERATED_AT__", generated_at)
        .replace("__STATE_FILE__", STATE_PATH.name)
        .replace("__RECORDING_STATE_FILE__", RECORDING_STATE_PATH.name)
        .replace("__BUNDLE_REVIEW_QUEUE_FILE__", BUNDLE_REVIEW_QUEUE_PATH.name)
        .replace("__DATA_JSON__", data_json)
    )


def main() -> int:
    state = load_state()
    recording_state = load_recording_state()
    review_queue = load_review_queue()
    aozora_manifest = load_aozora_manifest()
    rows = load_rows(recording_state, aozora_manifest)
    index = build_index(rows)
    groups = build_compilation_groups(rows)
    candidates = build_compilation_candidates(groups, rows, state)
    theme_scores = load_theme_scores()
    payload: dict[str, Any] = {
        **index,
        "gaps": build_gap_payload(rows, aozora_manifest),
        "youtube_seed_report": load_seed_shortworks_report(),
        "compilation": {
            "groups": groups,
            "state": state,
        },
        "recording": {
            "state": recording_state,
        },
        "review_queue": {
            "state": review_queue,
        },
        "theme_match": build_theme_match_payload(theme_scores),
    }

    OUT_PATH.write_text(render_html(payload), encoding="utf-8")
    write_needs_recording_reports(rows)
    write_synopsis_gap_report(rows)
    COMPILATION_MD_PATH.write_text(
        render_compilation_markdown(rows, state, candidates),
        encoding="utf-8",
    )

    print(f"Wrote: {OUT_PATH.relative_to(ROOT)}")
    print(f"Wrote: {COMPILATION_MD_PATH.relative_to(ROOT)}")
    print(f"Wrote: {STATE_PATH.relative_to(ROOT)}")
    print(f"Wrote: {RECORDING_STATE_PATH.relative_to(ROOT)}")
    print(f"Wrote: {BUNDLE_REVIEW_QUEUE_PATH.relative_to(ROOT)}")
    print(f"Wrote: {NEEDS_RECORDING_MD_PATH.relative_to(ROOT)}")
    print(f"Wrote: {NEEDS_RECORDING_CSV_PATH.relative_to(ROOT)}")
    print(f"Wrote: {SYNOPSIS_GAPS_MD_PATH.relative_to(ROOT)}")
    print(f"Works: {len(rows)}")
    print(f"Compilation groups: {len(groups)}")
    print(f"Compilation candidates: {len(candidates)}")
    print(f"Needs recording: {sum(1 for row in rows if row['needs_recording'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
