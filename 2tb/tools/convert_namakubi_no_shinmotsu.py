#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
右門捕物帖「生首の進物」変換スクリプト
"""

import json
import codecs
import re


def convert_namakubi_no_shinmotsu():
    """生首の進物をJSON形式に変換"""

    input_file = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/右門捕物帖/2.右門捕物帖 生首の進物 佐々木味津三  .txt"
    output_file = "/Volumes/2TB/Marutake AudioBook Library/bookdata/生首の進物.json"

    # Shift-JISファイルを読み込み
    with codecs.open(input_file, "r", encoding="shift-jis") as f:
        content = f.read()

    # タイトルと著者を抽出
    title = "生首の進物"
    author = "佐々木味津三"

    # 章分け（１、２、３の数字マーカーで分割）
    chapters_content = []
    lines = content.split("\n")

    current_chapter = []
    chapter_started = False

    for line in lines:
        stripped = line.strip()

        # 章マーカーを検出（全角数字の１、２、３、４）
        if stripped in ["１", "２", "３", "４", "1", "2", "3", "4"] or re.match(
            r"^　+[１２３４1234]$", stripped
        ):
            if current_chapter:  # 前の章を保存
                chapters_content.append("\n".join(current_chapter))
            current_chapter = []
            chapter_started = True
            continue

        # タイトル、著者行をスキップ
        if (
            not chapter_started
            or stripped == title
            or stripped == author
            or stripped == "右門捕物帖"
        ):
            continue

        # 章の内容を追加
        if chapter_started and line:
            current_chapter.append(line)

    # 最後の章を追加
    if current_chapter:
        chapters_content.append("\n".join(current_chapter))

    # 章タイトル
    chapter_titles = ["第二番手柄", "番町の怪", "生首の謎"]

    # 章データを構築
    chapters = []
    for i, (ch_title, ch_content) in enumerate(
        zip(chapter_titles, chapters_content), 1
    ):
        chapters.append({"title": ch_title, "content": ch_content.strip()})

    # シノプシス
    synopsis = "番町の旗本・小田切久之進の胸の上に、三夜続けて生首が置かれる怪事件。いずれも左目をえぐられた女、座頭、老人の首だった。同心のあばたの敬四郎に先を越されながらも、むっつり右門は独自の推理で事件の核心に迫る。秘密を守ろうとする旗本の真意とは。生首に隠された驚愕の真実。"

    # 著者プロフィール
    author_profile = {
        "name": author,
        "desc": "明治～昭和初期の大衆文学作家。時代小説の分野で活躍し、特に「右門捕物帖」シリーズで知られる。江戸を舞台にした捕物帳は、むっつり右門を主人公に、知略と推理を駆使した事件解決が描かれ、多くの読者を魅了した。簡潔で力強い文体が特徴。",
    }

    # キャラクター
    characters = [
        {
            "name": "むっつり右門",
            "desc": "江戸八丁堀の同心。無口だが卓越した推理力と観察力を持つ美丈夫。",
        },
        {
            "name": "伝六",
            "desc": "右門の手下の岡っ引き。おしゃべりでひょうきんだが、職業本能は鋭い。",
        },
        {
            "name": "小田切久之進",
            "desc": "番町の旗本。三百石取り。元はお鷹匠で温厚篤実な性格。",
        },
        {
            "name": "あばたの敬四郎",
            "desc": "八丁堀の同心。右門の先輩で、功名を争うライバル。",
        },
        {
            "name": "松平伊豆守",
            "desc": "徳川幕府の老中。知恵伊豆と称される。右門の才能を認めている。",
        },
        {"name": "神尾元勝", "desc": "南町奉行。右門を信頼し、百両の官金を貸与する。"},
        {"name": "目明かし", "desc": "敬四郎配下の岡っ引き。小田切屋敷の警備を担当。"},
        {"name": "白羽矢之助", "desc": "右門が名乗った偽名。"},
        {"name": "お弓", "desc": "事件に関わる少女の名前として登場。"},
    ]

    # JSON構造を作成
    book_data = {
        "title": title,
        "author": author,
        "synopsis": synopsis,
        "authorProfile": author_profile,
        "characters": characters,
        "chapters": chapters,
    }

    # JSONファイルに出力
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)

    # 確認用の情報を出力
    print(f"Title: {title}")
    print(f"Author: {author}")
    print(f"Chapters: {len(chapters)}")
    for i, chapter in enumerate(chapters, 1):
        print(f"  Chapter {i}: {chapter['title']} ({len(chapter['content'])} chars)")
    print(f"\nSuccessfully generated {output_file}")


if __name__ == "__main__":
    convert_namakubi_no_shinmotsu()
