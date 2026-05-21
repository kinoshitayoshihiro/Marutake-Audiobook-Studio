#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
斑猫呪文 → immersive_reader JSON 変換スクリプト
テキストファイルを読み込んで章ごとに分割し、JSONを生成します。
"""

import json
import re
from pathlib import Path

# ============================================================
# 設定
# ============================================================

# 入力ファイル（Google Driveからコピーしてください）
INPUT_FILE = "斑猫呪文.txt"

# 出力ファイル
OUTPUT_FILE = "../bookdata/斑猫呪文.json"

# ============================================================
# メタデータ設定
# ============================================================

METADATA = {
    "title": "斑猫呪文",
    "author": "山本周五郎",
    "synopsis": (
        "仕官の口を求めて江戸へ出てきた出羽浪人・陣守伊兵衛と、"
        "御書院番の嫡男でありながら放蕩三昧の生活を送る「若様浪人」こと宮部鮎二郎。\n\n"
        "二人は辻幻術師の妖艶な女・阿捨（おすて）と、彼女につきまとう不気味な巨大な斑猫（はんみょう）が引き起こす怪異に巻き込まれる。"
        "伊兵衛の親友・静馬の失踪、宮部家お取り潰しの危機、そして将軍家大奥に纏わる五十年前の恐るべき「石子詰め」の呪い。\n\n"
        "鮎二郎は許嫁の節子姫を守るため、伊兵衛とともに剣と智恵で妖術使いの老婆に立ち向かう。"
        "幻術と剣戟が交錯する、山本周五郎の怪奇時代小説。"
    ),
    "authorProfile": {
        "name": "山本 周五郎",
        "desc": (
            "1903年（明治36年）生まれ。日本の小説家。本名は清水三十六（しみず さとむ）。\n"
            "庶民の生活や人情を描いた時代小説で絶大な人気を博した。"
            "『樅ノ木は残った』『赤ひげ診療譚』『青べか物語』など数多くの名作を残す。"
            "人間の哀歓を温かい眼差しで描く作風が特徴だが、本作のような怪奇ミステリー色の強い作品も手がけている。"
        )
    },
    "characters": [
        {
            "name": "宮部鮎二郎",
            "role": "主人公",
            "desc": "七千石の旗本・宮部家の嫡男だが、家を出て「じだらく」な浪人生活を送る美男の剣客。実は家系に纏わる呪いと陰謀を探っている。"
        },
        {
            "name": "陣守伊兵衛",
            "role": "相棒",
            "desc": "出羽出身の剛直な浪人。鮎二郎と街中で一触即発の出会いをするが、後に共に怪異に立ち向かうことになる。諏訪流の使い手。"
        },
        {
            "name": "阿捨（おすて）",
            "role": "幻術師",
            "desc": "辻幻術を行う妖艶な美女。鮎二郎を執拗に誘惑し、支配しようとする。その正体には恐るべき秘密が隠されている。"
        },
        {
            "name": "節子姫（おつう）",
            "role": "ヒロイン",
            "desc": "酒井伯耆守の娘で、鮎二郎の許嫁。鮎二郎の放蕩を信じず、彼を待ち続ける一途な女性。呪いの標的となる。"
        },
        {
            "name": "斑猫",
            "role": "怪異",
            "desc": "阿捨につき従う巨大な猫。人を襲い、不思議な妖気を放つ。事件の鍵を握る存在。"
        },
        {
            "name": "河村静馬",
            "role": "友人",
            "desc": "伊兵衛の友人。辻幻術の「函術」の実験台にされて以来、様子がおかしくなり、怪異な失踪を遂げる。"
        },
        {
            "name": "香折",
            "role": "静馬の妹",
            "desc": "兄と共に江戸へ出てきた美しい娘。兄の失踪後、伊兵衛に守られることになる。"
        }
    ]
}

# 章タイトルパターン
CHAPTER_PATTERNS = [
    r'^(じだらく三味|辻幻術|怪異|春雪|渦紋|遁道|声|ひでり雨|藪の中|元文秘記)\s*$',
]

# サブ章パターン（其の一、其の二...）
SUB_CHAPTER_PATTERN = r'^其の[一二三四五六七八九十]+\s*$'


def detect_chapters(text: str) -> list:
    """テキストを章ごとに分割"""
    lines = text.split('\n')
    chapters = []
    current_chapter = None
    current_content = []
    
    chapter_pattern = re.compile('|'.join(CHAPTER_PATTERNS))
    sub_pattern = re.compile(SUB_CHAPTER_PATTERN)
    
    for line in lines:
        stripped = line.strip()
        
        # 章タイトル検出
        if chapter_pattern.match(stripped):
            # 前の章を保存
            if current_chapter:
                chapters.append({
                    "title": current_chapter,
                    "content": '\n'.join(current_content).strip()
                })
            current_chapter = stripped
            current_content = []
        elif sub_pattern.match(stripped):
            # サブ章は本文の一部として含める（見出しとして）
            current_content.append(f"\n{stripped}\n")
        else:
            current_content.append(line)
    
    # 最後の章を保存
    if current_chapter:
        chapters.append({
            "title": current_chapter,
            "content": '\n'.join(current_content).strip()
        })
    
    return chapters


def main():
    print("=" * 60)
    print("斑猫呪文 - Immersive Reader JSON 生成")
    print("=" * 60)
    
    input_path = Path(__file__).parent / INPUT_FILE
    output_path = Path(__file__).parent / OUTPUT_FILE
    
    # 入力ファイル確認
    if not input_path.exists():
        print(f"\n❌ 入力ファイルが見つかりません: {input_path}")
        print("\n【手順】")
        print(f"1. Google Driveから「山本周五郎著　斑猫呪文.txt」をダウンロード")
        print(f"2. ファイル名を「{INPUT_FILE}」に変更")
        print(f"3. {input_path.parent} に配置")
        print("4. このスクリプトを再実行")
        return
    
    # テキスト読み込み
    print(f"\n📖 読み込み中: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 章分割
    chapters = detect_chapters(text)
    print(f"✅ {len(chapters)} 章を検出")
    
    for i, ch in enumerate(chapters, 1):
        print(f"   {i}. {ch['title']} ({len(ch['content'])}文字)")
    
    # JSON構築
    output_data = {
        **METADATA,
        "chapters": chapters
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
