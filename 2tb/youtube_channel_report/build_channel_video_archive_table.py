#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

OUTPUT_HEADERS = [
    'publishedAt',
    'published_year',
    'videoId',
    'title',
    'privacyStatus',
    'uploadStatus',
    'viewCount',
    'likeCount',
    'commentCount',
    'like_rate_percent',
    'duration',
    'duration_seconds',
    'duration_minutes',
    'length_bucket',
    'average_view_duration_seconds',
    'average_view_duration_minutes',
    'retention_rate_percent',
    'estimated_minutes_watched',
    'impressions',
    'impression_ctr_percent',
    'definition',
    'caption',
    'in_report',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build an archive-friendly date-sorted table for all channel videos.')
    parser.add_argument('--inventory-input', default='old_channel_report/channel_upload_inventory.csv')
    parser.add_argument('--report-input', default='old_channel_report/youtube_video_report_last_90_days_all_videos.csv')
    parser.add_argument('--csv-output', default='old_channel_report/channel_videos_by_date.csv')
    parser.add_argument('--md-output', default='old_channel_report/channel_videos_by_date.md')
    parser.add_argument('--sample-size', type=int, default=120)
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


def to_int(value: object) -> int:
    try:
        return int(float(str(value or '0').replace(',', '')))
    except ValueError:
        return 0


def to_float(value: object) -> float:
    try:
        return float(str(value or '0').replace(',', ''))
    except ValueError:
        return 0.0


def fmt_float(value: float, digits: int = 2) -> str:
    if value <= 0:
        return ''
    return f'{value:.{digits}f}'


def parse_iso8601_duration(value: str) -> int:
    match = re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', value or '')
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def length_bucket(duration_seconds: int) -> str:
    if duration_seconds <= 180:
        return 'Short候補'
    if duration_seconds > 10800:
        return '長編'
    if duration_seconds > 5400:
        return '中篇'
    return '短編'


def escape_md(text: object) -> str:
    return str(text or '').replace('|', '\\|').replace('\n', ' ').strip()


def load_report_metrics(path: Path) -> dict[str, dict[str, object]]:
    metrics: dict[str, dict[str, object]] = {}
    if not path.exists():
        return metrics
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            video_id = (row.get('videoId') or '').strip()
            if not video_id:
                continue
            avg_seconds = to_int(row.get('averageViewDuration'))
            metrics[video_id] = {
                'views': to_int(row.get('views')),
                'estimated_minutes_watched': to_int(row.get('estimatedMinutesWatched')),
                'average_view_duration_seconds': avg_seconds,
                'average_view_duration_minutes': avg_seconds / 60 if avg_seconds else 0.0,
                'impressions': to_int(row.get('impressions')),
                'impression_ctr_percent': to_float(row.get('impressionCtr')) * 100.0,
            }
    return metrics


def build_rows(inventory_path: Path, report_path: Path) -> list[dict[str, object]]:
    report_metrics = load_report_metrics(report_path)
    rows: list[dict[str, object]] = []

    with inventory_path.open('r', encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            video_id = (row.get('videoId') or '').strip()
            published_at = row.get('publishedAt', '') or ''
            published_dt = parse_datetime(published_at)
            published_year = published_dt.year if published_dt else ''

            duration = row.get('duration', '') or ''
            duration_seconds = parse_iso8601_duration(duration)
            views = to_int(row.get('viewCount'))
            likes = to_int(row.get('likeCount'))
            report = report_metrics.get(video_id, {})
            avg_seconds = int(report.get('average_view_duration_seconds', 0))
            retention_rate = (avg_seconds / duration_seconds * 100.0) if avg_seconds and duration_seconds else 0.0
            like_rate = (likes / views * 100.0) if likes and views else 0.0

            rows.append(
                {
                    'publishedAt': published_at,
                    'published_year': published_year,
                    'videoId': video_id,
                    'title': row.get('title', '') or '',
                    'privacyStatus': row.get('privacyStatus', '') or '',
                    'uploadStatus': row.get('uploadStatus', '') or '',
                    'viewCount': views,
                    'likeCount': likes,
                    'commentCount': to_int(row.get('commentCount')),
                    'like_rate_percent': fmt_float(like_rate),
                    'duration': duration,
                    'duration_seconds': duration_seconds,
                    'duration_minutes': fmt_float(duration_seconds / 60.0),
                    'length_bucket': length_bucket(duration_seconds),
                    'average_view_duration_seconds': avg_seconds or '',
                    'average_view_duration_minutes': fmt_float(float(report.get('average_view_duration_minutes', 0.0))),
                    'retention_rate_percent': fmt_float(retention_rate),
                    'estimated_minutes_watched': report.get('estimated_minutes_watched', '') or '',
                    'impressions': report.get('impressions', '') or '',
                    'impression_ctr_percent': fmt_float(float(report.get('impression_ctr_percent', 0.0))),
                    'definition': row.get('definition', '') or '',
                    'caption': row.get('caption', '') or '',
                    'in_report': 'yes' if video_id in report_metrics else 'no',
                }
            )

    rows.sort(key=lambda item: (item['publishedAt'], item['videoId']))
    return rows


def write_csv_output(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, '') for header in OUTPUT_HEADERS})


def build_markdown(rows: list[dict[str, object]], sample_size: int) -> str:
    year_counts = Counter(str(row['published_year'] or 'unknown') for row in rows)
    privacy_counts = Counter(str(row['privacyStatus'] or 'unknown') for row in rows)
    bucket_counts = Counter(str(row['length_bucket'] or 'unknown') for row in rows)
    report_count = sum(1 for row in rows if row['in_report'] == 'yes')
    retention_count = sum(1 for row in rows if str(row['retention_rate_percent']).strip())

    lines = [
        '# チャンネル動画アーカイブ一覧',
        '',
        '削除前の保存用として、チャンネル全動画を古い順に並べた一覧です。',
        'CSV は全件、Markdown はサマリーと古い順サンプルです。',
        '',
        f'- 全動画数: {len(rows)}',
        f'- Analytics/report 連結済み: {report_count}',
        f'- 視聴維持率が計算できた動画数: {retention_count}',
        '',
        '## 件数サマリー',
        '',
        f'- privacy: {dict(privacy_counts)}',
        f'- 尺区分: {dict(bucket_counts)}',
        '',
        '## 年別件数',
        '',
        '| year | count |',
        '| --- | ---: |',
    ]
    for year in sorted(year_counts):
        lines.append(f'| {year} | {year_counts[year]} |')

    lines.extend([
        '',
        f'## 古い順サンプル {min(sample_size, len(rows))}本',
        '',
        '| 公開日 | title | privacy | views | 高評価率 | 平均視聴時間(分) | 視聴維持率 |',
        '| --- | --- | --- | ---: | ---: | ---: | ---: |',
    ])
    for row in rows[:sample_size]:
        lines.append(
            f"| {row['publishedAt']} | {escape_md(row['title'])} | {row['privacyStatus']} | {row['viewCount']} | "
            f"{row['like_rate_percent'] or '-'} | {row['average_view_duration_minutes'] or '-'} | {row['retention_rate_percent'] or '-'} |"
        )

    return '\n'.join(lines) + '\n'


def main() -> int:
    args = parse_args()
    inventory_path = Path(args.inventory_input)
    report_path = Path(args.report_input)
    csv_output = Path(args.csv_output)
    md_output = Path(args.md_output)

    if not inventory_path.exists():
        raise SystemExit(f'missing inventory input: {inventory_path}')

    rows = build_rows(inventory_path, report_path)
    write_csv_output(csv_output, rows)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(build_markdown(rows, args.sample_size), encoding='utf-8')

    print(f'wrote {csv_output}')
    print(f'wrote {md_output}')
    print(f'rows: {len(rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
