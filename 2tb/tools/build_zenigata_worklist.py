#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import io
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"

CHRONOLOGY_CSV_CANDIDATES = [
    REPORTS_DIR / "zenigata_heiji_chronology.csv",
    ROOT / "data" / "zenigata_heiji_chronology.csv",
]

AUDIO_ARCHIVE_DIRS = [
    Path(
        os.environ.get(
            "ZENIGATA_AUDIO_ARCHIVE_DIR",
            "/Users/kinoshitayoshihiro/Library/CloudStorage/"
            "GoogleDrive-shimogami88@gmail.com/マイドライブ/"
            "AudioBook/3.野村胡堂/銭形平次捕物控",
        )
    ).expanduser(),
    Path("/Volumes/SSD-PUTA - Data/AudioBook/02_銭形平次捕物控").expanduser(),
]

CSV_SOURCES = [
    ROOT / "marutake_library.csv",
    ROOT / "marutake_library-01.csv",
]

READING_DIRS = [
    ROOT / "Reading_library" / "銭形平次捕物控",
    ROOT / "Reading_library" / "野村胡堂" / "銭形平次捕物控",
]

BOOKDATA_GLOBS = [
    ROOT / "bookdata" / "3_nomura",
]

META_GLOBS = [
    ROOT / "tools",
]

SERIES_NAME = "銭形平次捕物控"

TITLE_ALIASES = {
    "yuudachi no onna": "夕立の女",
    "八五郎の戀": "八五郎の恋",
    "八五郎の戀人": "八五郎の恋人",
    "北冥の魚": "北溟の魚",
    "妹の扱帶": "妹の扱帯",
    "お珊文身調べ": "お珊文身調べ",
    "長篇幽霊大名": "幽霊大名",
    "金色の乙女": "金色の処女",
    "お部屋様お退屈 最終話 十": "お部屋様お退屈",
    "乞食ころし": "乞食殺し",
    "人魚の死": "人女の死",
    "八五郎の恋人": "八五郎恋人",
    "出世街道 中篇": "出世街道",
    "出世街道 後篇": "出世街道",
    "十一人の娘": "娘十一人",
    "女護の島異変": "女護島異変",
    "娘の役目": "娘の役割",
    "密室の鍵を破るは、香の匂い 銭形平次捕物控 六軒長屋": "六軒長屋",
    "巾着切の娘": "巾着切りの娘",
    "怪盗系図1": "怪盗系図",
    "敵討果てて": "仇討果てて",
    "歎きの菩薩": "嘆きの菩薩",
    "殺され半蔵": "殺された半蔵",
    "猿回し": "猿廻し",
    "玉の輿の呪": "玉の輿の呪い",
    "美女をあらいだす": "美女を洗い出す",
    "艶妻傳": "艶妻伝",
    "花見の仇討ち": "花見の仇討",
    "金の鯉(銭形平次捕物控より)": "金の鯉",
    "長篇「地獄の門 完結!": "地獄の門",
    "長篇地獄の門 完結!": "地獄の門",
}

EXCLUDED_WORK_TITLES = {
    "テーマソング七選",
    "人情感涙編 六篇",
}

STOP_TAGS = {
    SERIES_NAME,
    "銭形平次",
    "野村胡堂",
    "江戸",
    "捕物帳",
    "岡っ引き",
    "投げ銭",
    "時代小説",
    "時代劇",
    "朗読",
    "七味春五郎",
    "丸竹書房",
}

PERSON_LIKE_PATTERNS = [
    re.compile(r"^(銭形平次|平次|八五郎|ガラッ八|お静|笹野新三郎)$"),
    re.compile(r"^お[一-龥々ぁ-ん]{1,4}$"),
    re.compile(
        r"^[一-龥々]{1,4}(?:之助|之丞|兵衛|右衛門|左衛門|新三郎|五郎|三郎|太郎|四郎|吉|助|作|蔵)$"
    ),
    re.compile(r"^[一-龥々]{2,6}$"),
]

THEME_RULES = [
    (
        "怪異・妖異",
        [
            "幽霊",
            "怪",
            "怪談",
            "呪",
            "妖",
            "霊薬",
            "人魚",
            "からくり",
            "忍術",
            "怪盗系図",
            "無間の鐘",
            "幽沢",
            "菩薩",
        ],
    ),
    (
        "復讐・因果",
        [
            "復讐",
            "仇",
            "因果",
            "罪",
            "怨",
            "祟",
            "呪い",
            "報い",
            "群盗",
            "名馬罪あり",
        ],
    ),
    (
        "恋愛・嫉妬",
        [
            "恋",
            "艶",
            "女難",
            "花嫁",
            "娘",
            "若衆",
            "妻",
            "美男",
            "お局",
            "女御用聞き",
            "八五郎の恋",
            "八五郎の恋人",
            "夕立の女",
            "金色の処女",
        ],
    ),
    (
        "人情・家族",
        [
            "父",
            "母",
            "親子",
            "巡礼",
            "子守",
            "妹",
            "娘の役目",
            "金の茶釜",
            "遠眼鏡の殿様",
            "雪の夜",
            "権八の罪",
        ],
    ),
    (
        "盗賊・悪党",
        [
            "盗",
            "賊",
            "巾着切",
            "掏摸",
            "怪盗",
            "巨盗",
            "猿回し",
            "群盗",
            "乞食ころし",
            "怪盗系図",
        ],
    ),
    (
        "謎解き・トリック",
        [
            "謎",
            "秘密",
            "密室",
            "文銭",
            "手紙",
            "遺書",
            "足跡",
            "からくり",
            "秤座",
            "一枚の文銭",
            "二本の脇差",
            "永楽銭",
            "独り芝居",
            "凧の糸目",
            "風呂場の秘密",
        ],
    ),
    (
        "大店・家督・金",
        [
            "千両",
            "十万両",
            "富籤",
            "金",
            "茶釜",
            "家督",
            "玉の輿",
            "千両箱",
            "路地の小判",
            "濡れた千両箱",
            "十万両の行方",
        ],
    ),
    (
        "八五郎活躍",
        [
            "八五郎",
            "ガラッ八",
            "祝言",
            "恋人",
            "女難",
            "八五郎の恋",
            "八五郎の恋人",
            "ガラッ八祝言",
            "八五郎女難",
        ],
    ),
    (
        "長編・冒険",
        [
            "長編",
            "御殿",
            "大名",
            "幽霊大名",
            "江戸の恋人たち",
            "お部屋様お退屈",
            "金色の処女",
            "無間の鐘",
        ],
    ),
]


@dataclass
class Work:
    title: str
    titles_seen: set[str] = field(default_factory=set)
    source_paths: set[str] = field(default_factory=set)
    video_ids: set[str] = field(default_factory=set)
    channel_titles: set[str] = field(default_factory=set)
    genres: set[str] = field(default_factory=set)
    moods: set[str] = field(default_factory=set)
    keywords: list[str] = field(default_factory=list)
    keyword_counter: Counter[str] = field(default_factory=Counter)
    summary: str = ""
    synopsis: str = ""
    characters: list[str] = field(default_factory=list)
    lineage: str = ""
    theme_secondary: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    has_local_text: bool = False
    has_bookdata: bool = False
    has_meta: bool = False
    has_channel_entry: bool = False
    has_audio_archive: bool = False
    aozora_like_source: bool = False
    published_dates: set[str] = field(default_factory=set)
    publication_years: set[str] = field(default_factory=set)
    magazines: set[str] = field(default_factory=set)
    chronology_ordinals: set[str] = field(default_factory=set)
    audio_archive_files: set[str] = field(default_factory=set)
    audio_archive_dirs: set[str] = field(default_factory=set)
    audio_segment_keys: set[str] = field(default_factory=set)
    audio_recording_years: set[str] = field(default_factory=set)
    audio_derivative_count: int = 0
    audio_duplicate_candidates: int = 0


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def normalize_spaces(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[\s\u3000]+", " ", text).strip()


def canonicalize_title(text: str) -> str:
    title = normalize_spaces(text)
    if re.fullmatch(r"江戸の恋人たち(?: [0-9一二三四五六七八九十]+)?", title):
        return "江戸の恋人達"
    if re.fullmatch(
        r"無間の鐘(?: [0-9一二三四五六七八九十]+(?: ?\(最終回\))?)?",
        title,
    ):
        return "無間の鐘"
    if title in {"春宵 第一回", "春宵 第二回", "春宵 第三回(終)"}:
        return "春宵"
    if title in {"春宵(銭形平次捕物控より)", "春宵第一回"}:
        return "春宵"
    return TITLE_ALIASES.get(title, title)


def display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def clean_episode_title(text: str) -> str:
    text = normalize_spaces(text)
    text = text.replace("＼", " ").replace("／", "/")
    text = text.replace("_", " ")
    text = text.replace("『", "").replace("』", "")
    text = text.replace("「", "").replace("」", "")
    text = text.lstrip("_-")
    text = re.sub(r"^野村胡堂[著作]*[\s　]*", "", text)
    text = re.sub(r"^錢形平次捕物控[\s　]*", "", text)
    text = re.sub(r"^銭形平次捕物控[\s　]*", "", text)
    text = re.sub(r"^銭形平次捕物控ショートショート三遍$", "ショートショート三遍", text)
    text = re.sub(r"^[【\[『「]", "", text)
    text = re.sub(r"[】\]』」]$", "", text)
    text = re.sub(
        r"^(長編連載|長編朗読まとめ|長編朗読|中編|前編|後編)[\s　]*", "", text
    )
    text = re.sub(r"^第\s*\d+話[\s　]*", "", text)
    text = re.sub(r"^その\s*\d+[\s　]*", "", text)
    text = re.sub(r"[\s　]*[（(]?(前編|中編|後編)[)）]?$", "", text)
    text = re.sub(r"[\s　]*[（(]?(前篇|中篇|後篇)[)）]?$", "", text)
    text = re.sub(r"[\s　]*第[一二三四五六七八九十\d]+話$", "", text)
    text = re.sub(r"[\s　]*その[一二三四五六七八九十\d]+$", "", text)
    text = re.sub(
        r"[\s　]*(第一回|第二回|第三回\(終\)|第四回|第五回|第六回|第七回)$",
        "",
        text,
    )
    text = re.sub(
        r"[\s　]*[一二三四五六七八九十\d]+[\s　]*\(最終回\)$",
        "",
        text,
    )
    text = re.sub(r"[\s　]*最終話[\s　]*[一二三四五六七八九十\d]+$", "", text)
    text = re.sub(r"[\s　]+", " ", text).strip(" '　『「【")
    return canonicalize_title(text)


def split_possible_compilation(title: str) -> list[str]:
    if "/" not in title:
        return [title]
    parts = [clean_episode_title(p) for p in title.split("/") if clean_episode_title(p)]
    if len(parts) >= 2:
        return parts
    return [title]


def derive_title_from_filename(path: Path) -> list[str]:
    stem = path.stem
    stem = stem.replace(".txt", "")
    stem = stem.replace(".tex", "")
    stem = normalize_spaces(stem)
    stem = re.sub(r"[\s　]*野村胡堂$", "", stem)
    stem = re.sub(r"[\s　]*野村胡堂著$", "", stem)
    stem = re.sub(r"^野村胡堂[著作]*[\s　]*", "", stem)
    titles = split_possible_compilation(clean_episode_title(stem))
    return [canonicalize_title(t) for t in titles if t and t != SERIES_NAME]


def strip_audio_extensions(name: str) -> str:
    name = re.sub(r"\.mp3(?:\.wbm)?$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\.wbm$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\.mp4$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\.m4a$", "", name, flags=re.IGNORECASE)
    return name


def infer_audio_recording_years(path: Path) -> set[str]:
    years = {
        match.group(1)
        for match in re.finditer(r"(?<!\d)(20\d{2})(?!\d)", path.as_posix())
    }
    if years:
        return years
    try:
        stat_year = str(datetime.fromtimestamp(path.stat().st_mtime).year)
    except OSError:
        return set()
    if re.fullmatch(r"20\d{2}", stat_year):
        return {stat_year}
    return set()


def parse_audio_title_and_segment(name: str) -> tuple[str, str, bool]:
    raw = normalize_spaces(strip_audio_extensions(name).replace("　", " "))
    raw = re.sub(r"^\d+[\s_-]+", "", raw)
    raw = re.sub(r"^(openingcredit|endingcredit)[\s_-]*", "", raw, flags=re.I)
    raw = re.sub(r"\s+(special|voice)でノイズ$", "", raw)
    match = re.match(
        r"^(.*?)(?:\s+(前編|中編|後編))?(?:\s+(\d+))(?:\s+(\d+))?$",
        raw,
    )
    if match:
        title_part, part_label, segment_no, duplicate_variant = match.groups()
        segment_key = " ".join(x for x in (part_label, segment_no) if x)
        title = clean_episode_title(title_part)
        return title, segment_key or "full", bool(duplicate_variant)
    title = clean_episode_title(raw)
    return title, "full", False


def should_ingest_local_text(path: Path, known_titles: set[str]) -> bool:
    name = normalize_spaces(path.stem)
    if any(token in name for token in ("銭形平次", "錢形平次")):
        return True
    derived_titles = derive_title_from_filename(path)
    return any(title in known_titles for title in derived_titles)


def read_text_best_effort(path: Path) -> str:
    for enc in ("utf-8", "cp932", "shift_jis", "utf-8-sig"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="ignore")


def looks_like_person(term: str) -> bool:
    term = term.strip()
    if not term or term in STOP_TAGS:
        return False
    if any(ch in term for ch in "・()（）／/"):
        return False
    for pat in PERSON_LIKE_PATTERNS:
        if pat.match(term):
            return True
    return False


def extract_name_candidates(text: str, top_n: int = 8) -> list[str]:
    if not text:
        return []
    pattern = (
        r"銭形平次|八五郎|ガラッ八|お静|笹野新三郎|"
        r"お[一-龥々ぁ-ん]{1,4}|"
        r"[一-龥々]{1,4}(?:之助|之丞|兵衛|右衛門|左衛門|"
        r"新三郎|五郎|三郎|太郎|四郎)"
    )
    candidates = re.findall(pattern, text)
    counter = Counter(candidates)
    ordered = [name for name, _ in counter.most_common() if looks_like_person(name)]
    unique: list[str] = []
    for name in ordered:
        if name not in unique:
            unique.append(name)
        if len(unique) >= top_n:
            break
    return unique


def merge_keywords(work: Work, items: list[str]) -> None:
    for item in items:
        value = normalize_spaces(str(item))
        if not value:
            continue
        work.keyword_counter[value] += 1


def choose_longer(current: str, new_value: str) -> str:
    if not new_value:
        return current
    if not current:
        return new_value
    return new_value if len(new_value) > len(current) else current


def get_or_create(catalog: dict[str, Work], title: str) -> Work:
    title = canonicalize_title(title)
    if title not in catalog:
        catalog[title] = Work(title=title)
    return catalog[title]


def ingest_csv(catalog: dict[str, Work], path: Path) -> None:
    if not path.exists():
        return
    raw = path.read_bytes()
    text = ""
    used_encoding = "utf-8"
    for encoding in ("utf-8", "utf-8-sig", "cp932", "shift_jis", "euc_jp"):
        try:
            text = raw.decode(encoding)
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = raw.decode("utf-8", errors="replace")
        used_encoding = "utf-8-replace"
    nul_count = text.count("\x00")
    if nul_count:
        text = text.replace("\x00", "")
        print(f"Warning: {path.name} contained {nul_count} NUL bytes; removed during catalog build")
    if "�" in text:
        print(f"Warning: {path.name} decoded with replacement characters via {used_encoding}")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    for row in reader:
            author = normalize_spaces(row.get("Author", ""))
            raw_title = row.get("Title", "")
            clean_title = row.get("CleanTitle", "")
            joined = f"{raw_title} {clean_title}"
            if author != "野村胡堂":
                continue
            seed_titles = {"金色の処女", "夕立の女", "凧の糸目", "腰抜け弥八"}
            if "銭形平次" not in joined and clean_title.strip() not in seed_titles:
                continue

            normalized_title = clean_episode_title(clean_title or raw_title)
            source_titles = split_possible_compilation(normalized_title)
            for title in source_titles:
                if not title or title in {SERIES_NAME, "ショートショート三遍"}:
                    continue
                work = get_or_create(catalog, title)
                work.has_channel_entry = True
                work.titles_seen.add(clean_title or raw_title)
                work.channel_titles.add(normalize_spaces(raw_title))
                work.video_ids.add(normalize_spaces(row.get("YoutubeID", "")))
                published = normalize_spaces(row.get("Published", ""))
                work.published_dates.add(published)
                work.genres.add(normalize_spaces(row.get("Genre", "")))
                work.moods.add(normalize_spaces(row.get("Mood", "")))
                keywords = [x.strip() for x in str(row.get("Keywords", "")).split(",")]
                merge_keywords(work, keywords)
                summary = normalize_spaces(row.get("Summary", ""))
                work.summary = choose_longer(work.summary, summary)
                work.source_paths.add(display_path(path))


def ingest_bookdata(catalog: dict[str, Work], path: Path) -> None:
    data = load_json(path)
    if not isinstance(data, dict):
        return
    raw_title = normalize_spaces(str(data.get("title", path.stem)))
    title = clean_episode_title(raw_title)
    work = get_or_create(catalog, title)
    work.has_bookdata = True
    work.titles_seen.add(raw_title)
    synopsis = normalize_spaces(str(data.get("synopsis", "")))
    setting = normalize_spaces(str(data.get("setting", "")))
    work.synopsis = choose_longer(work.synopsis, synopsis)
    work.summary = choose_longer(work.summary, setting)
    keywords = [str(x) for x in data.get("keywords", []) if str(x).strip()]
    merge_keywords(work, keywords)
    work.genres.add(normalize_spaces(str(data.get("japanese_genre", ""))))
    work.genres.add(normalize_spaces(str(data.get("sub_genre", ""))))
    for item in data.get("themes", []):
        value = normalize_spaces(str(item))
        if value:
            work.theme_secondary.append(value)
    chars = []
    for item in data.get("characters", []):
        if isinstance(item, dict):
            name = normalize_spaces(str(item.get("name", "")))
            if name:
                chars.append(name)
    if chars:
        work.characters = chars
    work.source_paths.add(display_path(path))


def ingest_meta(catalog: dict[str, Work], path: Path) -> None:
    data = load_json(path)
    if not isinstance(data, dict):
        return
    fallback_title = path.stem.replace("meta_zenigata_", "")
    raw_title = normalize_spaces(str(data.get("title", fallback_title)))
    title = clean_episode_title(raw_title)
    work = get_or_create(catalog, title)
    work.has_meta = True
    work.titles_seen.add(raw_title)
    synopsis = normalize_spaces(str(data.get("synopsis", "")))
    setting = normalize_spaces(str(data.get("setting", "")))
    work.synopsis = choose_longer(work.synopsis, synopsis)
    work.summary = choose_longer(work.summary, setting)
    keywords = [str(x) for x in data.get("keywords", []) if str(x).strip()]
    merge_keywords(work, keywords)
    chars = []
    for item in data.get("characters", []):
        if isinstance(item, dict):
            name = normalize_spaces(str(item.get("name", "")))
            if name:
                chars.append(name)
    if chars:
        work.characters = chars
    work.source_paths.add(display_path(path))


def ingest_local_texts(catalog: dict[str, Work], path: Path) -> None:
    titles = derive_title_from_filename(path)
    if not titles:
        return
    text = read_text_best_effort(path)
    candidates = extract_name_candidates(text)
    for title in titles:
        work = get_or_create(catalog, title)
        work.has_local_text = True
        work.aozora_like_source = True
        work.source_paths.add(display_path(path))
        work.titles_seen.add(path.stem)
        if not work.characters and candidates:
            work.characters = candidates


def ingest_chronology(catalog: dict[str, Work], path: Path) -> None:
    if not path.exists() or path.suffix.lower() != ".csv":
        return
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_title = (
                row.get("title")
                or row.get("作品名")
                or row.get("name")
                or row.get("題名")
                or ""
            )
            title = clean_episode_title(str(raw_title))
            if not title:
                continue
            work = get_or_create(catalog, title)
            year = normalize_spaces(
                str(
                    row.get("publication_year")
                    or row.get("year")
                    or row.get("発表年")
                    or row.get("年")
                    or ""
                )
            )
            magazine = normalize_spaces(
                str(
                    row.get("magazine")
                    or row.get("掲載誌")
                    or row.get("雑誌")
                    or row.get("初出")
                    or ""
                )
            )
            ordinal = normalize_spaces(
                str(
                    row.get("order_no")
                    or row.get("order")
                    or row.get("番号")
                    or row.get("通番")
                    or ""
                )
            )
            if year:
                work.publication_years.add(year)
            if magazine:
                work.magazines.add(magazine)
            if ordinal:
                work.chronology_ordinals.add(ordinal)
            work.source_paths.add(display_path(path))


def ingest_audio_archive(
    catalog: dict[str, Work], directory: Path, known_titles: set[str]
) -> None:
    if not directory.exists():
        return
    for path in sorted(directory.rglob("*")):
        if path.is_dir() or path.name.startswith("."):
            continue
        lower_name = path.name.lower()
        if not (
            lower_name.endswith(".mp3")
            or lower_name.endswith(".mp3.wbm")
            or lower_name.endswith(".mp4")
            or lower_name.endswith(".m4a")
            or lower_name.endswith(".wbm")
        ):
            continue
        title, segment_key, duplicate_variant = parse_audio_title_and_segment(path.name)
        if not title or title in {"手本", SERIES_NAME}:
            continue
        if title not in known_titles:
            continue
        work = get_or_create(catalog, title)
        work.has_audio_archive = True
        work.audio_archive_files.add(path.name)
        work.audio_archive_dirs.add(display_path(path.parent))
        work.audio_recording_years.update(infer_audio_recording_years(path))
        if lower_name.endswith(".wbm"):
            work.audio_derivative_count += 1
        if segment_key:
            work.audio_segment_keys.add(segment_key)


def find_chronology_source() -> Path | None:
    for path in CHRONOLOGY_CSV_CANDIDATES:
        if path.exists():
            return path
    return None
    return None


def classify_lineage(work: Work) -> tuple[str, list[str]]:
    core_parts = [work.title, work.synopsis, work.summary, " / ".join(work.characters)]
    core_joined = "\n".join(x for x in core_parts if x).lower()
    keyword_joined = "\n".join(str(x) for x in work.keyword_counter.keys() if x).lower()
    scores: list[tuple[int, str, list[str]]] = []
    for label, patterns in THEME_RULES:
        target_text = (
            core_joined
            if label == "八五郎活躍"
            else "\n".join(part for part in (core_joined, keyword_joined) if part)
        )
        hits = [p for p in patterns if p.lower() in target_text]
        scores.append((len(hits), label, hits))
    scores.sort(key=lambda x: (-x[0], x[1]))
    best_score, best_label, best_hits = scores[0]
    if best_score == 0:
        best_label = "事件のどんでん返し"
        best_hits = []
    secondary = [label for score, label, _ in scores[1:] if score > 0][:2]
    return best_label, secondary or best_hits[:2]


def finalize_work(work: Work) -> None:
    if not work.characters:
        chars = [
            kw for kw, _ in work.keyword_counter.most_common() if looks_like_person(kw)
        ]
        work.characters = chars[:6]

    if not work.synopsis:
        work.synopsis = work.summary

    lineage, secondary = classify_lineage(work)
    work.lineage = lineage
    if secondary:
        normalized_secondary = [
            normalize_spaces(str(x)) for x in secondary if normalize_spaces(str(x))
        ]
        seen: set[str] = set()
        deduped_secondary: list[str] = []
        for item in normalized_secondary:
            if item in seen:
                continue
            seen.add(item)
            deduped_secondary.append(item)
        work.theme_secondary = deduped_secondary[:3]

    tags = []
    for kw, _ in work.keyword_counter.most_common():
        clean_kw = normalize_spaces(kw)
        if not clean_kw or clean_kw in STOP_TAGS:
            continue
        if clean_kw == work.title:
            continue
        tags.append(clean_kw)
        if len(tags) >= 8:
            break
    if work.lineage and work.lineage not in tags:
        tags.insert(0, work.lineage)
    work.tags = tags[:8]

    if work.has_audio_archive:
        work.audio_duplicate_candidates = max(
            0,
            len(work.audio_archive_files)
            - len(work.audio_segment_keys)
            - work.audio_derivative_count,
        )


def build_catalog() -> dict[str, Work]:
    catalog: dict[str, Work] = {}

    for csv_path in CSV_SOURCES:
        ingest_csv(catalog, csv_path)

    for base in BOOKDATA_GLOBS:
        for path in sorted(base.glob("銭形平次捕物控_*.json")):
            ingest_bookdata(catalog, path)

    for base in META_GLOBS:
        for path in sorted(base.glob("meta_zenigata*.json")):
            ingest_meta(catalog, path)

    chronology_source = find_chronology_source()
    if chronology_source is not None:
        ingest_chronology(catalog, chronology_source)

    for directory in READING_DIRS:
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_dir():
                continue
            allowed_suffixes = {".txt", ".tex", ".py", ".vjm", ".vrew"}
            if path.suffix.lower() not in allowed_suffixes:
                continue
            if not should_ingest_local_text(path, set(catalog.keys())):
                continue
            ingest_local_texts(catalog, path)

    known_titles = set(catalog.keys())
    for directory in AUDIO_ARCHIVE_DIRS:
        ingest_audio_archive(catalog, directory, known_titles)

    filtered = {
        title: work
        for title, work in catalog.items()
        if title
        and title not in {SERIES_NAME, "ショートショート三遍"}
        and title not in EXCLUDED_WORK_TITLES
        and not title.startswith("総集編")
    }

    for work in filtered.values():
        finalize_work(work)
    return filtered


def bundle_title_for_theme(theme: str) -> str:
    mapping = {
        "怪異・妖異": "怪異と闇の江戸編",
        "復讐・因果": "因果が返る三事件編",
        "恋愛・嫉妬": "恋と嫉妬の捕物編",
        "人情・家族": "人情と親子の涙編",
        "盗賊・悪党": "盗賊と悪党追跡編",
        "謎解き・トリック": "謎解き三番勝負編",
        "大店・家督・金": "大店と大金の闇編",
        "八五郎活躍": "八五郎大活躍編",
        "長編・冒険": "長編冒険ベスト3編",
    }
    return mapping.get(theme, f"{theme}総集編")


def build_theme_bundles(works: list[Work]) -> list[dict[str, Any]]:
    by_theme: dict[str, list[Work]] = defaultdict(list)
    for work in works:
        if work.synopsis:
            by_theme[work.lineage].append(work)

    bundles: list[dict[str, Any]] = []
    sorted_themes = sorted(by_theme.items(), key=lambda x: (-len(x[1]), x[0]))
    for theme, items in sorted_themes:
        if len(items) < 3:
            continue
        items = sorted(
            items,
            key=lambda w: (
                not w.has_local_text,
                not w.has_bookdata,
                not w.has_channel_entry,
                w.title,
            ),
        )
        picked = items[:3]
        hook = " / ".join(w.title for w in picked)
        bundles.append(
            {
                "theme": theme,
                "bundle_title": bundle_title_for_theme(theme),
                "works": picked,
                "hook": hook,
            }
        )
    return bundles


def write_csv(works: list[Work], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "title",
                "story_lineage",
                "theme_secondary",
                "tags",
                "characters",
                "synopsis",
                "summary",
                "has_local_text",
                "has_bookdata",
                "has_meta",
                "has_channel_entry",
                "has_audio_archive",
                "audio_file_count",
                "audio_segment_count",
                "audio_recording_years",
                "audio_archive_dirs",
                "audio_derivative_count",
                "audio_duplicate_candidates",
                "publication_years",
                "magazines",
                "chronology_ordinals",
                "source_paths",
                "published_dates",
                "channel_titles",
            ]
        )
        for work in works:
            writer.writerow(
                [
                    work.title,
                    work.lineage,
                    " / ".join(work.theme_secondary),
                    " / ".join(work.tags),
                    " / ".join(work.characters),
                    work.synopsis,
                    work.summary,
                    "yes" if work.has_local_text else "no",
                    "yes" if work.has_bookdata else "no",
                    "yes" if work.has_meta else "no",
                    "yes" if work.has_channel_entry else "no",
                    "yes" if work.has_audio_archive else "no",
                    len(work.audio_archive_files),
                    len(work.audio_segment_keys),
                    " | ".join(sorted(work.audio_recording_years)),
                    " | ".join(sorted(work.audio_archive_dirs)),
                    work.audio_derivative_count,
                    work.audio_duplicate_candidates,
                    " | ".join(sorted(work.publication_years)),
                    " | ".join(sorted(work.magazines)),
                    " | ".join(sorted(work.chronology_ordinals)),
                    " | ".join(sorted(work.source_paths)),
                    " | ".join(sorted(x for x in work.published_dates if x)),
                    " | ".join(sorted(work.channel_titles)),
                ]
            )


def write_audio_inventory_csv(works: list[Work], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "title",
                "audio_file_count",
                "audio_segment_count",
                "audio_recording_years",
                "audio_archive_dirs",
                "audio_derivative_count",
                "audio_duplicate_candidates",
                "has_channel_entry",
                "has_local_text",
                "published_dates",
                "channel_titles",
            ]
        )
        for work in works:
            if not work.has_audio_archive:
                continue
            writer.writerow(
                [
                    work.title,
                    len(work.audio_archive_files),
                    len(work.audio_segment_keys),
                    " | ".join(sorted(work.audio_recording_years)),
                    " | ".join(sorted(work.audio_archive_dirs)),
                    work.audio_derivative_count,
                    work.audio_duplicate_candidates,
                    "yes" if work.has_channel_entry else "no",
                    "yes" if work.has_local_text else "no",
                    " | ".join(sorted(x for x in work.published_dates if x)),
                    " | ".join(sorted(work.channel_titles)),
                ]
            )


def write_markdown(
    works: list[Work], bundles: list[dict[str, Any]], out_path: Path
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# 銭形平次捕物控 作品一覧（拡張版）")
    lines.append("")
    lines.append("既存のローカル本文・既存bookdata・チャンネルCSVを突き合わせて作成。")
    lines.append("")
    lines.append("## 概況")
    lines.append("")
    lines.append(f"- 総作品数: {len(works)}")
    lines.append(f"- ローカル本文あり: {sum(1 for w in works if w.has_local_text)}")
    lines.append(f"- 詳細bookdataあり: {sum(1 for w in works if w.has_bookdata)}")
    lines.append(f"- 追加メタあり: {sum(1 for w in works if w.has_meta)}")
    channel_count = sum(1 for w in works if w.has_channel_entry)
    lines.append(f"- チャンネル掲載履歴あり: {channel_count}")
    audio_count = sum(1 for w in works if w.has_audio_archive)
    lines.append(f"- 外部音声アーカイブあり: {audio_count}")
    chronology_count = sum(1 for w in works if w.publication_years or w.magazines)
    lines.append(f"- 年表データあり: {chronology_count}")
    lines.append("")
    lines.append("## 総集編テーマ案")
    lines.append("")
    for bundle in bundles:
        lines.append(f"### {bundle['bundle_title']}")
        lines.append("")
        lines.append(f"- 軸: {bundle['theme']}")
        lines.append(f"- 候補3本: {bundle['hook']}")
        for work in bundle["works"]:
            short_synopsis = work.synopsis[:100]
            if len(work.synopsis) > 100:
                short_synopsis += "…"
            lines.append(f"- {work.title}: {short_synopsis}")
        lines.append("")

    lines.append("## 詳細一覧")
    lines.append("")
    for work in works:
        lines.append(f"### {work.title}")
        lines.append("")
        lines.append(f"- 系統: {work.lineage}")
        if work.theme_secondary:
            lines.append(f"- 補助テーマ: {' / '.join(work.theme_secondary)}")
        if work.tags:
            lines.append(f"- タグ: {' / '.join(work.tags)}")
        if work.characters:
            lines.append(f"- 登場人物: {' / '.join(work.characters)}")
        if work.synopsis:
            lines.append(f"- あらすじ: {work.synopsis}")
        availability = []
        if work.has_local_text:
            availability.append("ローカル本文あり")
        if work.has_bookdata:
            availability.append("bookdataあり")
        if work.has_meta:
            availability.append("追加メタあり")
        if work.has_channel_entry:
            availability.append("チャンネル履歴あり")
        if availability:
            lines.append(f"- 利用可能性: {' / '.join(availability)}")
        if work.has_audio_archive:
            lines.append(
                "- 音声保管: "
                f"媒体{len(work.audio_archive_files)}件 / "
                f"セグメント{len(work.audio_segment_keys)}件 / "
                f"派生{work.audio_derivative_count}件 / "
                f"重複候補{work.audio_duplicate_candidates}件"
            )
        if work.publication_years or work.magazines:
            year_text = " / ".join(sorted(work.publication_years)) or "年不明"
            magazine_text = " / ".join(sorted(work.magazines))
            if magazine_text:
                lines.append(f"- 初出: {year_text} / {magazine_text}")
            else:
                lines.append(f"- 初出: {year_text}")
        if work.channel_titles:
            related_titles = " | ".join(sorted(work.channel_titles)[:3])
            lines.append(f"- 関連動画題名: {related_titles}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    catalog = build_catalog()
    works = sorted(
        catalog.values(),
        key=lambda w: (
            not w.has_local_text,
            not w.has_bookdata,
            w.title,
        ),
    )
    bundles = build_theme_bundles(works)

    csv_path = REPORTS_DIR / "zenigata_heiji_works_catalog.csv"
    md_path = REPORTS_DIR / "zenigata_heiji_works_catalog.md"
    audio_csv_path = REPORTS_DIR / "zenigata_heiji_audio_inventory.csv"
    write_csv(works, csv_path)
    write_markdown(works, bundles, md_path)
    write_audio_inventory_csv(works, audio_csv_path)

    print(f"Wrote: {csv_path.relative_to(ROOT)}")
    print(f"Wrote: {md_path.relative_to(ROOT)}")
    print(f"Wrote: {audio_csv_path.relative_to(ROOT)}")
    print(f"Works: {len(works)}")
    print(f"Bundles: {len(bundles)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
