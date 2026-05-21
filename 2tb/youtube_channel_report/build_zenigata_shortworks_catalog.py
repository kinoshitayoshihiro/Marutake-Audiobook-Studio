#!/usr/bin/env python3

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, List

BASE_DIR = Path('/Volumes/SSD-PUTA - Data/音本・唄本倶楽部/2tb')
RANKED_PATH = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_upload_inventory_ranked.csv'
CATALOG_PATH = BASE_DIR / 'reports/zenigata_heiji_works_catalog.csv'
OUT_CSV = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_shortworks_2021_2025.csv'
OUT_MD = BASE_DIR / 'youtube_channel_report/old_channel_report/zenigata_shortworks_2021_2025.md'

EXCLUDE_KEYWORDS = ['主題歌', '紹介', 'ショート', '予告', '再録']
ALIASES = {
    '金色の乙女': '金色の処女',
    '呪いの銀釵': '呪いの銀簪',
    '巾着切りの娘': '巾着切の娘',
    '花見の仇討ち': '花見の仇討',
    '玉の輿の呪': '玉の輿の呪い',
    '辻斬綺談': '辻斬綺譚',
}
REVERSE_ALIASES = {v: k for k, v in ALIASES.items()}


def strip_title_noise(text: str) -> str:
    t = text
    t = t.replace('＼', ' ')
    t = re.sub(r'銭形平次捕物控', ' ', t)
    t = re.sub(r'野村胡堂(?:作|著)?', ' ', t)
    t = re.sub(r'ナレーター七味春五郎.*', ' ', t)
    t = re.sub(r'読み手七味春五郎.*', ' ', t)
    t = re.sub(r'発行元丸竹書房.*', ' ', t)
    t = re.sub(r'@\S+', ' ', t)
    t = re.sub(r'作業用BGM.*', ' ', t)
    t = re.sub(r'字幕付き.*', ' ', t)
    t = re.sub(r'※.*', ' ', t)
    t = re.sub(r'毎週日曜夜八時.*', ' ', t)
    t = re.sub(r'オーディオブック.*', ' ', t)
    t = re.sub(r'AudioBook.*', ' ', t)
    t = re.sub(r'朗読一人でドラマ', ' ', t)
    t = re.sub(r'人情朗読', ' ', t)
    t = re.sub(r'朗読時代小説', ' ', t)
    t = re.sub(r'日曜朗読劇場', ' ', t)
    t = re.sub(r'朗読', ' ', t)
    t = re.sub(r'長編朗読まとめ|長編朗読|朗読まとめ|長編まとめ|長編|長篇|中編', ' ', t)
    t = re.sub(r'第[一二三四五六七八九十0-9]+回', ' ', t)
    t = re.sub(r'[前中後]編', ' ', t)
    t = re.sub(r'第一回|第二回|第三回|第四回|第五回|第六回|完結|全編', ' ', t)
    t = re.sub(r'第\d+話', ' ', t)
    t = re.sub(r'[／/|｜\\\-]', ' ', t)
    t = re.sub(r'\s+', ' ', t)
    return t.strip(' 　"\'')


def normalize_key(text: str) -> str:
    t = text
    t = t.replace('處', '処').replace('釵', '簪')
    t = t.replace('藝', '芸').replace('兩', '両')
    t = t.replace('繪', '絵').replace('戀', '恋')
    t = t.replace('讐', '讎')
    t = t.replace('　', '')
    t = re.sub(r'[「」『』【】()（）\[\]"“”‘’・!！?？:,，、\.\s]', '', t)
    return t


def candidate_titles_from_video(title: str) -> List[str]:
    candidates: List[str] = []
    bracket_contents = re.findall(r'[【『「](.*?)[】』」]', title)
    for part in bracket_contents:
        part = re.sub(r'^\d+話', '', part).strip()
        if part:
            candidates.append(part)
    cleaned = strip_title_noise(title)
    if cleaned:
        candidates.append(cleaned)
    # Split by separators and keep promising chunks.
    for part in re.split(r'[／/｜|]', cleaned):
        part = part.strip()
        if len(part) >= 2:
            candidates.append(part)
    # alias variants
    expanded = []
    for c in candidates:
        expanded.append(c)
        if c in ALIASES:
            expanded.append(ALIASES[c])
        if c in REVERSE_ALIASES:
            expanded.append(REVERSE_ALIASES[c])
    # Deduplicate preserving order.
    dedup: List[str] = []
    seen = set()
    for c in expanded:
        if c not in seen:
            dedup.append(c)
            seen.add(c)
    return dedup


def build_catalog_maps(catalog_rows: List[Dict[str, str]]):
    exact = {row['title']: row for row in catalog_rows}
    normalized: Dict[str, Dict[str, str]] = {}
    normalized_keys: List[tuple[str, Dict[str, str]]] = []
    for row in catalog_rows:
        keys = {normalize_key(row['title'])}
        if row['title'] in ALIASES:
            keys.add(normalize_key(ALIASES[row['title']]))
        if row['title'] in REVERSE_ALIASES:
            keys.add(normalize_key(REVERSE_ALIASES[row['title']]))
        for key in keys:
            normalized.setdefault(key, row)
            normalized_keys.append((key, row))
    return exact, normalized, normalized_keys


def match_catalog_row(title: str, exact_map, normalized_map, normalized_keys):
    for candidate in candidate_titles_from_video(title):
        row = exact_map.get(candidate)
        if row:
            return candidate, row
        candidate_key = normalize_key(candidate)
        row = normalized_map.get(candidate_key)
        if row:
            return row['title'], row
        best = None
        best_len = 0
        for catalog_key, catalog_row in normalized_keys:
            if len(catalog_key) < 3:
                continue
            if catalog_key in candidate_key or candidate_key in catalog_key:
                key_len = len(catalog_key)
                if key_len > best_len:
                    best = catalog_row
                    best_len = key_len
        if best:
            return best['title'], best
    return '', None


def load_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    ranked_rows = load_rows(RANKED_PATH)
    catalog_rows = load_rows(CATALOG_PATH)
    exact_map, normalized_map, normalized_keys = build_catalog_maps(catalog_rows)

    works: Dict[str, Dict[str, object]] = {}
    for row in ranked_rows:
        title = row['title']
        if any(keyword in title for keyword in EXCLUDE_KEYWORDS):
            continue
        if row['is_short_candidate'] == 'true':
            continue
        duration_seconds = int(row['duration_seconds'] or 0)
        if duration_seconds > 5400:
            continue
        matched_title, catalog_row = match_catalog_row(title, exact_map, normalized_map, normalized_keys)
        normalized_title = matched_title or title
        bucket = works.setdefault(normalized_title, {
            'channel_year': row['published_year'],
            'representative_minutes': duration_seconds // 60,
            'matched_rows': 0,
            'publication_years': '',
            'magazines': '',
            'chronology_ordinals': '',
            'catalog_match': 'no',
        })
        bucket['channel_year'] = min([y for y in [bucket['channel_year'], row['published_year']] if y])
        bucket['representative_minutes'] = max(bucket['representative_minutes'], duration_seconds // 60)
        bucket['matched_rows'] += 1
        if catalog_row:
            bucket['publication_years'] = catalog_row.get('publication_years', '')
            bucket['magazines'] = catalog_row.get('magazines', '')
            bucket['chronology_ordinals'] = catalog_row.get('chronology_ordinals', '')
            bucket['catalog_match'] = 'yes'

    out_rows = []
    for title, payload in works.items():
        if payload['channel_year'] not in {'2021', '2022', '2023', '2024', '2025'}:
            continue
        out_rows.append({
            'channel_year': payload['channel_year'],
            'normalized_title': title,
            'representative_minutes': payload['representative_minutes'],
            'matched_rows': payload['matched_rows'],
            'publication_years': payload['publication_years'],
            'magazines': payload['magazines'],
            'chronology_ordinals': payload['chronology_ordinals'],
            'catalog_match': payload['catalog_match'],
        })
    out_rows.sort(key=lambda row: (row['channel_year'], row['normalized_title']))

    with OUT_CSV.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0].keys()))
        writer.writeheader()
        writer.writerows(out_rows)

    lines = [
        '# Zenigata Short Works 2021-2025',
        '',
        '- filters: exclude re-record, song, intro, trailer, and short videos',
        '- rule: 90 min and under',
        '',
    ]
    for year in ['2021', '2022', '2023', '2024', '2025']:
        subset = [row for row in out_rows if row['channel_year'] == year]
        lines.extend([
            f'## {year}',
            '',
            f'- works: {len(subset)}',
            f"- catalog matched: {sum(1 for row in subset if row['catalog_match'] == 'yes')}",
            '',
            '| title | minutes | publication_years | magazines | chronology |',
            '| --- | --- | --- | --- | --- |',
        ])
        for row in subset:
            title_md = row['normalized_title'].replace('|', '\\|')
            publication_md = row['publication_years'].replace('|', '\\|')
            magazines_md = row['magazines'].replace('|', '\\|')
            lines.append(
                f"| {title_md} | {row['representative_minutes']} | {publication_md} | {magazines_md} | {row['chronology_ordinals']} |"
            )
        lines.append('')
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')

    print(OUT_CSV)
    print(OUT_MD)
    print(f'matched_catalog={sum(1 for row in out_rows if row["catalog_match"] == "yes")}/{len(out_rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
