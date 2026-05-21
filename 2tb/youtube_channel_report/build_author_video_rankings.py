#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

SERIES_AUTHOR_PATTERNS = [
    ('岡本綺堂', ['半七捕物帳', '半七']),
    ('野村胡堂', ['銭形平次捕物控', '池田大助捕物帳', '美男狩', '三万両五十三次', '磯川兵助功名噺']),
    ('佐々木味津三', ['右門捕物帖', '旗本退屈男']),
    ('林不忘', ['釘抜藤吉', '釘抜き藤吉', '早耳三次捕物聞書', '丹下左膳']),
    ('三上於菟吉', ['雪之丞変化']),
    ('江戸川乱歩', ['幽霊塔', '二銭銅貨', '陰獣', '月と手袋']),
]

AUTHOR_PATTERNS = [
    ('山本周五郎', ['山本周五郎']),
    ('野村胡堂', ['野村胡堂']),
    ('吉川英治', ['吉川英治']),
    ('岡本綺堂', ['岡本綺堂']),
    ('佐々木味津三', ['佐々木味津三']),
    ('久生十蘭', ['久生十蘭']),
    ('林不忘', ['林不忘']),
    ('菊池寛', ['菊池寛']),
    ('三上於菟吉', ['三上於菟吉']),
    ('江戸川乱歩', ['江戸川乱歩']),
    ('夏目漱石', ['夏目漱石']),
    ('岡本かの子', ['岡本かの子']),
    ('太宰治', ['太宰治']),
    ('芥川龍之介', ['芥川龍之介']),
    ('泉鏡花', ['泉鏡花']),
    ('ディケンズ', ['チャールズ・ディケンズ', 'ディケンズ']),
]

HEADERS = [
    'author',
    'publishedAt',
    'published_year',
    'videoId',
    'title',
    'privacyStatus',
    'viewCount',
    'like_rate_percent',
    'average_view_duration_minutes',
    'retention_rate_percent',
    'length_bucket',
    'impressions',
    'impression_ctr_percent',
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build per-author rankings from channel archive tables.')
    parser.add_argument('--archive-input', default='old_channel_report/channel_videos_by_date.csv')
    parser.add_argument('--report-input', default='old_channel_report/youtube_video_report_last_90_days_all_videos.csv')
    parser.add_argument('--csv-output', default='old_channel_report/channel_videos_by_author.csv')
    parser.add_argument('--md-output', default='old_channel_report/channel_videos_by_author.md')
    parser.add_argument('--top-per-author', type=int, default=20)
    parser.add_argument('--min-videos-for-section', type=int, default=3)
    return parser.parse_args()


def to_int(value: object) -> int:
    try:
        return int(float(str(value or '0').replace(',', '')))
    except ValueError:
        return 0


def detect_author(title_text: str, report_text: str) -> str:
    combined_text = title_text + '\n' + report_text
    for author, patterns in SERIES_AUTHOR_PATTERNS:
        if any(pattern in title_text for pattern in patterns):
            return author
    for author, patterns in AUTHOR_PATTERNS:
        if any(pattern in title_text for pattern in patterns):
            return author
    for author, patterns in SERIES_AUTHOR_PATTERNS:
        if any(pattern in combined_text for pattern in patterns):
            return author
    for author, patterns in AUTHOR_PATTERNS:
        if any(pattern in combined_text for pattern in patterns):
            return author
    return '未判定'


def escape_md(text: object) -> str:
    return str(text or '').replace('|', '\\|').replace('\n', ' ').strip()


def load_report_texts(path: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    if not path.exists():
        return texts
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            video_id = (row.get('videoId') or '').strip()
            if not video_id:
                continue
            texts[video_id] = (row.get('title', '') or '') + '\n' + (row.get('description', '') or '')
    return texts


def build_rows(archive_path: Path, report_path: Path) -> list[dict[str, object]]:
    report_texts = load_report_texts(report_path)
    rows: list[dict[str, object]] = []
    with archive_path.open('r', encoding='utf-8-sig', newline='') as fh:
        for row in csv.DictReader(fh):
            video_id = row.get('videoId', '') or ''
            title_text = row.get('title', '') or ''
            report_text = report_texts.get(video_id, '')
            author = detect_author(title_text, report_text)
            out = {header: row.get(header, '') for header in HEADERS if header != 'author'}
            out['author'] = author
            rows.append(out)
    rows.sort(key=lambda item: (item['author'], -to_int(item['viewCount']), item['publishedAt']))
    return rows


def write_csv_output(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({header: row.get(header, '') for header in HEADERS})


def build_markdown(rows: list[dict[str, object]], top_per_author: int, min_videos_for_section: int) -> str:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row['author'] or '未判定')].append(row)

    author_summary = []
    for author, items in grouped.items():
        total_views = sum(to_int(item['viewCount']) for item in items)
        author_summary.append((author, len(items), total_views))
    author_summary.sort(key=lambda item: (-item[2], item[0]))

    lines = [
        '# 作家別 再生数上位一覧',
        '',
        'チャンネル全動画を作家別に分け、再生数上位で見やすくした一覧です。',
        '作者名はタイトル優先、ついでシリーズ名と説明文から推定しています。',
        '',
        f'- 作家数: {len(author_summary)}',
        f'- 全動画数: {len(rows)}',
        '',
        '## 作家別サマリー',
        '',
        '| author | videos | total_views |',
        '| --- | ---: | ---: |',
    ]
    for author, count, total_views in author_summary:
        lines.append(f'| {author} | {count} | {total_views} |')

    for author, count, total_views in author_summary:
        if count < min_videos_for_section:
            continue
        items = grouped[author]
        items.sort(key=lambda item: (-to_int(item['viewCount']), item['publishedAt']))
        lines.extend([
            '',
            f'## {author} 再生数上位 {min(top_per_author, len(items))}本',
            '',
            f'- 動画数: {count}',
            f'- 総再生数: {total_views}',
            '',
            '| views | title | 公開日 | privacy | 高評価率 | 維持率 |',
            '| ---: | --- | --- | --- | ---: | ---: |',
        ])
        for row in items[:top_per_author]:
            lines.append(
                f"| {row['viewCount']} | {escape_md(row['title'])} | {row['publishedAt']} | {row['privacyStatus']} | "
                f"{row['like_rate_percent'] or '-'} | {row['retention_rate_percent'] or '-'} |"
            )
    return '\n'.join(lines) + '\n'


def main() -> int:
    args = parse_args()
    archive_path = Path(args.archive_input)
    report_path = Path(args.report_input)
    csv_output = Path(args.csv_output)
    md_output = Path(args.md_output)

    if not archive_path.exists():
        raise SystemExit(f'missing archive input: {archive_path}')

    rows = build_rows(archive_path, report_path)
    write_csv_output(csv_output, rows)
    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(
        build_markdown(rows, args.top_per_author, args.min_videos_for_section),
        encoding='utf-8',
    )

    print(f'wrote {csv_output}')
    print(f'wrote {md_output}')
    print(f'rows: {len(rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
