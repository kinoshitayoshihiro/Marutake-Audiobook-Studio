#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import Counter
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
READING_DIR = ROOT / "Reading_library" / "吉川英治"
AOZORA_DIR = READING_DIR / "青空文庫"
LIBRARY_PATHS = [ROOT / "marutake_library-01.csv", ROOT / "marutake_library.csv"]
SHORT_CANDIDATE_PATH = (
    ROOT
    / "youtube_channel_report"
    / "old_channel_report"
    / "youtube_video_report_last_90_days_short_candidate.csv"
)
OUT_CSV = REPORTS_DIR / "yoshikawa_works_catalog.csv"
OUT_MD = REPORTS_DIR / "yoshikawa_works_catalog.md"

SERIES_TITLES = {
    "新書太閤記",
    "宮本武蔵",
    "鳴門秘帖",
    "江戸城心中",
    "新編忠臣蔵",
    "篝火の女",
    "剣の四君子 小野忠明",
    "剣の四君子 柳生石舟斎",
}

NORMALIZATION_NOTES = {
    "新書太閤記": "回次・巻次・章題違い・総集編系を統合",
    "宮本武蔵": "巻名・前後編・巻番号違いを統合",
    "鳴門秘帖": "幕・巻違いを統合",
    "江戸城心中": "其の一・其の二・其の四・後篇を統合",
    "新編忠臣蔵": "第一夜-第四夜・後編を統合",
    "篝火の女": "前篇・後篇を統合",
    "剣の四君子 小野忠明": "前編・後編を統合",
    "剣の四君子 柳生石舟斎": "上・下を統合",
}


@dataclass
class WorkRow:
    title: str
    work_type: str
    video_count: int
    raw_title_variant_count: int
    first_published: str
    last_published: str
    primary_genre: str
    primary_era: str
    report_priority: str
    has_local_text: str
    local_text_count: int
    local_text_paths: str
    representative_clean_titles: str
    normalization_note: str


def normalize_title(title: str) -> str | None:
    text = " ".join((title or "").split())
    if not text:
        return None
    if "新書太閤記" in text or ("第七十三話" in text and "堺町人" in text):
        return "新書太閤記"
    if "新編忠臣蔵" in text:
        return "新編忠臣蔵"
    if "宮本武蔵" in text:
        return "宮本武蔵"
    if "鳴門秘帖" in text:
        return "鳴門秘帖"
    if "江戸城心中" in text:
        return "江戸城心中"
    if "篝火の女" in text:
        return "篝火の女"
    if "剣の四君子" in text and "小野忠明" in text:
        return "剣の四君子 小野忠明"
    if "剣の四君子" in text and "林崎甚助" in text:
        return "剣の四君子 林崎甚助"
    if "剣の四君子" in text and "高橋泥舟" in text:
        return "剣の四君子 高橋泥舟"
    if "剣の四君子" in text and any(
        key in text for key in ["柳生石舟", "柳生石舟齊", "柳生石舟齋"]
    ):
        return "剣の四君子 柳生石舟斎"
    if "／" in text or "総集編" in text:
        return None
    return text


def normalize_local_text_title(raw_title: str) -> str | None:
    text = (raw_title or "").strip()
    if not text:
        return None
    if text.startswith("吉川英治_"):
        text = text[len("吉川英治_") :]
    text = text.replace("_", " ")
    return normalize_title(text)


def load_library_rows() -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for path in LIBRARY_PATHS:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                if row.get("Author") != "吉川英治":
                    continue
                clean_title = (row.get("CleanTitle") or "").strip()
                if not clean_title:
                    continue
                youtube_id = (row.get("YoutubeID") or "").strip()
                key = youtube_id or "|".join(
                    [
                        row.get("Title", "").strip(),
                        row.get("Published", "").strip(),
                        clean_title,
                    ]
                )
                deduped[key] = row
    return list(deduped.values())


def detect_local_texts() -> dict[str, list[str]]:
    matches: dict[str, list[str]] = defaultdict(list)
    if not READING_DIR.exists():
        return matches
    for path in sorted(READING_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".txt", ".py"}:
            continue

        normalized = None
        try:
            relative = path.relative_to(AOZORA_DIR)
        except ValueError:
            relative = None

        if relative and len(relative.parts) >= 2:
            normalized = normalize_local_text_title(relative.parts[0])
        else:
            normalized = normalize_local_text_title(path.stem)

        if normalized is None:
            continue
        matches[normalized].append(path.relative_to(ROOT).as_posix())
    return matches


def load_report_priority_titles() -> set[str]:
    if not SHORT_CANDIDATE_PATH.exists():
        return set()
    priorities: set[str] = set()
    with SHORT_CANDIDATE_PATH.open(encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("🌱") or "吉川英治" not in line:
                continue
            title = line.lstrip("🌱").strip()
            title = title.replace("吉川英治", "").strip()
            normalized = normalize_title(title)
            if normalized:
                priorities.add(normalized)
    return priorities


def most_common_value(counter: Counter[str]) -> str:
    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def build_work_rows() -> list[WorkRow]:
    rows = load_library_rows()
    local_texts = detect_local_texts()
    report_priorities = load_report_priority_titles()

    buckets: dict[str, dict[str, object]] = {}
    for row in rows:
        normalized = normalize_title((row.get("CleanTitle") or "").strip())
        if not normalized:
            continue
        bucket = buckets.setdefault(
            normalized,
            {
                "video_count": 0,
                "raw_titles": Counter(),
                "published_dates": [],
                "genres": Counter(),
                "eras": Counter(),
            },
        )
        bucket["video_count"] += 1
        bucket["raw_titles"][(row.get("CleanTitle") or "").strip()] += 1
        published = (row.get("Published") or "").strip()
        if published:
            bucket["published_dates"].append(published)
        genre = (row.get("Genre") or "").split(",")[0].strip()
        if genre:
            bucket["genres"][genre] += 1
        era = (row.get("Era") or "").strip()
        if era:
            bucket["eras"][era] += 1

    work_rows: list[WorkRow] = []
    for title, payload in buckets.items():
        raw_titles: Counter[str] = payload["raw_titles"]
        published_dates: list[str] = sorted(payload["published_dates"])
        text_paths = local_texts.get(title, [])
        representative_titles = [
            raw_title
            for raw_title, _ in sorted(raw_titles.items(), key=lambda item: (-item[1], item[0]))[:5]
        ]
        work_rows.append(
            WorkRow(
                title=title,
                work_type="シリーズ" if title in SERIES_TITLES else "単発",
                video_count=int(payload["video_count"]),
                raw_title_variant_count=len(raw_titles),
                first_published=published_dates[0] if published_dates else "",
                last_published=published_dates[-1] if published_dates else "",
                primary_genre=most_common_value(payload["genres"]),
                primary_era=most_common_value(payload["eras"]),
                report_priority="yes" if title in report_priorities else "no",
                has_local_text="yes" if text_paths else "no",
                local_text_count=len(text_paths),
                local_text_paths=" | ".join(text_paths),
                representative_clean_titles=" | ".join(representative_titles),
                normalization_note=NORMALIZATION_NOTES.get(title, ""),
            )
        )

    work_rows.sort(key=lambda item: (-item.video_count, item.title))
    return work_rows


def write_csv(work_rows: list[WorkRow]) -> None:
    fieldnames = [
        "sort_order",
        "title",
        "work_type",
        "video_count",
        "raw_title_variant_count",
        "first_published",
        "last_published",
        "primary_genre",
        "primary_era",
        "report_priority",
        "has_local_text",
        "local_text_count",
        "local_text_paths",
        "representative_clean_titles",
        "normalization_note",
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(work_rows, start=1):
            writer.writerow(
                {
                    "sort_order": index,
                    "title": row.title,
                    "work_type": row.work_type,
                    "video_count": row.video_count,
                    "raw_title_variant_count": row.raw_title_variant_count,
                    "first_published": row.first_published,
                    "last_published": row.last_published,
                    "primary_genre": row.primary_genre,
                    "primary_era": row.primary_era,
                    "report_priority": row.report_priority,
                    "has_local_text": row.has_local_text,
                    "local_text_count": row.local_text_count,
                    "local_text_paths": row.local_text_paths,
                    "representative_clean_titles": row.representative_clean_titles,
                    "normalization_note": row.normalization_note,
                }
            )


def write_markdown(work_rows: list[WorkRow]) -> None:
    series_rows = [row for row in work_rows if row.work_type == "シリーズ"]
    standalone_rows = [row for row in work_rows if row.work_type == "単発"]
    local_text_rows = [row for row in work_rows if row.has_local_text == "yes"]
    priority_rows = [row for row in work_rows if row.report_priority == "yes"]

    lines = [
        "# 吉川英治 作品カタログ",
        "",
        "既存のチャンネル掲載履歴とローカル本文を突き合わせて作成。",
        "",
        "## 概況",
        "",
        f"- 総作品数: {len(work_rows)}",
        f"- シリーズ作品: {len(series_rows)}",
        f"- 単発作品: {len(standalone_rows)}",
        f"- ローカル本文あり: {len(local_text_rows)}",
        f"- 短尺候補レポート掲載あり: {len(priority_rows)}",
        f"- 集計元CSV: {', '.join(path.name for path in LIBRARY_PATHS)}",
        "",
        "## レポート優先候補",
        "",
    ]

    if priority_rows:
        for row in priority_rows:
            lines.append(f"- {row.title}: 動画{row.video_count}件")
    else:
        lines.append("- 該当なし")

    lines.extend([
        "",
        "## 詳細一覧",
        "",
    ])

    for index, row in enumerate(work_rows, start=1):
        lines.extend(
            [
                f"### No.{index:02d} {row.title}",
                "",
                f"- 種別: {row.work_type}",
                f"- 動画数: {row.video_count}",
                f"- CleanTitle派生数: {row.raw_title_variant_count}",
                f"- 投稿日: {row.first_published} - {row.last_published}" if row.first_published else "- 投稿日: 不明",
                f"- 主ジャンル: {row.primary_genre or '不明'}",
                f"- 主時代: {row.primary_era or '不明'}",
                f"- ローカル本文: {row.local_text_count}件" if row.has_local_text == "yes" else "- ローカル本文: なし",
            ]
        )
        if row.local_text_paths:
            lines.append(f"- ローカル本文パス: {row.local_text_paths}")
        lines.append(
            f"- 短尺候補レポート: {'あり' if row.report_priority == 'yes' else 'なし'}"
        )
        if row.representative_clean_titles:
            lines.append(f"- 代表表記: {row.representative_clean_titles}")
        if row.normalization_note:
            lines.append(f"- 正規化メモ: {row.normalization_note}")
        lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    work_rows = build_work_rows()
    write_csv(work_rows)
    write_markdown(work_rows)
    print(f"wrote {OUT_CSV}")
    print(f"wrote {OUT_MD}")
    print(f"works={len(work_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())