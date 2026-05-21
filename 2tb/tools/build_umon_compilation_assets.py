#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = ROOT.parent
REPORTS_DIR = ROOT / "reports"
LEDGER_DIR = WORKSPACE_ROOT / "reports"
READING_DIR = ROOT / "Reading_library" / "右門捕物帖"

SELECTION_CSV = LEDGER_DIR / "common_ledger_selection_status.csv"
LATEST_CSV = LEDGER_DIR / "common_ledger_latest_only.csv"

OUT_WORKS_CSV = REPORTS_DIR / "umon_works_catalog.csv"
OUT_PERF_CSV = REPORTS_DIR / "umon_channel_performance.csv"
OUT_PLAN_MD = REPORTS_DIR / "umon_compilation_plan.md"
OUT_BUNDLES_JSON = REPORTS_DIR / "umon_adopted_bundles.json"
OUT_HTML = REPORTS_DIR / "umon_compilation.html"
OUT_MANIFEST = REPORTS_DIR / "umon_aozora_manifest.json"

AUTHOR_KEY = "sasaki_mitsuzo"
SERIES_KEYWORD = "右門捕物帖"

TITLE_ALIASES = {
    "朱彫の花嫁": ["朱彫りの花嫁"],
    "朱彫りの花嫁": ["朱彫の花嫁"],
}


@dataclass
class Work:
    work_id: str
    title: str
    old_channel_only: bool
    current_channel_adopted: bool
    rerecord_exists: bool
    preferred_video_id: str
    views: int
    avg_view_duration_ratio: float
    duration_seconds: int
    published_at: str
    video_title: str
    has_local_text: bool
    local_text_paths: list[str]


@dataclass
class Bundle:
    sequence: int
    volume_label: str
    custom_title: str
    works: list[str]
    size: int
    category: str
    compilation_theme: str
    note: str


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def to_bool(value: str) -> bool:
    return str(value or "").strip().lower() == "yes"


def to_int(value: str) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def to_float(value: str) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def first_of(row: dict[str, str], keys: list[str], default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def normalize_title(text: str) -> str:
    t = unicodedata.normalize("NFKC", str(text or ""))
    t = t.replace("佐々木味津三", "")
    t = t.replace("右門捕物帖", "")
    t = re.sub(r"^[0-9]+[.．]\s*", "", t)
    t = t.replace("_", " ")
    t = re.sub(r"[\s\-−ー〜～・、。『』「」【】\[\]（）()]+", "", t)
    return t.strip().lower()


def build_local_text_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    if not READING_DIR.exists():
        return index

    for path in sorted(READING_DIR.glob("*.txt")):
        key = normalize_title(path.stem)
        index.setdefault(key, []).append(str(path.relative_to(ROOT)))

    return index


def title_lookup_keys(title: str) -> list[str]:
    keys = [normalize_title(title)]
    for alias in TITLE_ALIASES.get(title, []):
        keys.append(normalize_title(alias))
    for canonical, aliases in TITLE_ALIASES.items():
        if title in aliases:
            keys.append(normalize_title(canonical))
    dedup: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key and key not in seen:
            dedup.append(key)
            seen.add(key)
    return dedup


def pick_latest_rows() -> dict[str, dict[str, str]]:
    rows = csv_rows(LATEST_CSV)
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        work_id = str(row.get("work_id", "")).strip()
        if not work_id.startswith(f"{AUTHOR_KEY}:"):
            continue
        title = first_of(row, ["title", "work_title"])
        video_title = first_of(row, ["video_title"])
        if SERIES_KEYWORD not in video_title and title != SERIES_KEYWORD:
            continue

        current = best.get(work_id)
        if not current:
            best[work_id] = row
            continue

        if to_int(first_of(row, ["views", "view_count"], "0")) > to_int(
            first_of(current, ["views", "view_count"], "0")
        ):
            best[work_id] = row

    return best


def classify_category(title: str) -> str:
    if any(word in title for word in ("幽霊", "怪", "呪", "闇", "血")):
        return "怪異・闇"
    if any(word in title for word in ("女", "花嫁", "小町", "遊女", "娘")):
        return "女と情念"
    if any(word in title for word in ("秘密", "謎", "匕首", "手形", "八卦")):
        return "謎解き"
    return "捕物帳"


def build_works() -> list[Work]:
    selection_rows = csv_rows(SELECTION_CSV)
    latest_map = pick_latest_rows()
    local_index = build_local_text_index()

    works: list[Work] = []
    for row in selection_rows:
        work_id = str(row.get("work_id", "")).strip()
        if not work_id.startswith(f"{AUTHOR_KEY}:"):
            continue

        title = str(work_id.split(":", 1)[1]).strip()
        latest = latest_map.get(work_id)
        if not latest and title != SERIES_KEYWORD:
            # 右門シリーズ判定できたものだけを対象化
            continue

        paths: list[str] = []
        for key in title_lookup_keys(title):
            paths.extend(local_index.get(key, []))
        unique_paths = sorted(set(paths))

        works.append(
            Work(
                work_id=work_id,
                title=title,
                old_channel_only=to_bool(row.get("old_channel_only", "")),
                current_channel_adopted=to_bool(row.get("current_channel_adopted", "")),
                rerecord_exists=to_bool(row.get("rerecord_exists", "")),
                preferred_video_id=str(row.get("preferred_video_id", "")).strip(),
                views=to_int(first_of((latest or {}), ["views", "view_count"], "0")),
                avg_view_duration_ratio=to_float(
                    first_of(
                        (latest or {}),
                        ["avg_view_duration_ratio", "retention_rate_percent"],
                        "0",
                    )
                ),
                duration_seconds=to_int(first_of((latest or {}), ["duration_seconds"], "0")),
                published_at=first_of((latest or {}), ["published_at"]),
                video_title=first_of((latest or {}), ["video_title"]),
                has_local_text=bool(unique_paths),
                local_text_paths=unique_paths,
            )
        )

    works.sort(key=lambda w: (-w.views, not w.has_local_text, w.title))
    return works


def make_bundles(works: list[Work]) -> list[Bundle]:
    base = [w for w in works if w.title != SERIES_KEYWORD]
    bundles: list[Bundle] = []
    size = 3
    bundle_count = math.ceil(len(base) / size)

    for i in range(bundle_count):
        chunk = base[i * size:(i + 1) * size]
        if not chunk:
            continue
        seq = i + 1
        top = chunk[0]
        categories = sorted({classify_category(item.title) for item in chunk})
        theme = " / ".join(categories)
        bundles.append(
            Bundle(
                sequence=seq,
                volume_label=f"右門総集編 第{seq:02d}巻",
                custom_title=f"{top.title}ほか{len(chunk)}篇",
                works=[item.title for item in chunk],
                size=len(chunk),
                category=categories[0],
                compilation_theme=theme,
                note=f"柱作品: {top.title}（再生 {top.views:,}）",
            )
        )
    return bundles


def write_works_csv(works: list[Work]) -> None:
    OUT_WORKS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_WORKS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "work_id",
            "title",
            "has_local_text",
            "local_text_count",
            "local_text_paths",
            "old_channel_only",
            "current_channel_adopted",
            "rerecord_exists",
            "preferred_video_id",
            "views",
            "avg_view_duration_ratio",
            "duration_seconds",
            "published_at",
            "video_title",
        ])
        for work in works:
            writer.writerow([
                work.work_id,
                work.title,
                "yes" if work.has_local_text else "no",
                len(work.local_text_paths),
                " | ".join(work.local_text_paths),
                "yes" if work.old_channel_only else "no",
                "yes" if work.current_channel_adopted else "no",
                "yes" if work.rerecord_exists else "no",
                work.preferred_video_id,
                work.views,
                f"{work.avg_view_duration_ratio:.2f}",
                work.duration_seconds,
                work.published_at,
                work.video_title,
            ])


def write_performance_csv(works: list[Work]) -> None:
    with OUT_PERF_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "title",
            "views",
            "avg_view_duration_ratio",
            "duration_seconds",
            "published_at",
            "preferred_video_id",
        ])
        for work in works:
            writer.writerow([
                work.title,
                work.views,
                f"{work.avg_view_duration_ratio:.2f}",
                work.duration_seconds,
                work.published_at,
                work.preferred_video_id,
            ])


def write_plan_md(works: list[Work], bundles: list[Bundle]) -> None:
    with_text = sum(1 for w in works if w.has_local_text)
    missing = [w for w in works if not w.has_local_text]

    lines: list[str] = []
    lines.append("# 右門捕物帖 総集編計画")
    lines.append("")
    lines.append(f"- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 対象作品: {len(works)}")
    lines.append(f"- 本文あり: {with_text}")
    lines.append(f"- 本文不足: {len(missing)}")
    lines.append("")
    lines.append("## 総集編バンドル")
    lines.append("")
    lines.append("| 巻 | タイトル | 構成 | 備考 |")
    lines.append("|---|---|---|---|")
    for bundle in bundles:
        lines.append(
            f"| {bundle.volume_label} | {bundle.custom_title} | {' / '.join(bundle.works)} | {bundle.note} |"
        )
    lines.append("")

    lines.append("## 本文不足一覧")
    lines.append("")
    lines.append("| 作品 | 再生数 | 備考 |")
    lines.append("|---|---:|---|")
    for work in sorted(missing, key=lambda x: (-x.views, x.title)):
        lines.append(f"| {work.title} | {work.views:,} | 本文未整備 |")
    lines.append("")

    OUT_PLAN_MD.write_text("\n".join(lines), encoding="utf-8")


def write_bundles_json(works: list[Work], bundles: list[Bundle]) -> None:
    lookup = {w.title: w for w in works}
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "series": "右門捕物帖",
        "bundle_count": len(bundles),
        "work_count": len(works),
        "adopted_bundles": [
            {
                "sequence": b.sequence,
                "volume_label": b.volume_label,
                "bundle_id": f"umon-compilation-{b.sequence:02d}",
                "custom_title": b.custom_title,
                "works": b.works,
                "size": b.size,
                "category": b.category,
                "compilation_theme": b.compilation_theme,
                "note": b.note,
                "performance": {
                    title: {
                        "views": lookup[title].views,
                        "avg_view_duration_ratio": lookup[title].avg_view_duration_ratio,
                        "duration_seconds": lookup[title].duration_seconds,
                        "has_local_text": lookup[title].has_local_text,
                    }
                    for title in b.works
                    if title in lookup
                },
            }
            for b in bundles
        ],
    }
    OUT_BUNDLES_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_manifest(works: list[Work]) -> None:
    items = []
    for work in works:
        status = "local_text_present" if work.has_local_text else "needs_lookup"
        note = (
            "手持ち本文あり。必要時のみ青空差分取得。"
            if work.has_local_text
            else "手持ち本文なし。青空文庫/公開テキストの照合対象。"
        )
        items.append(
            {
                "title": work.title,
                "normalized_title": work.title,
                "has_local_text": work.has_local_text,
                "local_text_paths": work.local_text_paths,
                "aozora_card_url": "",
                "aozora_text_url": "",
                "status": status,
                "notes": note,
            }
        )

    payload = {
        "description": "右門捕物帖本文補完用 manifest。ローカル本文突合と青空照合状態を管理する。",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }
    OUT_MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_html(works: list[Work], bundles: list[Bundle]) -> None:
    payload = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "works": [
            {
                "title": w.title,
                "views": w.views,
                "duration_minutes": w.duration_seconds // 60,
                "retention": w.avg_view_duration_ratio,
                "has_local_text": w.has_local_text,
                "local_text_paths": w.local_text_paths,
            }
            for w in works
        ],
        "bundles": [
            {
                "volume_label": b.volume_label,
                "custom_title": b.custom_title,
                "works": b.works,
                "note": b.note,
                "theme": b.compilation_theme,
            }
            for b in bundles
        ],
    }
    data = json.dumps(payload, ensure_ascii=False)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = """<!doctype html>
<html lang=\"ja\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>右門捕物帖 Compilation Viewer</title>
<style>
:root {{
  --bg: #f4efe7;
  --panel: #fff9f0;
  --ink: #2d2218;
  --muted: #6f5c49;
  --accent: #8a2f1f;
  --line: #dcc9b3;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: \"Hiragino Mincho ProN\", \"Yu Mincho\", serif; background: radial-gradient(circle at 15% 0%, #fff7ea, #f4efe7 60%, #e8dccb 100%); color: var(--ink); }}
main {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
.hero {{ background: linear-gradient(135deg, #8a2f1f, #b45f30); color: #fff4e8; border-radius: 20px; padding: 20px; }}
.hero h1 {{ margin: 0 0 8px; }}
.hero p {{ margin: 0; }}
.grid {{ display: grid; grid-template-columns: 320px 1fr; gap: 16px; margin-top: 16px; }}
.panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 14px; }}
.bundle {{ border: 1px solid var(--line); border-radius: 12px; padding: 10px; margin-bottom: 10px; background: #fffdf8; }}
.badge {{ display: inline-block; padding: 2px 8px; border: 1px solid var(--line); border-radius: 999px; margin-right: 6px; font-size: 12px; color: var(--muted); }}
.ok {{ color: #1f6b47; border-color: #7eb99a; }}
.ng {{ color: #8f3e24; border-color: #e0a183; }}
small {{ color: var(--muted); }}
@media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
  <section class=\"hero\">
    <h1>右門捕物帖 総集編 Viewer</h1>
    <p>右門作品の総集編案と本文在庫を同時に確認するローカルページ</p>
        <small>Generated at __GENERATED_AT__</small>
  </section>
  <section class=\"grid\">
    <aside class=\"panel\" id=\"bundleList\"></aside>
    <article class=\"panel\" id=\"workList\"></article>
  </section>
</main>
<script>
const DATA = __DATA_JSON__;
const bundleList = document.getElementById('bundleList');
const workList = document.getElementById('workList');

bundleList.innerHTML = `<h2>バンドル ${'{'}DATA.bundles.length{'}'}件</h2>` +
  DATA.bundles.map((b, idx) => `
    <div class=\"bundle\">
      <div><strong>${'{'}b.volume_label{'}'}</strong></div>
      <div>${'{'}b.custom_title{'}'}</div>
      <small>${'{'}b.theme{'}'}</small>
      <div style=\"margin-top:6px;\">${'{'}b.works.map(w => `<span class=\\\"badge\\\">${'{'}w{'}'}</span>`).join(''){'}'}</div>
      <small>${'{'}b.note{'}'}</small>
    </div>
  `).join('');

workList.innerHTML = `<h2>作品 ${'{'}DATA.works.length{'}'}件</h2>` +
  DATA.works.map((w) => {
    const cls = w.has_local_text ? 'ok' : 'ng';
    const txt = w.has_local_text ? '本文あり' : '本文不足';
    const paths = (w.local_text_paths || []).join(' / ') || '—';
    return `
      <div class=\"bundle\">
        <div><strong>${'{'}w.title{'}'}</strong> <span class=\"badge ${'{'}cls{'}'}\">${'{'}txt{'}'}</span></div>
        <small>再生 ${'{'}w.views.toLocaleString(){'}'} / 維持率 ${'{'}w.retention.toFixed(2){'}'} / 約${'{'}w.duration_minutes{'}'}分</small>
        <div><small>${'{'}paths{'}'}</small></div>
      </div>
    `;
  }).join('');
</script>
</body>
</html>
"""
    html = html.replace("__GENERATED_AT__", generated_at)
    html = html.replace("__DATA_JSON__", data)
    OUT_HTML.write_text(html, encoding="utf-8")


def main() -> int:
    works = build_works()
    bundles = make_bundles(works)

    write_works_csv(works)
    write_performance_csv(works)
    write_plan_md(works, bundles)
    write_bundles_json(works, bundles)
    write_manifest(works)
    write_html(works, bundles)

    print(f"Wrote: {OUT_WORKS_CSV.relative_to(ROOT)}")
    print(f"Wrote: {OUT_PERF_CSV.relative_to(ROOT)}")
    print(f"Wrote: {OUT_PLAN_MD.relative_to(ROOT)}")
    print(f"Wrote: {OUT_BUNDLES_JSON.relative_to(ROOT)}")
    print(f"Wrote: {OUT_MANIFEST.relative_to(ROOT)}")
    print(f"Wrote: {OUT_HTML.relative_to(ROOT)}")
    print(f"Works: {len(works)}")
    print(f"Bundles: {len(bundles)}")
    print(f"Local text present: {sum(1 for w in works if w.has_local_text)}")
    print(f"Needs text: {sum(1 for w in works if not w.has_local_text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
