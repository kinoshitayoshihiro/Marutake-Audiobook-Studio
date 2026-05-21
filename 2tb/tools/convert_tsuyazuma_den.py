#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
野村胡堂「錢形平次捕物控 艶妻傳」変換スクリプト
"""

import json


def convert_tsuyazuma_den():
    """艶妻傳をJSON形式に変換"""

    input_file = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/銭形平次捕物控/錢形平次捕物控 艶妻傳 野村胡堂.py"
    output_file = "/Volumes/2TB/Marutake AudioBook Library/bookdata/艶妻傳.json"

    # UTF-8ファイルを読み込み
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # タイトルと著者を抽出
    title = "艶妻傳"
    author = "野村胡堂"

    # 章分け（一、二、三、四、五の数字マーカーで分割）
    chapters_content = []
    lines = content.split("\n")

    current_chapter = []
    chapter_started = False

    for line in lines:
        stripped = line.strip()

        # 章マーカーを検出（漢数字の一、二、三、四、五）
        if stripped in ["一", "二", "三", "四", "五"]:
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
            or stripped == "錢形平次捕物控"
            or stripped == "銭形平次捕物控"
        ):
            continue

        # 章の内容を追加
        if chapter_started and line:
            current_chapter.append(line)

    # 最後の章を追加
    if current_chapter:
        chapters_content.append("\n".join(current_chapter))

    # 章タイトル
    chapter_titles = ["ガラッ八の恋心", "娘の死", "物干台の謎", "第二の事件", "真相"]

    # 章データを構築
    chapters = []
    for i, (ch_title, ch_content) in enumerate(
        zip(chapter_titles, chapters_content), 1
    ):
        chapters.append({"title": ch_title, "content": ch_content.strip()})

    # シノプシス
    synopsis = "鎌倉町の油問屋・越前屋の若い内儀お加奈。地味で控えめながら、時折見せる艶やかさに男たちは魅了される。ガラッ八もその一人だった。ある夜、娘お菊が物干台から転落死。継母お加奈への疑惑が高まる中、今度は主人治兵衛までもが物干台で刺殺される。錢形平次が見抜いた美しき女の魔性と、その影に潜む真の下手人とは。"

    # 著者プロフィール
    author_profile = {
        "name": author,
        "desc": "明治～昭和の小説家。本名は野村長一。音楽評論家としても活躍し、ペンネーム「あらえびす」で知られる。代表作『銭形平次捕物控』は383編にも及ぶ大シリーズとなり、江戸の岡っ引き銭形平次の活躍を描いた。推理と人情味あふれる作風で人気を博した。",
    }

    # キャラクター
    characters = [
        {
            "name": "錢形平次",
            "desc": "明神下に住む岡っ引き。鋭い洞察力と人間理解で難事件を解決する名探偵。",
        },
        {
            "name": "ガラッ八（八五郎）",
            "desc": "平次の子分。おしゃべりで間抜けだが憎めない性格。お加奈に惚れる。",
        },
        {
            "name": "お加奈",
            "desc": "越前屋の若い内儀。地味だが時折見せる艶やかさで男を魅了する不思議な女性。",
        },
        {
            "name": "越前屋治兵衛",
            "desc": "油問屋の主人。五十を越えた老人だが若い妻お加奈を溺愛している。",
        },
        {
            "name": "お菊",
            "desc": "治兵衛の先妻の娘。十七歳。継母お加奈と折り合いが悪い。",
        },
        {
            "name": "房太郎",
            "desc": "隣の小間物屋の息子。お菊と恋仲だが家同士の仲が悪く添えない。",
        },
        {
            "name": "丸吉",
            "desc": "越前屋の手代。主人の遠縁。丈夫で恰幅の良い二十四五の男。",
        },
        {
            "name": "久助",
            "desc": "越前屋の手代。三十歳。痩せてヒョロヒョロの男。お菊を追い回していた。",
        },
        {
            "name": "お冬婆さん",
            "desc": "先妻の母親でお菊の祖母。隠居部屋に住む。お加奈を激しく憎む。",
        },
        {"name": "治八郎", "desc": "主人の義弟で店の支配人。四十男で足が悪い。"},
        {
            "name": "三河町の伊太松",
            "desc": "岡っ引き。強気で負け嫌いだが正直者。平次に助けを求める。",
        },
        {"name": "お静", "desc": "平次の恋女房。若く美しい。"},
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
    convert_tsuyazuma_den()
