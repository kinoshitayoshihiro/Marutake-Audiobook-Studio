#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山本周五郎「四条畷」変換スクリプト
"""

import json


def convert_shijounawate():
    """四条畷をJSON形式に変換"""

    input_file = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/山本周五郎/山本周五郎　四条畷.txt"
    output_file = "/Volumes/2TB/Marutake AudioBook Library/bookdata/四条畷.json"

    # UTF-8ファイルを読み込み
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # タイトルと著者を抽出
    title = "四条畷"
    author = "山本周五郎"

    # タイトル・著者行を削除してコンテンツを整理
    lines = content.split("\n")
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped != title and stripped != author:
            filtered_lines.append(line)

    main_content = "\n".join(filtered_lines)

    # この作品は短編なので章分けせず1章として扱う
    chapters = [{"title": "四条畷", "content": main_content.strip()}]

    # シノプシス
    synopsis = "南北朝時代、楠木正成の遺志を継いだ息子・正行の物語。父の壮烈な戦死から十年、正行は延元元年五月の桜井駅での父の遺言を胸に、足利尊氏率いる大軍と対峙する。わずか三千の兵で八万の敵軍に立ち向かう正行の忠烈と勇猛、そして二十二歳で散った若き武将の生涯を描く。"

    # 著者プロフィール
    author_profile = {
        "name": author,
        "desc": "明治～昭和の小説家。本名は清水三十六。時代小説、歴史小説の名手として知られ、庶民の哀歓を温かく描いた作品で人気を博した。代表作に『樅ノ木は残った』『赤ひげ診療譚』『青べか物語』など多数。直木賞選考委員も務めた。",
    }

    # キャラクター
    characters = [
        {
            "name": "楠木正行",
            "desc": "楠木正成の長男。父の遺志を継ぎ忠節を貫く若き武将。正四位下、帯刀、検非違使左衛門尉、河内守。",
        },
        {
            "name": "楠木正成",
            "desc": "正行の父。湊川で壮烈な戦死を遂げた忠臣。息子に忠義の道を説いた。",
        },
        {
            "name": "正行の母",
            "desc": "正成の妻。息子が自害しようとした際、父の遺命を思い出させた強い女性。",
        },
        {"name": "正朝", "desc": "正行の従弟。和田正朝。正行と共に戦う。"},
        {"name": "足利尊氏", "desc": "賊軍の総帥。正成の首を丁重に送り返した。"},
        {"name": "高師直", "desc": "尊氏配下の武将。八万の大軍を率いて正行と対峙。"},
        {"name": "護良親王", "desc": "皇族。三条景繁と宗信により助けられる。"},
        {"name": "後村上天皇", "desc": "正行が仕える帝。正行の忠義を賞賛した。"},
        {"name": "菊池重武", "desc": "官軍の諸将の一人。"},
        {"name": "新田義貞", "desc": "官軍の武将。戦死した。"},
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
    convert_shijounawate()
