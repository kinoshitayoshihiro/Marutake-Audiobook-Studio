#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress投稿用ショートコード生成
=================================
bookdata.json を [immersive_reader] ショートコード形式に変換します。

【使い方】
python json_to_shortcode.py bookdata.json -o wordpress_post.txt
"""

import json
import argparse
from pathlib import Path


def json_to_shortcode(bookdata: dict) -> str:
    """bookdata辞書をショートコード形式に変換"""
    
    # JSON文字列を整形（ショートコード内に埋め込み）
    json_str = json.dumps(bookdata, ensure_ascii=False, indent=2)
    
    shortcode = f"""[immersive_reader]
{json_str}
[/immersive_reader]"""
    
    return shortcode


def main():
    parser = argparse.ArgumentParser(
        description='bookdata.jsonをWordPress用ショートコードに変換'
    )
    parser.add_argument('input', help='入力JSONファイル（bookdata）')
    parser.add_argument('-o', '--output', help='出力ファイル')
    
    args = parser.parse_args()
    
    # 入力ファイル読み込み
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {args.input}")
        return 1
    
    with open(input_path, 'r', encoding='utf-8') as f:
        bookdata = json.load(f)
    
    # ショートコード生成
    shortcode = json_to_shortcode(bookdata)
    
    # 出力
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(shortcode)
        print(f"✅ 出力完了: {args.output}")
        print(f"📋 このファイルの内容をWordPressの投稿にコピペしてください")
        print(f"📁 カテゴリ: reading_application を選択")
    else:
        print(shortcode)
    
    return 0


if __name__ == '__main__':
    exit(main())
