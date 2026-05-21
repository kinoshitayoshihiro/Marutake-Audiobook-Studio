#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: E501

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from html import escape
from pathlib import Path

from shichinosuke_catalog_builder_impl import (
    CATALOG_JSON_PATH,
    ROOT,
    build_catalog,
  load_adopted_bundle_state,
  resolve_adopted_bundles,
    write_catalog_reports,
)

OUT_PATH = ROOT / "reports" / "shichinosuke_search.html"
OLD_CHANNEL_ALL_VIDEOS_PATH = (
    ROOT
    / "youtube_channel_report"
    / "old_channel_report"
    / "youtube_video_report_last_90_days_all_videos.csv"
)
SEED_SHORTWORKS_PATH = ROOT / "reports" / "shichinosuke_seed_shortworks.csv"

SHICHINOSUKE_VIDEO_TITLE_NOISE = (
    "七之助捕物帳",
    "納言恭平著",
    "ナレーター七味春五郎",
    "朗読",
    "朗読時代劇",
    "朗読一人でドラマ",
    "毎週火曜夜八時は",
    "発行元丸竹書房",
    "七味春五郎",
    "作業用",
    "睡眠用",
    "睡眠",
    "bgm",
    "ハイライト",
    "紹介",
    "最終話",
)
SHICHINOSUKE_VARIANT_MAP = {
    "生きている小町娘": "生きていた小町娘",
    "夢の首つり": "夢の首吊り",
    "蛇の目の女": "蛇の眼の女",
    "人食い花": "人喰い花",
    "仇討ち幽霊": "仇討幽霊",
    "鳥追いお巻": "鳥追お巻",
    "お高祖頭巾の女": "お高祖頭巾",
    "水野深川": "水の深川",
    "射的競べの怪": "射的競べの怪",
}


def parse_int(value: object) -> int:
    try:
        return int(float(str(value or "").strip()))
    except (TypeError, ValueError):
        return 0


def parse_float(value: object) -> float:
    try:
        return float(str(value or "").strip())
    except (TypeError, ValueError):
        return 0.0


def normalize_shichinosuke_title(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"第[一二三四五六七八九十百0-9]+巻", " ", text)
    text = re.sub(r"第[一二三四五六七八九十百0-9]+話", " ", text)
    text = re.sub(r"[『「【](.*?)[』」】]", r" \1 ", text)
    for source, target in SHICHINOSUKE_VARIANT_MAP.items():
        text = text.replace(source, target)
    lowered = text.lower()
    for marker in SHICHINOSUKE_VIDEO_TITLE_NOISE:
        lowered = lowered.replace(marker.lower(), " ")
    lowered = re.sub(r"[｜|／/・「」『』【】（）()、。!！,:：\-_　\s]+", "", lowered)
    return lowered


def candidate_names_for_work(work: dict) -> list[str]:
    values = [
        str(work.get("title", "")).strip(),
        str(work.get("short_title", "")).strip(),
        str(work.get("canonical_title", "")).strip(),
    ]
    normalized: list[str] = []
    for value in values:
        if not value:
            continue
        cleaned = normalize_shichinosuke_title(value)
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    for source, target in SHICHINOSUKE_VARIANT_MAP.items():
        canonical = str(work.get("canonical_title", "")).strip()
        short = str(work.get("short_title", "")).strip()
        if canonical in {source, target} or short in {source, target}:
            alt = normalize_shichinosuke_title(source)
            if alt and alt not in normalized:
                normalized.append(alt)
    return normalized


def load_youtube_seed_report(payload: dict) -> dict:
    if SEED_SHORTWORKS_PATH.exists():
        with SEED_SHORTWORKS_PATH.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            entries = []
            for row in reader:
                clean = {
                    str(key).replace("\ufeff", "").strip(): value
                    for key, value in row.items()
                }
                if not str(clean.get("work_key", "")).strip():
                    continue
                entries.append(
                    {
                        "rank": parse_int(clean.get("rank")),
                        "work_key": str(clean.get("work_key", "")).strip(),
                        "title": str(clean.get("title", "")).strip(),
                        "short_title": str(clean.get("short_title", "")).strip(),
                        "published_at": str(clean.get("published_at", "")).strip(),
                        "channel_title": str(clean.get("channel_title", "")).strip(),
                        "duration_seconds": parse_int(clean.get("duration_seconds")),
                        "views": parse_int(clean.get("views")),
                        "estimated_minutes_watched": parse_int(
                            clean.get("estimated_minutes_watched")
                        ),
                        "average_view_duration_seconds": parse_int(
                            clean.get("average_view_duration_seconds")
                        ),
                        "score": parse_float(clean.get("score")),
                        "major_category": str(clean.get("major_category", "")).strip(),
                        "has_text": str(clean.get("has_text", "")).strip()
                        in {"yes", "true", "1"},
                        "has_audio": str(clean.get("has_audio", "")).strip()
                        in {"yes", "true", "1"},
                        "privacy": str(clean.get("privacy", "")).strip(),
                    }
                )
        return {
            "generated_at": datetime.fromtimestamp(
                SEED_SHORTWORKS_PATH.stat().st_mtime
            ).isoformat(timespec="seconds"),
            "entries": entries,
        }

    works = payload.get("works", [])
    if not OLD_CHANNEL_ALL_VIDEOS_PATH.exists():
        return {"generated_at": "", "entries": []}
    work_name_map: dict[str, dict] = {}
    for work in works:
        for name in candidate_names_for_work(work):
            work_name_map.setdefault(name, work)

    entries: list[dict] = []
    seen_keys: set[str] = set()
    with OLD_CHANNEL_ALL_VIDEOS_PATH.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            title = str(row.get("title", "")).strip()
            if "七之助" not in title:
                continue
            normalized_title = normalize_shichinosuke_title(title)
            if not normalized_title:
                continue
            matched_work = None
            for key, work in work_name_map.items():
                if key and (key in normalized_title or normalized_title in key):
                    matched_work = work
                    break
            if not matched_work:
                continue
            duration_seconds = parse_int(row.get("duration_seconds"))
            if duration_seconds <= 180 or duration_seconds > 5400:
                continue
            if any(
                marker in title
                for marker in ("総集編", "主題歌", "睡眠", "作業用", "ハイライト", "紹介")
            ):
                continue
            work_key = str(matched_work.get("key", "")).strip()
            if not work_key or work_key in seen_keys:
                continue
            views = parse_int(row.get("views"))
            avg_duration = parse_int(row.get("averageViewDuration"))
            estimated_minutes = parse_int(row.get("estimatedMinutesWatched"))
            score = views * 0.45 + avg_duration * 1.2 + estimated_minutes * 0.08
            entries.append(
                {
                    "work_key": work_key,
                    "title": str(matched_work.get("title", "")).strip(),
                    "short_title": str(matched_work.get("short_title", "")).strip(),
                    "published_at": str(row.get("publishedAt", "")).strip(),
                    "channel_title": title,
                    "duration_seconds": duration_seconds,
                    "views": views,
                    "average_view_duration_seconds": avg_duration,
                    "estimated_minutes_watched": estimated_minutes,
                    "privacy": (
                        "public"
                        if str(row.get("is_public", "")).strip().lower() == "true"
                        else "private"
                        if str(row.get("is_private", "")).strip().lower() == "true"
                        else "other"
                    ),
                    "score": round(score, 3),
                    "major_category": str(matched_work.get("major_category", "")).strip(),
                    "has_text": bool(matched_work.get("text_paths")),
                    "has_audio": bool(matched_work.get("audio_paths")),
                }
            )
            seen_keys.add(work_key)

    entries.sort(
        key=lambda entry: (
            -float(entry.get("score", 0)),
            -int(entry.get("views", 0)),
            str(entry.get("short_title", "")),
        )
    )
    for index, entry in enumerate(entries, start=1):
        entry["rank"] = index
    return {
        "generated_at": datetime.fromtimestamp(
            OLD_CHANNEL_ALL_VIDEOS_PATH.stat().st_mtime
        ).isoformat(timespec="seconds"),
        "entries": entries[:12],
    }


def render_html(payload: dict) -> str:
    data_json = json.dumps(payload, ensure_ascii=False)
    workspace_root = json.dumps(ROOT.as_posix(), ensure_ascii=False)
    generated_at = escape(
        payload.get("generated_at", datetime.now().isoformat(timespec="seconds"))
    )
    stats = payload.get("stats", {})
    title = "七之助捕物帳 検索・3本総集編アプリ"
    return f"""<!DOCTYPE html>
<html lang=\"ja\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{escape(title)}</title>
<style>
:root {{
  --bg: #0f172a;
  --panel: rgba(15, 23, 42, 0.78);
  --panel-2: rgba(30, 41, 59, 0.82);
  --panel-3: rgba(51, 65, 85, 0.34);
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #22c55e;
  --accent-2: #38bdf8;
  --accent-3: #f97316;
  --warn: #f59e0b;
  --danger: #f87171;
  --border: rgba(148, 163, 184, 0.2);
  --shadow: 0 24px 60px rgba(2, 8, 23, 0.45);
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: "Hiragino Sans", "Yu Gothic", sans-serif;
  background:
    radial-gradient(circle at top left, rgba(56, 189, 248, 0.18), transparent 28%),
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.16), transparent 24%),
    linear-gradient(180deg, #111827 0%, #0f172a 46%, #020617 100%);
  color: var(--text);
}}
a {{ color: #93c5fd; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.container {{ max-width: 1480px; margin: 0 auto; padding: 28px; }}
.hero {{ display: grid; grid-template-columns: 1.7fr 1fr; gap: 18px; margin-bottom: 18px; }}
.panel {{
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 20px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(14px);
}}
.hero-main {{ padding: 26px; }}
.hero h1 {{ margin: 0 0 10px; font-size: 34px; line-height: 1.15; font-family: "Hiragino Mincho ProN", "Yu Mincho", serif; letter-spacing: 0.03em; }}
.hero p {{ margin: 0; color: var(--muted); line-height: 1.65; }}
.stats {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; padding: 18px; }}
.stat {{ background: var(--panel-2); border-radius: 16px; padding: 16px; border: 1px solid var(--border); }}
.stat strong {{ display: block; font-size: 28px; margin-bottom: 4px; }}
.stat span {{ color: var(--muted); font-size: 13px; }}
.controls {{ padding: 18px; margin-bottom: 18px; position: sticky; top: 0; z-index: 5; }}
.review-controls {{ padding: 18px; margin-bottom: 18px; }}
.mode-controls {{ padding: 18px; margin-bottom: 18px; }}
.bundle-controls {{ padding: 18px; margin-bottom: 18px; }}
.grid {{ display: grid; gap: 12px; }}
.control-grid {{ grid-template-columns: 2fr repeat(5, minmax(0, 1fr)) 1.2fr; }}
.search-note {{ margin-top: 10px; color: var(--muted); font-size: 12px; }}
.insight-grid {{ display: grid; grid-template-columns: 1.35fr 1fr; gap: 18px; margin-bottom: 18px; }}
.insight-panel {{ padding: 18px; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.summary-card {{ border-radius: 16px; padding: 14px; background: linear-gradient(180deg, rgba(15, 23, 42, 0.82), rgba(30, 41, 59, 0.88)); border: 1px solid var(--border); }}
.summary-card strong {{ display: block; font-size: 22px; margin-bottom: 6px; }}
.summary-card span {{ color: var(--muted); font-size: 12px; }}
.chip-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.chip {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  border: 1px solid rgba(125, 211, 252, 0.2);
  background: rgba(8, 47, 73, 0.46);
  color: #dbeafe;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.2;
}}
.chip.button {{
  cursor: pointer;
  background: linear-gradient(135deg, rgba(14, 116, 144, 0.9), rgba(30, 64, 175, 0.86));
}}
.chip.button[data-chip="gaps"] {{
  background: linear-gradient(135deg, rgba(194, 65, 12, 0.88), rgba(180, 83, 9, 0.88));
}}
.chip.empty {{
  border-style: dashed;
  background: rgba(51, 65, 85, 0.25);
  color: var(--muted);
}}
.mode-switch {{ display: flex; flex-wrap: wrap; gap: 10px; }}
.mode-button.active, .view-button.active {{ background: linear-gradient(135deg, #0f766e, #0891b2); }}
.mode-summary {{ color: var(--muted); font-size: 13px; margin-top: 10px; }}
.section-toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
.section-toolbar .meta {{ white-space: nowrap; }}
.mode-section {{ display: none; }}
.mode-section.active {{ display: block; }}
input, select, button {{
  width: 100%;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.9);
  color: var(--text);
  padding: 12px 14px;
  font-size: 14px;
}}
button {{ cursor: pointer; background: linear-gradient(135deg, #2563eb, #0891b2); border: none; font-weight: 700; }}
button.secondary {{ background: rgba(51, 65, 85, 0.85); border: 1px solid var(--border); }}
.layout {{ display: grid; grid-template-columns: 1.4fr 1fr; gap: 18px; align-items: start; }}
.section {{ padding: 18px; }}
.section h2 {{ margin: 0 0 14px; font-size: 22px; }}
.section-header {{ display:flex; justify-content: space-between; gap: 10px; align-items: baseline; margin-bottom: 14px; }}
.section-header .meta {{ color: var(--muted); font-size: 13px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 14px; }}
.cards.simple {{ grid-template-columns: 1fr; }}
.card {{ background: var(--panel-2); border: 1px solid var(--border); border-radius: 18px; padding: 16px; }}
.card h3 {{ margin: 0 0 8px; font-size: 20px; line-height: 1.35; }}
.card.selected, .bundle.selected {{ border-color: rgba(56, 189, 248, 0.55); box-shadow: inset 0 0 0 1px rgba(56, 189, 248, 0.28); }}
.simple-work {{ background: var(--panel-2); border: 1px solid var(--border); border-radius: 16px; padding: 14px 16px; display: grid; gap: 8px; }}
.simple-work-main {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; align-items: baseline; }}
.simple-work-title {{ font-size: 17px; font-weight: 700; color: var(--text); }}
.simple-work-meta {{ color: var(--muted); font-size: 13px; }}
.meta-line {{ color: var(--muted); font-size: 13px; margin-bottom: 10px; }}
.meta-line strong {{ color: #e0f2fe; font-weight: 600; }}
.badges {{ display:flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }}
.badge {{ font-size: 12px; padding: 6px 10px; border-radius: 999px; background: rgba(59, 130, 246, 0.16); color: #bfdbfe; border: 1px solid rgba(59, 130, 246, 0.24); }}
.badge.warn {{ background: rgba(245, 158, 11, 0.14); color: #fcd34d; border-color: rgba(245, 158, 11, 0.24); }}
.badge.ok {{ background: rgba(34, 197, 94, 0.14); color: #86efac; border-color: rgba(34, 197, 94, 0.24); }}
.badge.danger {{ background: rgba(248, 113, 113, 0.14); color: #fecaca; border-color: rgba(248, 113, 113, 0.24); }}
.synopsis {{ color: #dbeafe; line-height: 1.6; font-size: 14px; }}
.links {{ display:flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }}
.links a {{ font-size: 13px; color: #c4b5fd; }}
.list {{ display: grid; gap: 12px; }}
.adopted-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 14px; }}
.adopted-card {{ display: grid; gap: 10px; }}
.seed-controls-grid {{ display: grid; grid-template-columns: 1.2fr repeat(3, minmax(0, 1fr)); gap: 10px; }}
.seed-summary-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }}
.youtube-seed-list {{ display: grid; gap: 12px; margin-bottom: 14px; }}
.youtube-seed-card {{ background: var(--panel-2); border: 1px solid var(--border); border-radius: 18px; padding: 16px; display: grid; gap: 10px; }}
.youtube-seed-head {{ display: flex; justify-content: space-between; gap: 10px; align-items: flex-start; }}
.youtube-seed-rank {{ font-size: 22px; font-weight: 700; color: #f0abfc; }}
.youtube-seed-score {{ color: var(--muted); font-size: 12px; text-align: right; white-space: nowrap; }}
.youtube-seed-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.youtube-seed-metric {{ border-radius: 14px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.66); padding: 10px 12px; }}
.youtube-seed-metric strong {{ display: block; font-size: 13px; margin-bottom: 4px; color: #e0f2fe; }}
.seed-list {{ display: grid; gap: 12px; }}
.seed-card {{ background: var(--panel-2); border: 1px solid var(--border); border-radius: 18px; padding: 16px; display: grid; gap: 10px; }}
.seed-card.good {{ border-color: rgba(34, 197, 94, 0.45); }}
.seed-card h3 {{ margin: 0; font-size: 18px; line-height: 1.4; }}
.seed-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
.seed-meta-box {{ border-radius: 14px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.66); padding: 10px 12px; }}
.seed-meta-box strong {{ display: block; font-size: 13px; margin-bottom: 4px; color: #e0f2fe; }}
.seed-actions {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.seed-empty {{ border: 1px dashed var(--border); border-radius: 16px; padding: 18px; color: var(--muted); background: rgba(15, 23, 42, 0.42); }}
.checkline {{ display: flex; align-items: center; gap: 8px; border-radius: 12px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.9); padding: 12px 14px; font-size: 13px; color: var(--muted); }}
.checkline input {{ width: 18px; height: 18px; margin: 0; padding: 0; accent-color: #22c55e; }}
.seed-review-tools {{ display: grid; gap: 10px; margin: 14px 0; }}
.adopted-title {{ font-size: 22px; line-height: 1.35; margin: 0; }}
.adopted-subtitle {{ color: #dbeafe; font-size: 14px; line-height: 1.5; }}
.adopted-origin {{ color: var(--muted); font-size: 12px; }}
.adopted-work-list {{ display: grid; gap: 8px; }}
.adopted-work-item {{ border-radius: 12px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.7); padding: 10px 12px; }}
.bundle {{ background: var(--panel-2); border: 1px solid var(--border); border-radius: 18px; padding: 16px; }}
.bundle h3 {{ margin: 0 0 8px; font-size: 18px; }}
.bundle ul {{ margin: 10px 0 0; padding-left: 18px; color: var(--text); }}
.bundle li {{ margin: 6px 0; }}
.bundle-header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
.bundle-meta-strip {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; margin: 12px 0; }}
.bundle-meta-card {{ border: 1px solid var(--border); border-radius: 14px; background: rgba(15, 23, 42, 0.66); padding: 10px 12px; }}
.bundle-meta-card strong {{ display: block; font-size: 13px; margin-bottom: 4px; color: #e0f2fe; }}
.bundle-meta-card span {{ color: var(--muted); font-size: 12px; line-height: 1.45; }}
.bundle-work-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }}
.bundle-work-card {{ border-radius: 14px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.76); padding: 12px; display: grid; gap: 8px; }}
.bundle-work-card h4 {{ margin: 0; font-size: 15px; line-height: 1.45; }}
.bundle-work-card .small {{ line-height: 1.5; }}
.bundle-select {{ display: flex; align-items: center; gap: 8px; white-space: nowrap; font-size: 13px; color: var(--muted); }}
.bundle-select input {{ width: 18px; height: 18px; padding: 0; accent-color: #38bdf8; }}
.bundle-actions {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
.action-btn {{ width: auto; padding: 8px 12px; font-size: 12px; border-radius: 10px; }}
.action-link {{ display: inline-flex; align-items: center; padding: 8px 12px; border-radius: 10px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.9); color: var(--text); text-decoration: none; font-size: 12px; }}
.bundle.adopted {{ border-color: rgba(34, 197, 94, 0.52); box-shadow: inset 0 0 0 1px rgba(34, 197, 94, 0.24), 0 0 0 1px rgba(34, 197, 94, 0.08); }}
.review-grid {{ display: grid; grid-template-columns: 1.3fr 1fr; gap: 14px; align-items: start; }}
.review-meta {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
.review-stat {{ background: var(--panel-2); border-radius: 14px; padding: 14px; border: 1px solid var(--border); }}
.review-stat strong {{ display: block; font-size: 22px; margin-bottom: 4px; }}
.review-stat span {{ color: var(--muted); font-size: 12px; }}
.review-actions {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }}
.command-box, .selection-box {{
  width: 100%;
  min-height: 120px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.92);
  color: var(--text);
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
}}
.review-guide {{
  border: 1px solid var(--border);
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.9);
  padding: 12px 14px;
}}
.queue-editor {{
  width: 100%;
  min-height: 120px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(15, 23, 42, 0.92);
  color: var(--text);
  padding: 12px 14px;
  font-size: 13px;
  line-height: 1.5;
  resize: vertical;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}}
.queue-edit-grid {{ display: grid; gap: 8px; }}
.queue-status-bar {{
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}}
.queue-note {{
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}}
.review-guide ol {{ margin: 8px 0 0; padding-left: 18px; color: var(--text); }}
.review-guide li {{ margin: 6px 0; }}
.status-line {{ min-height: 20px; color: #bfdbfe; font-size: 12px; margin-top: 8px; }}
.small {{ color: var(--muted); font-size: 12px; }}
.footer {{ margin-top: 18px; text-align: right; color: var(--muted); font-size: 12px; }}
#reviewSection,
#gapSection,
#modeSwitch [data-mode="review"],
#modeSwitch [data-mode="gaps"] {{
  display: none !important;
}}
@media (max-width: 1180px) {{
  .hero, .layout {{ grid-template-columns: 1fr; }}
  .insight-grid {{ grid-template-columns: 1fr; }}
  .control-grid {{ grid-template-columns: 1fr 1fr; }}
  .review-grid {{ grid-template-columns: 1fr; }}
}}
@media (max-width: 720px) {{
  .container {{ padding: 14px; }}
  .controls {{ position: static; }}
  .control-grid {{ grid-template-columns: 1fr; }}
  .stats {{ grid-template-columns: 1fr 1fr; }}
  .summary-grid {{ grid-template-columns: 1fr; }}
  .seed-controls-grid, .seed-summary-grid, .seed-grid, .youtube-seed-grid {{ grid-template-columns: 1fr; }}
  .cards {{ grid-template-columns: 1fr; }}
  .bundle-meta-strip, .bundle-work-grid {{ grid-template-columns: 1fr; }}
  .review-meta, .review-actions {{ grid-template-columns: 1fr; }}
  .simple-work-main {{ flex-direction: column; align-items: flex-start; }}
}}
</style>
</head>
<body>
<div class=\"container\">
  <div class=\"hero\">
    <div class=\"panel hero-main\">
      <h1>{escape(title)}</h1>
      <p>56作品を対象に、作品検索、本文・bookdata確認、音声/動画所在の確認、テーマ別3本セット、連番3本総集編の候補比較を1ページに集約した七之助専用アプリです。本文確認が済んだ前提で、公開しやすい3本セットの選定を主目的に使えます。</p>
    </div>
    <div class=\"panel stats\">
      <div class=\"stat\"><strong>{stats.get('works', 0)}</strong><span>作品</span></div>
      <div class=\"stat\"><strong>{stats.get('with_audio', 0)}</strong><span>MP3確認済み</span></div>
      <div class=\"stat\"><strong>{stats.get('with_video', 0)}</strong><span>動画確認済み</span></div>
      <div class=\"stat\"><strong>{stats.get('needs_mp3', 0)}</strong><span>MP3化必要</span></div>
    </div>
  </div>

  <div class="panel section" id="adoptedSection" style="margin-bottom: 18px;">
    <div class="section-header">
      <h2>採用済み総集編</h2>
      <div class="meta"><span id="adoptedBundleCount">0</span>件</div>
    </div>
    <div id="adoptedBundles" class="adopted-grid"></div>
  </div>

  <div class=\"panel controls\">
    <div class=\"grid control-grid\">
      <input id=\"searchInput\" type=\"search\" placeholder=\"作品名 / synopsis / themes / keywords / characters / ファイル名で検索\" />
      <select id=\"themeFilter\"><option value=\"\">テーマ全体</option></select>
      <select id=\"majorCategoryFilter\"><option value=\"\">大分類全体</option></select>
      <select id=\"minorCategoryFilter\"><option value=\"\">小分類全体</option></select>
      <select id=\"mediaFilter\">
        <option value=\"\">媒体全体</option>
        <option value=\"audio\">MP3あり</option>
        <option value="audio-missing">MP3未確認</option>
        <option value=\"video\">動画あり</option>
        <option value=\"text\">本文あり</option>
        <option value=\"needs-mp3\">MP3化必要</option>
      </select>
      <select id=\"metaFilter\">
        <option value=\"\">メタデータ全体</option>
        <option value=\"missing-synopsis\">synopsis未整備</option>
        <option value=\"missing-themes\">themes未整備</option>
        <option value=\"complete\">最低限整備済み</option>
      </select>
      <div class=\"grid\" style=\"grid-template-columns: 1fr 1fr; gap: 10px;\">
        <button id=\"resetButton\" class=\"secondary\">条件クリア</button>
        <button id=\"showGapsButton\">公開しやすい候補</button>
      </div>
    </div>
    <div class="search-note">検索は空白区切りの複数語に対応しています。作品名、あらすじ、登場人物、分類、ファイル名をまとめて横断検索します。日常導線は作品検索と総集編比較に絞っています。</div>
  </div>

  <div class="insight-grid">
    <div class="panel insight-panel">
      <div class="section-header">
        <h2>現在の絞り込み</h2>
        <div class="meta" id="resultSummary">結果を集計中</div>
      </div>
      <div class="summary-grid">
        <div class="summary-card">
          <strong id="summaryVisibleWorks">0</strong>
          <span>表示中作品</span>
        </div>
        <div class="summary-card">
          <strong id="summaryReadyBundles">0</strong>
          <span>すぐ組める総集編</span>
        </div>
        <div class="summary-card">
          <strong id="summaryWorkNeeded">0</strong>
          <span>MP3化必要</span>
        </div>
      </div>
      <div class="small" style="margin: 14px 0 6px;">有効な条件</div>
      <div class="chip-row" id="activeFilterChips"></div>
    </div>

    <div class="panel insight-panel">
      <div class="section-header">
        <h2>クイック導線</h2>
        <div class="meta">七之助向けの近道</div>
      </div>
      <div class="chip-row" id="quickActionChips">
        <button class="chip button" type="button" data-chip="needs-mp3">MP3化必要だけ</button>
        <button class="chip button" type="button" data-chip="ready-bundles">3本ともMP3あり</button>
        <button class="chip button" type="button" data-chip="primary-bundles">本命候補だけ</button>
        <button class="chip button" type="button" data-chip="adopted-bundles">採用済み総集編</button>
        <button class="chip button" type="button" data-chip="audio-missing">MP3未確認だけ</button>
      </div>
      <div class="small" style="margin-top: 14px;" id="quickActionHint">作品確認と3本セット比較を素早く切り替えるための導線です。</div>
    </div>
  </div>

  <div class="grid" style="gap: 18px; margin-top: 18px;">
    <div class="panel mode-controls">
      <div class="section-header">
        <h2>画面モード</h2>
        <div class="meta" id="modeSummary">必要な作業に応じて表示を切り替えます。</div>
      </div>
      <div id="modeSwitch" class="mode-switch">
        <button class="mode-button" type="button" data-mode="all">全体</button>
        <button class="mode-button active" type="button" data-mode="bundles">総集編中心</button>
        <button class="mode-button" type="button" data-mode="seed">核作品候補</button>
        <button class="mode-button" type="button" data-mode="works">作品検索</button>
        <button class="mode-button" type="button" data-mode="gaps">改善優先</button>
        <button class="mode-button" type="button" data-mode="review">LLM審査</button>
      </div>
    </div>

    <div class="panel bundle-controls" id="bundleControlsSection">
      <div class="section-header">
        <h2>総集編フィルタ</h2>
        <div class="meta" id="bundleFilterSummary">総集編候補の表示を絞り込みます。</div>
      </div>
      <div class="grid" style="grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px;">
        <select id="bundleTierFilter">
          <option value="">候補区分すべて</option>
          <option value="primary">本命候補</option>
          <option value="alternate">代替候補</option>
        </select>
        <select id="bundlePriorityFilter">
          <option value="">公開優先すべて</option>
          <option value="high">公開優先 高</option>
          <option value="medium">公開優先 中</option>
          <option value="low">公開優先 低</option>
        </select>
        <select id="bundleReadyFilter">
          <option value="">準備状況すべて</option>
          <option value="ready">3本ともMP3あり</option>
          <option value="needs-work">未整備を含む</option>
        </select>
        <select id="bundleStatusFilter">
          <option value="">採用状態すべて</option>
          <option value="adopted">採用済みのみ</option>
          <option value="candidate">未採用候補のみ</option>
        </select>
      </div>
    </div>
  </div>

  <div class="layout" id="mainLayout" style="margin-top: 18px;">
    <div class="panel section" id="worksSection">
      <div class="section-header">
        <h2>作品検索</h2>
        <div class="section-toolbar">
          <select id="workSort">
            <option value="serial">通し番号順</option>
            <option value="title">タイトル順</option>
            <option value="audio">MP3件数順</option>
            <option value="metadata">メタデータ不足順</option>
          </select>
          <div id="workViewSwitch" class="mode-switch">
            <button class="view-button active" type="button" data-view="cards">カード表示</button>
            <button class="view-button" type="button" data-view="simple">簡潔一覧</button>
          </div>
          <div class="meta"><span id="workCount">0</span>件表示</div>
        </div>
      </div>
      <div id="workCards" class="cards"></div>
    </div>

    <div class="grid" style="gap: 18px;" id="bundleColumn">
      <div class="panel section" id="seedSection">
        <div class="section-header">
          <h2>核作品から候補を探す</h2>
          <div class="meta" id="seedSummary">本文と分類の近さで相方候補を並べます。</div>
        </div>
        <div class="section-header" style="margin-top: 6px;">
          <h2 style="font-size: 18px;">YouTube成績から核を選ぶ</h2>
          <div>
            <div class="meta" id="youtubeSeedSummary">旧チャンネルの実績から短編核候補を拾います。</div>
            <label class="checkline"><input id="youtubeSeedPreferBacklog" type="checkbox" checked />採用済み総集編に入っていない作品を優先表示</label>
          </div>
        </div>
        <div id="youtubeSeedList" class="youtube-seed-list"></div>
        <div class="seed-summary-grid">
          <div class="summary-card">
            <strong id="seedSelectedTitle">未選択</strong>
            <span>核作品</span>
          </div>
          <div class="summary-card">
            <strong id="seedCandidateCount">0</strong>
            <span>候補表示件数</span>
          </div>
          <div class="summary-card">
            <strong id="seedReadyCount">0</strong>
            <span>MP3確認済み候補</span>
          </div>
        </div>
        <div class="seed-controls-grid">
          <button id="seedClearButton" class="secondary" type="button">核作品を解除</button>
          <label class="checkline"><input id="seedExcludeAdopted" type="checkbox" checked />採用済み総集編の収録作を除外</label>
          <label class="checkline"><input id="seedRecordedOnly" type="checkbox" />MP3確認済みだけ</label>
          <label class="checkline"><input id="seedTextOnly" type="checkbox" checked />本文ありだけ</label>
        </div>
        <div class="small" style="margin: 12px 0;">作品カードの「この作品から候補」から開始します。themes・分類・keywords・登場人物の重なりで相方候補を上位表示します。</div>
        <div class="seed-review-tools">
          <div class="review-actions">
            <button id="copySeedReviewCommandButton" type="button">seed review コマンドをコピー</button>
            <a id="seedReviewIndexLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_seed_review_prompts_selected.md').as_posix())}">seed index を開く</a>
            <a id="seedReviewJsonlLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_seed_review_prompts_selected.jsonl').as_posix())}">seed JSONL を開く</a>
            <a id="seedReviewDirLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_seed_review_prompts_selected').as_posix())}">seed prompt フォルダを開く</a>
            <a id="seedFeedbackLogLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_seed_feedback_log.csv').as_posix())}">seed feedback_log を開く</a>
          </div>
          <div>
            <div class="small" style="margin-bottom: 6px;">seed review 実行コマンド</div>
            <textarea id="seedReviewCommandPreview" class="command-box" readonly></textarea>
          </div>
          <div class="status-line" id="seedActionStatus"></div>
        </div>
        <div id="seedCandidateList" class="seed-list"></div>
      </div>

      <div class="panel section" id="themeSection">
        <div class="section-header">
          <h2>テーマ別3本セット候補</h2>
          <div class="meta"><span id="themeBundleCount">0</span>件</div>
        </div>
        <div id="themeBundles" class="list"></div>
      </div>

      <div class="panel section" id="sequentialSection">
        <div class="section-header">
          <h2>連番3本総集編候補</h2>
          <div class="meta"><span id="sequentialBundleCount">0</span>件</div>
        </div>
        <div id="sequentialBundles" class="list"></div>
      </div>

      <div class="panel section" id="gapSection">
        <div class="section-header">
          <h2>改善優先</h2>
          <div class="meta">未整備データ / MP3化必要作品</div>
        </div>
        <div id="gapList" class="list"></div>
      </div>
    </div>
  </div>

  <div class="panel review-controls" id="reviewSection" style="margin-top: 18px;">
    <div class="section-header">
      <h2>LLM審査コマンド生成</h2>
      <div class="meta">bundle選択 → コマンドコピー → VS/Codexで実行</div>
    </div>
    <div class="review-grid">
      <div class="grid" style="gap: 12px;">
        <div class="review-meta">
          <div class="review-stat"><strong id="selectedBundleCount">0</strong><span>選択 bundle</span></div>
          <div class="review-stat"><strong id="selectedPrimaryCount">0</strong><span>本命候補</span></div>
          <div class="review-stat"><strong id="visibleBundleCount">0</strong><span>現在表示中 bundle</span></div>
        </div>
        <div class="review-actions">
          <button id="selectVisibleBundlesButton" class="secondary">表示中 bundle を選択</button>
          <button id="selectPrimaryBundlesButton">本命候補を一括選択</button>
          <button id="clearSelectedBundlesButton" class="secondary">選択解除</button>
          <button id="copySelectedBundleIdsButton" class="secondary">bundle_id 一覧をコピー</button>
          <button id="copyClipboardTaskNameButton" class="secondary">clipboard task名をコピー</button>
          <button id="copyInputTaskNameButton" class="secondary">input task名をコピー</button>
          <button id="copyReviewCommandButton">生成して開くコマンドをコピー</button>
          <a id="selectedReviewIndexLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_bundle_review_prompts_selected.md').as_posix())}">選択 index を開く</a>
          <a id="selectedReviewJsonlLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_bundle_review_prompts_selected.jsonl').as_posix())}">選択 JSONL を開く</a>
          <a id="selectedReviewDirLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_bundle_review_prompts_selected').as_posix())}">選択 prompt フォルダを開く</a>
          <a id="reviewPromptDirLink" class="action-link" href="file://{escape((ROOT / 'reports' / 'shichinosuke_bundle_review_prompts').as_posix())}">既存 prompt フォルダを開く</a>
        </div>
        <div>
          <div class="small" style="margin-bottom: 6px;">実行コマンド</div>
          <textarea id="reviewCommandPreview" class="command-box" readonly></textarea>
        </div>
        <div class="review-guide">
          <div class="section-header" style="margin-bottom: 10px;">
            <div class="small">LLM review queue</div>
            <div class="section-toolbar">
              <button id="loadReviewQueueJsonButton" class="secondary" type="button">JSONを表示</button>
              <button id="exportReviewQueueButton" class="secondary" type="button">JSONをコピー</button>
            </div>
          </div>
          <textarea id="reviewQueueEditor" class="queue-editor" placeholder="review queue JSON をここで確認・編集できます"></textarea>
          <div class="review-actions" style="margin-top: 10px;">
            <button id="importReviewQueueButton" class="secondary" type="button">JSONを反映</button>
            <button id="resetReviewQueueButton" class="secondary" type="button">queueを空にする</button>
          </div>
          <div class="small" style="margin-top: 10px;"><span id="reviewQueueCount">0</span>件の queue を保持</div>
          <div id="reviewQueueList" class="list" style="margin-top: 12px;"></div>
        </div>
      </div>
      <div class="grid" style="gap: 12px;">
        <div>
          <div class="small" style="margin-bottom: 6px;">選択 bundle_id</div>
          <textarea id="selectedBundleIdsPreview" class="selection-box" readonly></textarea>
        </div>
        <div class="review-guide">
          <div class="small">おすすめ手順</div>
          <ol id="reviewGuideSteps"></ol>
        </div>
        <div class="status-line" id="reviewActionStatus"></div>
      </div>
    </div>
  </div>

  <div class="footer">Generated at {generated_at} / source: {escape(CATALOG_JSON_PATH.name)}</div>
</div>

<script>
const APP_DATA = {data_json};
const WORKSPACE_ROOT = {workspace_root};
const works = APP_DATA.works || [];
const youtubeSeedReport = APP_DATA.youtube_seed_report || {{ generated_at: '', entries: [] }};
const themeBundles = [
  ...(APP_DATA.bundles?.classification || []),
  ...(APP_DATA.bundles?.theme_content || []),
  ...(APP_DATA.bundles?.theme || []),
];
const sequentialBundles = APP_DATA.bundles?.sequential || [];
const adoptedBundles = APP_DATA.adopted_bundles || [];
const allBundles = [...themeBundles, ...sequentialBundles];
const adoptedBundleIds = new Set(adoptedBundles.map((bundle) => bundle.bundle_id).filter(Boolean));
const CLIPBOARD_TASK_NAME = 'Generate shichinosuke review prompts from clipboard';
const INPUT_TASK_NAME = 'Generate shichinosuke review prompts from input';
const SEED_REVIEW_TASK_NAME = 'Generate shichinosuke seed review prompts';
const UI_STATE_KEY = 'shichinosukeSearchUiStateV1';
const REVIEW_QUEUE_KEY = 'shichinosukeReviewQueueV1';
const bundleById = new Map(allBundles.map((bundle) => [bundle.bundle_id, bundle]));
const selectedBundleIds = new Set(
  JSON.parse(localStorage.getItem('shichinosukeSelectedBundleIds') || '[]')
);
let visibleThemeBundles = [];
let visibleSequentialBundles = [];
const uiState = JSON.parse(localStorage.getItem(UI_STATE_KEY) || '{{}}');
let activeMode = uiState.activeMode || 'bundles';
let activeWorkView = uiState.activeWorkView || 'cards';
let selectedSeedKey = uiState.selectedSeedKey || '';
let reviewQueue = normalizeReviewQueuePayload(loadReviewQueue()) || [];

const els = {{
  searchInput: document.getElementById('searchInput'),
  themeFilter: document.getElementById('themeFilter'),
  majorCategoryFilter: document.getElementById('majorCategoryFilter'),
  minorCategoryFilter: document.getElementById('minorCategoryFilter'),
  mediaFilter: document.getElementById('mediaFilter'),
  metaFilter: document.getElementById('metaFilter'),
  resetButton: document.getElementById('resetButton'),
  showGapsButton: document.getElementById('showGapsButton'),
  resultSummary: document.getElementById('resultSummary'),
  summaryVisibleWorks: document.getElementById('summaryVisibleWorks'),
  summaryReadyBundles: document.getElementById('summaryReadyBundles'),
  summaryWorkNeeded: document.getElementById('summaryWorkNeeded'),
  activeFilterChips: document.getElementById('activeFilterChips'),
  quickActionChips: document.getElementById('quickActionChips'),
  quickActionHint: document.getElementById('quickActionHint'),
  modeSwitch: document.getElementById('modeSwitch'),
  modeSummary: document.getElementById('modeSummary'),
  bundleControlsSection: document.getElementById('bundleControlsSection'),
  bundleFilterSummary: document.getElementById('bundleFilterSummary'),
  bundleTierFilter: document.getElementById('bundleTierFilter'),
  bundlePriorityFilter: document.getElementById('bundlePriorityFilter'),
  bundleReadyFilter: document.getElementById('bundleReadyFilter'),
  bundleStatusFilter: document.getElementById('bundleStatusFilter'),
  adoptedSection: document.getElementById('adoptedSection'),
  adoptedBundles: document.getElementById('adoptedBundles'),
  adoptedBundleCount: document.getElementById('adoptedBundleCount'),
  workSort: document.getElementById('workSort'),
  workViewSwitch: document.getElementById('workViewSwitch'),
  workCards: document.getElementById('workCards'),
  workCount: document.getElementById('workCount'),
  worksSection: document.getElementById('worksSection'),
  bundleColumn: document.getElementById('bundleColumn'),
  seedSection: document.getElementById('seedSection'),
  seedSummary: document.getElementById('seedSummary'),
  youtubeSeedSummary: document.getElementById('youtubeSeedSummary'),
  youtubeSeedList: document.getElementById('youtubeSeedList'),
  youtubeSeedPreferBacklog: document.getElementById('youtubeSeedPreferBacklog'),
  seedSelectedTitle: document.getElementById('seedSelectedTitle'),
  seedCandidateCount: document.getElementById('seedCandidateCount'),
  seedReadyCount: document.getElementById('seedReadyCount'),
  seedClearButton: document.getElementById('seedClearButton'),
  seedExcludeAdopted: document.getElementById('seedExcludeAdopted'),
  seedRecordedOnly: document.getElementById('seedRecordedOnly'),
  seedTextOnly: document.getElementById('seedTextOnly'),
  copySeedReviewCommandButton: document.getElementById('copySeedReviewCommandButton'),
  seedReviewIndexLink: document.getElementById('seedReviewIndexLink'),
  seedReviewJsonlLink: document.getElementById('seedReviewJsonlLink'),
  seedReviewDirLink: document.getElementById('seedReviewDirLink'),
  seedFeedbackLogLink: document.getElementById('seedFeedbackLogLink'),
  seedReviewCommandPreview: document.getElementById('seedReviewCommandPreview'),
  seedActionStatus: document.getElementById('seedActionStatus'),
  seedCandidateList: document.getElementById('seedCandidateList'),
  themeSection: document.getElementById('themeSection'),
  sequentialSection: document.getElementById('sequentialSection'),
  gapSection: document.getElementById('gapSection'),
  themeBundles: document.getElementById('themeBundles'),
  themeBundleCount: document.getElementById('themeBundleCount'),
  sequentialBundles: document.getElementById('sequentialBundles'),
  sequentialBundleCount: document.getElementById('sequentialBundleCount'),
  gapList: document.getElementById('gapList'),
  selectedBundleCount: document.getElementById('selectedBundleCount'),
  selectedPrimaryCount: document.getElementById('selectedPrimaryCount'),
  visibleBundleCount: document.getElementById('visibleBundleCount'),
  selectVisibleBundlesButton: document.getElementById('selectVisibleBundlesButton'),
  selectPrimaryBundlesButton: document.getElementById('selectPrimaryBundlesButton'),
  clearSelectedBundlesButton: document.getElementById('clearSelectedBundlesButton'),
  copySelectedBundleIdsButton: document.getElementById('copySelectedBundleIdsButton'),
  copyClipboardTaskNameButton: document.getElementById('copyClipboardTaskNameButton'),
  copyInputTaskNameButton: document.getElementById('copyInputTaskNameButton'),
  copyReviewCommandButton: document.getElementById('copyReviewCommandButton'),
  loadReviewQueueJsonButton: document.getElementById('loadReviewQueueJsonButton'),
  exportReviewQueueButton: document.getElementById('exportReviewQueueButton'),
  importReviewQueueButton: document.getElementById('importReviewQueueButton'),
  resetReviewQueueButton: document.getElementById('resetReviewQueueButton'),
  reviewQueueEditor: document.getElementById('reviewQueueEditor'),
  reviewQueueCount: document.getElementById('reviewQueueCount'),
  reviewQueueList: document.getElementById('reviewQueueList'),
  selectedReviewIndexLink: document.getElementById('selectedReviewIndexLink'),
  selectedReviewJsonlLink: document.getElementById('selectedReviewJsonlLink'),
  selectedReviewDirLink: document.getElementById('selectedReviewDirLink'),
  reviewCommandPreview: document.getElementById('reviewCommandPreview'),
  selectedBundleIdsPreview: document.getElementById('selectedBundleIdsPreview'),
  reviewGuideSteps: document.getElementById('reviewGuideSteps'),
  reviewActionStatus: document.getElementById('reviewActionStatus'),
  reviewSection: document.getElementById('reviewSection'),
}};

function uniq(items) {{
  return [...new Set(items.filter(Boolean))];
}}

function escapeHtml(value) {{
  return String(value ?? '').replace(/[&<>\"']/g, (char) => ({{
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }})[char]);
}}

function fileUrl(path) {{
  return `file://${{encodeURI(path)}}`;
}}

function formatNumber(value) {{
  const numeric = Number(value || 0);
  return Number.isFinite(numeric) ? numeric.toLocaleString('ja-JP') : '0';
}}

function formatDurationSeconds(value) {{
  const total = Math.max(0, Number(value || 0));
  const minutes = Math.floor(total / 60);
  const seconds = Math.floor(total % 60);
  return `${{minutes}}:${{String(seconds).padStart(2, '0')}}`;
}}

function shellQuote(value) {{
  return `'${{String(value).replace(/'/g, `'\\''`)}}'`;
}}

function sanitizePromptStem(value) {{
  return String(value || '').replace(/[\\/:*?"<>| ]/g, '_');
}}

function promptRelativePath(bundle) {{
  const stem = sanitizePromptStem(
    `${{bundle.candidate_tier || 'primary'}}_${{bundle.bundle_id || 'bundle'}}`
  );
  return `reports/shichinosuke_bundle_review_prompts/${{stem}}.md`;
}}

function setStatus(message) {{
  els.reviewActionStatus.textContent = message;
}}

function setSeedStatus(message) {{
  els.seedActionStatus.textContent = message;
}}

function persistSelectedBundles() {{
  localStorage.setItem(
    'shichinosukeSelectedBundleIds',
    JSON.stringify([...selectedBundleIds])
  );
}}

function persistUiState() {{
  localStorage.setItem(
    UI_STATE_KEY,
    JSON.stringify({{ activeMode, activeWorkView, selectedSeedKey }})
  );
}}

function loadReviewQueue() {{
  try {{
    const parsed = JSON.parse(localStorage.getItem(REVIEW_QUEUE_KEY) || '[]');
    return Array.isArray(parsed) ? parsed : [];
  }} catch (_error) {{
    return [];
  }}
}}

function saveReviewQueue(queue) {{
  localStorage.setItem(REVIEW_QUEUE_KEY, JSON.stringify(queue, null, 2));
}}

function normalizeReviewQueuePayload(payload) {{
  const list = Array.isArray(payload)
    ? payload
    : (payload && Array.isArray(payload.review_queue) ? payload.review_queue : null);
  if (!list) return null;
  return list.map((item, index) => {{
    if (typeof item === 'string') {{
      const bundle = bundleById.get(item);
      if (!bundle) return null;
      return {{
        bundle_id: item,
        recommended_title: bundle.recommended_title || bundle.label || '',
        review_status: 'pending',
        publication_priority: bundle.publication_priority || 'medium',
        review_reason: '',
        memo: '',
        added_at: '',
        sequence: index + 1,
      }};
    }}
    if (!item || typeof item !== 'object') return null;
    const bundleId = typeof item.bundle_id === 'string'
      ? item.bundle_id
      : (typeof item.bundleId === 'string' ? item.bundleId : '');
    if (!bundleId) return null;
    const bundle = bundleById.get(bundleId);
    return {{
      bundle_id: bundleId,
      recommended_title: typeof item.recommended_title === 'string'
        ? item.recommended_title
        : (bundle?.recommended_title || bundle?.label || ''),
      review_status: typeof item.review_status === 'string' && item.review_status
        ? item.review_status
        : 'pending',
      publication_priority: typeof item.publication_priority === 'string' && item.publication_priority
        ? item.publication_priority
        : (bundle?.publication_priority || 'medium'),
      review_reason: typeof item.review_reason === 'string' ? item.review_reason : '',
      memo: typeof item.memo === 'string' ? item.memo : (typeof item.note === 'string' ? item.note : ''),
      added_at: typeof item.added_at === 'string' ? item.added_at : '',
      sequence: Number.isInteger(item.sequence) ? item.sequence : index + 1,
    }};
  }}).filter(Boolean).map((item, index) => ({{ ...item, sequence: index + 1 }}));
}}

async function copyText(text, successMessage) {{
  try {{
    await navigator.clipboard.writeText(text);
    setStatus(successMessage);
  }} catch (_error) {{
    setStatus('クリップボード書き込みに失敗しました。表示欄から手動コピーしてください。');
  }}
}}

function getSelectedBundles() {{
  return [...selectedBundleIds]
    .map((bundleId) => bundleById.get(bundleId))
    .filter(Boolean);
}}

function buildReviewCommand(bundles) {{
  const args = bundles
    .map((bundle) => `--bundle-id ${{shellQuote(bundle.bundle_id)}}`)
    .join(' ');
  const base = [
    `cd ${{shellQuote(WORKSPACE_ROOT)}}`,
    `&& ${{shellQuote(`${{WORKSPACE_ROOT}}/.venv/bin/python`)}} tools/generate_and_open_shichinosuke_bundle_review_prompts.py`,
    '--tier all',
    '--bundle-group all',
    '--output-dir reports/shichinosuke_bundle_review_prompts_selected',
    '--index-path reports/shichinosuke_bundle_review_prompts_selected.md',
    '--jsonl-path reports/shichinosuke_bundle_review_prompts_selected.jsonl',
  ];
  return `${{base.join(' ')}}${{args ? ` ${{args}}` : ''}}`;
}}

function buildSeedReviewCommand() {{
  const seed = selectedSeedWork();
  if (!seed) return '';
  const base = [
    `cd ${{shellQuote(WORKSPACE_ROOT)}}`,
    `&& ${{shellQuote(`${{WORKSPACE_ROOT}}/.venv/bin/python`)}} tools/generate_and_open_shichinosuke_seed_review_prompts.py`,
    `--seed-key ${{shellQuote(seed.key || '')}}`,
    '--limit 10',
    '--output-dir reports/shichinosuke_seed_review_prompts_selected',
    '--index-path reports/shichinosuke_seed_review_prompts_selected.md',
    '--jsonl-path reports/shichinosuke_seed_review_prompts_selected.jsonl',
    '--feedback-log-path reports/shichinosuke_seed_feedback_log.csv',
  ];
  if (!els.seedExcludeAdopted.checked) {{
    base.push('--include-adopted');
  }}
  if (els.seedRecordedOnly.checked) {{
    base.push('--recorded-only');
  }}
  if (!els.seedTextOnly.checked) {{
    base.push('--include-no-text');
  }}
  return base.join(' ');
}}

function buildGuideSteps(selectedCount) {{
  if (selectedCount > 0) {{
    return [
      'bundle を選択したら「bundle_id 一覧をコピー」を押す',
      `VS Code で task 「${{CLIPBOARD_TASK_NAME}}」を実行する`,
      '生成後に開いた index / JSONL / prompt フォルダで審査を始める',
    ];
  }}
  return [
    'まず総集編カードのチェックで bundle を選択する',
    `複数手入力したい場合は task 「${{INPUT_TASK_NAME}}」を使う`,
    'コマンドを直接使う場合は下の実行コマンド欄をコピーする',
  ];
}}

function refreshReviewPanel() {{
  const selectedBundles = getSelectedBundles();
  const selectedPrimaryCount = selectedBundles.filter(
    (bundle) => bundle.candidate_tier !== 'alternate'
  ).length;
  els.selectedBundleCount.textContent = String(selectedBundles.length);
  els.selectedPrimaryCount.textContent = String(selectedPrimaryCount);
  els.visibleBundleCount.textContent = String(
    visibleThemeBundles.length + visibleSequentialBundles.length
  );
  els.reviewCommandPreview.value = buildReviewCommand(selectedBundles);
  els.selectedBundleIdsPreview.value = selectedBundles.length
    ? JSON.stringify(
        selectedBundles.map((bundle) => bundle.bundle_id),
        null,
        2
      )
    : '[]';
  els.reviewGuideSteps.innerHTML = buildGuideSteps(selectedBundles.length)
    .map((step) => `<li>${{escapeHtml(step)}}</li>`)
    .join('');
}}

function persistReviewQueue() {{
  reviewQueue = reviewQueue.map((item, index) => ({{ ...item, sequence: index + 1 }}));
  saveReviewQueue(reviewQueue);
  els.reviewQueueCount.textContent = String(reviewQueue.length);
  els.reviewQueueEditor.value = JSON.stringify({{ review_queue: reviewQueue }}, null, 2);
}}

function queueEntryFromBundle(bundle, previous = null) {{
  return {{
    bundle_id: bundle.bundle_id,
    recommended_title: previous?.recommended_title || bundle.recommended_title || bundle.label || '',
    review_status: previous?.review_status || 'pending',
    publication_priority: previous?.publication_priority || bundle.publication_priority || 'medium',
    review_reason: previous?.review_reason || '',
    memo: previous?.memo || '',
    added_at: previous?.added_at || new Date().toISOString(),
  }};
}}

function updateReviewQueueItem(bundleId, patch) {{
  reviewQueue = reviewQueue.map((item) => item.bundle_id === bundleId ? {{ ...item, ...patch }} : item);
  persistReviewQueue();
  renderReviewQueue();
}}

function renderReviewQueue() {{
  els.reviewQueueList.innerHTML = reviewQueue.length
    ? reviewQueue.map((item) => {{
      const bundle = bundleById.get(item.bundle_id);
      const worksHtml = bundle
        ? (bundle.works || []).map((entry, index) => {{
          const work = entry.key ? works.find((candidate) => candidate.key === entry.key) : null;
          const title = entry.title || work?.title || '';
          const retention = work?.channel_avg_retention_pct ? `維持率 ${{Math.round(Number(work.channel_avg_retention_pct || 0))}}% / ` : '';
          const audio = work?.audio_paths?.length ? `MP3 ${{work.audio_paths.length}}件 / ` : 'MP3未確認 / ';
          const adopted = work?.title && adoptedTitleSet(new Map(works.map((candidate) => [candidate.key, candidate]))).has(String(work.title))
            ? '採用済み総集編に含む'
            : '';
          return `<div class="adopted-work-item"><div class="small">第${{index + 1}}話</div><div>${{escapeHtml(title)}}</div><div class="small">${{escapeHtml(retention + audio + adopted)}}</div></div>`;
        }}).join('')
        : '<div class="queue-note">現在の bundle 定義に見つかりません。</div>';
      return `
        <article class="bundle">
          <div class="bundle-header">
            <h3>${{escapeHtml(item.recommended_title || bundle?.recommended_title || item.bundle_id)}}</h3>
            <span class="badge">${{escapeHtml(item.review_status || 'pending')}}</span>
          </div>
          <div class="badges">
            <span class="badge">priority: ${{escapeHtml(item.publication_priority || 'medium')}}</span>
            ${{bundle?.candidate_tier ? `<span class="badge">${{escapeHtml(bundle.candidate_tier === 'alternate' ? '代替候補' : '本命候補')}}</span>` : ''}}
            ${{bundle?.publication_priority ? `<span class="badge">${{escapeHtml(`公開優先 ${{bundle.publication_priority}}`)}}</span>` : ''}}
          </div>
          <div class="queue-status-bar">
            <select data-review-status="${{escapeHtml(item.bundle_id)}}">
              <option value="pending"${{item.review_status === 'pending' ? ' selected' : ''}}>pending</option>
              <option value="adopt"${{item.review_status === 'adopt' ? ' selected' : ''}}>adopt</option>
              <option value="hold"${{item.review_status === 'hold' ? ' selected' : ''}}>hold</option>
              <option value="reject"${{item.review_status === 'reject' ? ' selected' : ''}}>reject</option>
            </select>
            <select data-review-priority="${{escapeHtml(item.bundle_id)}}">
              <option value="high"${{item.publication_priority === 'high' ? ' selected' : ''}}>high</option>
              <option value="medium"${{item.publication_priority === 'medium' ? ' selected' : ''}}>medium</option>
              <option value="low"${{item.publication_priority === 'low' ? ' selected' : ''}}>low</option>
            </select>
            <button type="button" class="action-btn secondary" data-review-remove="${{escapeHtml(item.bundle_id)}}">queueから外す</button>
          </div>
          <div class="queue-edit-grid" style="margin-top: 10px;">
            <input type="text" data-review-title="${{escapeHtml(item.bundle_id)}}" value="${{escapeHtml(item.recommended_title || '')}}" placeholder="レビュー用タイトル" />
            <input type="text" data-review-reason="${{escapeHtml(item.bundle_id)}}" value="${{escapeHtml(item.review_reason || '')}}" placeholder="短い判断理由" />
            <textarea class="command-box" data-review-memo="${{escapeHtml(item.bundle_id)}}" placeholder="LLM 比較メモ">${{escapeHtml(item.memo || '')}}</textarea>
          </div>
          <div class="adopted-work-list" style="margin-top: 12px;">${{worksHtml}}</div>
        </article>`;
    }}).join('')
    : '<div class="bundle">まだ queue はありません。</div>';

  els.reviewQueueList.querySelectorAll('[data-review-status]').forEach((input) => {{
    input.addEventListener('change', () => updateReviewQueueItem(input.dataset.reviewStatus, {{ review_status: input.value }}));
  }});
  els.reviewQueueList.querySelectorAll('[data-review-priority]').forEach((input) => {{
    input.addEventListener('change', () => updateReviewQueueItem(input.dataset.reviewPriority, {{ publication_priority: input.value }}));
  }});
  els.reviewQueueList.querySelectorAll('[data-review-title]').forEach((input) => {{
    input.addEventListener('change', () => updateReviewQueueItem(input.dataset.reviewTitle, {{ recommended_title: input.value }}));
  }});
  els.reviewQueueList.querySelectorAll('[data-review-reason]').forEach((input) => {{
    input.addEventListener('change', () => updateReviewQueueItem(input.dataset.reviewReason, {{ review_reason: input.value }}));
  }});
  els.reviewQueueList.querySelectorAll('[data-review-memo]').forEach((input) => {{
    input.addEventListener('change', () => updateReviewQueueItem(input.dataset.reviewMemo, {{ memo: input.value }}));
  }});
  els.reviewQueueList.querySelectorAll('[data-review-remove]').forEach((button) => {{
    button.addEventListener('click', () => {{
      reviewQueue = reviewQueue.filter((item) => item.bundle_id !== button.dataset.reviewRemove);
      persistReviewQueue();
      renderReviewQueue();
    }});
  }});
  persistReviewQueue();
}}

function bundleIsReady(bundle, recordMap) {{
  const works = bundle.works || [];
  if (!works.length) return false;
  return works.every((entry) => {{
    const key = entry.key || findRecordKeyByTitle(entry.title, recordMap);
    const work = key ? recordMap.get(key) : null;
    return Boolean(work?.audio_paths?.length);
  }});
}}

function renderWorkSimpleRow(work) {{
  const serial = work.serial_number
    ? `No.${{String(work.serial_number).padStart(2, '0')}}`
    : 'No.--';
  const media = [
    work.audio_paths?.length ? `MP3:${{work.audio_paths.length}}` : 'MP3なし',
    work.video_paths?.length ? `動画:${{work.video_paths.length}}` : '動画なし',
    work.text_paths?.length ? '本文あり' : '本文なし',
  ].join(' / ');
  return `
    <article class="simple-work" id="${{escapeHtml(work.key)}}">
      <div class="simple-work-main">
        <div class="simple-work-title"><a href="#${{escapeHtml(work.key)}}">${{escapeHtml(serial)}} ${{escapeHtml(work.title)}}</a></div>
        <div class="simple-work-meta">${{escapeHtml(work.major_category || '分類なし')}} / ${{escapeHtml(media)}}</div>
      </div>
      <div class="badges">${{renderBadges(work)}}</div>
      <div class="small">${{escapeHtml(work.short_title || '')}}</div>
      <div class="seed-actions"><button type="button" class="action-btn secondary" data-seed-key="${{escapeHtml(work.key)}}">この作品から候補</button></div>
    </article>`;
}}

function sortWorks(items) {{
  const works = [...items];
  const sortMode = els.workSort.value || 'serial';
  works.sort((left, right) => {{
    if (sortMode === 'title') {{
      return String(left.title || '').localeCompare(String(right.title || ''), 'ja');
    }}
    if (sortMode === 'audio') {{
      return (right.audio_paths?.length || 0) - (left.audio_paths?.length || 0)
        || left.sort_order - right.sort_order;
    }}
    if (sortMode === 'metadata') {{
      const leftScore = Number(left.has_synopsis) + Number(left.has_themes);
      const rightScore = Number(right.has_synopsis) + Number(right.has_themes);
      return leftScore - rightScore || left.sort_order - right.sort_order;
    }}
    return left.sort_order - right.sort_order;
  }});
  return works;
}}

function updateModeVisibility() {{
  const summaryMap = {{
    all: '作品一覧と総集編候補をまとめて確認します。',
    bundles: '総集編候補の比較と絞り込みを主画面で進めます。',
    seed: '核作品を決めて、相方候補を本文前提で見比べます。',
    works: '作品本文や素材状況の確認に集中します。',
    gaps: 'MP3化が必要な作品だけを確認します。',
    review: 'レビュー系機能は補助用途として退避しています。',
  }};
  const isWorks = activeMode === 'all' || activeMode === 'works';
  const isBundles = activeMode === 'all' || activeMode === 'bundles';
  const isSeed = activeMode === 'all' || activeMode === 'seed';
  const isGaps = false;
  const isReview = false;
  els.worksSection.style.display = isWorks ? '' : 'none';
  els.bundleControlsSection.style.display = isBundles ? '' : 'none';
  els.bundleColumn.style.display = (isBundles || isSeed || isGaps) ? '' : 'none';
  els.seedSection.style.display = isSeed ? '' : 'none';
  els.themeSection.style.display = isBundles ? '' : 'none';
  els.sequentialSection.style.display = isBundles ? '' : 'none';
  els.gapSection.style.display = isGaps ? '' : 'none';
  els.reviewSection.style.display = isReview ? '' : 'none';
  els.modeSummary.textContent = summaryMap[activeMode] || summaryMap.all;
  for (const button of els.modeSwitch.querySelectorAll('[data-mode]')) {{
    button.classList.toggle('active', button.dataset.mode === activeMode);
  }}
  for (const button of els.workViewSwitch.querySelectorAll('[data-view]')) {{
    button.classList.toggle('active', button.dataset.view === activeWorkView);
  }}
  persistUiState();
}}

function renderBadges(work) {{
  const badges = [];
  if (work.serial_number) badges.push(`<span class=\"badge\">通しNo.${{String(work.serial_number).padStart(2, '0')}}</span>`);
  if (work.volume_number) badges.push(`<span class=\"badge\">第${{String(work.volume_number).padStart(2, '0')}}巻</span>`);
  if (work.major_category) badges.push(`<span class=\"badge\">${{escapeHtml(work.major_category)}}</span>`);
  if (work.compilation_priority === 'high') badges.push(`<span class=\"badge warn\">総集編優先 高</span>`);
  if (work.audio_paths?.length) badges.push(`<span class=\"badge ok\">MP3 ${{work.audio_paths.length}}件</span>`);
  if (work.video_paths?.length) badges.push(`<span class=\"badge ok\">動画 ${{work.video_paths.length}}件</span>`);
  if (work.text_paths?.length) badges.push(`<span class=\"badge ok\">本文 ${{work.text_paths.length}}件</span>`);
  if (work.needs_mp3_conversion) badges.push(`<span class=\"badge warn\">MP3化必要</span>`);
  if (!work.has_synopsis) badges.push(`<span class=\"badge danger\">synopsis未整備</span>`);
  if (!work.has_themes) badges.push(`<span class=\"badge danger\">themes未整備</span>`);
  return badges.join('');
}}

function renderThemeBadges(work) {{
  const categoryBadges = (work.minor_categories || []).slice(0, 2)
    .map((category) => `<span class=\"badge\">${{escapeHtml(category)}}</span>`);
  const themeBadges = (work.themes || []).slice(0, 4)
    .map((theme) => `<span class=\"badge\">${{escapeHtml(theme)}}</span>`);
  return [...categoryBadges, ...themeBadges].join('');
}}

function renderLinks(work) {{
  const links = [];
  if (work.bookdata_path) links.push(`<a href="${{fileUrl(`${{WORKSPACE_ROOT}}/${{work.bookdata_path}}`)}}">bookdata</a>`);
  if (work.text_paths?.[0]) links.push(`<a href="${{fileUrl(work.text_paths[0])}}">本文</a>`);
  if (work.audio_story_dirs?.[0]) links.push(`<a href="${{fileUrl(work.audio_story_dirs[0])}}">音声フォルダ</a>`);
  else if (work.audio_paths?.[0]) links.push(`<a href="${{fileUrl(work.audio_paths[0])}}">MP3</a>`);
  if (work.video_paths?.[0]) links.push(`<a href="${{fileUrl(work.video_paths[0])}}">動画</a>`);
  return links.join('');
}}

function renderYoutubeSeedCard(entry) {{
  const seedKey = String(entry.work_key || '').trim();
  const backlogStatus = String(entry.backlog_status || '').trim() || '未採用';
  const statusBadgeClass = backlogStatus === '未採用' ? 'warn' : 'ok';
  return `
    <article class="youtube-seed-card">
      <div class="youtube-seed-head">
        <div>
          <div class="youtube-seed-rank">#${{escapeHtml(entry.rank || '-')}}</div>
          <div class="simple-work-title">${{escapeHtml(entry.short_title || entry.title || '')}}</div>
          <div class="small">${{escapeHtml(entry.major_category || '分類なし')}} / ${{escapeHtml(entry.privacy || 'unknown')}}</div>
          <div class="badges" style="margin-top: 6px;"><span class="badge ${{statusBadgeClass}}">${{escapeHtml(backlogStatus)}}</span></div>
        </div>
        <div class="youtube-seed-score">score<br>${{escapeHtml(Math.round(Number(entry.score || 0)))}}</div>
      </div>
      <div class="youtube-seed-grid">
        <div class="youtube-seed-metric"><strong>views</strong>${{escapeHtml(formatNumber(entry.views))}}</div>
        <div class="youtube-seed-metric"><strong>平均視聴</strong>${{escapeHtml(formatDurationSeconds(entry.average_view_duration_seconds))}}</div>
        <div class="youtube-seed-metric"><strong>総再生分</strong>${{escapeHtml(formatNumber(entry.estimated_minutes_watched))}}</div>
      </div>
      <div class="small">${{escapeHtml(entry.channel_title || '')}}</div>
      <div class="seed-actions"><button type="button" class="action-btn secondary" data-seed-key="${{escapeHtml(seedKey)}}">この作品から候補</button></div>
    </article>`;
}}

function renderYoutubeSeedPanel(recordMap) {{
  const adoptedTitles = adoptedTitleSet(recordMap);
  const preferBacklog = Boolean(els.youtubeSeedPreferBacklog?.checked);
  const entries = (Array.isArray(youtubeSeedReport.entries) ? youtubeSeedReport.entries : [])
    .map((entry) => ({{
      ...entry,
      backlog_rank: youtubeSeedBacklogRank(entry, adoptedTitles),
      backlog_status: youtubeSeedBacklogLabel(entry, adoptedTitles),
    }}))
    .sort((left, right) => {{
      if (preferBacklog && left.backlog_rank !== right.backlog_rank) {{
        return left.backlog_rank - right.backlog_rank;
      }}
      if (Number(right.score || 0) !== Number(left.score || 0)) {{
        return Number(right.score || 0) - Number(left.score || 0);
      }}
      if (Number(right.views || 0) !== Number(left.views || 0)) {{
        return Number(right.views || 0) - Number(left.views || 0);
      }}
      return String(left.short_title || left.title || '').localeCompare(
        String(right.short_title || right.title || ''),
        'ja',
      );
    }});
  if (!entries.length) {{
    els.youtubeSeedSummary.textContent = 'YouTube成績データはまだありません。';
    els.youtubeSeedList.innerHTML = '<div class="seed-empty">old channel report から核候補をまだ作れていません。</div>';
    return;
  }}
  const top = entries[0];
  const backlogCount = entries.filter((entry) => entry.backlog_rank === 0).length;
  const modeLabel = preferBacklog ? '未採用優先' : '純粋な成績順';
  els.youtubeSeedSummary.textContent = `${{entries.length}}件表示 / 未採用 ${{backlogCount}}件 / ${{modeLabel}} / 首位は ${{top.short_title || top.title}} / score ${{Math.round(Number(top.score || 0))}}`;
  els.youtubeSeedList.innerHTML = entries.slice(0, 6).map(renderYoutubeSeedCard).join('');
}}

function renderWorkCard(work) {{
  const synopsis = work.synopsis ? escapeHtml(work.synopsis) : 'synopsis未整備';
  const chars = (work.characters || []).slice(0, 6).join(' / ');
  const serial = work.serial_number ? `No.${{String(work.serial_number).padStart(2, '0')}}` : '';
  return `
    <article class="card" id="${{escapeHtml(work.key)}}">
      <h3>${{serial ? `<span class="badge">${{serial}}</span> ` : ''}}${{escapeHtml(work.title)}}</h3>
      <div class="meta-line">${{escapeHtml(work.short_title || '')}} / bookdata: ${{escapeHtml(work.bookdata_path || '')}}</div>
      <div class="badges">${{renderBadges(work)}}${{renderThemeBadges(work)}}</div>
      <div class="synopsis">${{synopsis}}</div>
      <div class="meta-line" style="margin-top: 10px;">登場人物: ${{escapeHtml(chars || '記載なし')}}</div>
      <div class="links">${{renderLinks(work)}}</div>
      <div class="seed-actions"><button type="button" class="action-btn secondary" data-seed-key="${{escapeHtml(work.key)}}">この作品から候補</button></div>
    </article>`;
}}

function workTagValues(work) {{
  return uniq([
    work.major_category,
    ...(work.minor_categories || []),
    ...(work.themes || []),
    ...(work.keywords || []).slice(0, 12),
  ].map((value) => String(value || '').trim()).filter(Boolean));
}}

function workCharacterValues(work) {{
  return uniq((work.characters || []).map((value) => String(value || '').trim()).filter(Boolean));
}}

function intersectionValues(left, right) {{
  const rightSet = new Set((right || []).map((value) => String(value || '').trim()).filter(Boolean));
  return uniq((left || []).map((value) => String(value || '').trim()).filter(Boolean))
    .filter((value) => rightSet.has(value));
}}

function selectedSeedWork() {{
  return works.find((work) => work.key === selectedSeedKey) || null;
}}

function adoptedTitleSet(recordMap) {{
  const adopted = new Set();
  for (const bundle of adoptedBundles) {{
    for (const entry of bundle.works || []) {{
      const key = entry.key || findRecordKeyByTitle(entry.title, recordMap);
      const work = key ? recordMap.get(key) : null;
      if (!work) continue;
      [work.title, work.short_title, work.canonical_title].forEach((value) => {{
        if (value) adopted.add(String(value));
      }});
    }}
  }}
  return adopted;
}}

function youtubeSeedBacklogRank(entry, adoptedTitles) {{
  const names = [
    entry.short_title,
    entry.title,
  ].map((value) => String(value || '').trim()).filter(Boolean);
  return names.some((value) => adoptedTitles.has(value)) ? 1 : 0;
}}

function youtubeSeedBacklogLabel(entry, adoptedTitles) {{
  return youtubeSeedBacklogRank(entry, adoptedTitles) === 0
    ? '未採用'
    : '採用済み総集編に含む';
}}

function scoreSeedCandidate(seed, work) {{
  const sharedMinor = intersectionValues(seed.minor_categories || [], work.minor_categories || []);
  const sharedThemes = intersectionValues(seed.themes || [], work.themes || []);
  const sharedKeywords = intersectionValues(workTagValues(seed), workTagValues(work))
    .filter((value) => !sharedThemes.includes(value) && value !== seed.major_category);
  const sharedCharacters = intersectionValues(workCharacterValues(seed), workCharacterValues(work));
  const chapterGap = Math.abs(Number(seed.chapter_count || 0) - Number(work.chapter_count || 0));
  const reasons = [];
  let score = 0;

  if (seed.major_category && seed.major_category === work.major_category) {{
    score += 28;
    reasons.push(`主分類一致: ${{seed.major_category}}`);
  }}
  if (sharedMinor.length) {{
    score += Math.min(24, sharedMinor.length * 8);
    reasons.push(`小分類一致: ${{sharedMinor.slice(0, 3).join(' / ')}}`);
  }}
  if (sharedThemes.length) {{
    score += Math.min(24, sharedThemes.length * 6);
    reasons.push(`themes一致: ${{sharedThemes.slice(0, 3).join(' / ')}}`);
  }}
  if (sharedKeywords.length) {{
    score += Math.min(16, sharedKeywords.length * 4);
    reasons.push(`語彙接点: ${{sharedKeywords.slice(0, 4).join(' / ')}}`);
  }}
  if (sharedCharacters.length) {{
    score += Math.min(12, sharedCharacters.length * 4);
    reasons.push(`人物接点: ${{sharedCharacters.slice(0, 3).join(' / ')}}`);
  }}
  if (chapterGap <= 1) {{
    score += 6;
    reasons.push('章立ての重さが近い');
  }}
  if (work.audio_paths?.length) {{
    score += 8;
    reasons.push('MP3確認済み');
  }}
  if (work.video_paths?.length) {{
    score += 3;
  }}
  if (work.text_paths?.length) {{
    score += 6;
    reasons.push('本文あり');
  }}
  return {{
    work,
    score,
    sharedMinor,
    sharedThemes,
    sharedKeywords,
    sharedCharacters,
    reasons,
  }};
}}

function buildSeedCandidates(recordMap) {{
  const seed = selectedSeedWork();
  if (!seed) return [];
  const adopted = adoptedTitleSet(recordMap);
  return works
    .filter((work) => work.key !== seed.key)
    .filter((work) => !els.seedExcludeAdopted.checked || !adopted.has(String(work.title || '')))
    .filter((work) => !els.seedRecordedOnly.checked || (work.audio_paths || []).length)
    .filter((work) => !els.seedTextOnly.checked || (work.text_paths || []).length)
    .map((work) => scoreSeedCandidate(seed, work))
    .filter((entry) => entry.score > 0)
    .sort((left, right) => {{
      if (left.score !== right.score) return right.score - left.score;
      if ((right.work.audio_paths?.length || 0) !== (left.work.audio_paths?.length || 0)) {{
        return (right.work.audio_paths?.length || 0) - (left.work.audio_paths?.length || 0);
      }}
      return left.work.sort_order - right.work.sort_order;
    }})
    .slice(0, 12);
}}

function renderSeedCandidate(entry) {{
  const work = entry.work;
  const scoreLabel = entry.score >= 70 ? '高' : entry.score >= 45 ? '中' : '低';
  return `
    <article class="seed-card ${{entry.score >= 70 ? 'good' : ''}}">
      <div class="bundle-header">
        <h3>${{escapeHtml(work.title)}}</h3>
        <span class="badge ${{entry.score >= 70 ? 'ok' : ''}}">一致度 ${{entry.score}} / 優先 ${{scoreLabel}}</span>
      </div>
      <div class="meta-line">${{escapeHtml(work.major_category || '分類なし')}} / 第${{String(work.volume_number || '--').padStart(2, '0')}}巻 / 章数 ${{escapeHtml(work.chapter_count || 0)}}</div>
      <div class="seed-grid">
        <div class="seed-meta-box">
          <strong>themes・分類</strong>
          <div class="small">${{escapeHtml((entry.sharedThemes || []).join(' / ') || (entry.sharedMinor || []).join(' / ') || '大きな重なりなし')}}</div>
        </div>
        <div class="seed-meta-box">
          <strong>人物・語彙</strong>
          <div class="small">${{escapeHtml((entry.sharedCharacters || []).join(' / ') || (entry.sharedKeywords || []).slice(0, 4).join(' / ') || '補助接点は薄め')}}</div>
        </div>
      </div>
      <div class="badges">
        ${{work.audio_paths?.length ? '<span class="badge ok">MP3あり</span>' : '<span class="badge warn">MP3未確認</span>'}}
        ${{work.video_paths?.length ? '<span class="badge ok">動画あり</span>' : ''}}
        ${{work.text_paths?.length ? '<span class="badge ok">本文あり</span>' : ''}}
      </div>
      <div class="synopsis">${{escapeHtml(work.synopsis || '要約未整備')}}</div>
      <div class="small">${{escapeHtml((entry.reasons || []).join(' / ') || '近さの根拠がまだ薄い候補です。')}}</div>
      <div class="links">${{renderLinks(work)}}</div>
    </article>`;
}}

function renderSeedSection(recordMap) {{
  renderYoutubeSeedPanel(recordMap);
  const seed = selectedSeedWork();
  els.seedReviewCommandPreview.value = buildSeedReviewCommand();
  if (!seed) {{
    els.seedSelectedTitle.textContent = '未選択';
    els.seedCandidateCount.textContent = '0';
    els.seedReadyCount.textContent = '0';
    els.seedSummary.textContent = '作品カードの「この作品から候補」から開始します。';
    els.seedReviewCommandPreview.value = '';
    els.seedCandidateList.innerHTML = '<div class="seed-empty">核作品を選ぶと、相方候補を12件まで表示します。</div>';
    return;
  }}
  const candidates = buildSeedCandidates(recordMap);
  const readyCount = candidates.filter((entry) => (entry.work.audio_paths || []).length).length;
  els.seedSelectedTitle.textContent = seed.short_title || seed.title;
  els.seedCandidateCount.textContent = String(candidates.length);
  els.seedReadyCount.textContent = String(readyCount);
  els.seedSummary.textContent = `${{seed.title}} を核に、分類・themes・keywords・登場人物の重なりで候補を並べています。`;
  els.seedCandidateList.innerHTML = candidates.length
    ? candidates.map(renderSeedCandidate).join('')
    : '<div class="seed-empty">条件に合う候補がありません。採用済み除外や MP3 条件をゆるめてください。</div>';
}}

function bundleSearchText(bundle) {{
  return [bundle.label, ...(bundle.works || []).map((work) => work.title || work.short_title || '')].join(' ');
}}

function renderBundle(bundle, recordMap) {{
  const worksHtml = (bundle.works || []).map((entry, index) => {{
    const key = entry.key || findRecordKeyByTitle(entry.title, recordMap);
    const work = key ? recordMap.get(key) : null;
    const serial = entry.serial_number || work?.serial_number;
    const link = work ? `#${{escapeHtml(work.key)}}` : '';
    const title = escapeHtml(entry.title || entry.short_title || '');
    const mediaBadges = [
      work?.audio_paths?.length ? '<span class="badge ok">MP3あり</span>' : '<span class="badge warn">MP3なし</span>',
      work?.video_paths?.length ? '<span class="badge ok">動画あり</span>' : '',
      work?.text_paths?.length ? '<span class="badge ok">本文あり</span>' : '',
    ].filter(Boolean).join('');
    const meta = work
      ? `${{serial ? `No.${{String(serial).padStart(2, '0')}} / ` : ''}}${{work.major_category || '分類なし'}}`
      : 'bookdata参照のみ';
    return `
      <article class="bundle-work-card">
        <div class="small">第${{index + 1}}話</div>
        <h4>${{link ? `<a href=\"${{link}}\">${{title}}</a>` : title}}</h4>
        <div class="badges">${{mediaBadges}}</div>
        <div class="small">${{escapeHtml(meta)}}</div>
      </article>`;
  }}).join('');
  const priorityLabel = bundle.publication_priority === 'high'
    ? '公開優先 高'
    : bundle.publication_priority === 'medium'
      ? '公開優先 中'
      : '公開優先 低';
  const tierLabel = bundle.candidate_tier === 'alternate'
    ? '代替候補'
    : '本命候補';
  const readyCount = (bundle.works || []).filter((entry) => {{
    const key = entry.key || findRecordKeyByTitle(entry.title, recordMap);
    const work = key ? recordMap.get(key) : null;
    return Boolean(work?.audio_paths?.length);
  }}).length;
  const summaryText = bundle.summary || bundle.candidate_tier_reason || bundle.publication_reason || '';
  const promptPath = promptRelativePath(bundle);
  const checked = selectedBundleIds.has(bundle.bundle_id) ? 'checked' : '';
  return `
    <article class="bundle ${{selectedBundleIds.has(bundle.bundle_id) ? 'selected' : ''}} ${{adoptedBundleIds.has(bundle.bundle_id) ? 'adopted' : ''}}">
      <div class="bundle-header">
        <h3>${{escapeHtml(bundle.label)}}</h3>
        <label class="bundle-select"><input type="checkbox" data-bundle-select="${{escapeHtml(bundle.bundle_id || '')}}" ${{checked}} />選択</label>
      </div>
      <div class=\"small\">source: ${{escapeHtml(bundle.source || 'theme')}}</div>
      ${{bundle.recommended_title ? `<div class=\"meta-line\">推奨タイトル: ${{escapeHtml(bundle.recommended_title)}}</div>` : ''}}
      <div class=\"badges\">
        <span class="badge">${{escapeHtml(tierLabel)}}</span>
        <span class=\"badge\">${{escapeHtml(priorityLabel)}}</span>
        ${{adoptedBundleIds.has(bundle.bundle_id) ? '<span class="badge ok">採用済み</span>' : ''}}
        ${{bundle.major_category ? `<span class=\"badge\">${{escapeHtml(bundle.major_category)}}</span>` : ''}}
        ${{bundle.minor_category ? `<span class=\"badge\">${{escapeHtml(bundle.minor_category)}}</span>` : ''}}
      </div>
      <div class="bundle-meta-strip">
        <div class="bundle-meta-card">
          <strong>推奨タイトル</strong>
          <span>${{escapeHtml(bundle.recommended_title || bundle.label || '')}}</span>
        </div>
        <div class="bundle-meta-card">
          <strong>準備状況</strong>
          <span>${{readyCount}} / ${{(bundle.works || []).length}}話でMP3確認済み</span>
        </div>
        <div class="bundle-meta-card">
          <strong>選定メモ</strong>
          <span>${{escapeHtml(summaryText || 'テーマの流れと公開優先で選定')}}</span>
        </div>
      </div>
      <div class="bundle-work-grid">${{worksHtml}}</div>
      <div class="bundle-actions">
        <a class="action-link" href="${{fileUrl(`${{WORKSPACE_ROOT}}/${{promptPath}}`)}}">既存 prompt を開く</a>
        <button type="button" class="action-btn secondary" data-action="queue-review" data-bundle-id="${{escapeHtml(bundle.bundle_id || '')}}">review queueへ追加</button>
        <button type="button" class="action-btn secondary" data-action="copy-command" data-bundle-id="${{escapeHtml(bundle.bundle_id || '')}}">この bundle のコマンド</button>
        <button type="button" class="action-btn secondary" data-action="copy-id" data-bundle-id="${{escapeHtml(bundle.bundle_id || '')}}">bundle_id をコピー</button>
      </div>
    </article>`;
}}

function renderAdoptedBundle(bundle, recordMap) {{
  const adoptedTitle = bundle.custom_title || bundle.recommended_title || bundle.label || '';
  const sourceLabel = bundle.bundle_group === 'sequential'
    ? '連番候補ベース'
    : bundle.bundle_group === 'classification'
      ? '分類候補ベース'
      : '既存候補ベース';
  const worksHtml = (bundle.works || []).map((entry, index) => {{
    const key = entry.key || findRecordKeyByTitle(entry.title, recordMap);
    const work = key ? recordMap.get(key) : null;
    const title = escapeHtml(entry.title || entry.short_title || '');
    const serial = entry.serial_number || work?.serial_number;
    const meta = work?.major_category || '';
    return `
      <div class="adopted-work-item">
        <div class="small">第${{index + 1}}話</div>
        <div>${{key ? `<a href="#${{escapeHtml(key)}}">${{title}}</a>` : title}}</div>
        <div class="small">${{escapeHtml(serial ? `No.${{String(serial).padStart(2, '0')}}` : '')}}${{serial && meta ? ' / ' : ''}}${{escapeHtml(meta)}}</div>
      </div>`;
  }}).join('');
  const showOriginalTitle = bundle.recommended_title && bundle.recommended_title !== adoptedTitle;
  return `
    <article class="card adopted-card">
      <div class="bundle-header">
        <h3>${{escapeHtml(bundle.volume_label || '')}}</h3>
        <span class="badge ok">採用済み</span>
      </div>
      <p class="adopted-title">${{escapeHtml(adoptedTitle)}}</p>
      <div class="adopted-subtitle">${{escapeHtml(bundle.note || '採用済みの3本構成です。')}}</div>
      <div class="badges">
        <span class="badge">${{escapeHtml(sourceLabel)}}</span>
        ${{bundle.major_category ? `<span class="badge">${{escapeHtml(bundle.major_category)}}</span>` : ''}}
        ${{bundle.minor_category ? `<span class="badge">${{escapeHtml(bundle.minor_category)}}</span>` : ''}}
      </div>
      ${{showOriginalTitle ? `<div class="adopted-origin">自動候補名: ${{escapeHtml(bundle.recommended_title)}}</div>` : ''}}
      <div class="adopted-origin">採用元: ${{escapeHtml(bundle.label || bundle.bundle_id || '')}}</div>
      <div class="adopted-work-list">${{worksHtml}}</div>
    </article>`;
}}

function findRecordKeyByTitle(title, recordMap) {{
  const normalized = String(title || '').replace(/\\s+/g, '').toLowerCase();
  for (const work of recordMap.values()) {{
    const candidates = [work.title, work.short_title, work.canonical_title].filter(Boolean);
    if (candidates.some((candidate) => String(candidate).replace(/\\s+/g, '').toLowerCase().includes(normalized) || normalized.includes(String(candidate).replace(/\\s+/g, '').toLowerCase()))) {{
      return work.key;
    }}
  }}
  return '';
}}

function currentFilters() {{
  const searchTerms = els.searchInput.value
    .trim()
    .toLowerCase()
    .split(/[\s\u3000]+/)
    .filter(Boolean);
  return {{
    search: els.searchInput.value.trim().toLowerCase(),
    searchTerms,
    theme: els.themeFilter.value,
    majorCategory: els.majorCategoryFilter.value,
    minorCategory: els.minorCategoryFilter.value,
    media: els.mediaFilter.value,
    meta: els.metaFilter.value,
    bundleTier: els.bundleTierFilter.value,
    bundlePriority: els.bundlePriorityFilter.value,
    bundleReady: els.bundleReadyFilter.value,
    bundleStatus: els.bundleStatusFilter.value,
  }};
}}

function matchWork(work, filters) {{
  if (filters.searchTerms.length) {{
    const haystack = String(work.search_text || '').toLowerCase();
    if (!filters.searchTerms.every((term) => haystack.includes(term))) return false;
  }}
  if (filters.theme && !(work.themes || []).includes(filters.theme)) return false;
  if (filters.majorCategory && work.major_category !== filters.majorCategory) return false;
  if (filters.minorCategory && !(work.minor_categories || []).includes(filters.minorCategory)) return false;
  if (filters.media === 'audio' && !(work.audio_paths || []).length) return false;
  if (filters.media === 'audio-missing' && (work.audio_paths || []).length) return false;
  if (filters.media === 'video' && !(work.video_paths || []).length) return false;
  if (filters.media === 'text' && !(work.text_paths || []).length) return false;
  if (filters.media === 'needs-mp3' && !work.needs_mp3_conversion) return false;
  if (filters.meta === 'missing-synopsis' && work.has_synopsis) return false;
  if (filters.meta === 'missing-themes' && work.has_themes) return false;
  if (filters.meta === 'complete' && (!work.has_synopsis || !work.has_themes)) return false;
  return true;
}}

function filterBundles(bundles, visibleWorks, recordMap, filters) {{
  const visibleKeys = new Set(visibleWorks.map((work) => work.key));
  return bundles.filter((bundle) => {{
    if (filters.bundleTier && (bundle.candidate_tier || 'primary') !== filters.bundleTier) return false;
    if (filters.bundlePriority && (bundle.publication_priority || 'low') !== filters.bundlePriority) return false;
    const isAdopted = adoptedBundleIds.has(bundle.bundle_id);
    if (filters.bundleStatus === 'adopted' && !isAdopted) return false;
    if (filters.bundleStatus === 'candidate' && isAdopted) return false;
    const ready = bundleIsReady(bundle, recordMap);
    if (filters.bundleReady === 'ready' && !ready) return false;
    if (filters.bundleReady === 'needs-work' && ready) return false;
    const bundleText = bundleSearchText(bundle).toLowerCase();
    const hasVisibleMatch = (bundle.works || []).some((entry) => {{
      const key = entry.key || findRecordKeyByTitle(entry.title, recordMap);
      return key && visibleKeys.has(key);
    }});
    if (filters.searchTerms.length && !filters.searchTerms.every((term) => bundleText.includes(term))) {{
      if (!hasVisibleMatch) return false;
    }}
    if (
      (filters.theme || filters.majorCategory || filters.minorCategory || filters.media || filters.meta)
      && !hasVisibleMatch
    ) {{
      return false;
    }}
    return true;
  }});
}}

function activeFilterLabels(filters) {{
  return [
    filters.search ? `検索: ${{filters.search}}` : '',
    filters.theme ? `テーマ: ${{filters.theme}}` : '',
    filters.majorCategory ? `大分類: ${{filters.majorCategory}}` : '',
    filters.minorCategory ? `小分類: ${{filters.minorCategory}}` : '',
    filters.media === 'audio' ? '媒体: MP3あり' : '',
    filters.media === 'audio-missing' ? '媒体: MP3未確認' : '',
    filters.media === 'video' ? '媒体: 動画あり' : '',
    filters.media === 'text' ? '媒体: 本文あり' : '',
    filters.media === 'needs-mp3' ? '媒体: MP3化必要' : '',
    filters.meta === 'missing-synopsis' ? 'メタ: synopsis未整備' : '',
    filters.meta === 'missing-themes' ? 'メタ: themes未整備' : '',
    filters.meta === 'complete' ? 'メタ: 最低限整備済み' : '',
    filters.bundleTier === 'primary' ? 'bundle: 本命候補' : '',
    filters.bundleTier === 'alternate' ? 'bundle: 代替候補' : '',
    filters.bundlePriority === 'high' ? '公開優先: 高' : '',
    filters.bundlePriority === 'medium' ? '公開優先: 中' : '',
    filters.bundlePriority === 'low' ? '公開優先: 低' : '',
    filters.bundleReady === 'ready' ? 'bundle: 3本ともMP3あり' : '',
    filters.bundleReady === 'needs-work' ? 'bundle: 未整備を含む' : '',
    filters.bundleStatus === 'adopted' ? 'bundle: 採用済みのみ' : '',
    filters.bundleStatus === 'candidate' ? 'bundle: 未採用候補のみ' : '',
  ].filter(Boolean);
}}

function renderFilterChips(filters) {{
  const labels = activeFilterLabels(filters);
  els.activeFilterChips.innerHTML = labels.length
    ? labels.map((label) => `<span class="chip">${{escapeHtml(label)}}</span>`).join('')
    : '<span class="chip empty">条件なし</span>';
}}

function updateSummaryPanel(visibleWorks, visibleThemeBundles, visibleSequentialBundles, recordMap, filters) {{
  const visibleBundles = [...visibleThemeBundles, ...visibleSequentialBundles];
  const readyBundles = visibleBundles.filter((bundle) => bundleIsReady(bundle, recordMap)).length;
  const workNeeded = visibleWorks.filter((work) => work.needs_mp3_conversion).length;
  els.summaryVisibleWorks.textContent = String(visibleWorks.length);
  els.summaryReadyBundles.textContent = String(readyBundles);
  els.summaryWorkNeeded.textContent = String(workNeeded);
  const labels = activeFilterLabels(filters);
  els.resultSummary.textContent = labels.length
    ? `${{visibleWorks.length}}作品 / ${{visibleBundles.length}} bundle`
    : '全作品・全bundleを表示中';
  renderFilterChips(filters);
}}

function renderAll() {{
  const filters = currentFilters();
  const recordMap = new Map(works.map((work) => [work.key, work]));
  els.adoptedSection.style.display = adoptedBundles.length ? '' : 'none';
  els.adoptedBundles.innerHTML = adoptedBundles.length
    ? adoptedBundles.map((bundle) => renderAdoptedBundle(bundle, recordMap)).join('')
    : '';
  els.adoptedBundleCount.textContent = String(adoptedBundles.length);
  const visibleWorks = sortWorks(works.filter((work) => matchWork(work, filters)));
  els.workCards.classList.toggle('simple', activeWorkView === 'simple');
  els.workCards.innerHTML = visibleWorks.length
    ? visibleWorks
      .map((work) => activeWorkView === 'simple' ? renderWorkSimpleRow(work) : renderWorkCard(work))
      .join('')
    : '<div class=\"card\">該当作品がありません。</div>';
  els.workCount.textContent = String(visibleWorks.length);

  visibleThemeBundles = filterBundles(themeBundles, visibleWorks, recordMap, filters);
  els.themeBundles.innerHTML = visibleThemeBundles.map((bundle) => renderBundle(bundle, recordMap)).join('') || '<div class=\"bundle\">該当セットがありません。</div>';
  els.themeBundleCount.textContent = String(visibleThemeBundles.length);

  visibleSequentialBundles = filterBundles(sequentialBundles, visibleWorks, recordMap, filters);
  els.sequentialBundles.innerHTML = visibleSequentialBundles.map((bundle) => renderBundle(bundle, recordMap)).join('') || '<div class=\"bundle\">該当セットがありません。</div>';
  els.sequentialBundleCount.textContent = String(visibleSequentialBundles.length);

  const gaps = works
    .filter((work) => !work.has_synopsis || !work.has_themes || work.needs_mp3_conversion)
    .sort((left, right) => Number(left.has_synopsis) - Number(right.has_synopsis) || Number(left.has_themes) - Number(right.has_themes) || left.sort_order - right.sort_order)
    .slice(0, 14);

  els.gapList.innerHTML = gaps.map((work) => `
    <article class=\"bundle\">
      <h3><a href=\"#${{escapeHtml(work.key)}}\">${{escapeHtml(work.title)}}</a></h3>
      <div class=\"badges\">
        ${{!work.has_synopsis ? '<span class=\"badge danger\">synopsis未整備</span>' : ''}}
        ${{!work.has_themes ? '<span class=\"badge danger\">themes未整備</span>' : ''}}
        ${{work.needs_mp3_conversion ? '<span class=\"badge warn\">MP3化必要</span>' : ''}}
      </div>
      <div class=\"small\">bookdata: ${{escapeHtml(work.bookdata_path || '')}}</div>
    </article>
  `).join('') || '<div class=\"bundle\">改善候補はありません。</div>';

  renderSeedSection(recordMap);
  renderReviewQueue();

  updateSummaryPanel(
    visibleWorks,
    visibleThemeBundles,
    visibleSequentialBundles,
    recordMap,
    filters
  );

  const totalVisibleBundles = visibleThemeBundles.length + visibleSequentialBundles.length;
  const filterLabels = [
    filters.bundleTier === 'primary' ? '本命候補' : '',
    filters.bundleTier === 'alternate' ? '代替候補' : '',
    filters.bundlePriority === 'high' ? '公開優先 高' : '',
    filters.bundlePriority === 'medium' ? '公開優先 中' : '',
    filters.bundlePriority === 'low' ? '公開優先 低' : '',
    filters.bundleReady === 'ready' ? '3本ともMP3あり' : '',
    filters.bundleReady === 'needs-work' ? '未整備を含む' : '',
    filters.bundleStatus === 'adopted' ? '採用済みのみ' : '',
    filters.bundleStatus === 'candidate' ? '未採用候補のみ' : '',
  ].filter(Boolean);
  els.bundleFilterSummary.textContent = filterLabels.length
    ? `総集編候補 ${{totalVisibleBundles}}件 / ${{filterLabels.join(' / ')}}`
    : `総集編候補 ${{totalVisibleBundles}}件を表示中`;

  updateModeVisibility();
  refreshReviewPanel();
}}

function populateThemeFilter() {{
  const themes = uniq(works.flatMap((work) => work.themes || [])).sort((a, b) => a.localeCompare(b, 'ja'));
  for (const theme of themes) {{
    const option = document.createElement('option');
    option.value = theme;
    option.textContent = theme;
    els.themeFilter.appendChild(option);
  }}
}}

function populateMajorCategoryFilter() {{
  const categories = uniq(
    works.map((work) => work.major_category).filter(Boolean)
  ).sort((a, b) => a.localeCompare(b, 'ja'));
  for (const category of categories) {{
    const option = document.createElement('option');
    option.value = category;
    option.textContent = category;
    els.majorCategoryFilter.appendChild(option);
  }}
}}

function populateMinorCategoryFilter() {{
  const currentValue = els.minorCategoryFilter.value;
  els.minorCategoryFilter.innerHTML = '<option value="">小分類全体</option>';
  const categories = uniq(
    works
      .filter((work) => !els.majorCategoryFilter.value || work.major_category === els.majorCategoryFilter.value)
      .flatMap((work) => work.minor_categories || [])
  ).sort((a, b) => a.localeCompare(b, 'ja'));
  for (const category of categories) {{
    const option = document.createElement('option');
    option.value = category;
    option.textContent = category;
    els.minorCategoryFilter.appendChild(option);
  }}
  if (categories.includes(currentValue)) {{
    els.minorCategoryFilter.value = currentValue;
  }}
}}

for (const element of [
  els.searchInput,
  els.themeFilter,
  els.majorCategoryFilter,
  els.minorCategoryFilter,
  els.mediaFilter,
  els.metaFilter,
  els.bundleTierFilter,
  els.bundlePriorityFilter,
  els.bundleReadyFilter,
  els.bundleStatusFilter,
  els.seedExcludeAdopted,
  els.seedRecordedOnly,
  els.seedTextOnly,
  els.youtubeSeedPreferBacklog,
]) {{
  element.addEventListener('input', renderAll);
  element.addEventListener('change', renderAll);
}}
els.majorCategoryFilter.addEventListener('change', () => {{
  populateMinorCategoryFilter();
  renderAll();
}});
els.resetButton.addEventListener('click', () => {{
  els.searchInput.value = '';
  els.themeFilter.value = '';
  els.majorCategoryFilter.value = '';
  populateMinorCategoryFilter();
  els.minorCategoryFilter.value = '';
  els.mediaFilter.value = '';
  els.metaFilter.value = '';
  els.bundleTierFilter.value = '';
  els.bundlePriorityFilter.value = '';
  els.bundleReadyFilter.value = '';
  els.bundleStatusFilter.value = '';
  activeMode = 'bundles';
  renderAll();
}});
els.showGapsButton.addEventListener('click', () => {{
  els.searchInput.value = '';
  els.themeFilter.value = '';
  els.majorCategoryFilter.value = '';
  populateMinorCategoryFilter();
  els.minorCategoryFilter.value = '';
  if (APP_DATA.stats?.needs_mp3) {{
    els.mediaFilter.value = 'needs-mp3';
    els.metaFilter.value = '';
  }} else if (APP_DATA.stats?.missing_synopsis) {{
    els.mediaFilter.value = '';
    els.metaFilter.value = 'missing-synopsis';
  }} else if (APP_DATA.stats?.missing_themes) {{
    els.mediaFilter.value = '';
    els.metaFilter.value = 'missing-themes';
  }} else {{
    els.mediaFilter.value = '';
    els.metaFilter.value = '';
  }}
  els.bundleTierFilter.value = 'primary';
  els.bundlePriorityFilter.value = '';
  els.bundleReadyFilter.value = 'ready';
  els.bundleStatusFilter.value = '';
  activeMode = 'bundles';
  renderAll();
}});

els.seedClearButton.addEventListener('click', () => {{
  selectedSeedKey = '';
  activeMode = 'seed';
  setSeedStatus('核作品を解除しました。');
  renderAll();
}});

populateThemeFilter();
populateMajorCategoryFilter();
populateMinorCategoryFilter();

if (activeWorkView !== 'simple') {{
  activeWorkView = 'cards';
}}

els.modeSwitch.addEventListener('click', (event) => {{
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const button = target.closest('[data-mode]');
  if (!(button instanceof HTMLElement)) return;
  const mode = button.dataset.mode;
  if (!mode) return;
  activeMode = mode;
  renderAll();
}});

els.workViewSwitch.addEventListener('click', (event) => {{
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const button = target.closest('[data-view]');
  if (!(button instanceof HTMLElement)) return;
  const view = button.dataset.view;
  if (!view) return;
  activeWorkView = view;
  renderAll();
}});

els.workSort.addEventListener('change', renderAll);

els.quickActionChips.addEventListener('click', (event) => {{
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const button = target.closest('[data-chip]');
  if (!(button instanceof HTMLElement)) return;
  const chip = button.dataset.chip;
  if (!chip) return;
  if (chip === 'needs-mp3') {{
    els.metaFilter.value = '';
    els.mediaFilter.value = 'needs-mp3';
    els.bundleReadyFilter.value = '';
    activeMode = 'works';
  }}
  if (chip === 'audio-missing') {{
    els.mediaFilter.value = 'audio-missing';
    els.metaFilter.value = '';
    activeMode = 'works';
  }}
  if (chip === 'ready-bundles') {{
    els.mediaFilter.value = '';
    els.metaFilter.value = '';
    els.bundleReadyFilter.value = 'ready';
    els.bundleStatusFilter.value = '';
    activeMode = 'bundles';
  }}
  if (chip === 'primary-bundles') {{
    els.mediaFilter.value = '';
    els.metaFilter.value = '';
    els.bundleTierFilter.value = 'primary';
    els.bundleStatusFilter.value = '';
    activeMode = 'bundles';
  }}
  if (chip === 'adopted-bundles') {{
    els.mediaFilter.value = '';
    els.metaFilter.value = '';
    els.bundleTierFilter.value = '';
    els.bundlePriorityFilter.value = '';
    els.bundleReadyFilter.value = '';
    els.bundleStatusFilter.value = 'adopted';
    activeMode = 'bundles';
  }}
  if (chip === 'gaps') {{
    els.showGapsButton.click();
    return;
  }}
  renderAll();
}});

els.workCards.addEventListener('click', (event) => {{
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const button = target.closest('[data-seed-key]');
  if (!(button instanceof HTMLElement)) return;
  selectedSeedKey = button.dataset.seedKey || '';
  activeMode = 'seed';
  renderAll();
}});

for (const container of [els.themeBundles, els.sequentialBundles]) {{
  container.addEventListener('change', (event) => {{
    const target = event.target;
    if (!(target instanceof HTMLInputElement)) return;
    const bundleId = target.dataset.bundleSelect;
    if (!bundleId) return;
    if (target.checked) selectedBundleIds.add(bundleId);
    else selectedBundleIds.delete(bundleId);
    persistSelectedBundles();
    refreshReviewPanel();
  }});
  container.addEventListener('click', async (event) => {{
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;
    const actionElement = target.closest('[data-action]');
    if (!(actionElement instanceof HTMLElement)) return;
    const action = actionElement.dataset.action;
    const bundleId = actionElement.dataset.bundleId;
    const bundle = bundleId ? bundleById.get(bundleId) : null;
    if (!bundle) return;
    if (action === 'copy-command') {{
      await copyText(
        buildReviewCommand([bundle]),
        `bundle ${{bundle.bundle_id}} の生成コマンドをコピーしました。`
      );
    }}
    if (action === 'queue-review') {{
      const existing = reviewQueue.find((item) => item.bundle_id === bundle.bundle_id);
      reviewQueue = [queueEntryFromBundle(bundle, existing), ...reviewQueue.filter((item) => item.bundle_id !== bundle.bundle_id)];
      persistReviewQueue();
      renderReviewQueue();
      setStatus(`review queue に追加しました: ${{bundle.bundle_id}}`);
    }}
    if (action === 'copy-id') {{
      await copyText(
        bundle.bundle_id || '',
        `bundle_id をコピーしました: ${{bundle.bundle_id}}`
      );
    }}
  }});
}}

els.selectVisibleBundlesButton.addEventListener('click', () => {{
  for (const bundle of [...visibleThemeBundles, ...visibleSequentialBundles]) {{
    if (bundle.bundle_id) selectedBundleIds.add(bundle.bundle_id);
  }}
  persistSelectedBundles();
  renderAll();
  setStatus('現在表示中の bundle を選択しました。');
}});
els.selectPrimaryBundlesButton.addEventListener('click', () => {{
  for (const bundle of allBundles) {{
    if (bundle.bundle_id && bundle.candidate_tier !== 'alternate') {{
      selectedBundleIds.add(bundle.bundle_id);
    }}
  }}
  persistSelectedBundles();
  renderAll();
  setStatus('本命候補 bundle を一括選択しました。');
}});
els.clearSelectedBundlesButton.addEventListener('click', () => {{
  selectedBundleIds.clear();
  persistSelectedBundles();
  renderAll();
  setStatus('bundle 選択を解除しました。');
}});
els.copySelectedBundleIdsButton.addEventListener('click', async () => {{
  await copyText(
    els.selectedBundleIdsPreview.value,
    '選択 bundle_id 一覧をコピーしました。'
  );
}});
els.copyClipboardTaskNameButton.addEventListener('click', async () => {{
  await copyText(
    CLIPBOARD_TASK_NAME,
    `task 名をコピーしました: ${{CLIPBOARD_TASK_NAME}}`
  );
}});
els.copyInputTaskNameButton.addEventListener('click', async () => {{
  await copyText(
    INPUT_TASK_NAME,
    `task 名をコピーしました: ${{INPUT_TASK_NAME}}`
  );
}});
els.copyReviewCommandButton.addEventListener('click', async () => {{
  await copyText(
    els.reviewCommandPreview.value,
    '選択 bundle 用の生成コマンドをコピーしました。'
  );
}});
els.loadReviewQueueJsonButton.addEventListener('click', () => {{
  persistReviewQueue();
  setStatus('review queue JSON を表示しました。');
}});
els.exportReviewQueueButton.addEventListener('click', async () => {{
  await copyText(
    JSON.stringify({{ review_queue: reviewQueue }}, null, 2),
    'review queue JSON をコピーしました。'
  );
}});
els.importReviewQueueButton.addEventListener('click', () => {{
  const raw = els.reviewQueueEditor.value || '';
  if (!raw.trim()) {{
    setStatus('review queue JSON を貼り付けてください。');
    return;
  }}
  let parsed;
  try {{
    parsed = JSON.parse(raw);
  }} catch (_error) {{
    setStatus('review queue JSON の解析に失敗しました。');
    return;
  }}
  const normalized = normalizeReviewQueuePayload(parsed);
  if (!normalized) {{
    setStatus('review_queue 配列または bundle_id 配列の JSON を指定してください。');
    return;
  }}
  reviewQueue = normalized;
  persistReviewQueue();
  renderReviewQueue();
  setStatus('review queue を JSON から反映しました。');
}});
els.resetReviewQueueButton.addEventListener('click', () => {{
  reviewQueue = [];
  persistReviewQueue();
  renderReviewQueue();
  setStatus('review queue を空にしました。');
}});

els.copySeedReviewCommandButton.addEventListener('click', async () => {{
  if (!els.seedReviewCommandPreview.value) {{
    setSeedStatus('核作品を選ぶと seed review コマンドを生成できます。');
    return;
  }}
  try {{
    await navigator.clipboard.writeText(els.seedReviewCommandPreview.value);
    setSeedStatus(`seed review コマンドをコピーしました。task 名: ${{SEED_REVIEW_TASK_NAME}}`);
  }} catch (_error) {{
    setSeedStatus('クリップボード書き込みに失敗しました。表示欄から手動コピーしてください。');
  }}
}});

renderAll();
</script>
</body>
</html>
"""


def main() -> int:
    if CATALOG_JSON_PATH.exists():
        payload = json.loads(CATALOG_JSON_PATH.read_text(encoding="utf-8"))
        payload["adopted_bundles"] = resolve_adopted_bundles(
            payload.get("bundles", {}),
            load_adopted_bundle_state(),
        )
    else:
        payload = build_catalog()
        write_catalog_reports(payload)
    payload["youtube_seed_report"] = load_youtube_seed_report(payload)
    OUT_PATH.write_text(render_html(payload), encoding="utf-8")
    print(f"Wrote: {OUT_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
