#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
花も刀も（山本周五郎）→ immersive_reader JSON 変換スクリプト
短編集を読み込んで、各短編を章として分割し、JSONを生成します。
"""

import json
import re
from pathlib import Path

# ============================================================
# 設定
# ============================================================

# 入力ファイル
INPUT_FILE = "花も刀も.txt"

# 出力ファイル
OUTPUT_FILE = "../bookdata/花も刀も.json"

# ============================================================
# メタデータ設定
# ============================================================

METADATA = {
    "title": "花も刀も",
    "author": "山本周五郎",
    "synopsis": (
        "山本周五郎が描く、市井に生きる人々の哀歓と矜持。\n\n"
        "道場から放逐された若き剣士の苦悩と再起を描く「みぞれの街」、"
        "生活に追われながらも誇りを失わない職人たちを描く「なりわい」「新粧」、"
        "愛と別離の機微を綴る「その人」「よせる波」など、"
        "七篇の珠玉の短編を収録。\n\n"
        "庶民の暮らしの中にある喜びと悲しみ、"
        "そして人間としての誇りと優しさを、"
        "温かな筆致で描き出した名作短編集。"
    ),
    "authorProfile": {
        "name": "山本 周五郎",
        "desc": (
            "1903年（明治36年）生まれ。日本の小説家。本名は清水三十六（しみず さとむ）。\n"
            "庶民の生活や人情を描いた時代小説で絶大な人気を博した。"
            "『樅ノ木は残った』『赤ひげ診療譚』『青べか物語』など数多くの名作を残す。"
            "人間の哀歓を温かい眼差しで描く作風が特徴。"
        )
    },
    "characters": []  # 短編集のため、個別の登場人物は設定しない
}

# 短編タイトルリスト
STORY_TITLES = [
    "みぞれの街",
    "なりわい", 
    "新粧",
    "その人",
    "よせる波",
    "暦日",
    "秋あらし"
]


def detect_stories(text: str) -> list:
    """テキストを短編ごとに分割"""
    lines = text.split('\n')
    stories = []
    current_story = None
    current_content = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 短編タイトル検出
        if stripped in STORY_TITLES:
            # 前の短編を保存
            if current_story:
                stories.append({
                    "title": current_story,
                    "content": '\n'.join(current_content).strip()
                })
            current_story = stripped
            current_content = []
        elif stripped == "花も刀も":
            # 全体タイトルはスキップ
            continue
        else:
            if current_story:  # タイトルが見つかってから収集開始
                current_content.append(line)
    
    # 最後の短編を保存
    if current_story:
        stories.append({
            "title": current_story,
            "content": '\n'.join(current_content).strip()
        })
    
    return stories


def main():
    print("=" * 60)
    print("花も刀も（山本周五郎 短編集）- Immersive Reader JSON 生成")
    print("=" * 60)
    
    input_path = Path(__file__).parent / INPUT_FILE
    output_path = Path(__file__).parent / OUTPUT_FILE
    
    # 入力ファイル確認
    if not input_path.exists():
        print(f"\n❌ 入力ファイルが見つかりません: {input_path}")
        return
    
    # テキスト読み込み（複数エンコーディング対応）
    print(f"\n📖 読み込み中: {input_path}")
    text = None
    for encoding in ['utf-8', 'shift_jis', 'cp932', 'euc-jp']:
        try:
            with open(input_path, 'r', encoding=encoding) as f:
                text = f.read()
            print(f"   エンコーディング: {encoding}")
            break
        except UnicodeDecodeError:
            continue
    
    if text is None:
        print("❌ ファイルの読み込みに失敗しました")
        return
    
    # 短編分割
    stories = detect_stories(text)
    print(f"✅ {len(stories)} 篇を検出")
    
    for i, story in enumerate(stories, 1):
        print(f"   {i}. {story['title']} ({len(story['content'])}文字)")
    
    # JSON構築
    output_data = {
        **METADATA,
        "chapters": stories
    }
    
    # 出力
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ JSON出力完了: {output_path}")
    print(f"   ファイルサイズ: {output_path.stat().st_size:,} bytes")
    
    # ショートコード用出力
    shortcode_path = output_path.with_suffix('.txt')
    with open(shortcode_path, 'w', encoding='utf-8') as f:
        json_str = json.dumps(output_data, ensure_ascii=False, separators=(',', ':'))
        f.write(f"[immersive_reader]{json_str}[/immersive_reader]")
    
    print(f"✅ ショートコード出力: {shortcode_path}")
    print("\n【使い方】")
    print("1. WordPress管理画面で投稿を編集")
    print("2. ショートコードファイルの内容を貼り付け")
    print("   または")
    print("3. JSONファイルをメディアにアップロードし、")
    print("   [immersive_reader file=\"JSONのURL\"][/immersive_reader] を使用")


if __name__ == "__main__":
    main()
