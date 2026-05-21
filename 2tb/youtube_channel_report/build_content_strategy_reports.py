#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build content planning CSV and strategy markdown reports.")
    parser.add_argument("--analysis-input", default="analysis_ready_normal_video.csv")
    parser.add_argument("--planning-output", default="content_planning_normal_video.csv")
    parser.add_argument("--zenigata-output", default="zenigata_strategy_report.md")
    parser.add_argument("--yamamoto-output", default="yamamoto_strategy_report.md")
    return parser.parse_args()


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def normalize_number(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def escape_md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def compute_metrics(row: Dict[str, str]) -> Dict[str, object]:
    title = row.get("title", "")
    watch_time = parse_float(row.get("watch_time_minutes"))
    if watch_time is None:
        watch_time = parse_float(row.get("estimatedMinutesWatched")) or 0.0
    avg_pct = parse_float(row.get("average_view_duration_percentage"))
    if avg_pct is None:
        avg_view_duration = parse_float(row.get("averageViewDuration"))
        duration_seconds = parse_int(row.get("duration_seconds"))
        if avg_view_duration is not None and duration_seconds:
            avg_pct = (avg_view_duration / duration_seconds) * 100
    views = parse_float(row.get("views")) or parse_float(row.get("statistics.viewCount")) or 0.0
    has_sleep = any(marker in title for marker in ["睡眠", "作業用", "睡眠導入", "BGM"])
    return {
        "watch_time_minutes": watch_time,
        "avg_view_pct": avg_pct,
        "views": views,
        "has_sleep_work_keyword": "true" if has_sleep or row.get("video_format") == "睡眠・作業用" else "false",
    }


def priority_bucket(series_name: str, watch_time: float, avg_pct: float | None) -> str:
    if series_name == "主題歌/MV":
        return "分離"
    if watch_time >= 20000:
        return "主力"
    if (avg_pct is not None and avg_pct >= 45) or watch_time >= 10000:
        return "準主力"
    if (avg_pct is not None and avg_pct >= 35) or watch_time >= 5000:
        return "育成"
    return "観測"


def publish_strategy(row: Dict[str, str], metrics: Dict[str, object]) -> str:
    series_name = row.get("series_name", "")
    video_format = row.get("video_format", "")
    if series_name == "主題歌/MV":
        return "通常動画戦略から分離してMV/主題歌枠で運用"
    if series_name == "怪談":
        return "メンバー向き寄りの深夜枠・怪談枠で運用"
    if video_format == "第一集":
        return "第一集フォーマットをシリーズ化"
    if video_format in {"三部作", "総集編/傑作選"}:
        return "まとめ企画として定期投入"
    if video_format == "長編連載":
        return "連載回として継続投稿"
    if video_format == "睡眠・作業用":
        return "睡眠・作業用の長尺枠で継続"
    if video_format == "聴くドラマ/一人でドラマ":
        return "演出強めのドラマ枠として展開"
    return "単話主軸で継続"


def recommended_next_action(row: Dict[str, str], metrics: Dict[str, object], bucket: str) -> str:
    series_name = row.get("series_name", "")
    video_format = row.get("video_format", "")
    if series_name == "主題歌/MV":
        return "通常朗読導線と切り分けて別管理"
    if series_name == "怪談":
        return "怪談特集またはメンバー向け怪談枠へ寄せる"
    if video_format == "第一集":
        return "同シリーズで第二集候補を組む"
    if video_format == "三部作":
        return "関連作の三本束ね再現を検討"
    if video_format == "総集編/傑作選":
        return "同テーマの再編集候補として維持"
    if video_format == "長編連載":
        return "次巻・次話を優先収録"
    if video_format == "睡眠・作業用":
        return "睡眠導線タイトルで横展開"
    if video_format == "聴くドラマ/一人でドラマ":
        return "演出寄せの同型企画を追加"
    if bucket in {"主力", "準主力"}:
        return "近い題材の単話を追加投入"
    return "反応観測を継続"


def suggested_title_pattern(row: Dict[str, str]) -> str:
    series_name = row.get("series_name", "")
    video_format = row.get("video_format", "")
    if series_name == "怪談":
        return "【怪談朗読】作品名｜睡眠・深夜向け｜七味春五郎"
    if video_format == "第一集":
        return "シリーズ名 第一集『テーマ名』｜三作まとめ｜七味春五郎"
    if video_format == "三部作":
        return "シリーズ名 三部作｜作品A・作品B・作品C｜七味春五郎"
    if video_format == "総集編/傑作選":
        return "シリーズ名 総集編｜テーマ訴求｜七味春五郎"
    if video_format == "長編連載":
        return "【長編朗読連載】シリーズ名『作品名』第N巻｜七味春五郎"
    if video_format == "睡眠・作業用":
        return "【睡眠朗読】シリーズ名『作品名』｜睡眠・作業用｜七味春五郎"
    if video_format == "聴くドラマ/一人でドラマ":
        return "【朗読一人でドラマ】シリーズ名『作品名』｜七味春五郎"
    return "朗読 シリーズ名『作品名』｜七味春五郎"


def suggested_thumbnail_pattern(row: Dict[str, str]) -> str:
    series_name = row.get("series_name", "")
    video_format = row.get("video_format", "")
    if series_name == "怪談":
        return "暗色背景 + 怪談キーワード大 + 作品名小"
    if video_format == "第一集":
        return "第一集を大文字 + テーマ3語 + シリーズ帯"
    if video_format == "三部作":
        return "三部作を大文字 + 3作品名小"
    if video_format == "総集編/傑作選":
        return "総集編/傑作選を大 + テーマ訴求"
    if video_format == "長編連載":
        return "第N巻を大 + 作品名 + 連載帯"
    if video_format == "睡眠・作業用":
        return "睡眠・作業用を大 + 作品名 + 落ち着いた配色"
    if video_format == "聴くドラマ/一人でドラマ":
        return "ドラマ訴求語 + 作品名 + 表情の強い見出し"
    if series_name == "主題歌/MV":
        return "MV/主題歌を大 + 曲名を中央配置"
    return "作品名を大 + シリーズ帯を上部配置"


def build_planning_rows(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    planning_rows: List[Dict[str, object]] = []
    for row in rows:
        metrics = compute_metrics(row)
        bucket = priority_bucket(row.get("series_name", ""), float(metrics["watch_time_minutes"]), metrics["avg_view_pct"])
        planning = dict(row)
        planning["priority_bucket"] = bucket
        planning["publish_strategy"] = publish_strategy(row, metrics)
        planning["has_sleep_work_keyword"] = metrics["has_sleep_work_keyword"]
        planning["recommended_next_action"] = recommended_next_action(row, metrics, bucket)
        planning["suggested_title_pattern"] = suggested_title_pattern(row)
        planning["suggested_thumbnail_pattern"] = suggested_thumbnail_pattern(row)
        planning_rows.append(planning)
    planning_rows.sort(
        key=lambda row: (
            {"主力": 0, "準主力": 1, "育成": 2, "観測": 3, "分離": 4}.get(row["priority_bucket"], 9),
            -float(parse_float(row.get("estimatedMinutesWatched")) or 0.0),
        )
    )
    return planning_rows


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_number(row.get(key)) for key in fieldnames})


def top_by(rows: List[Dict[str, str]], *, series_name: str, video_format: str | None = None, limit: int = 10) -> List[Dict[str, str]]:
    filtered = [row for row in rows if row.get("series_name") == series_name]
    if video_format is not None:
        filtered = [row for row in filtered if row.get("video_format") == video_format]
    filtered.sort(key=lambda row: float(parse_float(row.get("estimatedMinutesWatched")) or 0.0), reverse=True)
    return filtered[:limit]


def high_retention(rows: List[Dict[str, str]], *, series_name: str, video_format: str | None = None, limit: int = 10) -> List[Dict[str, str]]:
    filtered = [row for row in rows if row.get("series_name") == series_name]
    if video_format is not None:
        filtered = [row for row in filtered if row.get("video_format") == video_format]

    def metric(row: Dict[str, str]) -> float:
        avg_pct = parse_float(row.get("average_view_duration_percentage"))
        if avg_pct is not None:
            return avg_pct
        avg_view_duration = parse_float(row.get("averageViewDuration"))
        duration_seconds = parse_int(row.get("duration_seconds"))
        if avg_view_duration is not None and duration_seconds:
            return (avg_view_duration / duration_seconds) * 100
        return 0.0

    filtered.sort(key=metric, reverse=True)
    return filtered[:limit]


def write_strategy_report(path: Path, rows: List[Dict[str, str]], series_name: str, report_title: str, analysis_input_label: str) -> None:
    series_rows = [row for row in rows if row.get("series_name") == series_name]
    if not series_rows:
        path.write_text(f"# {report_title}\n\n対象データがありません。\n", encoding="utf-8")
        return

    single_rows = top_by(series_rows, series_name=series_name, video_format="単話", limit=10)
    first_collection_rows = top_by(series_rows, series_name=series_name, video_format="第一集", limit=10)
    comp_rows = top_by(series_rows, series_name=series_name, video_format="総集編/傑作選", limit=10)
    trilogy_rows = top_by(series_rows, series_name=series_name, video_format="三部作", limit=10)
    sleep_rows = top_by(series_rows, series_name=series_name, video_format="睡眠・作業用", limit=10)
    drama_rows = top_by(series_rows, series_name=series_name, video_format="聴くドラマ/一人でドラマ", limit=10)

    if len(comp_rows) < 5:
        extra = [row for row in high_retention(series_rows, series_name=series_name, video_format="単話", limit=10) if row not in comp_rows]
        comp_rows.extend(extra[: max(0, 5 - len(comp_rows))])

    next_five: List[tuple[str, str]] = []
    if first_collection_rows:
        next_five.append((first_collection_rows[0]["title"], "第一集の続編・派生企画として優先"))
    if trilogy_rows:
        next_five.append((trilogy_rows[0]["title"], "三部作フォーマットが成立しているため横展開候補"))
    if sleep_rows:
        next_five.append((sleep_rows[0]["title"], "睡眠・作業用導線で再現しやすい"))
    if drama_rows:
        next_five.append((drama_rows[0]["title"], "ドラマ演出枠として再利用しやすい"))
    for row in single_rows:
        if len(next_five) >= 5:
            break
        title = row["title"]
        if all(existing_title != title for existing_title, _ in next_five):
            next_five.append((title, "単話の強い回として次の投稿候補"))

    lines: List[str] = []
    lines.append(f"# {report_title}")
    lines.append("")
    lines.append(f"- 対象シリーズ: {series_name}")
    lines.append(f"- 対象本数: {len(series_rows)}")
    lines.append(f"- 元データ: {analysis_input_label}")
    lines.append("")

    def append_rows(title: str, section_rows: List[Dict[str, str]]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if not section_rows:
            lines.append("該当候補なし。")
            lines.append("")
            return
        lines.append("| 順位 | タイトル | フォーマット | watch_time_minutes | avg_view_duration_pct |")
        lines.append("| --- | --- | --- | ---: | ---: |")
        for index, row in enumerate(section_rows, start=1):
            avg_pct = parse_float(row.get("average_view_duration_percentage"))
            if avg_pct is None:
                avg_view_duration = parse_float(row.get("averageViewDuration"))
                duration_seconds = parse_int(row.get("duration_seconds"))
                avg_pct = (avg_view_duration / duration_seconds) * 100 if avg_view_duration is not None and duration_seconds else 0.0
            lines.append(
                f"| {index} | {escape_md(row['title'])} | {escape_md(row.get('video_format',''))} | {float(parse_float(row.get('estimatedMinutesWatched')) or 0.0):,.1f} | {avg_pct:,.2f} |"
            )
        lines.append("")

    append_rows("単話で強い回ランキング", single_rows)
    append_rows("第一集向き候補", first_collection_rows or single_rows[:5])
    append_rows("三作総集編向き候補", trilogy_rows + comp_rows[: max(0, 10 - len(trilogy_rows))])
    append_rows("睡眠・作業用に向く候補", sleep_rows or high_retention(series_rows, series_name=series_name, video_format="単話", limit=5))
    append_rows("聴くドラマ/一人でドラマに向く候補", drama_rows or high_retention(series_rows, series_name=series_name, video_format="単話", limit=5))

    lines.append("## 次に出すべき5本の提案")
    lines.append("")
    for index, (title, reason) in enumerate(next_five[:5], start=1):
        lines.append(f"{index}. {escape_md(title)}")
        lines.append(f"理由: {reason}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    analysis_path = (base_dir / args.analysis_input).resolve()
    planning_path = (base_dir / args.planning_output).resolve()
    zenigata_path = (base_dir / args.zenigata_output).resolve()
    yamamoto_path = (base_dir / args.yamamoto_output).resolve()

    rows = load_rows(analysis_path)
    planning_rows = build_planning_rows(rows)
    write_csv(planning_path, planning_rows)
    write_strategy_report(zenigata_path, planning_rows, "銭形平次捕物控", "銭形平次 投稿戦略レポート", analysis_path.name)
    write_strategy_report(yamamoto_path, planning_rows, "山本周五郎", "山本周五郎 投稿戦略レポート", analysis_path.name)

    print(f"Planning CSV: {planning_path}")
    print(f"Zenigata report: {zenigata_path}")
    print(f"Yamamoto report: {yamamoto_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
