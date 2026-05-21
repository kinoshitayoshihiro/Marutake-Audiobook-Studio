#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雪之丞変化 → immersive_reader 変換
==================================

【使い方】
1. INPUT_FILE のパスを設定
2. 下記のメタデータを編集
3. 実行: python convert_yukinojo.py

【注意】
- このファイルは「雪之丞変化」専用の設定ファイルです
- 他の作品には novel_to_immersive.py をコピーして使用してください
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Tuple


# ============================================================
# ▼▼▼ 設定エリア ▼▼▼
# ============================================================

# 入力・出力ファイル
INPUT_FILE = "/Users/kinoshitayoshihiro/Library/CloudStorage/GoogleDrive-shimogami88@gmail.com/マイドライブ/丸竹書房/三上於菟吉　雪之丞変化.txt"
OUTPUT_FILE = "../bookdata/雪之丞変化.json"

# 基本情報
TITLE = "雪之丞変化"
AUTHOR = "三上於菟吉"
GENRE = "時代小説・復讐劇"
ERA = "江戸時代"
YEAR = "1934-1935年"

# あらすじ
SYNOPSIS = """
長崎の豪商・松浦屋を父に持つ雪之丞は、幼くして一家離散の悲運に遭う。
土部三斎、門倉平馬、広海屋——三人の悪党による陰謀で、父は無実の罪を着せられ、
母と共に非業の死を遂げた。

二十年の歳月を経て、雪之丞は上方随一の女形として江戸に下る。
その妖艶な美貌の下には、復讐の炎が静かに燃えていた。

義賊・闇太郎との奇縁、敵の娘・浪路との禁断の恋、
そして三人の仇との対峙——。
復讐と愛憎が絡み合う、哀切にして壮絶な時代絵巻。
""".strip()

# 見どころ
HIGHLIGHTS = [
    "女形・雪之丞の妖艶な美と剣の腕前",
    "義賊・闘太郎との友情と共闘",
    "仇の娘・浪路との禁断の恋",
    "二十年越しの復讐劇の行方",
    "江戸歌舞伎の華やかな世界",
]

# 登場人物
CHARACTERS = [
    {
        "name": "中村雪之丞",
        "role": "主人公",
        "desc": "上方随一の女形。本名は松浦屋の遺児。父母の仇を討つため江戸に下る。妖艷な美貌と剣の達人。"
    },
    {
        "name": "闇太郎",
        "role": "義賊",
        "desc": "江戸を騒がす義賊。雪之丞の協力者となり、復讐に手を貸す。粋で義理堅い男。"
    },
    {
        "name": "土部三斎",
        "role": "仇敵",
        "desc": "老中。松浦屋を陥れた首謀者の一人。権力を笠に着る悪党。"
    },
    {
        "name": "門倉平馬",
        "role": "仇敵", 
        "desc": "土部三斎の腹心。松浦屋一家滅亡の実行者。"
    },
    {
        "name": "広海屋",
        "role": "仇敵",
        "desc": "江戸の大商人。土部三斎と結託し、松浦屋を陥れて財を成した。"
    },
    {
        "name": "浪路",
        "role": "ヒロイン",
        "desc": "土部三斎の娘。雪之丞に恋心を抱く。仇の娘と知りながら、雪之丞も心惹かれる。"
    },
    {
        "name": "お初",
        "role": "協力者",
        "desc": "雪之丞を慕う女。復讐に協力する。"
    },
]

# 著者プロフィール
AUTHOR_PROFILE = {
    "name": "三上於菟吉",
    "desc": "1891年（明治24年）埼玉県生まれ。大正・昭和期の大衆小説家。『雪之丞変化』は新聞連載時から大人気を博し、映画・舞台化され国民的作品となった。1944年没。"
}

# 章パターン（雪之丞変化用）
# 「第○篇」「○の○」などに対応
EXTRA_CHAPTER_PATTERNS = [
    r'^第[一二三四五六七八九十]+篇',  # 第一篇 など
    r'^[一二三四五六七八九十]+の[一二三四五六七八九十]+',  # 一の一 など
]

# ============================================================
# ▲▲▲ 設定エリア終了 ▲▲▲
# ============================================================


# 組み込みパターン
BUILTIN_CHAPTER_PATTERNS = [
    r'^第[一二三四五六七八九十百千〇零壱弐参肆伍陸漆捌玖拾]+[章編部話回節篇巻]',
    r'^第\d+[章編部話回節篇巻]',
    r'^その[一二三四五六七八九十]+',
    r'^その\d+',
    r'^[一二三四五六七八九十]+の[一二三四五六七八九十]+',
    r'^[一二三四五六七八九十]+$',
    r'^[（\(][一二三四五六七八九十\d]+[）\)]',
    r'^[前中後上下]編?$',
    r'^(序章?|終章|エピローグ|プロローグ|結び|あとがき|はじめに)$',
    r'^■',
    r'^.{2,10}[篇編]$',
]

SUB_CHAPTER_PATTERNS = [
    r'^その[一二三四五六七八九十\d]+',
    r'^[一二三四五六七八九十]+$',
    r'^[（\(][一二三四五六七八九十\d]+[）\)]$',
    r'^[一二三四五六七八九十]+の[一二三四五六七八九十]+',
]


def get_all_patterns():
    return BUILTIN_CHAPTER_PATTERNS + EXTRA_CHAPTER_PATTERNS


def is_chapter_title(line: str) -> bool:
    line = line.strip()
    for pattern in get_all_patterns():
        if re.match(pattern, line):
            return True
    return False


def is_sub_chapter(line: str) -> bool:
    line = line.strip()
    for pattern in SUB_CHAPTER_PATTERNS:
        if re.match(pattern, line):
            return True
    return False


def is_potential_title(line: str, prev_empty: bool, next_empty: bool) -> bool:
    line = line.strip()
    if not line:
        return False
    
    # 長すぎる行は章タイトルではない（誤検出防止）
    if len(line) > 40:
        return False
    
    if is_chapter_title(line):
        return True
    if not (prev_empty and next_empty):
        return False
    if len(line) > 30:
        return False
    if line.endswith(('。', '、', '」', '…', '――', '！', '？')):
        return False
    if line.startswith('「') and line.endswith('」'):
        return False
    return True


def extract_title_author(text: str) -> Tuple[str, str]:
    lines = text.strip().split('\n')
    for line in lines[:10]:
        line = line.strip()
        if not line:
            continue
        if '著' in line:
            parts = re.split(r'著\s*', line)
            if len(parts) >= 2:
                return parts[1].strip(), parts[0].strip()
        if '　' in line:
            parts = line.split('　')
            if len(parts) >= 2 and len(parts[0]) <= 10:
                return '　'.join(parts[1:]).strip(), parts[0].strip()
    return "", ""


def parse_chapters(text: str) -> List[Dict]:
    lines = text.split('\n')
    chapters = []
    current = {"title": "", "sub_title": "", "content": ""}
    buffer = []
    
    # 冒頭スキップ
    start = 0
    for i, line in enumerate(lines[:10]):
        if '著' in line or (line.strip() and '　' in line):
            start = i + 1
            break
    
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        prev_empty = (i == 0) or (lines[i-1].strip() == "")
        next_empty = (i == len(lines) - 1) or (lines[i+1].strip() == "")
        
        if is_potential_title(stripped, prev_empty, next_empty):
            if buffer or current["title"]:
                current["content"] = '\n'.join(buffer).strip()
                if current["title"] or current["content"]:
                    chapters.append(current.copy())
                buffer = []
            
            if is_chapter_title(stripped) and not is_sub_chapter(stripped):
                current = {"title": stripped, "sub_title": "", "content": ""}
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines):
                    next_line = lines[j].strip()
                    np = (lines[j-1].strip() == "") if j > 0 else True
                    nn = (j == len(lines) - 1) or (lines[j+1].strip() == "")
                    if is_sub_chapter(next_line) or is_potential_title(next_line, np, nn):
                        current["sub_title"] = next_line
                        i = j
            elif is_sub_chapter(stripped):
                if current["title"] and buffer:
                    current["content"] = '\n'.join(buffer).strip()
                    chapters.append(current.copy())
                    buffer = []
                    current = {"title": current["title"], "sub_title": stripped, "content": ""}
                elif current["title"]:
                    current["sub_title"] = stripped
                else:
                    current = {"title": stripped, "sub_title": "", "content": ""}
            else:
                current = {"title": stripped, "sub_title": "", "content": ""}
        elif stripped:
            buffer.append(line)
        
        i += 1
    
    if buffer or current["title"]:
        current["content"] = '\n'.join(buffer).strip()
        if current["title"] or current["content"]:
            chapters.append(current)
    
    return chapters


def merge_chapters(chapters: List[Dict]) -> List[Dict]:
    if not chapters:
        return chapters
    
    merged = []
    pending = ""
    
    for ch in chapters:
        # 本文が非常に短い章（誤検出）は前の章にマージ
        content = ch["content"].strip()
        if len(content) < 50 and merged:
            # 前の章に追記
            merged[-1]["content"] += "\n\n" + content
            continue
        
        if not content:
            if not ch["sub_title"]:
                pending = ch["title"]
            continue
        
        new_ch = ch.copy()
        if pending:
            if is_sub_chapter(new_ch["title"]):
                new_ch["sub_title"] = new_ch["title"]
                new_ch["title"] = pending
            elif pending != new_ch["title"]:
                if not new_ch["sub_title"]:
                    new_ch["sub_title"] = new_ch["title"]
                new_ch["title"] = pending
            pending = ""
        
        merged.append(new_ch)
    
    # 最初の章がタイトルのみ（空または非常に短い）場合は除去
    if merged and len(merged[0].get("content", "").strip()) < 20:
        merged = merged[1:]
    
    return merged


def format_title(ch: Dict) -> str:
    """章タイトルを整形（■を除去）"""
    title = ch["title"].lstrip('■').strip()
    sub = ch.get("sub_title", "").lstrip('■').strip()
    if sub:
        return f"{title}（{sub}）"
    return title


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


def main():
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print(f"❌ ファイルが見つかりません: {input_path}")
        return
    
    print(f"📖 読み込み中: {input_path.name}")
    
    text = read_file_with_encoding(input_path)
    
    det_title, det_author = extract_title_author(text)
    final_title = TITLE if TITLE else det_title if det_title else "無題"
    final_author = AUTHOR if AUTHOR else det_author if det_author else "不明"
    
    print(f"📕 {final_title} / {final_author}")
    
    chapters = parse_chapters(text)
    chapters = merge_chapters(chapters)
    
    print(f"📑 {len(chapters)}章を検出")
    
    for i, ch in enumerate(chapters[:15]):
        print(f"   {i+1}. {format_title(ch)} ({len(ch['content'])}文字)")
    if len(chapters) > 15:
        print(f"   ... 他 {len(chapters) - 15} 章")
    
    data = {
        "title": final_title,
        "author": final_author,
        "genre": GENRE,
        "era": ERA,
        "year": YEAR,
        "synopsis": SYNOPSIS,
        "highlights": HIGHLIGHTS,
        "characters": CHARACTERS,
        "authorProfile": AUTHOR_PROFILE,
        "chapters": [
            {"title": format_title(ch), "content": re.sub(r'\n{3,}', '\n\n', ch["content"]).strip()}
            for ch in chapters
        ]
    }
    
    output = f"[immersive_reader]\n{json.dumps(data, ensure_ascii=False, indent=2)}\n[/immersive_reader]"
    
    output_path = Path(OUTPUT_FILE)
    if not output_path.is_absolute():
        output_path = Path(__file__).parent / OUTPUT_FILE
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    total = sum(len(ch["content"]) for ch in chapters)
    print(f"\n✅ 出力: {output_path}")
    print(f"   {len(chapters)}章 / {total:,}文字")


if __name__ == "__main__":
    main()
