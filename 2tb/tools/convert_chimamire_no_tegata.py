#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
右門捕物帖「血染めの手形」変換スクリプト
"""

import json
import codecs
import re


def convert_chimamire_no_tegata():
    """血染めの手形をJSON形式に変換"""

    input_file = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/右門捕物帖/3.右門捕物帖 血染めの手形 佐々木味津三.txt"
    output_file = "/Volumes/2TB/Marutake AudioBook Library/bookdata/血染めの手形.json"

    # Shift-JISファイルを読み込み
    with codecs.open(input_file, "r", encoding="shift-jis") as f:
        content = f.read()

    # タイトルと著者を抽出
    title = "血染めの手形"
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
    chapter_titles = ["忍への道行", "血染めの手形", "右門の推理"]

    # 章データを構築
    chapters = []
    for i, (ch_title, ch_content) in enumerate(
        zip(chapter_titles, chapters_content), 1
    ):
        chapters.append({"title": ch_title, "content": ch_content.strip()})

    # シノプシス
    synopsis = "武州忍藩で起きた謎の辻斬り事件。狙われたのは藩内の武芸達人ばかりで、いずれも右腕を斬り落とされていた。徳川宿老・松平伊豆守に呼ばれた江戸のむっつり右門は、変装して忍へ向かう。事件の裏には将軍の日光社参を巡る大きな陰謀が隠されていた。血染めの手形が示す真実とは。"

    # 著者プロフィール
    author_profile = {
        "name": author,
        "desc": "明治～昭和初期の大衆文学作家。時代小説の分野で活躍し、特に「右門捕物帖」シリーズで知られる。江戸を舞台にした捕物帳は、むっつり右門を主人公に、知略と推理を駆使した事件解決が描かれ、多くの読者を魅了した。簡潔で力強い文体が特徴。",
    }

    # キャラクター
    characters = [
        {
            "name": "むっつり右門",
            "desc": "江戸八丁堀の同心。無口だが鋭い洞察力と推理力を持つ。美丈夫で武芸にも優れる。",
        },
        {
            "name": "伝六",
            "desc": "右門の手下の岡っ引き。おしゃべりで軽口をたたくが、職業本能は鋭い。",
        },
        {
            "name": "松平伊豆守",
            "desc": "徳川幕府の老中。知恵伊豆と称される名君。忍藩三万石の藩主。",
        },
        {
            "name": "お弓",
            "desc": "伊豆守が右門の宿に差し向けた十五、六歳の少女。楚々としてういういしい。",
        },
        {
            "name": "小田切久之進",
            "desc": "番町の旗本。三百石取りの小身だが、事件の鍵を握る人物。",
        },
        {
            "name": "あばたの敬四郎",
            "desc": "八丁堀の同心。右門より年上の先輩で、右門に対抗意識を燃やす。",
        },
        {"name": "長助", "desc": "事件に関わる人物。"},
        {"name": "鈴江", "desc": "事件に登場する女性。"},
        {"name": "坂上与一郎", "desc": "忍藩の藩士。役儀により右門を出迎える。"},
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
    convert_chimamire_no_tegata()
