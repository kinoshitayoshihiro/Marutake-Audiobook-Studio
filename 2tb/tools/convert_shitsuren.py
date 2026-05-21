#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
失恋第六番（山本周五郎）JSON変換スクリプト
"""

import json
import re
import os


def detect_encoding(file_path):
    """ファイルのエンコーディングを検出"""
    encodings = ["utf-8", "shift_jis", "cp932", "euc-jp"]
    for enc in encodings:
        try:
            with open(file_path, "r", encoding=enc) as f:
                f.read()
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


def load_text(file_path):
    """テキストファイルを読み込む"""
    encoding = detect_encoding(file_path)
    print(f"検出エンコーディング: {encoding}")
    with open(file_path, "r", encoding=encoding) as f:
        return f.read()


def split_chapters(text):
    """テキストを章ごとに分割"""
    # 漢数字パターン（一、二、三...）
    chapter_pattern = r"^([一二三四五六七八九十]+)\s*$"

    lines = text.split("\n")
    chapters = []
    current_chapter = None
    current_content = []

    for line in lines:
        match = re.match(chapter_pattern, line.strip())
        if match:
            # 前の章を保存
            if current_chapter is not None:
                content = "\n".join(current_content).strip()
                if content:
                    chapters.append({"number": current_chapter, "content": content})
            # 新しい章を開始
            current_chapter = match.group(1)
            current_content = []
        else:
            # 最初の章が始まる前のテキスト（プロローグ的なもの）も考慮
            if current_chapter is not None:
                current_content.append(line)
            elif line.strip():  # 章番号の前にテキストがある場合
                # 章番号なしで開始する場合の処理（必要なら）
                # 今回は章番号ありと仮定
                pass

    # 最後の章を保存
    if current_chapter is not None:
        content = "\n".join(current_content).strip()
        if content:
            chapters.append({"number": current_chapter, "content": content})

    # 章が見つからない場合、全体を1つの章として扱う
    if not chapters and text.strip():
        chapters.append({"number": "一", "content": text.strip()})

    return chapters


def clean_text(text):
    """テキストをクリーンアップ"""
    # 複数の空行を1つに
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 行末のスペースを削除
    text = re.sub(r" +\n", "\n", text)
    # 前後の空白を削除
    text = text.strip()
    return text


def kanji_to_int(kanji):
    """漢数字を整数に変換"""
    kanji_map = {
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
    }
    if kanji in kanji_map:
        return kanji_map[kanji]
    # 十一〜十八のケース
    if kanji.startswith("十"):
        if len(kanji) == 1:
            return 10
        return 10 + kanji_map.get(kanji[1], 0)
    # 二十などのケース（必要なら拡張）
    return 0


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "失恋第六番.txt")
    output_dir = os.path.join(os.path.dirname(script_dir), "bookdata")
    output_file = os.path.join(output_dir, "失恋第六番.json")

    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)

    if not os.path.exists(input_file):
        print(f"エラー: 入力ファイルが見つかりません: {input_file}")
        return

    print(f"読み込み中: {input_file}")
    raw_text = load_text(input_file)

    # 青空文庫形式のルビなどを削除（必要なら）
    # text = re.sub(r'《[^》]+》', '', raw_text)
    # text = re.sub(r'［[^］]+］', '', text)
    text = raw_text

    chapters = split_chapters(text)
    print(f"章数: {len(chapters)}")

    formatted_chapters = []
    for ch in chapters:
        cleaned_content = clean_text(ch["content"])
        formatted_chapters.append(
            {
                "id": kanji_to_int(ch["number"]),
                "title": ch["number"],
                "content": cleaned_content,
            }
        )

    # メタデータ
    book_data = {
        "title": "失恋第六番",
        "author": "山本周五郎",
        "synopsis": "戦後東京を舞台に、恋と正義が交錯するドラマ。\n銀座の喫茶店での約束をすっぽかされ、肩を落とした千田二郎。だがその日、街を騒がせた銀行ギャング事件と、友人・沼井の重傷が彼の運命を動かし始める。お見合いの席に乱入した拳銃男、激しいタクシー内の格闘、そして赦しと涙の病室──。\n「九人組強盗団」を追い詰める捜査の裏で、人間の罪と赦しを描き出す、戦後ノワールの傑作。\n二郎の「失恋第六番」が意味するものとは？",
        "characters": [
            {
                "name": "千田二郎",
                "reading": "せんだ じろう",
                "description": "東邦合成樹脂・連絡課長。社長の一人息子。皮肉屋で飄々としているが、腕っぷしと度胸は一級。銀行ギャング事件で犯人を生け捕りにし、仲間の死と向き合いながら「九人組」壊滅に動く。",
            },
            {
                "name": "千田仁一郎",
                "reading": "じんいちろう",
                "description": "東邦合成樹脂社長。白髪混じりのダンディな紳士で、息子とは友人のような距離感。私生活には口を出さないふりをしつつ、実はこっそり縁談を仕掛ける。",
            },
            {
                "name": "千田夫人",
                "reading": "おふくろ",
                "description": "二郎の母。明るくおしゃべりで、息子の結婚話に熱心。鰻屋「竹葉」でのお見合いの場を整え、思わぬ乱入者（ギャング）に悲鳴を上げる。",
            },
            {
                "name": "宮田俊子",
                "reading": "みやた としこ",
                "description": "二郎の秘書。流行遅れの外套と地味な帽子で、年より老けて見えるが、本気で装えば見違える美人。",
            },
            {
                "name": "楠田まり子",
                "reading": "くすだ まりこ",
                "description": "銀座・喫茶「マクスエル」のレジ係。二郎が惚れ込んでいる娘。機嫌を損ねると、マラルメの言葉まで持ち出して二郎を「色魔」呼ばわりする、聡明で気の強いタイプ。",
            },
            {
                "name": "沼井裕作",
                "reading": "ぬまい ゆうさく",
                "description": "二郎たちの仲間。映画の帰りに銀行ギャングの流れ弾を浴び、瀕死の重傷を負う。",
            },
            {
                "name": "梶原宗助",
                "reading": "かじわら そうすけ",
                "description": "二郎の友人。酒神（バッカス）倶楽部のメンバーで、情報連絡役として立ち回る。浦和での張り込み・突入作戦にも参加。",
            },
            {
                "name": "森口乙彦",
                "reading": "もりぐち おとひこ",
                "description": "二郎の友人。冷静な観察眼を持ち、病院や倶楽部で状況をまとめる参謀タイプ。沼井の写真をアルバムに貼り、「彼はその責任を果した」という言葉を書き込む。",
            },
            {
                "name": "橋本五郎",
                "reading": "はしもと ごろう",
                "description": "二郎の仲間。病院と現場を走り回る足の速い実務派。浦和での張り込み現場から、決定的な情報を持ち込む。",
            },
            {
                "name": "早川大吉",
                "reading": "はやかわ だいきち",
                "description": "黒いジャンパーの若い銀行ギャング。",
            },
            {
                "name": "大乃木太市",
                "reading": "おおのぎ たいち",
                "description": "すでに警視庁に拘束されている前科者。",
            },
            {
                "name": "捜査一課長・部長たち",
                "reading": "",
                "description": "警視庁の捜査陣。銀行ギャング事件を追い、千田たち民間側と連携して「九人組」の壊滅に当たる。",
            },
            {
                "name": "パリジャン女史",
                "reading": "",
                "description": "銀座の高級ブティック「パリジャン」の店員。",
            },
        ],
        "chapters": formatted_chapters,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)

    print(f"変換完了: {output_file}")


if __name__ == "__main__":
    main()
