#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
菊屋敷（山本周五郎）JSON変換スクリプト
章番号（一、二、三...）で区切られた中篇小説
"""

import json
import re
import os

def detect_encoding(file_path):
    """ファイルのエンコーディングを検出"""
    encodings = ['utf-8', 'shift_jis', 'cp932', 'euc-jp']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                f.read()
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return 'utf-8'

def load_text(file_path):
    """テキストファイルを読み込む"""
    encoding = detect_encoding(file_path)
    print(f"検出エンコーディング: {encoding}")
    with open(file_path, 'r', encoding=encoding) as f:
        return f.read()

def split_chapters(text):
    """テキストを章ごとに分割"""
    # 漢数字パターン
    chapter_pattern = r'^([一二三四五六七八九十]+)\s*$'
    
    lines = text.split('\n')
    chapters = []
    current_chapter = None
    current_content = []
    
    for line in lines:
        match = re.match(chapter_pattern, line.strip())
        if match:
            # 前の章を保存
            if current_chapter is not None:
                content = '\n'.join(current_content).strip()
                if content:
                    chapters.append({
                        'number': current_chapter,
                        'content': content
                    })
            # 新しい章を開始
            current_chapter = match.group(1)
            current_content = []
        else:
            if current_chapter is not None:
                current_content.append(line)
    
    # 最後の章を保存
    if current_chapter is not None:
        content = '\n'.join(current_content).strip()
        if content:
            chapters.append({
                'number': current_chapter,
                'content': content
            })
    
    return chapters

def clean_text(text):
    """テキストをクリーンアップ"""
    # 複数の空行を1つに
    text = re.sub(r'\n{3,}', '\n\n', text)
    # 行末のスペースを削除
    text = re.sub(r' +\n', '\n', text)
    # 前後の空白を削除
    text = text.strip()
    return text

def kanji_to_int(kanji):
    """漢数字を整数に変換"""
    kanji_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, 
                 '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    if kanji in kanji_map:
        return kanji_map[kanji]
    # 十一〜十八のケース
    if kanji.startswith('十'):
        if len(kanji) == 1:
            return 10
        return 10 + kanji_map.get(kanji[1], 0)
    return 0

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, '菊屋敷.txt')
    output_dir = os.path.join(os.path.dirname(script_dir), 'bookdata')
    
    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)
    
    print("=" * 60)
    print("菊屋敷 JSON変換")
    print("=" * 60)
    
    # テキスト読み込み
    text = load_text(input_file)
    print(f"ファイル読み込み完了: {len(text)} 文字")
    
    # 章に分割
    chapters = split_chapters(text)
    print(f"検出した章数: {len(chapters)}")
    
    for ch in chapters:
        content = clean_text(ch['content'])
        ch['content'] = content
        print(f"  第{ch['number']}章: {len(content)} 文字")
    
    # JSON構造を作成
    book_data = {
        "title": "菊屋敷",
        "author": "山本周五郎",
        "synopsis": """山本周五郎が描く、一人の女性の静かな自己犠牲と、その内に秘められた強い意志の物語。

主人公の志保は、亡き父の跡を継ぎ、村塾で子供たちを教えながら穏やかに暮らしている。彼女の元に、父の門下生からと思われる差出人不明の恋文が届き、心に静かな波紋が広がる。

そんな中、野心を抱く夫と共に高田から戻った妹・小松に、長男の晋太郎を養子として預かってほしいと懇願される。自らの幸福の可能性と、姉としての責任との間で、志保が下した決断とは。

女性の生き方、家族の絆、そして武士の時代の理想と現実が、美しい菊の咲く屋敷を舞台に繊細な筆致で描かれます。""",
        "authorProfile": {
            "name": "山本 周五郎",
            "desc": "1903年（明治36年）〜1967年（昭和42年）。日本の小説家。本名は清水三十六（しみず さとむ）。庶民の生活や人情を描いた時代小説で絶大な人気を博した。『樅ノ木は残った』『赤ひげ診療譚』『青べか物語』など数多くの名作を残す。人間の哀歓を温かい眼差しで描く作風が特徴。"
        },
        "characters": [
            {
                "name": "志保",
                "desc": "物語の主人公。亡き父の遺志を継ぎ、村塾を営む聡明で芯の強い女性。自らを美しいと思わず、学問の道を志したが父に止められた過去を持つ。甥の晋太郎を我が子として育てる。"
            },
            {
                "name": "小松",
                "desc": "志保の妹。美しく勝気な性格。夫・晋吾の出世のため、長男を姉に預けるという大胆な行動に出る。環境によって心の在り様が大きく変わる。"
            },
            {
                "name": "園部 晋吾",
                "desc": "小松の夫。志保の父の門下生で秀才だったが、立身出世への野心を強く持つ。妻と共に蘭学を学ぶため長崎へ向かう。"
            },
            {
                "name": "晋太郎",
                "desc": "小松と晋吾の長男。志保に引き取られ、武士として厳しく育てられる。幼いながらも、自分の意志で厳しい道を選ぶ気骨を持つ。"
            },
            {
                "name": "杉田 庄三郎",
                "desc": "志保の父の門下生たちの中心的存在。志保に密かな想いを寄せている可能性が示唆される人物。国を憂い、仲間と共に幕政を批判する活動を行う。"
            },
            {
                "name": "お萱",
                "desc": "志保と小松の乳母で、現在は志保の世話をしている。志保を深く理解し、その身を案じている。"
            }
        ],
        "chapters": []
    }
    
    # 章データを追加
    for ch in chapters:
        chapter_num = kanji_to_int(ch['number'])
        book_data["chapters"].append({
            "title": f"第{ch['number']}章",
            "content": ch['content']
        })
    
    # JSON出力
    output_file = os.path.join(output_dir, '菊屋敷.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)
    
    file_size = os.path.getsize(output_file)
    print(f"\n✅ JSON出力完了: {output_file}")
    print(f"   ファイルサイズ: {file_size:,} bytes")
    
    # ショートコード用テキスト出力
    shortcode_file = os.path.join(output_dir, '菊屋敷_shortcode.txt')
    with open(shortcode_file, 'w', encoding='utf-8') as f:
        f.write('[immersive_reader]\n')
        json.dump(book_data, f, ensure_ascii=False)
        f.write('\n[/immersive_reader]')
    
    print(f"✅ ショートコード出力完了: {shortcode_file}")
    
    # 総文字数計算
    total_chars = sum(len(ch['content']) for ch in chapters)
    print(f"\n📖 総文字数: {total_chars:,} 文字")
    print(f"📚 全{len(chapters)}章")

if __name__ == '__main__':
    main()
