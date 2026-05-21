#!/usr/bin/env python3

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from build_zenigata_shortworks_catalog import (
    BASE_DIR,
    CATALOG_PATH,
    EXCLUDE_KEYWORDS,
    build_catalog_maps,
    candidate_titles_from_video,
    load_rows,
    normalize_key,
)

RANKED_PATH = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_upload_inventory_ranked.csv'
OUT_CSV = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_rerecorded_works.csv'
OUT_MD = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_rerecorded_works.md'
OUT_LATEST_CSV = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_rerecorded_latest_only.csv'
OUT_LATEST_MD = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_rerecorded_latest_only.md'


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def resolve_work_title(title: str, exact_map, normalized_map, normalized_keys):
    generic_candidates = {'毎週日曜夜八時は', '朗読', '人情朗読', '朗読一人でドラマ', 'audiobook', 'audiobook銭形平次捕物控'}
    for candidate in candidate_titles_from_video(title):
        candidate = candidate.strip()
        candidate_key = normalize_key(candidate)
        if len(candidate_key) < 2:
            continue
        if candidate_key in {normalize_key(v) for v in generic_candidates}:
            continue
        row = exact_map.get(candidate)
        if row:
            return row['title'], row
        row = normalized_map.get(candidate_key)
        if row:
            return row['title'], row

    full_key = normalize_key(title)
    best_row = None
    best_len = 0
    for catalog_key, catalog_row in normalized_keys:
        if len(catalog_key) < 3:
            continue
        if catalog_key in full_key and len(catalog_key) > best_len:
            best_row = catalog_row
            best_len = len(catalog_key)
    if best_row:
        return best_row['title'], best_row
    return '', None


def main() -> int:
    ranked_rows = load_rows(RANKED_PATH)
    catalog_rows = load_rows(CATALOG_PATH)
    exact_map, normalized_map, normalized_keys = build_catalog_maps(catalog_rows)

    grouped: Dict[str, Dict[str, object]] = {}
    extra_exclude_keywords = set(EXCLUDE_KEYWORDS) | {'毎週日曜夜八時は'}
    for row in ranked_rows:
        title = row['title']
        if any(keyword in title for keyword in extra_exclude_keywords):
            continue
        matched_title, catalog_row = resolve_work_title(title, exact_map, normalized_map, normalized_keys)
        normalized_title = matched_title or title
        bucket = grouped.setdefault(normalized_title, {
            'title': normalized_title,
            'publication_years': catalog_row.get('publication_years', '') if catalog_row else '',
            'chronology_ordinals': catalog_row.get('chronology_ordinals', '') if catalog_row else '',
            'versions': {},
        })
        bucket['publication_years'] = bucket['publication_years'] or (catalog_row.get('publication_years', '') if catalog_row else '')
        bucket['chronology_ordinals'] = bucket['chronology_ordinals'] or (catalog_row.get('chronology_ordinals', '') if catalog_row else '')
        bucket['versions'][row['videoId']] = row

    out_rows: List[Dict[str, object]] = []
    for normalized_title, payload in grouped.items():
        versions = list(payload['versions'].values())
        unique_video_ids = {row['videoId'] for row in versions}
        if len(unique_video_ids) < 2:
            continue
        versions.sort(key=lambda row: parse_dt(row['publishedAt']))
        latest = versions[-1]
        earliest = versions[0]
        years = sorted({row['published_year'] for row in versions if row.get('published_year')})
        if len(years) < 2 and not any('再録' in row['title'] for row in versions):
            continue
        has_explicit_rerecord_label = any('再録' in row['title'] for row in versions)
        has_parts_mix = any(any(token in row['title'] for token in ['前編', '中編', '後篇', '後編', '完結', '全編']) for row in versions)
        if has_explicit_rerecord_label:
            selection_reason = '再録ありのため最新版を採用'
        elif has_parts_mix:
            selection_reason = '分割版と全編版が混在するため最新版を採用'
        else:
            selection_reason = '複数年にまたがる重複のため最新版を採用'
        out_rows.append({
            'normalized_title': normalized_title,
            'publication_years': payload['publication_years'],
            'chronology_ordinals': payload['chronology_ordinals'],
            'version_count': len(unique_video_ids),
            'years_seen': ','.join(years),
            'has_explicit_rerecord_label': 'yes' if has_explicit_rerecord_label else 'no',
            'selection_reason': selection_reason,
            'earliest_video_id': earliest['videoId'],
            'earliest_published_at': earliest['publishedAt'],
            'latest_video_id': latest['videoId'],
            'latest_published_at': latest['publishedAt'],
            'latest_title': latest['title'],
            'latest_views': latest['viewCount'],
            'latest_views_per_day': latest['views_per_day'],
            'preferred_video_id': latest['videoId'],
            'preferred_year': latest['published_year'],
            'preferred_title': latest['title'],
        })

    out_rows.sort(key=lambda row: (row['preferred_year'], row['normalized_title']))
    with OUT_CSV.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    latest_only_rows = [{
        'normalized_title': row['normalized_title'],
        'publication_years': row['publication_years'],
        'chronology_ordinals': row['chronology_ordinals'],
        'years_seen': row['years_seen'],
        'selection_reason': row['selection_reason'],
        'video_id': row['preferred_video_id'],
        'published_year': row['preferred_year'],
        'published_at': row['latest_published_at'],
        'title': row['preferred_title'],
        'views': row['latest_views'],
        'views_per_day': row['latest_views_per_day'],
    } for row in out_rows]
    with OUT_LATEST_CSV.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(latest_only_rows[0].keys()))
        writer.writeheader()
        writer.writerows(latest_only_rows)

    lines = [
        '# Zenigata Rerecorded Works',
        '',
        '- rule: works with multiple distinct video IDs and at least two channel years, or explicit `再録` mention',
        '- preferred version: newest `publishedAt`',
        '',
        f'- works: {len(out_rows)}',
        '',
        '| title | publication_years | years_seen | versions | reason | preferred_year | preferred_video_id | preferred_title |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in out_rows:
        escaped_title = row['normalized_title'].replace('|', '\\|')
        escaped_publication_years = row['publication_years'].replace('|', '\\|')
        escaped_preferred_title = row['preferred_title'].replace('|', '\\|')
        lines.append(
            f"| {escaped_title} | {escaped_publication_years} | {row['years_seen']} | {row['version_count']} | {row['selection_reason']} | {row['preferred_year']} | {row['preferred_video_id']} | {escaped_preferred_title} |"
        )
    OUT_MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    latest_lines = [
        '# Zenigata Rerecorded Works Latest Only',
        '',
        '- only newest version is kept for each rerecorded work',
        '',
        f'- works: {len(latest_only_rows)}',
        '',
        '| title | publication_years | years_seen | published_year | video_id | views_per_day | latest_title |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    for row in latest_only_rows:
        escaped_title = row['normalized_title'].replace('|', '\\|')
        escaped_publication_years = row['publication_years'].replace('|', '\\|')
        escaped_latest_title = row['title'].replace('|', '\\|')
        latest_lines.append(
            f"| {escaped_title} | {escaped_publication_years} | {row['years_seen']} | {row['published_year']} | {row['video_id']} | {row['views_per_day']} | {escaped_latest_title} |"
        )
    OUT_LATEST_MD.write_text('\n'.join(latest_lines) + '\n', encoding='utf-8')

    print(OUT_CSV)
    print(OUT_MD)
    print(OUT_LATEST_CSV)
    print(OUT_LATEST_MD)
    print(f'rerecorded_works={len(out_rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
