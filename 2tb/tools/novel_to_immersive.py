#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
長編小説 → immersive_reader JSON 変換ツール
============================================

【使い方】
1. このファイルの「設定エリア」にメタデータを記入
2. コマンド実行: python novel_to_immersive.py

【対応する章タイトルパターン】
- 第○章、第○編、第○部、第○話
- その一、その1
- 一、二、三...（漢数字）
- （一）、（1）
- 前編、後編、上、中、下
- 序章、終章、エピローグ、プロローグ
- ■ で始まる行

【出力フォーマット】
WordPress [immersive_reader] ショートコード形式
"""

import json
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional


# ============================================================
# ▼▼▼ 設定エリア（ここを編集してください） ▼▼▼
# ============================================================

# 1. 入力・出力ファイル
INPUT_FILE = "../texts/novel.txt"  # 読み込むテキストファイル
OUTPUT_FILE = "../bookdata/output.json"  # 出力ファイル

# 2. 基本情報（空欄の場合、テキストから自動検出を試みます）
TITLE = ""  # 作品タイトル
AUTHOR = ""  # 著者名
GENRE = "時代小説"  # ジャンル
ERA = ""  # 時代設定（例: 江戸時代）
YEAR = ""  # 発表年（例: 1935年）

# 3. あらすじ（三重引用符で複数行OK）
SYNOPSIS = """
ここに「あらすじ」を入力してください。
改行もそのまま反映されます。
""".strip()

# 4. 見どころ（リスト形式）
HIGHLIGHTS = [
    "見どころ1",
    "見どころ2",
    "見どころ3",
]

# 5. 登場人物
CHARACTERS = [
    {
        "name": "主人公の名前",
        "role": "主人公",  # 役割
        "desc": "キャラクターの説明文"
    },
    {
        "name": "登場人物2",
        "role": "脇役",
        "desc": "説明文"
    },
    # 必要に応じて追加...
]

# 6. 著者プロフィール
AUTHOR_PROFILE = {
    "name": "",  # 空欄の場合、AUTHORを使用
    "desc": "著者の紹介文をここに入力"
}

# 7. 章タイトルの追加パターン（必要に応じて）
# デフォルトで多くのパターンに対応済み
EXTRA_CHAPTER_PATTERNS = [
    # r"^★",  # 例: ★で始まる行
    # r"^【.+】",  # 例: 【】で囲まれた行
]

# 8. 章タイトルから除外するパターン（誤検出防止）
EXCLUDE_PATTERNS = [
    # r"^お",  # 例: 「お」で始まる行は除外
]

# ============================================================
# ▲▲▲ 設定エリア終了 ▲▲▲
# ============================================================


# =====================================
# 章タイトル判定パターン（組み込み）
# =====================================

BUILTIN_CHAPTER_PATTERNS = [
    # 「第○章」「第○編」「第○部」「第○話」「第○回」
    r'^第[一二三四五六七八九十百千〇零壱弐参肆伍陸漆捌玖拾]+[章編部話回節篇巻]',
    r'^第\d+[章編部話回節篇巻]',
    # 「その一」「その1」
    r'^その[一二三四五六七八九十]+',
    r'^その\d+',
    # 「○の○」パターン（例: 一の一）
    r'^[一二三四五六七八九十]+の[一二三四五六七八九十]+',
    # 「一」「二」などの漢数字のみ
    r'^[一二三四五六七八九十]+$',
    # 「（一）」「（1）」
    r'^[（\(][一二三四五六七八九十\d]+[）\)]',
    # 「前編」「後編」「上」「中」「下」
    r'^[前中後上下]編?$',
    # 「序」「序章」「終章」「エピローグ」「プロローグ」
    r'^(序章?|終章|エピローグ|プロローグ|結び|あとがき|はじめに)$',
    # 「■」で始まる
    r'^■',
    # 「〇〇篇」「〇〇編」
    r'^.{2,10}[篇編]$',
]

# サブ章（節）パターン
SUB_CHAPTER_PATTERNS = [
    r'^その[一二三四五六七八九十\d]+',
    r'^[一二三四五六七八九十]+$',
    r'^[（\(][一二三四五六七八九十\d]+[）\)]$',
]


def get_all_chapter_patterns() -> List[str]:
    """すべての章パターンを取得"""
    return BUILTIN_CHAPTER_PATTERNS + EXTRA_CHAPTER_PATTERNS


def is_excluded(line: str) -> bool:
    """除外パターンにマッチするか"""
    for pattern in EXCLUDE_PATTERNS:
        if re.match(pattern, line.strip()):
            return True
    return False


def is_explicit_chapter_title(line: str) -> bool:
    """明示的な章タイトルパターンにマッチするか"""
    line = line.strip()
    if is_excluded(line):
        return False
    for pattern in get_all_chapter_patterns():
        if re.match(pattern, line):
            return True
    return False


def is_sub_chapter_title(line: str) -> bool:
    """サブ章（節）パターンにマッチするか"""
    line = line.strip()
    if is_excluded(line):
        return False
    for pattern in SUB_CHAPTER_PATTERNS:
        if re.match(pattern, line):
            return True
    return False


def is_potential_chapter_title(line: str, prev_empty: bool, next_empty: bool) -> bool:
    """
    章タイトルの可能性があるか判定
    
    条件:
    1. 前後に空行がある
    2. 1行のセンテンス
    3. 長すぎない（30文字以下）
    4. 句読点で終わらない
    """
    line = line.strip()
    
    if not line or is_excluded(line):
        return False
    
    # 明示的パターンは空行関係なく認識
    if is_explicit_chapter_title(line):
        return True
    
    # 前後に空行がない場合は章タイトルではない
    if not (prev_empty and next_empty):
        return False
    
    # 長すぎる行は本文
    if len(line) > 30:
        return False
    
    # 句読点で終わる行は本文
    if line.endswith(('。', '、', '」', '…', '――', '！', '？', '」', '）', ')')):
        return False
    
    # 「」で囲まれている場合は会話文（本文）
    if line.startswith('「') and line.endswith('」'):
        return False
    
    # 「」を含む行は会話（本文）の可能性
    if '「' in line and '」' in line:
        return False
    
    return True


def extract_title_author(text: str) -> Tuple[str, str]:
    """
    テキストの冒頭からタイトルと著者を抽出
    
    対応フォーマット:
    - 山本周五郎著　立春なみだ橋
    - 三上於菟吉　雪之丞変化
    - 著者名 作品タイトル
    """
    lines = text.strip().split('\n')
    
    title = ""
    author = ""
    
    for line in lines[:10]:  # 冒頭10行を検索
        line = line.strip()
        if not line:
            continue
        
        # 「著」を含む行
        if '著' in line:
            parts = re.split(r'著\s*', line)
            if len(parts) >= 2:
                author = parts[0].strip()
                title = parts[1].strip()
                break
        
        # 全角スペースで区切られている場合
        if '　' in line:
            parts = line.split('　')
            if len(parts) >= 2:
                # 著者名っぽいかチェック（短い＋漢字多め）
                if len(parts[0]) <= 10:
                    author = parts[0].strip()
                    title = '　'.join(parts[1:]).strip()
                    break
    
    return title, author


def parse_chapters(text: str) -> List[Dict]:
    """
    テキストを解析して章構造を抽出
    
    Returns:
        [
            {
                "title": "章タイトル",
                "sub_title": "節タイトル（あれば）",
                "content": "本文"
            },
            ...
        ]
    """
    lines = text.split('\n')
    chapters = []
    
    current_chapter = {"title": "", "sub_title": "", "content": ""}
    content_buffer = []
    
    # 冒頭のタイトル・著者行をスキップ
    start_idx = 0
    for i, line in enumerate(lines[:10]):
        if '著' in line or (line.strip() and '　' in line):
            start_idx = i + 1
            break
    
    i = start_idx
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # 前後の空行チェック
        prev_empty = (i == 0) or (lines[i-1].strip() == "")
        next_empty = (i == len(lines) - 1) or (lines[i+1].strip() == "")
        
        # 章タイトル判定
        if is_potential_chapter_title(stripped, prev_empty, next_empty):
            # 現在のバッファを保存
            if content_buffer or current_chapter["title"]:
                current_chapter["content"] = '\n'.join(content_buffer).strip()
                if current_chapter["title"] or current_chapter["content"]:
                    chapters.append(current_chapter.copy())
                content_buffer = []
            
            # 新しい章を開始
            if is_explicit_chapter_title(stripped) and not is_sub_chapter_title(stripped):
                # メイン章タイトル
                current_chapter = {"title": stripped, "sub_title": "", "content": ""}
                
                # 次の行もタイトルかチェック（階層構造）
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines):
                    next_line = lines[j].strip()
                    next_prev_empty = (lines[j-1].strip() == "") if j > 0 else True
                    next_next_empty = (j == len(lines) - 1) or (lines[j+1].strip() == "")
                    if is_sub_chapter_title(next_line) or (
                        is_potential_chapter_title(next_line, next_prev_empty, next_next_empty) 
                        and not is_explicit_chapter_title(next_line)
                    ):
                        current_chapter["sub_title"] = next_line
                        i = j  # スキップ
            
            elif is_sub_chapter_title(stripped):
                # サブ章（節）タイトル
                if current_chapter["title"]:
                    # 既存の章にサブタイトルとして追加
                    # ただし内容がある場合は新しい章として扱う
                    if content_buffer:
                        current_chapter["content"] = '\n'.join(content_buffer).strip()
                        chapters.append(current_chapter.copy())
                        content_buffer = []
                        # 前の章タイトルを引き継ぎつつ、新しいサブタイトル
                        current_chapter = {
                            "title": current_chapter["title"],
                            "sub_title": stripped,
                            "content": ""
                        }
                    else:
                        current_chapter["sub_title"] = stripped
                else:
                    current_chapter = {"title": stripped, "sub_title": "", "content": ""}
            else:
                # その他の章タイトル
                current_chapter = {"title": stripped, "sub_title": "", "content": ""}
        
        elif stripped:
            # 本文
            content_buffer.append(line)
        
        i += 1
    
    # 最後のバッファを保存
    if content_buffer or current_chapter["title"]:
        current_chapter["content"] = '\n'.join(content_buffer).strip()
        if current_chapter["title"] or current_chapter["content"]:
            chapters.append(current_chapter)
    
    return chapters


def merge_chapters(chapters: List[Dict]) -> List[Dict]:
    """
    章構造を整理
    - 本文のない章は次の章にマージ
    - 同じメインタイトルの章をサブタイトルで区別
    """
    if not chapters:
        return chapters
    
    merged = []
    pending_title = ""
    
    for ch in chapters:
        # 本文がない章
        if not ch["content"].strip():
            if not ch["sub_title"]:
                pending_title = ch["title"]
            continue
        
        new_ch = ch.copy()
        
        # 保留中のタイトルがあれば適用
        if pending_title:
            if is_sub_chapter_title(new_ch["title"]):
                new_ch["sub_title"] = new_ch["title"]
                new_ch["title"] = pending_title
            elif pending_title != new_ch["title"]:
                if not new_ch["sub_title"]:
                    new_ch["sub_title"] = new_ch["title"]
                new_ch["title"] = pending_title
            pending_title = ""
        
        merged.append(new_ch)
    
    return merged


def format_chapter_title(ch: Dict) -> str:
    """章タイトルを1つの文字列にフォーマット"""
    if ch["sub_title"]:
        return f"{ch['title']}（{ch['sub_title']}）"
    return ch["title"]


def format_content(content: str) -> str:
    """本文を整形"""
    # 連続する空行を1つに
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content.strip()


def read_file_with_encoding(path: Path) -> str:
    """複数のエンコーディングを試してファイルを読み込む"""
    encodings = ['utf-8', 'shift_jis', 'cp932', 'euc_jp', 'utf-16']
    
    for enc in encodings:
        try:
            with open(path, 'r', encoding=enc) as f:
                content = f.read()
            print(f"   エンコーディング: {enc}")
            return content
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    raise ValueError(f"対応するエンコーディングが見つかりません: {path}")


def generate_immersive_json() -> None:
    """メイン処理: JSONを生成"""
    
    # 入力ファイル読み込み
    input_path = Path(INPUT_FILE)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent / INPUT_FILE
    
    if not input_path.exists():
        print(f"❌ エラー: ファイルが見つかりません: {input_path}")
        return
    
    print(f"📖 読み込み中: {input_path}")
    
    text = read_file_with_encoding(input_path)
    
    # タイトル・著者の取得
    detected_title, detected_author = extract_title_author(text)
    final_title = TITLE if TITLE else detected_title if detected_title else "無題"
    final_author = AUTHOR if AUTHOR else detected_author if detected_author else "不明"
    
    print(f"📕 タイトル: {final_title}")
    print(f"✍️  著者: {final_author}")
    
    # 章解析
    chapters = parse_chapters(text)
    chapters = merge_chapters(chapters)
    
    print(f"📑 検出された章: {len(chapters)}")
    
    # 章情報を表示
    for i, ch in enumerate(chapters[:10]):  # 最初の10章だけ表示
        title_str = format_chapter_title(ch)
        content_len = len(ch["content"])
        print(f"   {i+1}. {title_str} ({content_len}文字)")
    if len(chapters) > 10:
        print(f"   ... 他 {len(chapters) - 10} 章")
    
    # immersive_reader用データ構造を構築
    immersive_data = {
        "title": final_title,
        "author": final_author,
        "genre": GENRE,
        "era": ERA,
        "year": YEAR,
        "synopsis": SYNOPSIS,
        "highlights": HIGHLIGHTS,
        "characters": CHARACTERS,
        "authorProfile": {
            "name": AUTHOR_PROFILE["name"] if AUTHOR_PROFILE["name"] else final_author,
            "desc": AUTHOR_PROFILE["desc"]
        },
        "chapters": [
            {
                "title": format_chapter_title(ch),
                "content": format_content(ch["content"])
            }
            for ch in chapters
        ]
    }
    
    # JSON生成
    json_output = json.dumps(immersive_data, ensure_ascii=False, indent=2)
    
    # ショートコードで囲む
    final_output = f"[immersive_reader]\n{json_output}\n[/immersive_reader]"
    
    # 出力
    output_path = Path(OUTPUT_FILE)
    if not output_path.is_absolute():
        output_path = Path(__file__).parent / OUTPUT_FILE
    
    # 出力ディレクトリ作成
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_output)
    
    print(f"\n✅ 出力完了: {output_path}")
    print(f"   ファイルサイズ: {len(final_output):,} bytes")
    print(f"   総章数: {len(chapters)}")
    
    # 統計
    total_chars = sum(len(ch["content"]) for ch in chapters)
    print(f"   総文字数: {total_chars:,} 文字")


def debug_chapters() -> None:
    """デバッグ用: 章構造を詳細表示"""
    input_path = Path(INPUT_FILE)
    if not input_path.is_absolute():
        input_path = Path(__file__).parent / INPUT_FILE
    
    if not input_path.exists():
        print(f"❌ エラー: ファイルが見つかりません: {input_path}")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    chapters = parse_chapters(text)
    chapters = merge_chapters(chapters)
    
    print(f"\n【章構造詳細】全{len(chapters)}章\n")
    print("=" * 60)
    
    for i, ch in enumerate(chapters):
        print(f"\n■ 第{i+1}章")
        print(f"  タイトル: {ch['title']}")
        if ch['sub_title']:
            print(f"  サブタイトル: {ch['sub_title']}")
        print(f"  本文: {len(ch['content'])}文字")
        # 本文の冒頭を表示
        preview = ch['content'][:100].replace('\n', '↵')
        print(f"  冒頭: {preview}...")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        debug_chapters()
    else:
        generate_immersive_json()
