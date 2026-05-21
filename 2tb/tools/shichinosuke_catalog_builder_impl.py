#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
BOOKDATA_DIR = ROOT / "bookdata" / "2_nagon"
TEXT_DIR = ROOT / "Reading_library" / "納言恭平著"
ALT_TEXT_DIR = Path(
    "/Users/kinoshitayoshihiro/Library/CloudStorage/GoogleDrive-shimogami88@gmail.com/マイドライブ/丸竹書房/Reading_library/納言恭平著"
)
THEME_MD_PATH = REPORTS_DIR / "theme_groups_七之助捕物帳.md"
THEME_CONTENT_MD_PATH = REPORTS_DIR / "theme_groups_七之助捕物帳_content.md"
VOLUME_MAPPING_PATH = ROOT / "tools" / "shichino_volume_mapping.json"
CATALOG_JSON_PATH = REPORTS_DIR / "shichinosuke_works_catalog.json"
CATALOG_CSV_PATH = REPORTS_DIR / "shichinosuke_works_catalog.csv"
CATALOG_MD_PATH = REPORTS_DIR / "shichinosuke_works_catalog.md"
GAP_REPORT_MD_PATH = REPORTS_DIR / "shichinosuke_metadata_gap_report.md"
CLASSIFICATION_REPORT_MD_PATH = REPORTS_DIR / "shichinosuke_classification_report.md"
BUNDLE_REVIEW_QUEUE_PATH = REPORTS_DIR / "shichinosuke_bundle_review_queue.json"
ADOPTED_BUNDLES_PATH = REPORTS_DIR / "shichinosuke_adopted_bundles.json"
SEARCH_HTML_PATH = REPORTS_DIR / "shichinosuke_search.html"
REVIEW_PROMPTS_DIR = REPORTS_DIR / "shichinosuke_bundle_review_prompts"
REMOTE_TEXT_CACHE_DIR = REPORTS_DIR / "shichinosuke_site_texts"
REMOTE_SEARCH_BASE_URL = "https://marutakesyobou.com/?s=%E4%B8%83%E4%B9%8B%E5%8A%A9%E6%8D%95%E7%89%A9%E5%B8%B3"
REMOTE_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CodexShichinosukeBot/1.0)"
}

AUDIO_ROOT = Path(
    "/Users/kinoshitayoshihiro/Library/CloudStorage/GoogleDrive-shimogami88@gmail.com/マイドライブ/AudioBook/13.文豪編/21.納言恭平/1.七之助捕物帳"
)
VIDEO_ROOT = Path("/Volumes/SSD-PUTA - Data/AudioBook/05_七之助捕物帳")
TEXT_SOURCE_DIRS = [TEXT_DIR, ALT_TEXT_DIR, VIDEO_ROOT, REMOTE_TEXT_CACHE_DIR]

MEDIA_AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".aac"}
MEDIA_VIDEO_EXTS = {".mp4", ".mov", ".m4v"}
TEXT_EXTS = {".txt"}
MAX_TEXT_NUL_RATIO = 0.20
MAX_TEXT_REPLACEMENT_CHARS = 5
MIN_TEXT_CHARS = 1000

SERIES_PREFIX = "七之助捕物帳"
EPISODE_ORDER_HINTS = {
    "小指千両": 44,
    "狂い蝶": 42,
    "謎の振袖": 43,
    "魔法布呂敷": 45,
    "宿借り仏": 46,
    "夢の首吊り": 47,
    "蛇の眼の女": 48,
    "石となった千両箱": 49,
}
MANUAL_ALIASES: dict[str, list[str]] = {
    "お高祖頭巾": ["お高祖頭巾の女"],
    "水の深川": ["水野深川"],
    "春宵手毬唄": ["春宵手鞠歌"],
    "鶯替騷動": ["鷽替騒動", "鶯替騒動"],
    "十手黑星": ["十手黒星"],
    "歎きの黒ン坊": ["歎きの黒人"],
    "口笛の秘密": ["口笛の謎"],
    "乞食の仇討": ["乞食の仇討ち"],
    "射的競べの怪": ["射的競べの怪"],
    "小夜しぐれ": ["小夜しぐれ"],
    "魔法布呂敷": ["魔法風呂敷"],
    "蛇の眼の女": ["蛇の目の女"],
    "夢の首吊り": ["夢の首つり"],
    "人喰い花": ["人食い花"],
    "色魔殺し": ["色魔ごろし"],
    "仇討幽霊": ["仇討ち幽霊"],
    "鳥追お巻": ["鳥追いお巻"],
    "第7巻": ["歎きの黒人"],
    "第8巻": ["口笛の謎"],
    "第9巻": ["人真似鳥の夢"],
    "第5巻": ["さかさ天一坊"],
    "第6巻": ["業平御殿"],
}
VARIANT_REPLACEMENTS = {
    "黑": "黒",
    "騷": "騒",
    "毬": "鞠",
    "唄": "歌",
    "布呂敷": "風呂敷",
    "蛇の目": "蛇の眼",
    "仇討ち": "仇討",
    "お高祖頭巾の女": "お高祖頭巾",
    "水野深川": "水の深川",
    "人食い花": "人喰い花",
    "色魔ごろし": "色魔殺し",
    "仇討ち幽霊": "仇討幽霊",
    "鳥追いお巻": "鳥追お巻",
    "鐘撞き": "鐘撞",
    "競べ": "競べ",
}
PUNCT_TRANSLATION = str.maketrans(
    {
        "　": "",
        " ": "",
        "_": "",
        "-": "",
        "ー": "",
        "・": "",
        "【": "",
        "】": "",
        "（": "",
        "）": "",
        "(": "",
        ")": "",
        "[": "",
        "]": "",
        "「": "",
        "」": "",
        "『": "",
        "』": "",
        "、": "",
        "。": "",
        ".": "",
        "!": "",
        "！": "",
        ":": "",
        "：": "",
    }
)

MAJOR_CATEGORY_RULES = [
    (
        "怪異・幽霊・見世物",
        [
            "幽霊",
            "怪",
            "怪異",
            "呪",
            "鬼",
            "仏",
            "ゆうれい",
            "見世物",
            "熊娘",
            "白鬼",
        ],
    ),
    (
        "仇討・復讐・怨念",
        ["仇討", "復讐", "怨念", "仇", "うらみ", "恨み"],
    ),
    (
        "盗み・千両箱・悪党の企て",
        [
            "千両",
            "盗",
            "強盗",
            "押込",
            "悪党",
            "押し込み",
            "盗賊",
            "金箱",
        ],
    ),
    (
        "色恋・情念・嫉妬",
        [
            "恋",
            "嫉妬",
            "情念",
            "色",
            "妾",
            "囲い",
            "女",
            "緋牡丹",
            "色魔",
        ],
    ),
    (
        "家族・身売り・人情",
        ["親", "娘", "母", "父", "家族", "人情", "身売", "恩", "孝"],
    ),
]

MINOR_CATEGORY_RULES = {
    "幽霊偽装": ["幽霊", "ゆうれい", "亡霊", "怪異"],
    "脅迫状": ["脅迫", "手紙", "文", "脅し"],
    "密室・怪死": ["怪死", "密室", "変死", "土左衛門", "死体"],
    "色仕掛け": ["色仕掛", "妾", "囲い", "色"],
    "囲い者騒動": ["囲い", "妾宅", "囲い者"],
    "仇討ち": ["仇討", "復讐", "うらみ", "恨み"],
    "千両箱争い": ["千両", "千両箱", "金箱"],
    "死体すり替え": ["替え玉", "すり替え", "死体偽装", "偽装"],
    "見世物小屋": ["見世物", "軽業", "熊娘", "芸人"],
    "舟・川筋事件": ["舟", "川", "堀", "河岸", "土左衛門"],
    "旗本屋敷事件": ["旗本", "屋敷", "知行所"],
    "商家内紛": ["番頭", "旦那", "商人", "女将", "質屋"],
}


@dataclass
class BookRecord:
    key: str
    title: str
    short_title: str
    canonical_title: str
    sort_order: int
    volume_number: int | None
    author: str
    synopsis: str
    themes: list[str]
    keywords: list[str]
    characters: list[str]
    major_category: str
    minor_categories: list[str]
    compilation_priority: str
    compilation_notes: str
    chapter_count: int
    has_synopsis: bool
    has_themes: bool
    bookdata_path: Path
    text_paths: list[Path]
    audio_paths: list[Path]
    video_paths: list[Path]
    raw_video_paths: list[Path]
    audio_story_dirs: list[Path]
    search_text: str


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    for src, dst in VARIANT_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = re.sub(r"第0*(\d+)巻", lambda m: f"第{int(m.group(1))}巻", text)
    text = re.sub(r"第0*(\d+)話", lambda m: f"第{int(m.group(1))}話", text)
    text = text.replace(SERIES_PREFIX, "")
    text = text.replace("納言恭平著", "").replace("納言恭平", "")
    text = text.translate(PUNCT_TRANSLATION)
    return text.lower()


def split_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[|/、,，]\s*", value)
        return [part.strip() for part in parts if part.strip()]
    return []


def compact_text(*parts: Any) -> str:
    return "\n".join(str(part or "") for part in parts if str(part or "").strip())


def infer_major_category(title: str, synopsis: str, themes: list[str]) -> str:
    haystack = normalize_text(compact_text(title, synopsis, " / ".join(themes)))
    best_category = "成りすまし・替え玉・偽装"
    best_score = -1
    for category, keywords in MAJOR_CATEGORY_RULES:
        score = sum(1 for keyword in keywords if normalize_text(keyword) in haystack)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


def infer_minor_categories(
    title: str,
    synopsis: str,
    themes: list[str],
    major_category: str,
) -> list[str]:
    haystack = normalize_text(compact_text(title, synopsis, " / ".join(themes)))
    matches = [
        label
        for label, keywords in MINOR_CATEGORY_RULES.items()
        if any(normalize_text(keyword) in haystack for keyword in keywords)
    ]
    if major_category == "怪異・幽霊・見世物" and "幽霊偽装" not in matches:
        matches.append("幽霊偽装")
    if major_category == "仇討・復讐・怨念" and "仇討ち" not in matches:
        matches.append("仇討ち")
    if major_category == "盗み・千両箱・悪党の企て" and "千両箱争い" not in matches:
        matches.append("千両箱争い")
    return matches[:3]


def infer_compilation_priority(
    has_audio: bool,
    has_video: bool,
    has_synopsis: bool,
    has_themes: bool,
) -> str:
    if has_audio and has_synopsis and has_themes:
        return "high"
    if (has_audio or has_video) and (has_synopsis or has_themes):
        return "medium"
    return "low"


def infer_compilation_notes(
    major_category: str,
    minor_categories: list[str],
    chapter_count: int,
) -> str:
    note_parts = [major_category]
    if minor_categories:
        note_parts.append(" / ".join(minor_categories[:2]))
    note_parts.append(f"{chapter_count}章")
    return " | ".join(note_parts)


def extract_volume_number(*values: str) -> int | None:
    for value in values:
        if not value:
            continue
        match = re.search(r"第\s*0*(\d+)\s*巻", value)
        if match:
            return int(match.group(1))
    return None


def extract_short_title(title: str, path: Path) -> str:
    match = re.search(r"【([^】]+)】", title)
    if match:
        return match.group(1).strip()

    stem = path.stem
    if stem.startswith(f"{SERIES_PREFIX}_"):
        stem = stem[len(f"{SERIES_PREFIX}_") :]
    if "_" in stem:
        parts = [part for part in stem.split("_") if part]
        if len(parts) >= 2:
            return parts[-1].strip()
    trimmed = title.replace(SERIES_PREFIX, "").strip(" 　_-")
    trimmed = re.sub(r"納言恭平.*$", "", trimmed).strip(" 　_-")
    trimmed = re.sub(r"^第[一二三四五六七八九十0-9]+巻", "", trimmed).strip(" 　_-")
    return trimmed or title.strip()


def canonical_title(title: str) -> str:
    title = str(title or "").strip()
    normalized = normalize_text(title)
    for canonical, aliases in MANUAL_ALIASES.items():
        if normalize_text(canonical) == normalized:
            return canonical
        if normalized in {normalize_text(alias) for alias in aliases}:
            return canonical
    return title


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fetch_remote_text(url: str) -> str:
    request = urllib.request.Request(url, headers=REMOTE_REQUEST_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def safe_cache_name(title: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "_", str(title or "").strip())
    text = text.replace("\n", " ").strip(" .")
    return text or "untitled"


def extract_remote_article_urls(search_html: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(
        r'href="(https://marutakesyobou\.com/[^"]+)"[^>]*>\s*納言恭平[^<]*七之助捕物帳',
        re.I,
    )
    for url in pattern.findall(search_html):
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def extract_remote_story_payload(html: str) -> dict[str, Any] | None:
    start_token = "window.immersiveCurrentData = "
    start = html.find(start_token)
    if start < 0:
        return None
    start += len(start_token)
    try:
        payload, _ = json.JSONDecoder().raw_decode(html[start:].lstrip())
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def remote_story_text(payload: dict[str, Any]) -> str:
    chapters = payload.get("chapters", [])
    if not isinstance(chapters, list):
        return ""
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        title = str(chapter.get("title", "")).strip()
        content = str(chapter.get("content", "")).strip()
        if title == "本文" and content:
            return content
    for chapter in chapters:
        if isinstance(chapter, dict):
            content = str(chapter.get("content", "")).strip()
            if content:
                return content
    return ""


def cache_remote_texts() -> list[Path]:
    REMOTE_TEXT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached_paths: list[Path] = []
    article_urls: list[str] = []
    seen_urls: set[str] = set()

    for page_num in range(1, 7):
        search_url = (
            REMOTE_SEARCH_BASE_URL
            if page_num == 1
            else f"https://marutakesyobou.com/page/{page_num}/?s=%E4%B8%83%E4%B9%8B%E5%8A%A9%E6%8D%95%E7%89%A9%E5%B8%B3"
        )
        try:
            search_html = fetch_remote_text(search_url)
        except (urllib.error.URLError, TimeoutError):
            continue
        urls = extract_remote_article_urls(search_html)
        if not urls:
            continue
        new_count = 0
        for url in urls:
            if url not in seen_urls:
                seen_urls.add(url)
                article_urls.append(url)
                new_count += 1
        if new_count == 0:
            break

    for url in article_urls:
        try:
            html = fetch_remote_text(url)
        except (urllib.error.URLError, TimeoutError):
            continue
        payload = extract_remote_story_payload(html)
        if not payload:
            continue
        text = remote_story_text(payload)
        if len(text.strip()) < MIN_TEXT_CHARS:
            continue
        title = str(payload.get("title", "")).strip() or urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        cache_path = REMOTE_TEXT_CACHE_DIR / f"{safe_cache_name(title)}.txt"
        cache_path.write_text(text, encoding="utf-8")
        cached_paths.append(cache_path)

    return cached_paths


def load_payload_from_search_html(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    match = re.search(r"const APP_DATA = (\{.*?\});\s*const WORKSPACE_ROOT", text, re.S)
    if not match:
        return None
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def load_works_from_review_prompts(base_dir: Path) -> list[dict[str, Any]]:
    if not base_dir.exists():
        return []
    works_by_title: dict[str, dict[str, Any]] = {}

    def flush_current(current: dict[str, Any] | None) -> None:
        if not current or "title" not in current or "short_title" not in current:
            return
        title = str(current["title"]).strip()
        serial_number = int(current.get("serial_number", 999))
        existing = works_by_title.get(title, {})
        existing_synopsis = str(existing.get("synopsis", ""))
        synopsis = str(current.get("synopsis", "")).strip()
        works_by_title[title] = {
            "key": existing.get("key", f"{serial_number:03d}:{normalize_text(str(current['short_title']))}"),
            "serial_number": serial_number,
            "sort_order": serial_number,
            "volume_number": serial_number,
            "title": title,
            "short_title": str(current["short_title"]).strip(),
            "canonical_title": canonical_title(str(current["short_title"]).strip()),
            "author": "納言恭平",
            "synopsis": synopsis if len(synopsis) >= len(existing_synopsis) else existing_synopsis,
            "themes": list(current.get("themes", [])),
            "keywords": existing.get("keywords", []),
            "characters": list(current.get("characters", [])),
            "major_category": str(current.get("major_category", "")).strip(),
            "minor_categories": list(current.get("minor_categories", [])),
            "compilation_priority": "high",
            "compilation_notes": existing.get("compilation_notes", ""),
            "chapter_count": existing.get("chapter_count", 0),
            "has_synopsis": True,
            "has_themes": True,
            "bookdata_path": str(current.get("bookdata_path", "")).strip(),
            "text_paths": list(current.get("text_paths", [])),
            "audio_paths": existing.get("audio_paths", []),
            "video_paths": existing.get("video_paths", []),
            "raw_video_paths": existing.get("raw_video_paths", []),
            "audio_story_dirs": existing.get("audio_story_dirs", []),
            "search_text": existing.get("search_text", ""),
        }

    for path in sorted(base_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        current: dict[str, Any] | None = None
        for raw_line in lines + ["## END"]:
            line = raw_line.strip()
            if line.startswith("### 作品"):
                flush_current(current)
                current = {}
                continue
            if current is None:
                continue
            if line.startswith("- 通し番号: "):
                current["serial_number"] = int(line.split(": ", 1)[1])
            elif line.startswith("- タイトル: "):
                current["title"] = line.split(": ", 1)[1].strip()
            elif line.startswith("- 短縮タイトル: "):
                current["short_title"] = line.split(": ", 1)[1].strip()
            elif line.startswith("- 大分類: "):
                current["major_category"] = line.split(": ", 1)[1].strip()
            elif line.startswith("- 小分類: "):
                current["minor_categories"] = [
                    part.strip() for part in line.split(": ", 1)[1].split(" / ") if part.strip()
                ]
            elif line.startswith("- themes: "):
                current["themes"] = [
                    part.strip() for part in line.split(": ", 1)[1].split(" / ") if part.strip()
                ]
            elif line.startswith("- characters: "):
                current["characters"] = [
                    part.strip() for part in line.split(": ", 1)[1].split(" / ") if part.strip()
                ]
            elif line.startswith("- 本文参照: "):
                current["text_paths"] = [
                    part.strip() for part in line.split(": ", 1)[1].split(" / ") if part.strip()
                ]
            elif line.startswith("- bookdata: "):
                current["bookdata_path"] = line.split(": ", 1)[1].strip()
            elif line.startswith("- synopsis: "):
                current["synopsis"] = line.split(": ", 1)[1].strip()

            if line.startswith("## ") or raw_line == "## END":
                flush_current(current)
                current = None
    return sorted(works_by_title.values(), key=lambda item: (int(item.get("sort_order", 999)), item.get("title", "")))


def normalize_adopted_bundle_state(raw: Any) -> dict[str, Any]:
    adopted_bundles: list[dict[str, Any]] = []
    if isinstance(raw, dict):
        for index, entry in enumerate(raw.get("adopted_bundles", []), start=1):
            if not isinstance(entry, dict):
                continue
            bundle_id = str(entry.get("bundle_id", "") or "").strip()
            if not bundle_id:
                continue
            sequence = entry.get("sequence", index)
            try:
                sequence = int(sequence)
            except (TypeError, ValueError):
                sequence = index
            volume_label = str(entry.get("volume_label", "") or "").strip()
            custom_title = str(entry.get("custom_title", "") or "").strip()
            note = str(entry.get("note", "") or "").strip()
            adopted_bundles.append(
                {
                    "sequence": sequence,
                    "volume_label": volume_label or f"第{sequence}集",
                    "bundle_id": bundle_id,
                    "custom_title": custom_title,
                    "note": note,
                }
            )
    adopted_bundles.sort(key=lambda entry: (entry["sequence"], entry["volume_label"]))
    return {"adopted_bundles": adopted_bundles}


def load_adopted_bundle_state() -> dict[str, Any]:
    if ADOPTED_BUNDLES_PATH.exists():
        try:
            state = normalize_adopted_bundle_state(
                json.loads(ADOPTED_BUNDLES_PATH.read_text(encoding="utf-8"))
            )
        except json.JSONDecodeError:
            state = normalize_adopted_bundle_state({})
    else:
        state = normalize_adopted_bundle_state({})
    ADOPTED_BUNDLES_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return state


def resolve_adopted_bundles(
    bundle_groups: dict[str, list[dict[str, Any]]],
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    bundle_by_id: dict[str, dict[str, Any]] = {}
    for bundle_group, bundles in bundle_groups.items():
        for bundle in bundles:
            bundle_id = str(bundle.get("bundle_id", "") or "").strip()
            if not bundle_id:
                continue
            bundle_by_id[bundle_id] = {**bundle, "bundle_group": bundle_group}

    adopted: list[dict[str, Any]] = []
    for entry in state.get("adopted_bundles", []):
        bundle = bundle_by_id.get(str(entry.get("bundle_id", "") or "").strip())
        if not bundle:
            continue
        adopted.append(
            {
                "sequence": int(entry.get("sequence", len(adopted) + 1)),
                "volume_label": str(entry.get("volume_label", "") or "").strip(),
                "bundle_id": bundle["bundle_id"],
                "bundle_group": bundle.get("bundle_group", ""),
                "label": bundle.get("label", ""),
                "source": bundle.get("source", ""),
                "custom_title": str(entry.get("custom_title", "") or "").strip(),
                "recommended_title": str(bundle.get("recommended_title", "") or "").strip(),
                "note": str(entry.get("note", "") or "").strip(),
                "publication_priority": bundle.get("publication_priority", "low"),
                "publication_reason": bundle.get("publication_reason", ""),
                "major_category": bundle.get("major_category", ""),
                "minor_category": bundle.get("minor_category", ""),
                "works": list(bundle.get("works", [])),
            }
        )
    adopted.sort(key=lambda entry: (entry["sequence"], entry["volume_label"]))
    return adopted


def scan_media_files(base: Path, extensions: set[str]) -> list[Path]:
    if not base.exists():
        return []
    return sorted(
        path
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions
    )


def scan_media_files_many(bases: list[Path], extensions: set[str]) -> list[Path]:
    seen: set[Path] = set()
    merged: list[Path] = []
    for base in bases:
        for path in scan_media_files(base, extensions):
            if path not in seen:
                seen.add(path)
                merged.append(path)
    return merged


def aliases_for_work(
    short_title: str,
    canonical: str,
    volume_number: int | None,
    *,
    include_volume: bool = True,
) -> set[str]:
    aliases = {short_title, canonical}
    aliases.update(MANUAL_ALIASES.get(canonical, []))
    if include_volume and volume_number is not None:
        aliases.add(f"第{volume_number}巻")
        aliases.add(f"{volume_number}.")
    if canonical in EPISODE_ORDER_HINTS:
        aliases.add(f"{EPISODE_ORDER_HINTS[canonical]}.")
    if canonical == "お高祖頭巾":
        aliases.add("お高祖頭巾の女")
    return {normalize_text(alias) for alias in aliases if alias}


def path_match_score(path: Path, aliases: set[str]) -> int:
    haystacks = {
        normalize_text(path.name),
        normalize_text(path.stem),
        normalize_text(str(path)),
    }
    for parent in list(path.parents)[:3]:
        haystacks.add(normalize_text(parent.name))
    score = 0
    for alias in aliases:
        if not alias:
            continue
        for haystack in haystacks:
            if alias and alias in haystack:
                score = max(score, len(alias))
    return score


@lru_cache(maxsize=None)
def inspect_text_path(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    raw = path.read_bytes()
    decoded = ""
    encoding = ""
    replacement_count = 0
    for candidate in ("utf-8", "utf-8-sig", "cp932", "shift_jis", "euc_jp"):
        try:
            decoded = raw.decode(candidate)
            encoding = candidate
            replacement_count = decoded.count("�")
            break
        except UnicodeDecodeError:
            continue
    if not decoded:
        decoded = raw.decode("utf-8", errors="replace")
        encoding = "utf-8-replace"
        replacement_count = decoded.count("�")

    nul_count = decoded.count("\x00")
    cleaned = decoded.replace("\x00", "")
    char_count = len(cleaned.strip())
    line_count = cleaned.count("\n") + 1 if cleaned else 0
    nul_ratio = (nul_count / len(decoded)) if decoded else 0.0
    valid = (
        char_count >= MIN_TEXT_CHARS
        and nul_ratio <= MAX_TEXT_NUL_RATIO
        and replacement_count <= MAX_TEXT_REPLACEMENT_CHARS
    )
    return {
        "path": path_str,
        "encoding": encoding,
        "nul_count": nul_count,
        "nul_ratio": round(nul_ratio, 6),
        "replacement_count": replacement_count,
        "char_count": char_count,
        "line_count": line_count,
        "valid": valid,
    }


def filter_valid_text_paths(paths: list[Path]) -> list[Path]:
    valid_paths: list[Path] = []
    for path in paths:
        inspection = inspect_text_path(path.as_posix())
        if inspection["valid"]:
            valid_paths.append(path)
    return valid_paths


def dedupe_story_dirs(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        parent = path.parent
        if parent not in seen:
            seen.add(parent)
            result.append(parent)
    return result


def load_volume_mapping() -> dict[int, Path]:
    if not VOLUME_MAPPING_PATH.exists():
        return {}
    raw = load_json(VOLUME_MAPPING_PATH)
    if not isinstance(raw, dict):
        return {}
    result: dict[int, Path] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        file_name = str(value.get("file", "")).strip()
        if not file_name:
            continue
        try:
            volume_num = int(key)
        except ValueError:
            continue
        result[volume_num] = TEXT_DIR / file_name
    return result


def choose_preferred_bookdata(paths: list[Path]) -> Path:
    def score(path: Path) -> tuple[int, int, int]:
        data = load_json(path)
        synopsis = str(data.get("synopsis", "") or "").strip()
        themes = split_list(data.get("themes", []))
        chapter_count = (
            len(data.get("chapters", []))
            if isinstance(data.get("chapters"), list)
            else 0
        )
        numbered = (
            1
            if extract_volume_number(path.stem, str(data.get("title", ""))) is not None
            else 0
        )
        return (len(synopsis), len(themes) * 10 + chapter_count, numbered)

    return max(paths, key=score)


def collect_book_files() -> list[Path]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(BOOKDATA_DIR.glob("七之助捕物帳*.json")):
        try:
            data = load_json(path)
        except json.JSONDecodeError:
            continue
        title = str(data.get("title", path.stem))
        short = extract_short_title(title, path)
        canonical = canonical_title(short)
        volume = extract_volume_number(path.stem, title)
        key = f"{volume or 999:03d}:{normalize_text(canonical)}"
        grouped[key].append(path)
    return [choose_preferred_bookdata(paths) for _, paths in sorted(grouped.items())]


def match_paths(
    paths: list[Path], aliases: set[str], *, minimum_score: int = 2
) -> list[Path]:
    matches: list[tuple[int, Path]] = []
    for path in paths:
        score = path_match_score(path, aliases)
        if score >= minimum_score:
            matches.append((score, path))
    matches.sort(key=lambda item: (-item[0], str(item[1])))
    return [path for _, path in matches]


def rebuild_records_from_existing_payload(
    payload: dict[str, Any],
    text_paths: list[Path],
    audio_paths: list[Path],
    video_paths: list[Path],
    volume_mapping: dict[int, Path],
) -> list[BookRecord]:
    records: list[BookRecord] = []
    for work in payload.get("works", []):
        if not isinstance(work, dict):
            continue
        title = str(work.get("title", "")).strip()
        short_title = str(work.get("short_title", "")).strip()
        if not title or not short_title:
            continue
        canonical = str(work.get("canonical_title", "")).strip() or canonical_title(short_title)
        volume_number = work.get("volume_number")
        try:
            volume_number = int(volume_number) if volume_number not in (None, "") else None
        except (TypeError, ValueError):
            volume_number = extract_volume_number(title, short_title)
        text_aliases = aliases_for_work(short_title, canonical, volume_number, include_volume=True)
        media_aliases = aliases_for_work(short_title, canonical, volume_number, include_volume=False)
        matched_texts = filter_valid_text_paths(match_paths(text_paths, text_aliases, minimum_score=2))
        mapped_text = volume_mapping.get(volume_number or -1)
        if (
            mapped_text
            and mapped_text.exists()
            and mapped_text not in matched_texts
            and inspect_text_path(mapped_text.as_posix())["valid"]
        ):
            matched_texts.insert(0, mapped_text)
        matched_audio = match_paths(audio_paths, media_aliases, minimum_score=4)
        matched_videos = match_paths(video_paths, media_aliases, minimum_score=4)
        raw_videos = [path for path in matched_videos if str(path).startswith(VIDEO_ROOT.as_posix())]
        audio_story_dirs = dedupe_story_dirs(matched_audio)
        bookdata_raw = str(work.get("bookdata_path", "")).strip()
        bookdata_path = (ROOT / bookdata_raw) if bookdata_raw and not Path(bookdata_raw).is_absolute() else Path(bookdata_raw or "bookdata/missing.json")
        characters = split_list(work.get("characters", []))
        records.append(
            BookRecord(
                key=str(work.get("key", "")).strip() or f"{int(work.get('sort_order', len(records)+1)):03d}:{normalize_text(canonical)}",
                title=title,
                short_title=short_title,
                canonical_title=canonical,
                sort_order=int(work.get("sort_order", len(records) + 1) or (len(records) + 1)),
                volume_number=volume_number,
                author=str(work.get("author", "")).strip(),
                synopsis=str(work.get("synopsis", "")).strip(),
                themes=split_list(work.get("themes", [])),
                keywords=split_list(work.get("keywords", [])),
                characters=characters,
                major_category=str(work.get("major_category", "")).strip(),
                minor_categories=split_list(work.get("minor_categories", [])),
                compilation_priority=str(work.get("compilation_priority", "low")).strip() or "low",
                compilation_notes=str(work.get("compilation_notes", "")).strip(),
                chapter_count=int(work.get("chapter_count", 0) or 0),
                has_synopsis=bool(work.get("has_synopsis", False) or str(work.get("synopsis", "")).strip()),
                has_themes=bool(work.get("has_themes", False) or split_list(work.get("themes", []))),
                bookdata_path=bookdata_path,
                text_paths=matched_texts,
                audio_paths=matched_audio,
                video_paths=matched_videos,
                raw_video_paths=raw_videos,
                audio_story_dirs=audio_story_dirs,
                search_text=str(work.get("search_text", "")).strip(),
            )
        )
    records.sort(key=lambda record: (record.sort_order, record.title))
    return records


def load_theme_bundles(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    bundles: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    bullet_pattern = re.compile(
        r"^-\s+(?P<title>.+?)\s*/\s*(?P<author>.+?)\s+\((?P<path>[^)]+)\)\s+\[hit:\s*(?P<hits>[^\]]*)\]$"
    )
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if line.startswith("## "):
                if current and current.get("works"):
                    bundles.append(current)
                current = {
                    "bundle_id": normalize_text(line[3:]) or f"bundle-{len(bundles)+1}",
                    "label": line[3:].strip(),
                    "source": path.name,
                    "works": [],
                }
                continue
            if not current:
                continue
            match = bullet_pattern.match(line)
            if not match:
                continue
            current["works"].append(
                {
                    "title": match.group("title").strip(),
                    "author": match.group("author").strip(),
                    "path": match.group("path").strip(),
                    "hits": [
                        item.strip()
                        for item in match.group("hits").split(",")
                        if item.strip()
                    ],
                }
            )
    if current and current.get("works"):
        bundles.append(current)
    return bundles


def write_csv(records: list[BookRecord]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with CATALOG_CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "serial_number",
                "sort_order",
                "volume_number",
                "title",
                "short_title",
                "major_category",
                "minor_categories",
                "compilation_priority",
                "bookdata_path",
                "text_count",
                "audio_track_count",
                "audio_story_dir_count",
                "video_count",
                "raw_video_count",
                "needs_mp3_conversion",
                "synopsis_len",
                "theme_count",
                "character_count",
                "themes",
                "characters",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    record.sort_order,
                    record.sort_order,
                    record.volume_number or "",
                    record.title,
                    record.short_title,
                    record.major_category,
                    " / ".join(record.minor_categories),
                    record.compilation_priority,
                    record.bookdata_path.relative_to(ROOT).as_posix(),
                    len(record.text_paths),
                    len(record.audio_paths),
                    len(record.audio_story_dirs),
                    len(record.video_paths),
                    len(record.raw_video_paths),
                    (
                        "yes"
                        if record.raw_video_paths and not record.audio_paths
                        else "no"
                    ),
                    len(record.synopsis),
                    len(record.themes),
                    len(record.characters),
                    " / ".join(record.themes),
                    " / ".join(record.characters),
                ]
            )


def write_markdown(records: list[BookRecord], bundles: list[dict[str, Any]]) -> None:
    lines = [
        "# 七之助捕物帳 作品カタログ",
        "",
        f"- 作品数: {len(records)}",
        f"- MP3確認済み作品: {sum(1 for record in records if record.audio_paths)}",
        f"- 動画確認済み作品: {sum(1 for record in records if record.video_paths)}",
        (
            f"- synopsis未整備: "
            f"{sum(1 for record in records if not record.has_synopsis)}"
        ),
        f"- themes未整備: {sum(1 for record in records if not record.has_themes)}",
        "",
        "## 作品一覧",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"### No.{record.sort_order:02d} {record.title}",
                "",
                f"- 通し番号: {record.sort_order:02d}",
                (
                    f"- 巻番号: 第{record.volume_number:02d}巻"
                    if record.volume_number
                    else "- 巻番号: なし"
                ),
                f"- 大分類: {record.major_category}",
                (
                    f"- 小分類: {' / '.join(record.minor_categories)}"
                    if record.minor_categories
                    else "- 小分類: 未設定"
                ),
                f"- 総集編優先度: {record.compilation_priority}",
                f"- bookdata: `{record.bookdata_path.relative_to(ROOT).as_posix()}`",
                f"- 本文: {len(record.text_paths)}件",
                (
                    f"- MP3: {len(record.audio_paths)}件 / 作品フォルダ: "
                    f"{len(record.audio_story_dirs)}件"
                ),
                f"- 動画: {len(record.video_paths)}件",
                f"- synopsis: {'あり' if record.has_synopsis else '未整備'}",
                f"- themes: {' / '.join(record.themes) if record.themes else '未整備'}",
                (
                    f"- characters: "
                    f"{' / '.join(record.characters[:6]) if record.characters else '記載なし'}"
                ),
                "",
            ]
        )
    if bundles:
        lines.extend(["## 3本セット（テーマ）", ""])
        for bundle in bundles:
            lines.append(f"### {bundle['label']}")
            lines.append("")
            for work in bundle.get("works", []):
                hits = ", ".join(work.get("hits", [])) or "-"
                lines.append(f"- {work['title']}（hit: {hits}）")
            lines.append("")
    CATALOG_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_gap_report(records: list[BookRecord]) -> None:
    missing_synopsis = [record for record in records if not record.has_synopsis]
    missing_themes = [record for record in records if not record.has_themes]
    needs_mp3 = [
        record
        for record in records
        if record.raw_video_paths and not record.audio_paths
    ]

    lines = [
        "# 七之助捕物帳 メタデータ改善レポート",
        "",
        f"- synopsis未整備: {len(missing_synopsis)}件",
        f"- themes未整備: {len(missing_themes)}件",
        f"- raw動画あり / mp3未確認: {len(needs_mp3)}件",
        "",
        "## synopsis未整備",
        "",
    ]
    for record in missing_synopsis:
        lines.append(
            f"- {record.title} ({record.bookdata_path.relative_to(ROOT).as_posix()})"
        )
    lines.extend(["", "## themes未整備", ""])
    for record in missing_themes:
        lines.append(
            f"- {record.title} ({record.bookdata_path.relative_to(ROOT).as_posix()})"
        )
    lines.extend(["", "## raw動画あり / mp3未確認", ""])
    if needs_mp3:
        for record in needs_mp3:
            lines.append(f"- {record.title}")
    else:
        lines.append("- 該当なし")
    GAP_REPORT_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_classification_report(records: list[BookRecord]) -> None:
    grouped: dict[str, list[BookRecord]] = defaultdict(list)
    for record in records:
        grouped[record.major_category].append(record)

    lines = [
        "# 七之助捕物帳 分類レポート",
        "",
        f"- 大分類数: {len(grouped)}",
        (
            f"- 高優先総集編候補: "
            f"{sum(1 for r in records if r.compilation_priority == 'high')}件"
        ),
        "",
    ]
    for category in sorted(grouped):
        works = sorted(grouped[category], key=lambda record: record.sort_order)
        lines.append(f"## {category} ({len(works)}件)")
        lines.append("")
        for record in works:
            minors = (
                " / ".join(record.minor_categories) if record.minor_categories else "-"
            )
            lines.append(
                f"- No.{record.sort_order:02d} {record.short_title} "
                f"| 小分類: {minors} | 優先度: {record.compilation_priority}"
            )
        lines.append("")
    CLASSIFICATION_REPORT_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


def build_sequential_bundles(records: list[BookRecord]) -> list[dict[str, Any]]:
    numbered = [record for record in records if record.sort_order < 900]
    bundles: list[dict[str, Any]] = []
    for index in range(0, len(numbered), 3):
        chunk = numbered[index : index + 3]
        if not chunk:
            continue
        start = chunk[0].sort_order
        end = chunk[-1].sort_order
        metadata = build_bundle_metadata(chunk, label_mode="sequential")
        bundles.append(
            {
                "bundle_id": f"sequential-{start:02d}-{end:02d}",
                "label": f"連番3本総集編候補 No.{start:02d}-{end:02d}",
                "source": "sequential",
                **metadata,
                "works": [
                    {
                        "serial_number": record.sort_order,
                        "title": record.title,
                        "short_title": record.short_title,
                        "key": record.key,
                    }
                    for record in chunk
                ],
            }
        )
    return bundles


def bundle_priority_score(record: BookRecord) -> tuple[int, int, int, int, int]:
    priority_map = {"high": 2, "medium": 1, "low": 0}
    return (
        priority_map.get(record.compilation_priority, 0),
        1 if record.audio_paths else 0,
        1 if record.video_paths else 0,
        1 if record.has_synopsis and record.has_themes else 0,
        -record.sort_order,
    )


def bundle_entry(record: BookRecord, hits: list[str]) -> dict[str, Any]:
    return {
        "key": record.key,
        "serial_number": record.sort_order,
        "title": record.title,
        "short_title": record.short_title,
        "hits": hits,
    }


def bundle_top_labels(records: list[BookRecord]) -> tuple[str, str]:
    major = Counter(record.major_category for record in records).most_common(1)[0][0]
    minor_counts = Counter(
        minor for record in records for minor in record.minor_categories
    )
    minor = minor_counts.most_common(1)[0][0] if minor_counts else ""
    return major, minor


def infer_bundle_publication_priority(
    records: list[BookRecord],
) -> tuple[str, str]:
    audio_count = sum(1 for record in records if record.audio_paths)
    ready_count = sum(
        1
        for record in records
        if record.has_synopsis and record.has_themes and record.audio_paths
    )
    high_count = sum(1 for record in records if record.compilation_priority == "high")
    if audio_count == len(records) and ready_count >= 2 and high_count >= 2:
        return "high", "音源が揃い、説明文も整っているため即編成向き"
    if audio_count >= 2 and high_count >= 1:
        return "medium", "素材は概ね揃っており、追加調整で公開可能"
    return "low", "素材またはメタデータ補強後の編成が望ましい"


def build_bundle_metadata(
    records: list[BookRecord],
    *,
    label_mode: str,
    lead_label: str | None = None,
) -> dict[str, Any]:
    major, minor = bundle_top_labels(records)
    priority, reason = infer_bundle_publication_priority(records)
    start = min(record.sort_order for record in records)
    end = max(record.sort_order for record in records)
    if label_mode == "sequential":
        hook = lead_label or major
        recommended_title = f"七之助捕物帳 連番総集編 No.{start:02d}-{end:02d} {hook}編"
    elif label_mode == "minor":
        recommended_title = f"七之助捕物帳 総集編 {lead_label or minor}編"
    else:
        recommended_title = f"七之助捕物帳 総集編 {lead_label or major}編"
    return {
        "work_count": len(records),
        "publication_priority": priority,
        "publication_reason": reason,
        "recommended_title": recommended_title,
        "major_category": major,
        "minor_category": minor,
    }


def build_classification_bundles(records: list[BookRecord]) -> list[dict[str, Any]]:
    bundles: list[dict[str, Any]] = []
    seen_signatures: set[tuple[str, ...]] = set()

    grouped_major: dict[str, list[BookRecord]] = defaultdict(list)
    grouped_minor: dict[str, list[BookRecord]] = defaultdict(list)
    for record in records:
        grouped_major[record.major_category].append(record)
        for minor in record.minor_categories:
            grouped_minor[minor].append(record)

    for major, works in sorted(grouped_major.items()):
        ranked = sorted(works, key=bundle_priority_score, reverse=True)
        if len(ranked) < 3:
            continue
        selected = ranked[:3]
        signature = tuple(sorted(record.key for record in selected))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        top_minors = [
            minor
            for minor, _count in Counter(
                minor for record in selected for minor in record.minor_categories
            ).most_common(2)
        ]
        metadata = build_bundle_metadata(
            selected,
            label_mode="major",
            lead_label=major,
        )
        bundles.append(
            {
                "bundle_id": f"classification-major-{normalize_text(major)}",
                "label": f"分類テーマ総集編 {major}編",
                "source": "classification-major",
                "summary": "大分類を軸にした自動編成候補",
                **metadata,
                "works": [
                    bundle_entry(
                        record,
                        [major, *top_minors[:1]],
                    )
                    for record in selected
                ],
            }
        )

    ranked_minor_groups = sorted(
        grouped_minor.items(),
        key=lambda item: (
            max(bundle_priority_score(record) for record in item[1]),
            len(item[1]),
            item[0],
        ),
        reverse=True,
    )
    for minor, works in ranked_minor_groups:
        ranked = sorted(works, key=bundle_priority_score, reverse=True)
        if len(ranked) < 3:
            continue
        selected = ranked[:3]
        signature = tuple(sorted(record.key for record in selected))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        major = Counter(record.major_category for record in selected).most_common(1)[0][
            0
        ]
        metadata = build_bundle_metadata(
            selected,
            label_mode="minor",
            lead_label=minor,
        )
        bundles.append(
            {
                "bundle_id": f"classification-minor-{normalize_text(minor)}",
                "label": f"分類テーマ総集編 {minor}編",
                "source": "classification-minor",
                "summary": f"小分類「{minor}」中心 / 主軸: {major}",
                **metadata,
                "works": [
                    bundle_entry(record, [minor, record.major_category])
                    for record in selected
                ],
            }
        )
        if (
            len(
                [
                    bundle
                    for bundle in bundles
                    if bundle["source"] == "classification-minor"
                ]
            )
            >= 8
        ):
            break

    bundles.sort(key=lambda bundle: bundle["label"])
    return bundles


def annotate_bundle_candidates(
    bundles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    priority_map = {"high": 2, "medium": 1, "low": 0}
    ranked = sorted(
        bundles,
        key=lambda bundle: (
            priority_map.get(str(bundle.get("publication_priority", "low")), 0),
            int(bundle.get("work_count", 0)),
            str(bundle.get("source", "")),
            str(bundle.get("label", "")),
        ),
        reverse=True,
    )
    primary_signatures: list[set[str]] = []
    annotated: list[dict[str, Any]] = []
    for bundle in ranked:
        signature = {
            str(work.get("key", ""))
            for work in bundle.get("works", [])
            if work.get("key")
        }
        max_overlap = max(
            (len(signature & primary) for primary in primary_signatures),
            default=0,
        )
        if max_overlap >= 2:
            tier = "alternate"
            tier_reason = f"本命候補と{max_overlap}作品重複"
        else:
            tier = "primary"
            tier_reason = "重複が少なく独立した候補"
            if signature:
                primary_signatures.append(signature)
        annotated.append(
            {
                **bundle,
                "candidate_tier": tier,
                "candidate_tier_reason": tier_reason,
                "overlap_with_primary": max_overlap,
            }
        )
    annotated.sort(key=lambda bundle: bundle["label"])
    return annotated


def build_bundle_review_queue(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    works_by_key = {str(work["key"]): work for work in payload.get("works", [])}
    review_items: list[dict[str, Any]] = []
    for bundle_group in ("classification", "sequential"):
        for bundle in payload.get("bundles", {}).get(bundle_group, []):
            review_items.append(
                {
                    "bundle_id": bundle.get("bundle_id"),
                    "bundle_group": bundle_group,
                    "label": bundle.get("label"),
                    "candidate_tier": bundle.get("candidate_tier", "primary"),
                    "candidate_tier_reason": bundle.get("candidate_tier_reason", ""),
                    "publication_priority": bundle.get("publication_priority", "low"),
                    "publication_reason": bundle.get("publication_reason", ""),
                    "recommended_title": bundle.get("recommended_title", ""),
                    "major_category": bundle.get("major_category", ""),
                    "minor_category": bundle.get("minor_category", ""),
                    "summary": bundle.get("summary", ""),
                    "review_prompt": (
                        "この3作品が本当に同一テーマ総集編として自然か、"
                        "themes・synopsis・characters・本文参照先を使って判定してください。"
                        "不自然なら代替方針も提案してください。"
                    ),
                    "works": [
                        {
                            "key": work.get("key"),
                            "serial_number": work.get("serial_number"),
                            "title": source_work.get("title", work.get("title")),
                            "short_title": source_work.get(
                                "short_title", work.get("short_title")
                            ),
                            "synopsis": source_work.get("synopsis", ""),
                            "themes": source_work.get("themes", []),
                            "characters": source_work.get("characters", []),
                            "major_category": source_work.get("major_category", ""),
                            "minor_categories": source_work.get("minor_categories", []),
                            "bookdata_path": source_work.get("bookdata_path", ""),
                            "text_paths": source_work.get("text_paths", []),
                            "audio_paths": source_work.get("audio_paths", []),
                            "video_paths": source_work.get("video_paths", []),
                        }
                        for work in bundle.get("works", [])
                        for source_work in [
                            works_by_key.get(str(work.get("key", "")), {})
                        ]
                    ],
                }
            )
    return review_items


def build_catalog() -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    cache_remote_texts()
    text_paths = scan_media_files_many(TEXT_SOURCE_DIRS, TEXT_EXTS)
    audio_paths = scan_media_files(AUDIO_ROOT, MEDIA_AUDIO_EXTS)
    video_paths = scan_media_files(AUDIO_ROOT, MEDIA_VIDEO_EXTS) + scan_media_files(
        VIDEO_ROOT, MEDIA_VIDEO_EXTS
    )
    volume_mapping = load_volume_mapping()

    records: list[BookRecord] = []
    book_files = collect_book_files()
    if not book_files:
        fallback_payload = load_payload_from_search_html(SEARCH_HTML_PATH)
        prompt_works = load_works_from_review_prompts(REVIEW_PROMPTS_DIR)
        fallback_work_count = (
            len(fallback_payload.get("works", []))
            if fallback_payload and isinstance(fallback_payload.get("works", []), list)
            else 0
        )
        if prompt_works and len(prompt_works) >= fallback_work_count:
            records = rebuild_records_from_existing_payload(
                {"works": prompt_works},
                text_paths,
                audio_paths,
                video_paths,
                volume_mapping,
            )
        elif fallback_payload and fallback_payload.get("works"):
            records = rebuild_records_from_existing_payload(
                fallback_payload, text_paths, audio_paths, video_paths, volume_mapping
            )

    for bookdata_path in book_files:
        data = load_json(bookdata_path)
        title = str(data.get("title", bookdata_path.stem)).strip()
        short_title = extract_short_title(title, bookdata_path)
        canonical = canonical_title(short_title)
        volume_number = extract_volume_number(bookdata_path.stem, title)
        if volume_number is None:
            volume_number = EPISODE_ORDER_HINTS.get(canonical)
        text_aliases = aliases_for_work(
            short_title, canonical, volume_number, include_volume=True
        )
        media_aliases = aliases_for_work(
            short_title, canonical, volume_number, include_volume=False
        )

        matched_texts = filter_valid_text_paths(
            match_paths(text_paths, text_aliases, minimum_score=2)
        )
        mapped_text = volume_mapping.get(volume_number or -1)
        if (
            mapped_text
            and mapped_text.exists()
            and mapped_text not in matched_texts
            and inspect_text_path(mapped_text.as_posix())["valid"]
        ):
            matched_texts.insert(0, mapped_text)

        matched_audio = match_paths(audio_paths, media_aliases, minimum_score=4)
        matched_videos = match_paths(video_paths, media_aliases, minimum_score=4)
        raw_videos = [
            path
            for path in matched_videos
            if str(path).startswith(VIDEO_ROOT.as_posix())
        ]
        audio_story_dirs = dedupe_story_dirs(matched_audio)

        themes = split_list(data.get("themes", []))
        keywords = split_list(data.get("keywords", []))
        characters = [
            str(item.get("name", "")).strip()
            for item in data.get("characters", [])
            if isinstance(item, dict) and str(item.get("name", "")).strip()
        ]
        chapters = data.get("chapters", [])
        synopsis = str(data.get("synopsis", "") or "").strip()
        major_category = str(data.get("major_category", "") or "").strip()
        if not major_category:
            major_category = infer_major_category(title, synopsis, themes)
        minor_categories = split_list(data.get("minor_categories", []))
        if not minor_categories:
            minor_categories = infer_minor_categories(
                title,
                synopsis,
                themes,
                major_category,
            )
        compilation_priority = str(data.get("compilation_priority", "") or "").strip()
        if not compilation_priority:
            compilation_priority = infer_compilation_priority(
                has_audio=bool(matched_audio),
                has_video=bool(matched_videos),
                has_synopsis=bool(synopsis),
                has_themes=bool(themes),
            )
        compilation_notes = str(data.get("compilation_notes", "") or "").strip()
        if not compilation_notes:
            compilation_notes = infer_compilation_notes(
                major_category,
                minor_categories,
                len(chapters) if isinstance(chapters, list) else 0,
            )
        sort_order = volume_number or EPISODE_ORDER_HINTS.get(
            canonical, 900 + len(records)
        )
        key = f"{sort_order:03d}:{normalize_text(canonical)}"
        search_text = "\n".join(
            [
                title,
                short_title,
                canonical,
                synopsis,
                " / ".join(themes),
                major_category,
                " / ".join(minor_categories),
                compilation_priority,
                " / ".join(keywords),
                " / ".join(characters),
                " / ".join(path.name for path in matched_texts),
                " / ".join(path.name for path in matched_audio),
                " / ".join(path.name for path in matched_videos),
            ]
        )

        records.append(
            BookRecord(
                key=key,
                title=title,
                short_title=short_title,
                canonical_title=canonical,
                sort_order=sort_order,
                volume_number=volume_number,
                author=str(data.get("author", "")).strip(),
                synopsis=synopsis,
                themes=themes,
                keywords=keywords,
                characters=characters,
                major_category=major_category,
                minor_categories=minor_categories,
                compilation_priority=compilation_priority,
                compilation_notes=compilation_notes,
                chapter_count=len(chapters) if isinstance(chapters, list) else 0,
                has_synopsis=bool(synopsis),
                has_themes=bool(themes),
                bookdata_path=bookdata_path,
                text_paths=matched_texts,
                audio_paths=matched_audio,
                video_paths=matched_videos,
                raw_video_paths=raw_videos,
                audio_story_dirs=audio_story_dirs,
                search_text=search_text,
            )
        )

    records.sort(key=lambda record: (record.sort_order, record.title))
    theme_bundles = load_theme_bundles(THEME_MD_PATH)
    content_theme_bundles = load_theme_bundles(THEME_CONTENT_MD_PATH)
    sequential_bundles = annotate_bundle_candidates(build_sequential_bundles(records))
    classification_bundles = annotate_bundle_candidates(
        build_classification_bundles(records)
    )
    bundle_groups = {
        "theme": theme_bundles,
        "theme_content": content_theme_bundles,
        "classification": classification_bundles,
        "sequential": sequential_bundles,
    }
    adopted_bundles = resolve_adopted_bundles(
        bundle_groups,
        load_adopted_bundle_state(),
    )

    payload = {
        "generated_at": __import__("datetime")
        .datetime.now()
        .isoformat(timespec="seconds"),
        "source_paths": {
            "bookdata_dir": BOOKDATA_DIR.as_posix(),
            "text_dir": TEXT_DIR.as_posix(),
            "text_dirs": [path.as_posix() for path in TEXT_SOURCE_DIRS if path.exists()],
            "audio_root": AUDIO_ROOT.as_posix(),
            "video_root": VIDEO_ROOT.as_posix(),
        },
        "stats": {
            "works": len(records),
            "with_text": sum(1 for record in records if record.text_paths),
            "with_audio": sum(1 for record in records if record.audio_paths),
            "with_video": sum(1 for record in records if record.video_paths),
            "missing_synopsis": sum(1 for record in records if not record.has_synopsis),
            "missing_themes": sum(1 for record in records if not record.has_themes),
            "needs_mp3": sum(
                1
                for record in records
                if record.raw_video_paths and not record.audio_paths
            ),
        },
        "works": [
            {
                "key": record.key,
                "serial_number": record.sort_order,
                "sort_order": record.sort_order,
                "volume_number": record.volume_number,
                "title": record.title,
                "short_title": record.short_title,
                "canonical_title": record.canonical_title,
                "author": record.author,
                "synopsis": record.synopsis,
                "themes": record.themes,
                "keywords": record.keywords,
                "characters": record.characters,
                "major_category": record.major_category,
                "minor_categories": record.minor_categories,
                "compilation_priority": record.compilation_priority,
                "compilation_notes": record.compilation_notes,
                "chapter_count": record.chapter_count,
                "has_synopsis": record.has_synopsis,
                "has_themes": record.has_themes,
                "bookdata_path": record.bookdata_path.relative_to(ROOT).as_posix(),
                "text_paths": [path.as_posix() for path in record.text_paths],
                "audio_paths": [path.as_posix() for path in record.audio_paths],
                "video_paths": [path.as_posix() for path in record.video_paths],
                "raw_video_paths": [path.as_posix() for path in record.raw_video_paths],
                "audio_story_dirs": [
                    path.as_posix() for path in record.audio_story_dirs
                ],
                "needs_mp3_conversion": bool(
                    record.raw_video_paths and not record.audio_paths
                ),
                "search_text": record.search_text,
            }
            for record in records
        ],
        "bundles": bundle_groups,
        "adopted_bundles": adopted_bundles,
    }
    return payload


def write_catalog_reports(payload: dict[str, Any]) -> None:
    records = [
        BookRecord(
            key=work["key"],
            title=work["title"],
            short_title=work["short_title"],
            canonical_title=work["canonical_title"],
            sort_order=int(work["sort_order"]),
            volume_number=work["volume_number"],
            author=work["author"],
            synopsis=work["synopsis"],
            themes=list(work["themes"]),
            keywords=list(work["keywords"]),
            characters=list(work["characters"]),
            major_category=work.get("major_category", "未分類"),
            minor_categories=list(work.get("minor_categories", [])),
            compilation_priority=work.get("compilation_priority", "low"),
            compilation_notes=work.get("compilation_notes", ""),
            chapter_count=int(work["chapter_count"]),
            has_synopsis=bool(work["has_synopsis"]),
            has_themes=bool(work["has_themes"]),
            bookdata_path=ROOT / work["bookdata_path"],
            text_paths=[Path(path) for path in work["text_paths"]],
            audio_paths=[Path(path) for path in work["audio_paths"]],
            video_paths=[Path(path) for path in work["video_paths"]],
            raw_video_paths=[Path(path) for path in work["raw_video_paths"]],
            audio_story_dirs=[Path(path) for path in work["audio_story_dirs"]],
            search_text=work["search_text"],
        )
        for work in payload["works"]
    ]
    CATALOG_JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_csv(records)
    theme_like_bundles = (
        list(payload["bundles"].get("classification", []))
        + list(payload["bundles"].get("theme_content", []))
        + list(payload["bundles"].get("theme", []))
    )
    write_markdown(records, theme_like_bundles)
    write_gap_report(records)
    write_classification_report(records)
    BUNDLE_REVIEW_QUEUE_PATH.write_text(
        json.dumps(
            build_bundle_review_queue(payload),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    payload = build_catalog()
    write_catalog_reports(payload)
    print(f"Wrote: {CATALOG_JSON_PATH.relative_to(ROOT)}")
    print(f"Wrote: {CATALOG_CSV_PATH.relative_to(ROOT)}")
    print(f"Wrote: {CATALOG_MD_PATH.relative_to(ROOT)}")
    print(f"Wrote: {GAP_REPORT_MD_PATH.relative_to(ROOT)}")
    print(f"Wrote: {CLASSIFICATION_REPORT_MD_PATH.relative_to(ROOT)}")
    print(f"Wrote: {BUNDLE_REVIEW_QUEUE_PATH.relative_to(ROOT)}")
    print(f"Works: {payload['stats']['works']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
