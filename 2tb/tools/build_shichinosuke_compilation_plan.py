#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""七之助捕物帳 総集編バンドル計画生成スクリプト

全56話のあらすじ・テーマ・パフォーマンスデータに基づき、
大分類ごとの総集編バンドル（3話組・2話組・単品）を決定する。

使用済み: 第一集(1,2,3) 第二集(20,21,37) / 重複: 44=41
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
CATALOG_JSON = REPORTS / "shichinosuke_works_catalog.json"
PERF_CSV = REPORTS / "shichinosuke_channel_performance.csv"
OUT_BUNDLES_JSON = REPORTS / "shichinosuke_adopted_bundles.json"
OUT_PLAN_MD = REPORTS / "shichinosuke_compilation_plan.md"

USED_EPISODES = {1, 2, 3, 20, 21, 37}
DUPLICATE_EPISODES = {44}  # 44 = 41 (小指千両)

# ─── あらすじ読解に基づく再分類 ───────────────────────────
# 現行の機械分類 (精度~30%) を、全話あらすじ精読で修正
# compilation_category = 総集編向け大分類
RECLASSIFICATION: dict[int, str] = {
    # ── 怪異・幽霊・見世物 ──
    4:  "怪異・幽霊・見世物",   # 獄門首異変: 生首発見
    7:  "怪異・幽霊・見世物",   # 歎きの黒ン坊: 見世物小屋
    8:  "怪異・幽霊・見世物",   # 口笛の秘密: 見世物小屋の死体人形
    12: "怪異・幽霊・見世物",   # 春風幽霊: 幽霊騒ぎ
    13: "怪異・幽霊・見世物",   # 青空呪文: 呪文と心理操作
    15: "怪異・幽霊・見世物",   # 蛇女: 蛇使い・縁切り
    18: "怪異・幽霊・見世物",   # 赤い羽根の矢: 鬼の能面の呪い
    42: "怪異・幽霊・見世物",   # 狂い蝶: 心中偽装・女賊
    46: "怪異・幽霊・見世物",   # 宿借り仏: 亡霊と怪死
    50: "怪異・幽霊・見世物",   # 緋牡丹狂い: 死んだはずの男
    51: "怪異・幽霊・見世物",   # 人喰い花: 脅迫・折檻・怪しい花
    55: "怪異・幽霊・見世物",   # 熊娘: 香具師・旗本刺傷

    # ── 色恋・情念・嫉妬 ──
    16: "色恋・情念・嫉妬",    # 家鴨を飼う娘: 監禁と密会
    23: "色恋・情念・嫉妬",    # 佐賀堀の秘密: 心中騒ぎ
    24: "色恋・情念・嫉妬",    # お市観音: 亡き娘への追慕
    25: "色恋・情念・嫉妬",    # 強盗二人馬鹿: 嫉妬から殺人 (旧: 盗み)
    26: "色恋・情念・嫉妬",    # 消え失せた男: 変装殺人・色恋
    27: "色恋・情念・嫉妬",    # かえり提灯: 色と慾の二面
    30: "色恋・情念・嫉妬",    # お高祖頭巾: 女装殺人・嫉妬
    31: "色恋・情念・嫉妬",    # 女師匠: 捨てられた女の復讐
    35: "色恋・情念・嫉妬",    # 鳥追お巻: 夫の深い愛情
    36: "色恋・情念・嫉妬",    # 小夜しぐれ: 妾詐欺
    40: "色恋・情念・嫉妬",    # 水の深川: 師匠殺害・変装
    45: "色恋・情念・嫉妬",    # 魔法布呂敷: 女掏摸・嫉妬
    48: "色恋・情念・嫉妬",    # 蛇の眼の女: 復讐の連鎖
    52: "色恋・情念・嫉妬",    # 白鬼: 愛憎の渦
    53: "色恋・情念・嫉妬",    # 色魔殺し: 色男殺害
    54: "色恋・情念・嫉妬",    # 金猫銀猫: 料理屋対決・正体暴き

    # ── 家族・身売り・人情 ──
    5:  "家族・身売り・人情",   # さかさ天一坊: 妹を救う
    9:  "家族・身売り・人情",   # 人真似鳥の夢: 父娘再会
    10: "家族・身売り・人情",   # 大黑丸秘譚: 冤罪・娘の孝心
    11: "家族・身売り・人情",   # 鶯替騷動: 腰元失踪・家族の選択
    14: "家族・身売り・人情",   # 鐘撞堂の娘: 噂と迷信・縁組破談
    17: "家族・身売り・人情",   # 因果娘: 因果応報・弱者の搾取
    19: "家族・身売り・人情",   # 物言わぬ舟: 偽装自殺・親心
    29: "家族・身売り・人情",   # 六百六十六両二分: 冤罪・献身 (旧: 盗み)
    32: "家族・身売り・人情",   # 大江戸二人娘: 義侠心
    33: "家族・身売り・人情",   # 春宵手毬唄: 因果応報・親心
    34: "家族・身売り・人情",   # 蝦夷菊: 兄の無償の愛
    39: "家族・身売り・人情",   # 裏店仁義: 長屋の義侠心 (旧: 色恋)

    # ── 盗み・千両箱・悪党の企て ──
    6:  "盗み・千両箱・悪党の企て",  # 業平御殿: 鬼瓦盗難・島破り (旧: 怪異)
    22: "盗み・千両箱・悪党の企て",  # おろしゃ船挿話: 建白書盗難
    28: "盗み・千両箱・悪党の企て",  # きつね駕籠: 偽装誘拐
    38: "盗み・千両箱・悪党の企て",  # 射的競べの怪: 翡翠盗難
    41: "盗み・千両箱・悪党の企て",  # 小指千両: 身代金誘拐
    47: "盗み・千両箱・悪党の企て",  # 夢の首吊り: 偽装殺人・金
    49: "盗み・千両箱・悪党の企て",  # 石となった千両箱: 千両箱・すり替え

    # ── 仇討・復讐・怨念 ──
    43: "仇討・復讐・怨念",    # 謎の振袖: 惨殺・歪んだ愛情
    56: "仇討・復讐・怨念",    # 仇討幽霊: ゆすり・怪死連鎖
}

# ─── 総集編バンドル定義 ───────────────────────────────
# 各バンドル内の順序 = 収録順（重→軽→締め の構成）
# size: 3=三話組, 2=二話組, 1=単品
@dataclass
class Bundle:
    sequence: int
    volume_label: str
    compilation_theme: str
    custom_title: str
    episodes: list[int]
    size: int
    category: str
    note: str = ""


BUNDLE_PLAN: list[Bundle] = [
    # ━━ 既存 ━━
    Bundle(1, "第一集", "御用始め",
           "七之助捕物帳 総集編 花川戸の御用聞、三つの事件",
           [1, 2, 3], 3, "（既存・使用済み）",
           "第1話から第3話を採用した連番構成。"),
    Bundle(2, "第二集", "仇討・復讐・怨念",
           "七之助捕物帳 総集編 仇討・復讐・怨念編",
           [20, 21, 37], 3, "仇討・復讐・怨念",
           "『乞食の仇討』『小指物語』『南天お房』を採用。"),

    # ━━ 怪異・幽霊・見世物（12話 → 4バンドル） ━━
    Bundle(3, "第三集", "幽霊騒ぎ",
           "七之助捕物帳 総集編 幽霊騒ぎ三連",
           [12, 46, 42], 3, "怪異・幽霊・見世物",
           "幽霊の噂→亡霊の影→心中偽装。幽霊の正体が暴かれていく構成。"),
    Bundle(4, "第四集", "呪い・妖",
           "七之助捕物帳 総集編 呪いと妖の三篇",
           [13, 15, 18], 3, "怪異・幽霊・見世物",
           "呪文→蛇女→能面の呪い。超常的な恐怖が段階的に深まる。"),
    Bundle(5, "第五集", "見世物小屋",
           "七之助捕物帳 総集編 見世物小屋の闇",
           [4, 7, 8], 3, "怪異・幽霊・見世物",
           "獄門首→黒人見世物→死体人形。江戸の見世物と怪事件の三題。"),
    Bundle(6, "第六集", "花と毒",
           "七之助捕物帳 総集編 花と毒",
           [50, 51, 55], 3, "怪異・幽霊・見世物",
           "緋牡丹→人喰い花→熊娘。危うい美と獣性の三篇。"),

    # ━━ 色恋・情念・嫉妬（16話 → 5バンドル + 1バンドル[2話]） ━━
    Bundle(7, "第七集", "嫉妬の刃",
           "七之助捕物帳 総集編 嫉妬の刃",
           [25, 30, 40], 3, "色恋・情念・嫉妬",
           "嫉妬→女装殺人→変装殺人。嫉妬が殺意へ変わる三篇。"),
    Bundle(8, "第八集", "女の復讐",
           "七之助捕物帳 総集編 女の復讐",
           [31, 36, 45], 3, "色恋・情念・嫉妬",
           "捨てられた女→妾詐欺→女掏摸。女たちの逆襲三連。"),
    Bundle(9, "第九集", "消えた影",
           "七之助捕物帳 総集編 消えた影",
           [26, 27, 35], 3, "色恋・情念・嫉妬",
           "消えた男→偽装工作→濡れ衣の夫。消失と偽装の三題。"),
    Bundle(10, "第十集", "色恋沙汰",
           "七之助捕物帳 総集編 色恋沙汰",
           [16, 23, 24], 3, "色恋・情念・嫉妬",
           "監禁された娘→心中騒ぎ→亡き娘の観音像。恋の三形態。"),
    Bundle(11, "第十一集", "復讐の女",
           "七之助捕物帳 総集編 復讐の女",
           [48, 52, 53], 3, "色恋・情念・嫉妬",
           "蛇の目→白鬼→色魔殺し。愛憎が暴力に変わる三篇。"),
    Bundle(12, "第十二集", "金猫銀猫",
           "七之助捕物帳 総集編 金猫銀猫・料理屋対決",
           [54], 1, "色恋・情念・嫉妬",
           "※単品リリース。料理屋同士の対決という独自の軽い題材。再生データ確認後に判断。"),

    # ━━ 家族・身売り・人情（12話 → 4バンドル） ━━
    Bundle(13, "第十三集", "親子の絆",
           "七之助捕物帳 総集編 親子の絆",
           [9, 10, 34], 3, "家族・身売り・人情",
           "父娘再会→娘の孝心→兄の無償の愛。血のつながりが事件を動かす。"),
    Bundle(14, "第十四集", "冤罪と義侠",
           "七之助捕物帳 総集編 冤罪と義侠の三篇",
           [29, 32, 33], 3, "家族・身売り・人情",
           "無実を背負う→身を犠牲に→因果応報。義の心が真相を動かす。"),
    Bundle(15, "第十五集", "噂と迷信",
           "七之助捕物帳 総集編 噂と迷信",
           [5, 11, 14], 3, "家族・身売り・人情",
           "天一坊騒ぎ→鷽替の夜→轆轤首の噂。噂に振り回される人々。"),
    Bundle(16, "第十六集", "人情裁き",
           "七之助捕物帳 総集編 人情裁き",
           [17, 19, 39], 3, "家族・身売り・人情",
           "因果娘→偽装自殺→長屋の義侠。七之助の温情ある裁き三題。"),

    # ━━ 盗み・千両箱・悪党の企て（7話 → 2バンドル + 1単品） ━━
    Bundle(17, "第十七集", "千両箱を追え",
           "七之助捕物帳 総集編 千両箱を追え",
           [41, 47, 49], 3, "盗み・千両箱・悪党の企て",
           "身代金誘拐→偽装殺人→石の千両箱。金を巡る知恵比べ。"),
    Bundle(18, "第十八集", "盗賊の知恵",
           "七之助捕物帳 総集編 盗賊の知恵",
           [6, 28, 38], 3, "盗み・千両箱・悪党の企て",
           "鬼瓦盗難→偽装誘拐→翡翠盗難。盗みの手口が光る三篇。"),
    Bundle(19, "第十九集", "おろしゃ船挿話",
           "七之助捕物帳 総集編 おろしゃ船挿話",
           [22], 1, "盗み・千両箱・悪党の企て",
           "※単品リリース。異国の脅威と情報戦という唯一無二の題材。再生3,579・維持47%で単品でも十分。"),

    # ━━ 仇討・復讐・怨念（残2話 → 1バンドル[2話]） ━━
    Bundle(20, "第二十集", "仇討二題",
           "七之助捕物帳 総集編 仇討二題",
           [43, 56], 2, "仇討・復讐・怨念",
           "惨殺と死体盗難→ゆすりと怪死連鎖。仇討の執念が貫く二篇。"),
]

# ─── データ読み込み ──────────────────────────────────

def load_catalog() -> dict[int, dict]:
    with open(CATALOG_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return {w["serial_number"]: w for w in data["works"]}


def load_performance() -> dict[int, dict]:
    result: dict[int, dict] = {}
    with open(PERF_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sn = int(row["serial_number"])
            result[sn] = {
                "views": int(row["views"]),
                "retention": float(row["average_view_duration_percentage"]),
                "duration_sec": int(row["latest_duration_seconds"]),
                "rank": int(row["rank"]),
            }
    return result


# ─── レポート生成 ─────────────────────────────────────

def generate_report(
    catalog: dict[int, dict],
    perf: dict[int, dict],
) -> str:
    lines: list[str] = []
    lines.append("# 七之助捕物帳 総集編バンドル計画")
    lines.append("")
    lines.append(f"- 全話数: 56")
    lines.append(f"- 使用済み: {sorted(USED_EPISODES)} (第一集・第二集)")
    lines.append(f"- 重複除外: {sorted(DUPLICATE_EPISODES)} (No.44 = No.41 小指千両)")
    lines.append(f"- 残り: 49話")
    lines.append(f"- バンドル数: {len(BUNDLE_PLAN)} (既存2 + 新規{len(BUNDLE_PLAN)-2})")
    lines.append("")

    # ── 再分類サマリー
    from collections import Counter
    cat_counts = Counter(
        RECLASSIFICATION[sn] for sn in RECLASSIFICATION
        if sn not in USED_EPISODES and sn not in DUPLICATE_EPISODES
    )
    lines.append("## 再分類サマリー（あらすじ精読による修正後）")
    lines.append("")
    lines.append("| 大分類 | 残り話数 |")
    lines.append("|---|---:|")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| {cat} | {cnt} |")
    lines.append("")

    # ── 再分類の変更点
    lines.append("### 機械分類からの主な変更")
    lines.append("")
    changes = []
    for sn, new_cat in sorted(RECLASSIFICATION.items()):
        if sn in USED_EPISODES or sn in DUPLICATE_EPISODES:
            continue
        w = catalog.get(sn)
        if w and w["major_category"] != new_cat:
            changes.append((sn, w["short_title"], w["major_category"], new_cat))
    if changes:
        lines.append("| No. | 作品 | 旧分類 | 新分類 | 理由 |")
        lines.append("|---:|---|---|---|---|")
        change_reasons = {
            6:  "鬼瓦盗難・島破り一味が主題",
            25: "嫉妬から殺人が動機の中心",
            29: "冤罪・夫婦の献身が本筋",
            39: "長屋住人の義侠心が主題",
        }
        for sn, title, old, new in changes:
            reason = change_reasons.get(sn, "あらすじ精読による判断")
            lines.append(f"| {sn} | {title} | {old} | {new} | {reason} |")
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

        size_label = {3: "三話組", 2: "二話組", 1: "単品"}[b.size]
        lines.append(f"#### {b.volume_label}「{b.compilation_theme}」（{size_label}）")
        lines.append("")
        lines.append(f"**{b.custom_title}**")
        lines.append("")

        # エピソード詳細
        total_sec = 0
        for ep_num in b.episodes:
            w = catalog.get(ep_num, {})
            p = perf.get(ep_num, {})
            short = w.get("short_title", f"第{ep_num}話")
            syn = w.get("synopsis", "")[:100]
            views = p.get("views", "—")
            ret = p.get("retention", None)
            dur = p.get("duration_sec", 0)
            total_sec += dur

            ret_str = f"{ret:.1f}%" if ret is not None else "—"
            views_str = f"{views:,}" if isinstance(views, int) else views
            dur_str = f"{dur//60}分{dur%60:02d}秒" if dur else "—"

            used = " **【使用済み】**" if ep_num in USED_EPISODES else ""
            lines.append(f"- **No.{ep_num:02d} {short}**{used}")
            lines.append(f"  - あらすじ: {syn}…")
            lines.append(f"  - 再生 {views_str} ／維持率 {ret_str} ／尺 {dur_str}")
        
        if total_sec > 0 and len(b.episodes) > 1:
            lines.append(f"- **合計尺: 約{total_sec//60}分**")
        
        lines.append(f"- 構成メモ: {b.note}")
        lines.append("")

    # ── パフォーマンス注目エピソード
    lines.append("## パフォーマンス注目エピソード")
    lines.append("")
    lines.append("### 高維持率トップ10（単品候補 or アンカー）")
    lines.append("")
    lines.append("| No. | 作品 | 再生数 | 維持率 | バンドル |")
    lines.append("|---:|---|---:|---:|---|")
    
    available_perf = {
        sn: p for sn, p in perf.items()
        if sn not in USED_EPISODES and sn not in DUPLICATE_EPISODES
    }
    top_retention = sorted(available_perf.items(), key=lambda x: -x[1]["retention"])[:10]
    
    # episode→bundle lookup
    ep_to_bundle = {}
    for b in BUNDLE_PLAN:
        for ep in b.episodes:
            ep_to_bundle[ep] = b.volume_label
    
    for sn, p in top_retention:
        short = catalog.get(sn, {}).get("short_title", f"第{sn}話")
        bname = ep_to_bundle.get(sn, "—")
        lines.append(
            f"| {sn} | {short} | {p['views']:,} | {p['retention']:.1f}% | {bname} |"
        )
    
    lines.append("")
    lines.append("### 高再生数トップ10（アンカー候補）")
    lines.append("")
    lines.append("| No. | 作品 | 再生数 | 維持率 | バンドル |")
    lines.append("|---:|---|---:|---:|---|")
    
    top_views = sorted(available_perf.items(), key=lambda x: -x[1]["views"])[:10]
    for sn, p in top_views:
        short = catalog.get(sn, {}).get("short_title", f"第{sn}話")
        bname = ep_to_bundle.get(sn, "—")
        lines.append(
            f"| {sn} | {short} | {p['views']:,} | {p['retention']:.1f}% | {bname} |"
        )
    
    lines.append("")

    # ── 未配信エピソード
    lines.append("## 未配信エピソード（パフォーマンスデータなし）")
    lines.append("")
    no_perf = [
        sn for sn in sorted(RECLASSIFICATION)
        if sn not in perf and sn not in USED_EPISODES and sn not in DUPLICATE_EPISODES
    ]
    if no_perf:
        lines.append("| No. | 作品 | 新分類 | バンドル |")
        lines.append("|---:|---|---|---|")
        for sn in no_perf:
            short = catalog.get(sn, {}).get("short_title", f"第{sn}話")
            cat = RECLASSIFICATION.get(sn, "—")
            bname = ep_to_bundle.get(sn, "—")
            lines.append(f"| {sn} | {short} | {cat} | {bname} |")
    lines.append("")

    return "\n".join(lines)


def generate_bundles_json() -> list[dict]:
    """adopted_bundles.json 形式で出力"""
    bundles = []
    for b in BUNDLE_PLAN:
        bundles.append({
            "sequence": b.sequence,
            "volume_label": b.volume_label,
            "bundle_id": f"compilation-{b.sequence:02d}-{b.compilation_theme}",
            "custom_title": b.custom_title,
            "episodes": b.episodes,
            "size": b.size,
            "category": b.category,
            "compilation_theme": b.compilation_theme,
            "note": b.note,
        })
    return bundles


def main():
    catalog = load_catalog()
    perf = load_performance()

    # Markdown レポート
    report = generate_report(catalog, perf)
    OUT_PLAN_MD.write_text(report, encoding="utf-8")
    print(f"✓ レポート出力: {OUT_PLAN_MD}")

    # JSON 出力
    bundles_data = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "total_episodes": 56,
        "used_episodes": sorted(USED_EPISODES),
        "duplicate_episodes": sorted(DUPLICATE_EPISODES),
        "available_episodes": 49,
        "bundle_count": len(BUNDLE_PLAN),
        "three_packs": sum(1 for b in BUNDLE_PLAN if b.size == 3),
        "two_packs": sum(1 for b in BUNDLE_PLAN if b.size == 2),
        "singles": sum(1 for b in BUNDLE_PLAN if b.size == 1),
        "adopted_bundles": generate_bundles_json(),
    }
    OUT_BUNDLES_JSON.write_text(
        json.dumps(bundles_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"✓ バンドルJSON出力: {OUT_BUNDLES_JSON}")

    # サマリー表示
    print()
    print("=== 総集編バンドル計画サマリー ===")
    print(f"全20バンドル（既存2 + 新規18）")
    print(f"  三話組: {sum(1 for b in BUNDLE_PLAN if b.size == 3)}本")
    print(f"  二話組: {sum(1 for b in BUNDLE_PLAN if b.size == 2)}本")
    print(f"  単品:   {sum(1 for b in BUNDLE_PLAN if b.size == 1)}本")
    print()
    for b in BUNDLE_PLAN:
        eps = ", ".join(
            catalog.get(sn, {}).get("short_title", f"#{sn}")
            for sn in b.episodes
        )
        used = " 【使用済】" if b.sequence <= 2 else ""
        print(f"  {b.volume_label}「{b.compilation_theme}」{used}")
        print(f"    → {eps}")


if __name__ == "__main__":
    main()
