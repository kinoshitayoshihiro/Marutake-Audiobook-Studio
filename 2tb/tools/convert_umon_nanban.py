# -*- coding: utf-8 -*-
import json
import os
import codecs


def convert_umon_nanban():
    # Read the Shift-JIS encoded file
    input_file = "Reading_library/右門捕物帖/1.右門捕物帖 南蛮幽霊 佐々木味津三 .txt"
    output_file = "bookdata/南蛮幽霊.json"

    with codecs.open(input_file, "r", encoding="shift-jis") as f:
        content = f.read()

    # Split by chapter markers (numbers in specific format)
    lines = content.split("\n")

    # Extract chapters based on the pattern "　　　　　1" etc.
    chapters_content = []
    current_chapter = []
    chapter_num = 0

    for line in lines:
        # Check if line contains chapter marker
        if line.strip() in ["１", "1", "　　　　　１", "　　　　　1"]:
            if current_chapter and chapter_num > 0:
                chapters_content.append("\n".join(current_chapter))
            current_chapter = []
            chapter_num += 1
        elif line.strip() in ["２", "2", "　　　　　２", "　　　　　2"]:
            if current_chapter:
                chapters_content.append("\n".join(current_chapter))
            current_chapter = []
            chapter_num += 1
        elif line.strip() in ["３", "3", "　　　　　３", "　　　　　3"]:
            if current_chapter:
                chapters_content.append("\n".join(current_chapter))
            current_chapter = []
            chapter_num += 1
        else:
            # Skip title lines at the beginning
            if not (line.strip() in ["右門捕物帖", "南蛮幽霊", "佐々木味津三", ""]):
                current_chapter.append(line)

    # Add the last chapter
    if current_chapter:
        chapters_content.append("\n".join(current_chapter))

    # Clean up chapters (remove empty lines at start/end)
    cleaned_chapters = []
    for ch in chapters_content:
        lines = ch.split("\n")
        # Remove leading empty lines
        while lines and not lines[0].strip():
            lines.pop(0)
        # Remove trailing empty lines
        while lines and not lines[-1].strip():
            lines.pop()
        if lines:
            cleaned_chapters.append("\n".join(lines))

    # Book data structure
    book_data = {
        "title": "南蛮幽霊",
        "author": "佐々木味津三",
        "synopsis": "八丁堀同心・むっつり右門の活躍を描く捕物帳。お花見の余興で起きた岡っ引き殺害事件、富くじで当たった三百両紛失事件、そして柳原の人さらい。一見無関係に見える事件の背後には、切支丹伴天連の残党による陰謀が隠されていた。催眠術を駆使する南蛮幽霊の正体とは。若き同心・右門の推理が事件の核心に迫る。",
        "authorProfile": {
            "name": "佐々木味津三",
            "desc": "時代小説・捕物帳の名手。右門捕物帖シリーズで知られる。緻密な推理と江戸の風俗描写が特徴。",
        },
        "characters": [
            {
                "name": "むっつり右門",
                "desc": "八丁堀同心。本名は近藤右門。26歳の若き同心で、寡黙だが鋭い推理力を持つ。",
            },
            {
                "name": "伝六",
                "desc": "右門の手下の岡っ引き。おしゃべりだが聞き込みが得意。",
            },
            {
                "name": "坂上与一郎",
                "desc": "与力次席の重職。娘の鈴江とともに事件に巻き込まれる。",
            },
            {"name": "鈴江", "desc": "坂上与一郎の娘。組屋敷小町と評判の美人。"},
            {
                "name": "長助",
                "desc": "岡っ引き。草相撲上がりの大男。お花見の余興で殺害される。",
            },
            {
                "name": "おでん屋親子",
                "desc": "柳原で屋台を出す美人親子。実は切支丹伴天連の残党。",
            },
            {"name": "玉乗り一座", "desc": "浅草の見世物小屋。南蛮渡来と称する一座。"},
            {"name": "鮫島老雲斎", "desc": "四谷大番町に住む南蛮研究の第一人者。"},
            {
                "name": "畳屋の職人",
                "desc": "富くじで三百両を当てたが、催眠術で盗まれる。",
            },
        ],
        "chapters": [],
    }

    # Add chapters with titles
    chapter_titles = ["八丁堀の花見", "凌英の駒", "南蛮の術"]

    for i, content in enumerate(cleaned_chapters):
        if i < len(chapter_titles):
            book_data["chapters"].append(
                {"title": chapter_titles[i], "content": content}
            )

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {output_file}")
    print(f"\n=== JSON Structure Validation ===")
    print(f"Title: {book_data['title']}")
    print(f"Author: {book_data['author']}")
    print(f"Chapters: {len(book_data['chapters'])}")
    for i, ch in enumerate(book_data["chapters"]):
        print(f"  Chapter {i+1}: {ch['title']} ({len(ch['content'])} chars)")


if __name__ == "__main__":
    convert_umon_nanban()
