#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

DEFAULT_AS_OF = '2026-04-04T23:59:59+09:00'
RANKED_HEADERS = [
    'videoId',
    'title',
    'publishedAt',
    'published_year',
    'days_since_publish',
    'views_per_day',
    'viewCount',
    'likeCount',
    'commentCount',
    'privacyStatus',
    'uploadStatus',
    'duration',
    'duration_seconds',
    'is_short_candidate',
    'definition',
    'caption',
    'in_old_report',
    'report_views',
    'report_estimated_minutes_watched',
    'average_view_duration_seconds',
    'average_view_duration_minutes',
    'impressions',
    'impression_ctr',
    'playlist_position',
    'source_channel_id',
    'source_channel_title',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Analyze old-channel Zenigata inventory with publish-year and views/day metrics.')
    parser.add_argument('--input', default='old_channel_report/zenigata_upload_inventory.csv')
    parser.add_argument('--report-input', default='old_channel_report/youtube_video_report_last_90_days_all_videos.csv')
    parser.add_argument('--ranked-output', default='old_channel_report/zenigata_upload_inventory_ranked.csv')
    parser.add_argument('--summary-output', default='old_channel_report/zenigata_upload_inventory_analysis.md')
    parser.add_argument('--as-of', default=DEFAULT_AS_OF)
    parser.add_argument('--min-days-stable', type=int, default=30)
    return parser.parse_args()


def parse_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        if value.endswith('Z'):
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def to_int(value: str) -> int:
    try:
        return int(float(value or 0))
    except ValueError:
        return 0


def to_float_str(value: float) -> str:
    return f'{value:.3f}'


def escape_md(text: object) -> str:
    return str(text).replace('|', '\\|').replace('\n', ' ').strip()


def parse_iso8601_duration(value: str) -> int:
    match = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', value or '')
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def load_report_metrics(path: Path) -> dict[str, dict[str, object]]:
    if not path.exists():
        return {}
    metrics = {}
    with path.open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            video_id = (row.get('videoId') or '').strip()
            if not video_id:
                continue
            avg_sec = to_int(row.get('averageViewDuration', ''))
            metrics[video_id] = {
                'report_views': to_int(row.get('views', '')),
                'report_estimated_minutes_watched': to_int(row.get('estimatedMinutesWatched', '')),
                'average_view_duration_seconds': avg_sec,
                'average_view_duration_minutes': avg_sec / 60 if avg_sec else 0.0,
                'impressions': row.get('impressions', '') or '',
                'impression_ctr': row.get('impressionCtr', '') or '',
            }
    return metrics


def load_rows(path: Path, report_metrics: dict[str, dict[str, object]], as_of: datetime) -> list[dict[str, object]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        source_rows = list(csv.DictReader(handle))

    analyzed: list[dict[str, object]] = []
    for row in source_rows:
        published_at = parse_datetime(row.get('publishedAt', ''))
        if published_at is None:
            published_year = ''
            days_since_publish = 1
        else:
            published_year = str(published_at.astimezone(timezone.utc).year)
            elapsed = as_of.astimezone(timezone.utc) - published_at.astimezone(timezone.utc)
            days_since_publish = max(1, elapsed.days + 1)
        view_count = to_int(row.get('viewCount', ''))
        duration_seconds = parse_iso8601_duration(row.get('duration', ''))
        report = report_metrics.get(row.get('videoId', ''), {})
        analyzed.append(
            {
                'videoId': row.get('videoId', ''),
                'title': row.get('title', ''),
                'publishedAt': row.get('publishedAt', ''),
                'published_year': published_year,
                'days_since_publish': days_since_publish,
                'views_per_day': view_count / days_since_publish,
                'viewCount': view_count,
                'likeCount': to_int(row.get('likeCount', '')),
                'commentCount': to_int(row.get('commentCount', '')),
                'privacyStatus': row.get('privacyStatus', ''),
                'uploadStatus': row.get('uploadStatus', ''),
                'duration': row.get('duration', ''),
                'duration_seconds': duration_seconds,
                'is_short_candidate': 'true' if duration_seconds <= 180 else 'false',
                'definition': row.get('definition', ''),
                'caption': row.get('caption', ''),
                'in_old_report': row.get('in_old_report', ''),
                'report_views': report.get('report_views', 0),
                'report_estimated_minutes_watched': report.get('report_estimated_minutes_watched', 0),
                'average_view_duration_seconds': report.get('average_view_duration_seconds', 0),
                'average_view_duration_minutes': report.get('average_view_duration_minutes', 0.0),
                'impressions': report.get('impressions', ''),
                'impression_ctr': report.get('impression_ctr', ''),
                'playlist_position': to_int(row.get('playlist_position', '')),
                'source_channel_id': row.get('source_channel_id', ''),
                'source_channel_title': row.get('source_channel_title', ''),
            }
        )
    return analyzed


def write_ranked_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=RANKED_HEADERS)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out['views_per_day'] = to_float_str(float(out['views_per_day']))
            out['average_view_duration_minutes'] = to_float_str(float(out['average_view_duration_minutes'])) if float(out['average_view_duration_minutes']) else ''
            writer.writerow(out)


def summarize_by_year(rows: list[dict[str, object]]) -> list[tuple[str, int, int, float, float]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row['published_year'] or 'unknown')].append(row)
    summary = []
    for year, items in grouped.items():
        total_views = sum(int(item['viewCount']) for item in items)
        avg_vpd = total_views / max(1, sum(int(item['days_since_publish']) for item in items))
        median_vpd = median(float(item['views_per_day']) for item in items)
        summary.append((year, len(items), total_views, avg_vpd, median_vpd))
    summary.sort(key=lambda item: item[0], reverse=True)
    return summary


def format_row(row: dict[str, object], include_avg: bool = False) -> str:
    base = (
        f"| {row['videoId']} | {row['published_year']} | {row['privacyStatus']} | {row['viewCount']} | "
        f"{to_float_str(float(row['views_per_day']))} | {row['days_since_publish']} |"
    )
    if include_avg:
        avg = row['average_view_duration_minutes']
        avg_text = to_float_str(float(avg)) if float(avg) else ''
        return base + f" {avg_text} | {escape_md(row['title'])} |"
    return base + f" {escape_md(row['title'])} |"


def write_summary(path: Path, rows: list[dict[str, object]], *, min_days_stable: int, as_of_label: str) -> None:
    by_views = sorted(rows, key=lambda row: (-int(row['viewCount']), int(row['playlist_position'])))
    stable_rows = [row for row in rows if int(row['days_since_publish']) >= min_days_stable]
    by_vpd = sorted(stable_rows, key=lambda row: (-float(row['views_per_day']), -int(row['viewCount'])))
    recent_rows = [row for row in rows if int(row['days_since_publish']) < min_days_stable]
    by_recent_vpd = sorted(recent_rows, key=lambda row: (-float(row['views_per_day']), -int(row['viewCount'])))
    longform_rows = [row for row in rows if row['is_short_candidate'] != 'true']
    stable_longform_rows = [row for row in longform_rows if int(row['days_since_publish']) >= min_days_stable]
    by_longform_vpd = sorted(stable_longform_rows, key=lambda row: (-float(row['views_per_day']), -int(row['viewCount'])))
    report_rows = [row for row in longform_rows if int(row['average_view_duration_seconds']) > 0]
    by_avg_duration = sorted(report_rows, key=lambda row: (-int(row['average_view_duration_seconds']), -int(row['report_views']), -int(row['viewCount'])))
    year_summary = summarize_by_year(longform_rows)
    short_count = sum(1 for row in rows if row['is_short_candidate'] == 'true')

    lines = ['# Zenigata Inventory Analysis', '']
    lines.append(f'- as_of: `{as_of_label}`')
    lines.append(f'- title_match_rows: {len(rows)}')
    lines.append(f'- short_candidates: {short_count}')
    lines.append(f'- longform_rows: {len(longform_rows)}')
    lines.append(f'- stable_threshold_days: {min_days_stable}')
    lines.append(f"- report_overlap_with_avg_view_duration: {len(report_rows)}")
    lines.append('')
    lines.append('## 公開年別サマリー 長尺のみ')
    lines.append('')
    lines.append('| year | count | total_views | avg_views_per_day_portfolio | median_views_per_day_video |')
    lines.append('| --- | --- | --- | --- | --- |')
    for year, count, total_views, avg_vpd, median_vpd in year_summary:
        lines.append(f'| {year} | {count} | {total_views} | {to_float_str(avg_vpd)} | {to_float_str(median_vpd)} |')

    lines.append('')
    lines.append(f'## 日割り上位20本 長尺のみ {min_days_stable}日以上')
    lines.append('')
    lines.append('| videoId | year | privacy | views | views/day | days | title |')
    lines.append('| --- | --- | --- | --- | --- | --- | --- |')
    for row in by_longform_vpd[:20]:
        lines.append(format_row(row))

    lines.append('')
    lines.append('## 総再生数上位20本 長尺のみ')
    lines.append('')
    lines.append('| videoId | year | privacy | views | views/day | days | title |')
    lines.append('| --- | --- | --- | --- | --- | --- | --- |')
    for row in [r for r in by_views if r['is_short_candidate'] != 'true'][:20]:
        lines.append(format_row(row))

    if by_recent_vpd:
        lines.append('')
        lines.append(f'## 初速候補 {min_days_stable}日未満 Short含む')
        lines.append('')
        lines.append('| videoId | year | privacy | views | views/day | days | title |')
        lines.append('| --- | --- | --- | --- | --- | --- | --- |')
        for row in by_recent_vpd[:20]:
            lines.append(format_row(row))

    if report_rows:
        lines.append('')
        lines.append('## 平均再生時間 上位15本 長尺かつreport overlapあり')
        lines.append('')
        lines.append('| videoId | year | privacy | views | views/day | days | avg_view_minutes | title |')
        lines.append('| --- | --- | --- | --- | --- | --- | --- | --- |')
        for row in by_avg_duration[:15]:
            lines.append(format_row(row, include_avg=True))

    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    input_path = (base_dir / args.input).resolve()
    report_input_path = (base_dir / args.report_input).resolve()
    ranked_output_path = (base_dir / args.ranked_output).resolve()
    summary_output_path = (base_dir / args.summary_output).resolve()
    as_of = parse_datetime(args.as_of)
    if as_of is None:
        raise SystemExit('--as-of is invalid')

    report_metrics = load_report_metrics(report_input_path)
    rows = load_rows(input_path, report_metrics, as_of)
    rows.sort(key=lambda row: (-float(row['views_per_day']), -int(row['viewCount']), int(row['playlist_position'])))
    write_ranked_csv(ranked_output_path, rows)
    write_summary(summary_output_path, rows, min_days_stable=args.min_days_stable, as_of_label=args.as_of)
    print(f'Ranked CSV: {ranked_output_path}')
    print(f'Summary report: {summary_output_path}')
    print(f'title_match_rows: {len(rows)}')
    print(f'short_candidates: {sum(1 for row in rows if row["is_short_candidate"] == "true")}')
    print(f'report_overlap_with_avg_view_duration: {sum(1 for row in rows if int(row["average_view_duration_seconds"]) > 0)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
