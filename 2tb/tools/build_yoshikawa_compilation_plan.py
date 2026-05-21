#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""吉川英治 短篇総集編バンドル計画生成スクリプト

カタログ (yoshikawa_works_catalog.csv) + 旧チャンネルパフォーマンスデータ
(old_channel_report/video_master_enriched.csv) に基づき、
単発短篇35作品 + 剣の四君子4作品のテーマ別バンドル計画を生成する。

出力:
  - yoshikawa_compilation_plan.md   (詳細レポート)
  - yoshikawa_adopted_bundles.json  (機械可読バンドル定義)
  - yoshikawa_community_post_2026.md (コミュニティ投稿用メモ)
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CATALOG_CSV = REPORTS / "yoshikawa_works_catalog.csv"
PERF_CSV = (
    ROOT / "youtube_channel_report" / "old_channel_report" / "video_master_enriched.csv"
)
OUT_PLAN_MD = REPORTS / "yoshikawa_compilation_plan.md"
OUT_BUNDLES_JSON = REPORTS / "yoshikawa_adopted_bundles.json"
OUT_COMMUNITY_MD = REPORTS / "yoshikawa_community_post_2026.md"
OUT_HTML = REPORTS / "yoshikawa_compilation.html"

# ─── 総集編バンドル対象 ──────────────────────────────
# 単発35作品 + 剣の四君子シリーズ4作品 = 計39作品
# シリーズ大作 (新書太閤記/宮本武蔵/鳴門秘帖/江戸城心中/新編忠臣蔵/篝火の女) は
# 別途「シリーズ総集編」として扱うため、本計画では除外。

SERIES_EXCLUDED = {"新書太閤記", "宮本武蔵", "鳴門秘帖", "江戸城心中", "新編忠臣蔵", "篝火の女"}

# 剣の四君子は4作品をまとめて特別編とする
KENSHI_TITLES = {
    "剣の四君子 林崎甚助",
    "剣の四君子 柳生石舟斎",
    "剣の四君子 小野忠明",
    "剣の四君子 高橋泥舟",
}

# ─── ジャンル再分類 ──────────────────────────────────
# カタログの primary_genre をベースに、テーマ組み向けに微調整
# key = カタログの title, value = 総集編向け大分類
GENRE_OVERRIDE: dict[str, str] = {
    # 仇討ち・復讐 + ミステリーを「仇討ち・闇の物語」に統合
    "ナンキン墓の夢": "仇討ち・闇の物語",
    "八寒道中":     "仇討ち・闇の物語",
    "べんがら炬燵":  "仇討ち・闇の物語",
}


# ─── 総集編バンドル定義 ──────────────────────────────
@dataclass
class Bundle:
    sequence: int
    volume_label: str
    compilation_theme: str
    custom_title: str
    works: list[str]       # カタログ title のリスト
    size: int
    category: str
    note: str = ""


BUNDLE_PLAN: list[Bundle] = [
    # ━━ 剣豪・武家（8作品 → 3バンドル） ━━
    Bundle(1, "第一集", "吉川剣豪譚",
           "吉川英治短篇 総集編 吉川剣豪譚",
           ["鬼", "洟かみ浪人", "無宿人国記"], 3, "剣豪・武家",
           "元禄の忠臣から浪人の矜持、流浪の剣客まで。吉川英治が描く武士の世界。"),
    Bundle(2, "第二集", "剣客の道",
           "吉川英治短篇 総集編 剣客の道",
           ["柳生月影抄", "大谷刑部", "脚"], 3, "剣豪・武家",
           "柳生新陰流の月下の斬合い、関ヶ原に散った知将、達人の業。剣に生きた男たちの物語。"),
    Bundle(3, "第三集", "武家の残照",
           "吉川英治短篇 総集編 武家の残照",
           ["醤油仏", "細川ガラシャ夫人"], 2, "剣豪・武家",
           "武家社会の裏面を照らす二篇。醤油仏の奇譚と、信仰に殉じたガラシャの物語。"),

    # ━━ 人情・市井・下町（11作品 → 4バンドル） ━━
    Bundle(4, "第四集", "江戸の灯",
           "吉川英治短篇 総集編 江戸の灯",
           ["鍋島甲斐守", "野槌の百", "夏虫行燈"], 3, "人情・市井・下町",
           "鍋島藩の怪に始まり、長屋の人情、夏の宵の幻想。江戸の夜を照らす三篇。"),
    Bundle(5, "第五集", "下町の四季",
           "吉川英治短篇 総集編 下町の四季",
           ["夕顔の門", "魚紋", "春の雁"], 3, "人情・市井・下町",
           "夕顔・魚・雁。自然の姿に人の情を重ねる吉川英治の市井小説三篇。"),
    Bundle(6, "第六集", "市井の肖像",
           "吉川英治短篇 総集編 市井の肖像",
           ["次郎吉格子", "御鷹", "銀河まつり"], 3, "人情・市井・下町",
           "義賊の末路、鬱屈した鷹匠、七夕の夜。江戸の暮らしの断面を描く三篇。"),
    Bundle(7, "第七集", "小さきものの声",
           "吉川英治短篇 総集編 小さきものの声",
           ["しんだ千鳥", "下頭橋由来"], 2, "人情・市井・下町",
           "千鳥の哀切と橋の由来。市井の片隅に光を当てる小品二篇。"),

    # ━━ 歴史・実録（9作品 → 3バンドル） ━━
    Bundle(8, "第八集", "幕末群像",
           "吉川英治短篇 総集編 幕末群像",
           ["山浦清麿", "田崎早雲とその子", "飢えたる彰義隊"], 3, "歴史・実録",
           "名刀鍛冶の生涯、志士の父子、壮絶な彰義隊。幕末の熱い風が吹く三篇。"),
    Bundle(9, "第九集", "戦国余話",
           "吉川英治短篇 総集編 戦国余話",
           ["茶漬三略", "太閤夫人", "静御前"], 3, "歴史・実録",
           "秀吉の知略、北政所の情愛、義経の愛妾。歴史の陰に隠れた人間ドラマ三篇。"),
    Bundle(10, "第十集", "文人と巡査",
           "吉川英治短篇 総集編 文人と巡査",
           ["玉堂琴士", "梅颸の杖", "旗岡巡査"], 3, "歴史・実録",
           "画家の風雅、学者の矜持、維新後の巡査。時代を映す三つの肖像。"),

    # ━━ 仇討ち・闇の物語（2+1=3作品 → 1バンドル） ━━
    Bundle(11, "第十一集", "復讐と謎",
           "吉川英治短篇 総集編 復讐と謎",
           ["八寒道中", "べんがら炬燵", "ナンキン墓の夢"], 3, "仇討ち・闇の物語",
           "雪中の仇討ち、復讐の炬燵、墓場の怪。吉川英治の暗い情念が渦巻く三篇。"),

    # ━━ 異色の単品（2作品） ━━
    Bundle(12, "第十二集", "雲霧閻魔帳",
           "吉川英治短篇 総集編 雲霧閻魔帳",
           ["雲霧閻魔帳"], 1, "捕物帳",
           "大盗賊・雲霧仁左衛門の捕物帳。約2時間の大作を単品で。"),
    Bundle(13, "第十三集", "増長天王",
           "吉川英治短篇 総集編 増長天王",
           ["増長天王"], 1, "職人・芸道",
           "仏師の矜持を描いた吉川英治の異色作。"),

    # ━━ 剣の四君子 特別編（4作品 → 1バンドル） ━━
    Bundle(14, "第十四集", "剣の四君子 完全版",
           "吉川英治短篇 総集編 剣の四君子 完全版",
           ["剣の四君子 林崎甚助", "剣の四君子 柳生石舟斎",
            "剣の四君子 小野忠明", "剣の四君子 高橋泥舟"], 4, "剣豪・武家（特別編）",
           "居合の祖から幕末の義士まで。四人の剣聖の生涯を一挙に聴く特別編。"),
]


# ─── データ読み込み ──────────────────────────────────

def load_catalog() -> dict[str, dict]:
    """カタログCSV読み込み。key = title"""
    with open(CATALOG_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return {
            row["title"]: {
                "sort_order": int(row["sort_order"]),
                "title": row["title"],
                "work_type": row["work_type"],
                "video_count": int(row["video_count"]),
                "primary_genre": row["primary_genre"],
                "primary_era": row["primary_era"],
                "has_local_text": row["has_local_text"] == "yes",
            }
            for row in reader
        }


def _match_video_to_work(title: str, catalog_titles: list[str]) -> str | None:
    """動画タイトルからカタログ作品名をマッチ。長い作品名を優先。"""
    matched = [ct for ct in catalog_titles if ct in title]
    if not matched:
        return None
    # 最長マッチ（「剣の四君子 小野忠明」を「鬼」より優先）
    return max(matched, key=len)


def load_performance(catalog: dict[str, dict]) -> dict[str, dict]:
    """旧チャンネルレポートから作品別パフォーマンスを抽出。
    各作品について最も再生数の多い normal_video のデータを保持。"""
    catalog_titles = sorted(catalog.keys(), key=len, reverse=True)
    best: dict[str, dict] = {}

    with open(PERF_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("content_type_bucket") != "normal_video":
                continue

            work = _match_video_to_work(row["title"], catalog_titles)
            if not work:
                continue

            views = int(row["views"]) if row["views"] else 0
            dur = int(row["duration_seconds"]) if row["duration_seconds"] else 0
            avg_view = int(row["averageViewDuration"]) if row["averageViewDuration"] else 0
            retention = (avg_view / dur * 100) if dur > 0 else 0

            entry = {
                "videoId": row["videoId"],
                "title": row["title"],
                "views": views,
                "estimatedMinutesWatched": int(row["estimatedMinutesWatched"]) if row["estimatedMinutesWatched"] else 0,
                "averageViewDuration": avg_view,
                "duration_seconds": dur,
                "retention": round(retention, 1),
                "impressions": int(row["impressions"]) if row["impressions"] else 0,
                "impressionCtr": float(row["impressionCtr"]) if row["impressionCtr"] else 0.0,
                "is_public": row.get("is_public", ""),
                "has_synopsis": row.get("has_description_synopsis", ""),
            }

            if work not in best or entry["views"] > best[work]["views"]:
                best[work] = entry

    return best


# ─── レポート生成 ─────────────────────────────────────

def generate_report(catalog: dict[str, dict], perf: dict[str, dict]) -> str:
    lines: list[str] = []
    lines.append("# 吉川英治 短篇総集編バンドル計画")
    lines.append("")

    # バンドル対象作品数
    bundle_works = set()
    for b in BUNDLE_PLAN:
        bundle_works.update(b.works)
    n_works = len(bundle_works)

    lines.append(f"- 対象: 単発短篇35作品 + 剣の四君子4作品 = 計{n_works}作品")
    lines.append(f"- バンドル数: {len(BUNDLE_PLAN)}")
    lines.append(f"  - 四話特別組: {sum(1 for b in BUNDLE_PLAN if b.size == 4)}本")
    lines.append(f"  - 三話組: {sum(1 for b in BUNDLE_PLAN if b.size == 3)}本")
    lines.append(f"  - 二話組: {sum(1 for b in BUNDLE_PLAN if b.size == 2)}本")
    lines.append(f"  - 単品: {sum(1 for b in BUNDLE_PLAN if b.size == 1)}本")
    lines.append(f"- 除外（シリーズ大作）: {', '.join(sorted(SERIES_EXCLUDED))}")
    lines.append("")

    # ── ジャンル別サマリー
    genre_counts: dict[str, int] = Counter()
    for title, w in catalog.items():
        if title in SERIES_EXCLUDED:
            continue
        genre = GENRE_OVERRIDE.get(title, w["primary_genre"])
        genre_counts[genre] += 1

    lines.append("## ジャンル別作品数")
    lines.append("")
    lines.append("| ジャンル | 作品数 |")
    lines.append("|---|---:|")
    for genre, cnt in sorted(genre_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {genre} | {cnt} |")
    lines.append("")

    # ── バンドル一覧
    lines.append("## 総集編バンドル一覧")
    lines.append("")

    current_cat = ""
    for b in BUNDLE_PLAN:
        if b.category != current_cat:
            current_cat = b.category
            lines.append(f"### 【{current_cat}】")
            lines.append("")

        size_label = {4: "四話特別組", 3: "三話組", 2: "二話組", 1: "単品"}[b.size]
        lines.append(f"#### {b.volume_label}「{b.compilation_theme}」（{size_label}）")
        lines.append("")
        lines.append(f"**{b.custom_title}**")
        lines.append("")

        # 各作品の詳細
        total_sec = 0
        for work_title in b.works:
            w = catalog.get(work_title, {})
            p = perf.get(work_title, {})
            genre = w.get("primary_genre", "—")
            era = w.get("primary_era", "—")
            views = p.get("views", "—")
            ret = p.get("retention", None)
            dur = p.get("duration_seconds", 0)
            total_sec += dur

            ret_str = f"{ret:.1f}%" if ret is not None else "—"
            views_str = f"{views:,}" if isinstance(views, int) else views
            dur_str = f"{dur // 60}分{dur % 60:02d}秒" if dur else "—"

            lines.append(f"- **{work_title}** [{genre} / {era}]")
            lines.append(f"  - 再生 {views_str} ／維持率 {ret_str} ／尺 {dur_str}")

        if total_sec > 0 and len(b.works) > 1:
            lines.append(f"- **合計尺: 約{total_sec // 60}分**")

        lines.append(f"- 構成メモ: {b.note}")
        lines.append("")

    # ── パフォーマンス注目作品
    lines.append("## パフォーマンス注目作品")
    lines.append("")

    # バンドル対象作品のパフォーマンスのみ
    bundle_perf = {
        title: p for title, p in perf.items()
        if title in bundle_works
    }

    # 作品→バンドル逆引き
    work_to_bundle: dict[str, str] = {}
    for b in BUNDLE_PLAN:
        for wt in b.works:
            work_to_bundle[wt] = b.volume_label

    lines.append("### 高再生数トップ10（アンカー候補）")
    lines.append("")
    lines.append("| 作品 | 再生数 | 維持率 | 尺 | バンドル |")
    lines.append("|---|---:|---:|---|---|")
    top_views = sorted(bundle_perf.items(), key=lambda x: -x[1]["views"])[:10]
    for title, p in top_views:
        dur_str = f"{p['duration_seconds'] // 60}分" if p['duration_seconds'] else "—"
        bname = work_to_bundle.get(title, "—")
        lines.append(
            f"| {title} | {p['views']:,} | {p['retention']:.1f}% | {dur_str} | {bname} |"
        )
    lines.append("")

    lines.append("### 高維持率トップ10")
    lines.append("")
    lines.append("| 作品 | 再生数 | 維持率 | 尺 | バンドル |")
    lines.append("|---|---:|---:|---|---|")
    top_ret = sorted(bundle_perf.items(), key=lambda x: -x[1]["retention"])[:10]
    for title, p in top_ret:
        dur_str = f"{p['duration_seconds'] // 60}分" if p['duration_seconds'] else "—"
        bname = work_to_bundle.get(title, "—")
        lines.append(
            f"| {title} | {p['views']:,} | {p['retention']:.1f}% | {dur_str} | {bname} |"
        )
    lines.append("")

    # ── パフォーマンスデータなしの作品
    no_perf = [
        title for title in sorted(bundle_works)
        if title not in perf
    ]
    if no_perf:
        lines.append("## パフォーマンスデータなしの作品")
        lines.append("")
        lines.append("| 作品 | ジャンル | バンドル |")
        lines.append("|---|---|---|")
        for title in no_perf:
            genre = catalog.get(title, {}).get("primary_genre", "—")
            bname = work_to_bundle.get(title, "—")
            lines.append(f"| {title} | {genre} | {bname} |")
        lines.append("")

    # ── シリーズ大作メモ
    lines.append("## シリーズ大作（本計画の対象外・別途検討）")
    lines.append("")
    lines.append("| 作品 | 動画数 | ジャンル | 時代 |")
    lines.append("|---|---:|---|---|")
    for title in sorted(SERIES_EXCLUDED):
        w = catalog.get(title, {})
        lines.append(
            f"| {title} | {w.get('video_count', '—')} | "
            f"{w.get('primary_genre', '—')} | {w.get('primary_era', '—')} |"
        )
    lines.append("")
    lines.append("これらのシリーズは、章別総集編やハイライト集として別途企画する。")
    lines.append("")

    return "\n".join(lines)


def generate_bundles_json(perf: dict[str, dict]) -> list[dict]:
    bundles = []
    for b in BUNDLE_PLAN:
        bundles.append({
            "sequence": b.sequence,
            "volume_label": b.volume_label,
            "bundle_id": f"yoshikawa-compilation-{b.sequence:02d}",
            "custom_title": b.custom_title,
            "works": b.works,
            "size": b.size,
            "category": b.category,
            "compilation_theme": b.compilation_theme,
            "note": b.note,
            "performance": {
                wt: {
                    "views": perf[wt]["views"],
                    "retention": perf[wt]["retention"],
                    "duration_seconds": perf[wt]["duration_seconds"],
                }
                for wt in b.works if wt in perf
            },
        })
    return bundles


def build_html_payload(catalog: dict[str, dict], perf: dict[str, dict]) -> dict[str, object]:
        bundle_works = sorted({work for bundle in BUNDLE_PLAN for work in bundle.works})
        categories = sorted({bundle.category for bundle in BUNDLE_PLAN})

        bundles = []
        for bundle in BUNDLE_PLAN:
                works = []
                total_views = 0
                total_duration = 0
                anchor_title = ""
                anchor_views = -1

                for title in bundle.works:
                        catalog_row = catalog.get(title, {})
                        perf_row = perf.get(title, {})
                        views = perf_row.get("views", 0)
                        total_views += views
                        total_duration += perf_row.get("duration_seconds", 0)
                        if views > anchor_views:
                                anchor_title = title
                                anchor_views = views

                        works.append({
                                "title": title,
                                "genre": catalog_row.get("primary_genre", "—"),
                                "era": catalog_row.get("primary_era", "—"),
                                "video_count": catalog_row.get("video_count", 0),
                                "has_local_text": catalog_row.get("has_local_text", False),
                                "views": perf_row.get("views"),
                                "retention": perf_row.get("retention"),
                                "duration_seconds": perf_row.get("duration_seconds"),
                        })

                bundles.append({
                        "sequence": bundle.sequence,
                        "volume_label": bundle.volume_label,
                        "category": bundle.category,
                        "compilation_theme": bundle.compilation_theme,
                        "custom_title": bundle.custom_title,
                        "size": bundle.size,
                        "note": bundle.note,
                        "works": works,
                        "total_views": total_views,
                        "total_duration_minutes": total_duration // 60,
                        "anchor_title": anchor_title,
                        "anchor_views": max(anchor_views, 0),
                })

        excluded_series = []
        for title in sorted(SERIES_EXCLUDED):
                row = catalog.get(title, {})
                excluded_series.append({
                        "title": title,
                        "video_count": row.get("video_count", 0),
                        "primary_genre": row.get("primary_genre", "—"),
                        "primary_era": row.get("primary_era", "—"),
                        "has_local_text": row.get("has_local_text", False),
                })

        top_anchors = []
        for title, row in sorted(
                ((title, perf[title]) for title in bundle_works if title in perf),
                key=lambda item: -item[1]["views"],
        )[:10]:
                top_anchors.append({
                        "title": title,
                        "views": row["views"],
                        "retention": row["retention"],
                        "duration_minutes": row["duration_seconds"] // 60,
                })

        return {
                "generated_at": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {
                        "bundle_count": len(BUNDLE_PLAN),
                        "work_count": len(bundle_works),
                        "category_count": len(categories),
                        "single_count": sum(1 for bundle in BUNDLE_PLAN if bundle.size == 1),
                        "four_pack_count": sum(1 for bundle in BUNDLE_PLAN if bundle.size == 4),
                        "three_pack_count": sum(1 for bundle in BUNDLE_PLAN if bundle.size == 3),
                        "two_pack_count": sum(1 for bundle in BUNDLE_PLAN if bundle.size == 2),
                },
                "categories": categories,
                "bundles": bundles,
                "excluded_series": excluded_series,
                "top_anchors": top_anchors,
        }


def render_html(payload: dict[str, object]) -> str:
        data_json = json.dumps(payload, ensure_ascii=False)
        html = """<!doctype html>
<html lang="ja">
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>吉川英治 総集編 Viewer</title>
    <style>
        :root {
            --bg: #f3eadb;
            --panel: rgba(255, 251, 245, 0.94);
            --panel-2: rgba(252, 246, 237, 0.98);
            --text: #2a2118;
            --muted: #6a5746;
            --border: rgba(122, 84, 48, 0.18);
            --accent: #8b3a2e;
            --accent-2: #c97b3d;
            --good: #226c49;
            --shadow: 0 18px 44px rgba(82, 54, 23, 0.12);
        }
        * { box-sizing: border-box; }
        body { margin: 0; font-family: "Hiragino Mincho ProN", "Yu Mincho", serif; background: radial-gradient(circle at top left, #fff7eb, #f3eadb 55%, #eadbc2 100%); color: var(--text); }
        a { color: inherit; }
        .page { max-width: 1420px; margin: 0 auto; padding: 28px; }
        .hero { background: linear-gradient(135deg, rgba(139,58,46,0.96), rgba(201,123,61,0.88)); color: #fff9f2; border-radius: 28px; padding: 28px; box-shadow: var(--shadow); position: relative; overflow: hidden; }
        .hero::after { content: ""; position: absolute; inset: auto -80px -120px auto; width: 260px; height: 260px; border-radius: 50%; background: rgba(255,255,255,0.08); }
        .hero h1 { margin: 0 0 8px; font-size: 34px; }
        .hero p { margin: 0; max-width: 860px; line-height: 1.8; color: rgba(255,249,242,0.92); }
        .hero-links { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }
        .hero-links a { text-decoration: none; border: 1px solid rgba(255,255,255,0.22); color: #fff9f2; border-radius: 999px; padding: 8px 12px; background: rgba(255,255,255,0.08); }
        .meta-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }
        .meta-card { background: rgba(255,255,255,0.12); border: 1px solid rgba(255,255,255,0.16); border-radius: 18px; padding: 14px 16px; }
        .meta-card strong { display: block; font-size: 22px; margin-bottom: 4px; }
        .layout { display: grid; grid-template-columns: 320px 1fr; gap: 20px; margin-top: 22px; }
        .panel { background: var(--panel); border: 1px solid var(--border); border-radius: 24px; box-shadow: var(--shadow); }
        .sidebar { padding: 18px; position: sticky; top: 18px; height: fit-content; }
        .section-title { font-size: 13px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); margin: 0 0 10px; }
        .control { display: grid; gap: 8px; margin-bottom: 16px; }
        .control input, .control select { width: 100%; border: 1px solid var(--border); background: #fffdf9; border-radius: 14px; padding: 11px 12px; font: inherit; color: var(--text); }
        .stat-list { display: grid; gap: 10px; margin-top: 8px; }
        .stat-item { background: var(--panel-2); border: 1px solid var(--border); border-radius: 18px; padding: 12px 14px; }
        .stat-item strong { display: block; margin-bottom: 4px; }
        .content { display: grid; gap: 20px; }
        .toolbar { display: flex; justify-content: space-between; gap: 12px; align-items: baseline; margin-bottom: 12px; }
        .bundles-panel, .series-panel, .anchors-panel { padding: 18px; }
        .bundle-grid, .anchors-grid, .series-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
        .bundle-card, .series-card, .anchor-card { background: var(--panel-2); border: 1px solid var(--border); border-radius: 20px; padding: 16px; display: grid; gap: 10px; }
        .bundle-card h3, .series-card h3, .anchor-card h3 { margin: 0; font-size: 22px; line-height: 1.35; }
        .meta-line { color: var(--muted); font-size: 14px; line-height: 1.6; }
        .badge-row { display: flex; flex-wrap: wrap; gap: 8px; }
        .badge { border-radius: 999px; padding: 5px 10px; font-size: 12px; background: rgba(201,123,61,0.12); color: #75431a; border: 1px solid rgba(201,123,61,0.18); }
        .badge.good { background: rgba(34,108,73,0.12); color: var(--good); border-color: rgba(34,108,73,0.2); }
        .works-list { display: grid; gap: 8px; }
        .work-row { border-top: 1px solid rgba(122, 84, 48, 0.12); padding-top: 8px; }
        .work-row:first-child { border-top: 0; padding-top: 0; }
        .work-title { font-weight: 700; }
        .summary { font-size: 14px; line-height: 1.75; color: var(--muted); }
        .empty { padding: 18px; border-radius: 18px; border: 1px dashed var(--border); color: var(--muted); background: rgba(255,255,255,0.46); }
        .footer { margin-top: 18px; color: var(--muted); font-size: 12px; text-align: right; }
        @media (max-width: 1100px) { .layout { grid-template-columns: 1fr; } .sidebar { position: static; } }
        @media (max-width: 800px) { .meta-grid, .bundle-grid, .anchors-grid, .series-grid { grid-template-columns: 1fr; } .page { padding: 16px; } .hero h1 { font-size: 28px; } }
    </style>
</head>
<body>
    <div class="page">
        <section class="hero">
            <h1>吉川英治 総集編 Viewer</h1>
            <p>吉川英治の短篇総集編計画を、カテゴリ・集数・アンカー作品ごとに見渡せるローカル閲覧ページです。既存の検索ページと同じく、ブラウザでそのまま開ける静的HTMLとして生成しています。</p>
            <div class="hero-links">
                <a href="yoshikawa_compilation_plan.md">計画Markdown</a>
                <a href="yoshikawa_community_post_2026.md">コミュニティ投稿メモ</a>
                <a href="yoshikawa_adopted_bundles.json">バンドルJSON</a>
            </div>
            <div class="meta-grid">
                <div class="meta-card"><strong id="metaBundles">0</strong><span>bundles</span></div>
                <div class="meta-card"><strong id="metaWorks">0</strong><span>works</span></div>
                <div class="meta-card"><strong id="metaCategories">0</strong><span>categories</span></div>
                <div class="meta-card"><strong id="metaSingles">0</strong><span>single releases</span></div>
            </div>
        </section>
        <div class="layout">
            <aside class="panel sidebar">
                <div class="section-title">Filters</div>
                <label class="control">
                    <span>検索</span>
                    <input id="queryInput" type="search" placeholder="集名・作品名・メモ" />
                </label>
                <label class="control">
                    <span>カテゴリ</span>
                    <select id="categoryFilter"><option value="">すべて</option></select>
                </label>
                <label class="control">
                    <span>構成</span>
                    <select id="sizeFilter">
                        <option value="">すべて</option>
                        <option value="4">四話特別組</option>
                        <option value="3">三話組</option>
                        <option value="2">二話組</option>
                        <option value="1">単品</option>
                    </select>
                </label>
                <div class="section-title">At a Glance</div>
                <div class="stat-list">
                    <div class="stat-item"><strong id="statThreePacks">0</strong><span>三話組</span></div>
                    <div class="stat-item"><strong id="statTwoPacks">0</strong><span>二話組</span></div>
                    <div class="stat-item"><strong id="statFourPacks">0</strong><span>四話特別組</span></div>
                    <div class="stat-item"><strong id="statSeries">0</strong><span>別途シリーズ企画</span></div>
                </div>
            </aside>
            <main class="content">
                <section class="panel bundles-panel">
                    <div class="toolbar">
                        <div>
                            <div class="section-title">Bundles</div>
                            <div class="meta-line" id="bundleSummary"></div>
                        </div>
                    </div>
                    <div id="bundleGrid" class="bundle-grid"></div>
                </section>
                <section class="panel anchors-panel">
                    <div class="toolbar">
                        <div>
                            <div class="section-title">Top Anchors</div>
                            <div class="meta-line">高再生の柱になっている作品を上位表示</div>
                        </div>
                    </div>
                    <div id="anchorsGrid" class="anchors-grid"></div>
                </section>
                <section class="panel series-panel">
                    <div class="toolbar">
                        <div>
                            <div class="section-title">Series For Separate Planning</div>
                            <div class="meta-line">長編シリーズは別ページ構成向けに切り分け</div>
                        </div>
                    </div>
                    <div id="seriesGrid" class="series-grid"></div>
                </section>
            </main>
        </div>
        <div class="footer">Generated at __GENERATED_AT__ / source: yoshikawa_adopted_bundles.json + yoshikawa_works_catalog.csv</div>
    </div>
    <script>
        const APP_DATA = __DATA_JSON__;
        const bundles = Array.isArray(APP_DATA.bundles) ? APP_DATA.bundles : [];
        const anchors = Array.isArray(APP_DATA.top_anchors) ? APP_DATA.top_anchors : [];
        const excludedSeries = Array.isArray(APP_DATA.excluded_series) ? APP_DATA.excluded_series : [];
        const summary = APP_DATA.summary || {};
        const els = {
            metaBundles: document.getElementById('metaBundles'),
            metaWorks: document.getElementById('metaWorks'),
            metaCategories: document.getElementById('metaCategories'),
            metaSingles: document.getElementById('metaSingles'),
            statThreePacks: document.getElementById('statThreePacks'),
            statTwoPacks: document.getElementById('statTwoPacks'),
            statFourPacks: document.getElementById('statFourPacks'),
            statSeries: document.getElementById('statSeries'),
            queryInput: document.getElementById('queryInput'),
            categoryFilter: document.getElementById('categoryFilter'),
            sizeFilter: document.getElementById('sizeFilter'),
            bundleSummary: document.getElementById('bundleSummary'),
            bundleGrid: document.getElementById('bundleGrid'),
            anchorsGrid: document.getElementById('anchorsGrid'),
            seriesGrid: document.getElementById('seriesGrid'),
        };

        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
        }

        function formatViews(value) {
            if (value === null || value === undefined || value === '') return '—';
            return Number(value).toLocaleString('ja-JP');
        }

        function populateSelect(select, values) {
            values.forEach((value) => {
                const option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                select.appendChild(option);
            });
        }

        function bundleMatches(bundle) {
            const query = String(els.queryInput.value || '').trim().toLowerCase();
            const worksText = (bundle.works || []).map((work) => [work.title, work.genre, work.era].join(' ')).join(' ');
            const haystack = [bundle.volume_label, bundle.compilation_theme, bundle.custom_title, bundle.note, worksText].join(' ').toLowerCase();
            if (query && !haystack.includes(query)) return false;
            if (els.categoryFilter.value && bundle.category !== els.categoryFilter.value) return false;
            if (els.sizeFilter.value && String(bundle.size) !== els.sizeFilter.value) return false;
            return true;
        }

        function renderBundleCard(bundle) {
            const sizeLabel = ({4: '四話特別組', 3: '三話組', 2: '二話組', 1: '単品'})[bundle.size] || `${bundle.size}話`;
            const badges = [
                `<span class="badge">${escapeHtml(bundle.category)}</span>`,
                `<span class="badge">${escapeHtml(sizeLabel)}</span>`,
                bundle.anchor_title ? `<span class="badge good">柱 ${escapeHtml(bundle.anchor_title)}</span>` : '',
            ].filter(Boolean).join('');
            const worksHtml = (bundle.works || []).map((work) => {
                const perf = work.views || work.retention || work.duration_seconds
                    ? `再生 ${formatViews(work.views)} / 維持率 ${work.retention ?? '—'}% / 尺 ${work.duration_seconds ? Math.floor(work.duration_seconds / 60) + '分' : '—'}`
                    : 'パフォーマンス未集計';
                return `
                    <div class="work-row">
                        <div class="work-title">${escapeHtml(work.title)}</div>
                        <div class="meta-line">${escapeHtml(work.genre || '—')} / ${escapeHtml(work.era || '—')} / 配信本数 ${escapeHtml(work.video_count ?? 0)}</div>
                        <div class="meta-line">${perf}</div>
                    </div>`;
            }).join('');
            return `
                <article class="bundle-card">
                    <div class="meta-line">${escapeHtml(bundle.volume_label)}</div>
                    <h3>${escapeHtml(bundle.compilation_theme)}</h3>
                    <div class="badge-row">${badges}</div>
                    <div class="meta-line">総再生 ${formatViews(bundle.total_views)} / 合計尺 約${escapeHtml(bundle.total_duration_minutes)}分</div>
                    <div class="summary">${escapeHtml(bundle.note || '')}</div>
                    <div class="works-list">${worksHtml}</div>
                </article>`;
        }

        function renderAnchorCard(item, index) {
            return `
                <article class="anchor-card">
                    <div class="meta-line">#${index + 1}</div>
                    <h3>${escapeHtml(item.title)}</h3>
                    <div class="badge-row">
                        <span class="badge good">再生 ${formatViews(item.views)}</span>
                        <span class="badge">維持率 ${escapeHtml(item.retention)}%</span>
                        <span class="badge">尺 ${escapeHtml(item.duration_minutes)}分</span>
                    </div>
                </article>`;
        }

        function renderSeriesCard(item) {
            const badges = [
                `<span class="badge">動画 ${escapeHtml(item.video_count)}</span>`,
                `<span class="badge">${escapeHtml(item.primary_genre)}</span>`,
                item.has_local_text ? `<span class="badge good">本文あり</span>` : '',
            ].filter(Boolean).join('');
            return `
                <article class="series-card">
                    <h3>${escapeHtml(item.title)}</h3>
                    <div class="badge-row">${badges}</div>
                    <div class="meta-line">${escapeHtml(item.primary_era || '—')}</div>
                </article>`;
        }

        function renderBundles() {
            const filtered = bundles.filter(bundleMatches);
            els.bundleSummary.textContent = `${filtered.length} / ${bundles.length}集表示`;
            els.bundleGrid.innerHTML = filtered.length ? filtered.map(renderBundleCard).join('') : '<div class="empty">条件に一致する総集編がありません。</div>';
        }

        function renderMeta() {
            els.metaBundles.textContent = String(summary.bundle_count || bundles.length || 0);
            els.metaWorks.textContent = String(summary.work_count || 0);
            els.metaCategories.textContent = String(summary.category_count || 0);
            els.metaSingles.textContent = String(summary.single_count || 0);
            els.statThreePacks.textContent = String(summary.three_pack_count || 0);
            els.statTwoPacks.textContent = String(summary.two_pack_count || 0);
            els.statFourPacks.textContent = String(summary.four_pack_count || 0);
            els.statSeries.textContent = String(excludedSeries.length);
        }

        function init() {
            populateSelect(els.categoryFilter, Array.isArray(APP_DATA.categories) ? APP_DATA.categories : []);
            renderMeta();
            renderBundles();
            els.anchorsGrid.innerHTML = anchors.length ? anchors.map(renderAnchorCard).join('') : '<div class="empty">アンカー候補はありません。</div>';
            els.seriesGrid.innerHTML = excludedSeries.length ? excludedSeries.map(renderSeriesCard).join('') : '<div class="empty">別途シリーズ企画はありません。</div>';
            [els.queryInput, els.categoryFilter, els.sizeFilter].forEach((el) => el.addEventListener('input', renderBundles));
            [els.categoryFilter, els.sizeFilter].forEach((el) => el.addEventListener('change', renderBundles));
        }

        init();
    </script>
</body>
</html>
"""
        return html.replace("__DATA_JSON__", data_json).replace("__GENERATED_AT__", str(payload["generated_at"]))


# ─── コミュニティ投稿メモ生成 ─────────────────────────

def generate_community_post(catalog: dict[str, dict], perf: dict[str, dict]) -> str:
    lines: list[str] = []
    lines.append("# 吉川英治短篇 総集編 コミュニティ投稿用メモ")
    lines.append("")
    lines.append("このメモは、単発短篇35作品＋剣の四君子4作品のジャンル別バンドル計画をもとにまとめた版です。")
    lines.append("")

    bundle_works = set()
    for b in BUNDLE_PLAN:
        bundle_works.update(b.works)

    lines.append(f"- 対象作品数: {len(bundle_works)}作品（単発短篇＋剣の四君子）")
    lines.append(f"- 総集編は全{len(BUNDLE_PLAN)}集")
    n3 = sum(1 for b in BUNDLE_PLAN if b.size == 3)
    n2 = sum(1 for b in BUNDLE_PLAN if b.size == 2)
    n4 = sum(1 for b in BUNDLE_PLAN if b.size == 4)
    n1 = sum(1 for b in BUNDLE_PLAN if b.size == 1)
    parts = []
    if n3:
        parts.append(f"三話組{n3}本")
    if n4:
        parts.append(f"四話特別組{n4}本")
    if n2:
        parts.append(f"二話組{n2}本")
    if n1:
        parts.append(f"単品{n1}本")
    lines.append(f"- {' / '.join(parts)}")
    lines.append(f"- シリーズ大作（新書太閤記・宮本武蔵・鳴門秘帖等）は別途企画")
    lines.append("")

    # ── 短文版
    lines.append("## コミュニティ欄用 短文版")
    lines.append("")
    lines.append("吉川英治の短篇作品の総集編について、お知らせです。")
    lines.append("")
    lines.append("これまでに配信した吉川英治の短篇を、ジャンルごとにまとめた総集編をお届けしていきます。")
    lines.append("新書太閤記や宮本武蔵などのシリーズ大作は別途まとめる予定です。")
    lines.append("")

    # バンドルをカテゴリ別に
    cat_bundles: dict[str, list[Bundle]] = defaultdict(list)
    for b in BUNDLE_PLAN:
        cat_bundles[b.category].append(b)

    for cat, bundles in cat_bundles.items():
        lines.append(f"【{cat}】全{len(bundles)}集")
        for b in bundles:
            works_str = "・".join(b.works)
            if b.size == 1:
                lines.append(f"{b.volume_label}「{b.compilation_theme}」（単品）")
            else:
                lines.append(f"{b.volume_label}「{b.compilation_theme}」{works_str}")
        lines.append("")

    lines.append("「この組合せで聴きたい」「この話は単品の方がいい」などのご意見があれば、コメントで教えてください。")
    lines.append("")

    # ── 丁寧版
    lines.append("## コミュニティ欄用 丁寧な文面版")
    lines.append("")
    lines.append("吉川英治の短篇作品の総集編について、お知らせです。")
    lines.append("")
    lines.append("これまでに配信してきた吉川英治の単発短篇と「剣の四君子」シリーズを合わせて、")
    lines.append(f"全{len(bundle_works)}作品をジャンルごとに分類し、総集編としてまとめていくことにしました。")
    lines.append("")
    lines.append("新書太閤記・宮本武蔵・鳴門秘帖などのシリーズ大作は、別途シリーズごとにまとめる予定です。")
    lines.append("")

    # ジャンル別の話数
    cat_work_count: dict[str, int] = Counter()
    for b in BUNDLE_PLAN:
        cat_work_count[b.category] += len(b.works)

    lines.append("ジャンルと作品数はこうなっています。")
    lines.append("")
    for cat, bundles in cat_bundles.items():
        cnt = cat_work_count[cat]
        lines.append(f"- {cat}: {cnt}作品（総集編{len(bundles)}集）")
    lines.append("")

    lines.append(f"今後の配信予定（全{len(BUNDLE_PLAN)}集）:")
    lines.append("")

    for cat, bundles in cat_bundles.items():
        lines.append(f"【{cat}】")
        for b in bundles:
            size_label = {4: "四話特別組", 3: "三話組", 2: "二話組", 1: "単品"}[b.size]
            lines.append(f"{b.volume_label}「{b.compilation_theme}」")
            lines.append(f" {b.note}")
            works_str = "・".join(b.works)
            if b.size == 1:
                lines.append(f" → {works_str}（単品）")
            else:
                lines.append(f" → {works_str}")
            lines.append("")
        lines.append("")

    lines.append("三話ひと組を基本にしていますが、")
    lines.append("「武家の残照」「小さきものの声」は二話組、")
    lines.append("「雲霧閻魔帳」「増長天王」は内容の独自性から単品、")
    lines.append("「剣の四君子」は四作品をまとめた特別編として出す予定です。")
    lines.append("")
    lines.append("「この組合せがいい」「この話は別のジャンルの方が合うのでは」")
    lines.append("「単品で聴きたい話がある」など、ご意見があればコメントで教えてください。")
    lines.append("")

    # ── 手元確認用メモ
    lines.append("## 手元確認用メモ")
    lines.append("")
    lines.append("- 対象: 単発短篇35作品 + 剣の四君子4作品 = 計39作品")
    lines.append("- シリーズ大作（新書太閤記82本/宮本武蔵30本/鳴門秘帖29本/江戸城心中11本/新編忠臣蔵6本/篝火の女4本）は別途企画")
    lines.append("- ジャンル分類はカタログのprimary_genreをベース")
    lines.append("- 仇討ち・復讐(2作品) + ミステリー(1作品) は「復讐と謎」として三話組に統合")
    lines.append("- 捕物帳（雲霧閻魔帳）と職人・芸道（増長天王）は独自性から単品")
    lines.append("- 剣の四君子はシリーズ2作品＋単発2作品を合わせた特別編")

    # アンカー情報
    work_to_bundle: dict[str, str] = {}
    for b in BUNDLE_PLAN:
        for wt in b.works:
            work_to_bundle[wt] = b.volume_label

    anchors = sorted(
        [(t, p) for t, p in perf.items() if t in bundle_works],
        key=lambda x: -x[1]["views"],
    )[:6]
    if anchors:
        lines.append("- パフォーマンス上位のアンカー配置:")
        for title, p in anchors:
            bname = work_to_bundle.get(title, "—")
            lines.append(f"  - {title}({p['views']:,}再生) → {bname}の柱")

    # 高維持率
    high_ret = sorted(
        [(t, p) for t, p in perf.items() if t in bundle_works],
        key=lambda x: -x[1]["retention"],
    )[:4]
    if high_ret:
        lines.append("- 高維持率作品:")
        for title, p in high_ret:
            bname = work_to_bundle.get(title, "—")
            lines.append(f"  - {title}({p['retention']:.1f}%) → {bname}")

    lines.append("")
    return "\n".join(lines)


# ─── メイン ───────────────────────────────────────

def main():
    catalog = load_catalog()
    perf = load_performance(catalog)
    bundle_works = {work for bundle in BUNDLE_PLAN for work in bundle.works}

    # Markdown レポート
    report = generate_report(catalog, perf)
    OUT_PLAN_MD.write_text(report, encoding="utf-8")
    print(f"✓ レポート出力: {OUT_PLAN_MD}")

    # JSON 出力
    bundles_data = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "total_works": len(bundle_works),
        "series_excluded": sorted(SERIES_EXCLUDED),
        "bundle_count": len(BUNDLE_PLAN),
        "four_packs": sum(1 for b in BUNDLE_PLAN if b.size == 4),
        "three_packs": sum(1 for b in BUNDLE_PLAN if b.size == 3),
        "two_packs": sum(1 for b in BUNDLE_PLAN if b.size == 2),
        "singles": sum(1 for b in BUNDLE_PLAN if b.size == 1),
        "adopted_bundles": generate_bundles_json(perf),
    }
    OUT_BUNDLES_JSON.write_text(
        json.dumps(bundles_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ バンドルJSON出力: {OUT_BUNDLES_JSON}")

    # コミュニティ投稿メモ
    community = generate_community_post(catalog, perf)
    OUT_COMMUNITY_MD.write_text(community, encoding="utf-8")
    print(f"✓ コミュニティ投稿メモ出力: {OUT_COMMUNITY_MD}")

    # 静的HTML閲覧ページ
    html_payload = build_html_payload(catalog, perf)
    OUT_HTML.write_text(render_html(html_payload), encoding="utf-8")
    print(f"✓ HTML Viewer出力: {OUT_HTML}")

    # サマリー表示
    print()
    print("=== 吉川英治短篇 総集編バンドル計画サマリー ===")
    print(f"全{len(BUNDLE_PLAN)}バンドル")
    print(f"  四話特別組: {sum(1 for b in BUNDLE_PLAN if b.size == 4)}本")
    print(f"  三話組:     {sum(1 for b in BUNDLE_PLAN if b.size == 3)}本")
    print(f"  二話組:     {sum(1 for b in BUNDLE_PLAN if b.size == 2)}本")
    print(f"  単品:       {sum(1 for b in BUNDLE_PLAN if b.size == 1)}本")
    print()
    for b in BUNDLE_PLAN:
        works = ", ".join(b.works)
        print(f"  {b.volume_label}「{b.compilation_theme}」")
        print(f"    → {works}")


if __name__ == "__main__":
    main()
