#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山本周五郎「泥棒と若殿」変換スクリプト
"""

import json
import codecs
import re


def convert_dorobou_to_wakadono():
    """泥棒と若殿をJSON形式に変換"""

    input_file = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/山本周五郎/山本周五郎　泥棒と若殿.txt"
    output_file = "/Volumes/2TB/Marutake AudioBook Library/bookdata/泥棒と若殿.json"

    # Shift-JISファイルを読み込み
    with codecs.open(input_file, "r", encoding="shift-jis") as f:
        content = f.read()

    # タイトルと著者を抽出
    title = "泥棒と若殿"
    author = "山本周五郎"

    # 章分け（一、二、三...の数字マーカーで分割）
    chapters_content = []
    lines = content.split("\n")

    current_chapter = []
    chapter_started = False

    for line in lines:
        stripped = line.strip()

        # 章マーカーを検出（漢数字の一、二、三...十）
        if stripped in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]:
            if current_chapter:  # 前の章を保存
                chapters_content.append("\n".join(current_chapter))
            current_chapter = []
            chapter_started = True
            continue

        # タイトル、著者行をスキップ
        if not chapter_started or stripped == title or stripped == author:
            continue

        # 章の内容を追加
        if chapter_started and line:
            current_chapter.append(line)

    # 最後の章を追加
    if current_chapter:
        chapters_content.append("\n".join(current_chapter))

    # 章タイトル
    chapter_titles = [
        "夜盗の訪問",
        "米を買う",
        "飯を炊く",
        "伝九郎の働き",
        "成信の身の上",
        "城への訴え",
        "梶田一派の陰謀",
        "二人の絆",
        "真実の露見",
        "決着",
    ]

    # 章データを構築
    chapters = []
    for i, (ch_title, ch_content) in enumerate(
        zip(chapter_titles, chapters_content), 1
    ):
        chapters.append({"title": ch_title, "content": ch_content.strip()})

    # シノプシス
    synopsis = "鬼塚山の荒れ果てた御殿に幽閉された若殿・成信。家督争いに巻き込まれ、餓死を待つ身となった彼のもとに、泥棒の伝九郎が侵入する。何もない屋敷に呆れた伝九郎は、なぜか成信に飯を食わせ始める。盗賊と若殿という奇妙な同居生活の中で、二人の間に不思議な絆が生まれてゆく。山本周五郎が描く人間愛の物語。"

    # 著者プロフィール
    author_profile = {
        "name": author,
        "desc": "明治～昭和の小説家。本名は清水三十六。時代小説、歴史小説の名手として知られ、庶民の哀歓を温かく描いた作品で人気を博した。代表作に『樅ノ木は残った』『赤ひげ診療譚』『青べか物語』など多数。直木賞選考委員も務めた。",
    }

    # キャラクター
    characters = [
        {
            "name": "成信",
            "desc": "大炊頭成豊の二男。家督争いに巻き込まれ鬼塚山の御殿に幽閉された若殿。",
        },
        {
            "name": "伝九郎",
            "desc": "泥棒。偶然成信の屋敷に侵入し、成信の面倒を見始める人情家。",
        },
        {"name": "大炊頭成豊", "desc": "成信の父。寺社奉行、老中などを歴任した重臣。"},
        {"name": "成武", "desc": "成信の兄。長男だが脳を病んで頭がわるくなった。"},
        {
            "name": "滝沢図書助",
            "desc": "江戸の筆頭家老。成武を家督に擁立する派閥の首班。",
        },
        {
            "name": "梶田重右衛門",
            "desc": "大炊頭の側用人。成信を擁立しようとした派閥の中心人物。",
        },
        {"name": "鮫島平馬", "desc": "成信に仕える侍。梶田派の失脚を知らせに来た。"},
        {"name": "成信の母", "desc": "大炊頭の側室。中屋敷で成信を育てた。"},
        {"name": "成光", "desc": "成信の祖父にあたる先代の大炊頭。"},
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
    convert_dorobou_to_wakadono()
