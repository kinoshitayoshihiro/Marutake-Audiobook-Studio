#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メタデータ拡張システムのデモンストレーション
"""

import json
from pathlib import Path

print("="*70)
print("📊 ジャンル・感情メタデータ拡張システム - デモンストレーション")
print("="*70)

# 1. ジャンル分類体系の確認
print("\n【1】ジャンル分類体系")
print("-" * 70)

with open('genre_taxonomy.json', 'r', encoding='utf-8') as f:
    taxonomy = json.load(f)

print(f"登録ジャンル数: {len(taxonomy['genres'])}種類")
print(f"感情タグ数: {len(taxonomy['emotions'])}種類")
print(f"テーマタグ数: {len(taxonomy['themes'])}種類")

print("\n主要ジャンル:")
for genre_id, genre_data in list(taxonomy['genres'].items())[:5]:
    print(f"  • {genre_data['label']}")
    print(f"    Schema.org: {genre_data['schema_genre']}")
    print(f"    説明: {genre_data['description'][:40]}...")

# 2. サンプルメタデータの確認
print("\n【2】サンプルメタデータ（艶妻傳）")
print("-" * 70)

with open('meta_example_tsuyazuma.json', 'r', encoding='utf-8') as f:
    sample_meta = json.load(f)

print(f"ジャンル: {sample_meta['japanese_genre']} ({sample_meta['genre']})")
print(f"サブジャンル: {', '.join(sample_meta['sub_genre'])}")
print(f"テーマ: {', '.join(sample_meta['themes'])}")
print(f"感情: {', '.join(sample_meta['emotions'])}")
print(f"舞台: {sample_meta['setting']['period']} - {sample_meta['setting']['location']}")

# 3. 既存データとの互換性確認
print("\n【3】既存データとの互換性テスト")
print("-" * 70)

test_files = [
    '../bookdata/艶妻傳.json',
    '../bookdata/四条畷.json',
    '../bookdata/泥棒と若殿.json'
]

for file_path in test_files:
    path = Path(file_path)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        has_new_fields = any([
            'japanese_genre' in data,
            'themes' in data,
            'emotions' in data
        ])
        
        status = "🆕 新メタデータあり" if has_new_fields else "✅ 互換性OK"
        print(f"  {path.name:25} {status}")

# 4. Schema.org変換シミュレーション
print("\n【4】Schema.org構造化データ変換")
print("-" * 70)

schema = {
    "@context": "https://schema.org",
    "@type": "Book",
    "name": sample_meta.get("title", "艶妻傳"),
    "author": {
        "@type": "Person",
        "name": sample_meta["author_info"]["name"]
    },
    "genre": sample_meta["genre"],
    "keywords": ", ".join(sample_meta["keywords"]),
    "additionalProperty": [
        {
            "@type": "PropertyValue",
            "name": "japanese_genre",
            "value": sample_meta["japanese_genre"]
        },
        {
            "@type": "PropertyValue",
            "name": "themes",
            "value": sample_meta["themes"]
        }
    ]
}

print(json.dumps(schema, ensure_ascii=False, indent=2)[:500] + "...")

# 5. キーワード密度分析
print("\n【5】SEOキーワード分析")
print("-" * 70)

all_keywords = set()
for keyword in sample_meta.get("keywords", []):
    all_keywords.add(keyword)
all_keywords.add(sample_meta.get("japanese_genre", ""))
all_keywords.update(sample_meta.get("themes", []))

print(f"総キーワード数: {len(all_keywords)}個")
print(f"キーワード: {', '.join(list(all_keywords)[:10])}")

print("\n" + "="*70)
print("✅ デモンストレーション完了")
print("="*70)
print("\n📚 詳細はMETADATA_EXTENSION_README.mdを参照してください")
