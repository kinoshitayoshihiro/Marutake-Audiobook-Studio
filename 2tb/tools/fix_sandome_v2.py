# -*- coding: utf-8 -*-
import json
import re
import os

# Input file path
input_path = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/山本周五郎/4.赤ひげ診療譚 三度目の正直 山本周五郎.txt"
output_path = (
    "/Volumes/2TB/Marutake AudioBook Library/bookdata/赤ひげ診療譚_三度目の正直.json"
)

# Metadata
metadata = {
    "title": "赤ひげ診療譚 三度目の正直",
    "author": "山本周五郎",
    "genre": "時代小説",
    "japanese_genre": "人情もの",
    "sub_genre": "医療ドラマ",
    "setting": "小石川養生所",
    "location": "江戸、小石川、むじな長屋",
    "time_period": "江戸時代",
    "keywords": ["赤ひげ", "診療譚", "山本周五郎", "人情", "医療"],
    "themes": ["貧困と病", "人間愛", "献身", "成長"],
    "emotions": ["感動", "哀愁", "希望"],
    "synopsis": "むじな長屋に暮らす、職人佐八。労咳で死も間際になりながら、長屋の住人への施しをやめない。佐八の度を超した献身は何に起因するのか？　下町に暮らす極貧な庶民の治療を通じて、成長していく見習医員の姿を、今回も描きだします——",
    "highlights": ["佐八の献身の理由", "見習医員の成長", "下町の人々の暮らし"],
    "authorProfile": {
        "name": "山本周五郎",
        "desc": "1903-1967。山梨県生まれ。本名、清水三十六（さとむ）。小学校卒業後、東京木挽町の山本周五郎商店に徒弟として住み込む。筆名はこれに由来。雑誌記者などを経て文筆業に専念。「日本婦道記」で直木賞に推されたが辞退。庶民の哀歓を描いた時代小説や現代小説で多くの読者を魅了した。",
    },
}

# Characters
characters = [
    {"name": "新出去定(赤ひげ)", "desc": "小石川養生所の医長。"},
    {
        "name": "保本登",
        "desc": "長崎へ遊学後、江戸へ戻り、小石川養生所の医員見習となる。",
    },
    {"name": "森半太夫", "desc": "養生所の見習医員。登の同僚。赤ひげを尊敬している。"},
    {"name": "お雪", "desc": "養生所の賄所で働く。森を慕っている。"},
    {"name": "津川玄三", "desc": "養生所の医員。登と交替して養生所を出る。"},
    {"name": "保本良庵", "desc": "登の父。町医者。"},
    {"name": "保本八重", "desc": "登の母。"},
    {"name": "天野源伯", "desc": "幕府の表御番医(法印)。登の後援者。"},
    {"name": "天野ちぐさ", "desc": "登の許婚者。登の遊学中に他の男と駆落ちをする。"},
    {"name": "天野まさを", "desc": "ちぐさの妹。"},
    {"name": "ゆみ", "desc": "富豪の娘。狂気で人を殺め養生所の離れに隔離されている。"},
    {"name": "お杉", "desc": "ゆみの付添い女中。"},
    {"name": "お初", "desc": "養生所の女中"},
    {"name": "竹造", "desc": "養生所の小者。"},
    {"name": "佐八", "desc": "輻屋の職人。末期の労咳患者。"},
    {"name": "おなか", "desc": "別れた佐八の妻"},
    {"name": "太吉", "desc": "おなかの息子"},
    {"name": "治兵衛", "desc": "むじな長屋の差配"},
    {"name": "おこと", "desc": "治兵衛の妻"},
    {"name": "平吉", "desc": "佐八の友人にして、むじな長屋の住人"},
    {"name": "お松", "desc": "むじな長屋の住人"},
    {"name": "川本靭負", "desc": "松平壱岐守の家老"},
    {"name": "岩橋隼人", "desc": "用人"},
]

# Glossary
glossary_raw_text = """
黙許……モッキョ・黙認
二丁……一丁は、約109メートル
定火消……明暦の大火を教訓につくられた防火組織。はじめは四組で、のちに増えたが、大名火消、町火消の整備とともに縮小、元の四組にもどる。
厚味……コウミ・味がこってりしておいしいこと。ごちそう。
貪食……ドンショク・がつがつ喰らうこと。むさぼりくうこと
塵芥……ジンカイ
義絶……ギゼツ・肉親との関係を断つこと
そぞろ……こころがおちつかない、そわそわすること
籠絡……ロウラク・巧みに手なずけて、自分の思い通りに操ること
因業……インゴウ・頑固で思いやりのないこと
二合五勺……コナカラ・一升の四分の一。0.45リットル
"""

glossary = []
for line in glossary_raw_text.strip().split("\n"):
    if "……" in line:
        term, rest = line.split("……", 1)
        reading = ""
        desc = ""

        if "・" in rest:
            reading, desc = rest.split("・", 1)
        else:
            # Heuristic: if rest is short and katakana, it's reading. Else description.
            # Simple check for Katakana: regex
            if re.match(r"^[ァ-ンー]+$", rest):
                reading = rest
                desc = ""  # Or maybe the term itself implies meaning?
            else:
                reading = ""  # No reading provided
                desc = rest

        glossary.append(
            {"term": term.strip(), "reading": reading.strip(), "desc": desc.strip()}
        )

# Read content
try:
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    print(f"Error: File not found at {input_path}")
    exit(1)

# Parse chapters
chapters = []
# Regex to find chapter headings like "一" or "二" surrounded by newlines
# The file format for Yamamoto Shugoro usually has simple kanji numbers for chapters
chapter_pattern = re.compile(r"\n([一二三四五六七八九十]+)\n")

matches = list(chapter_pattern.finditer(content))

if not matches:
    # Try another pattern, maybe just lines? Or maybe the file is short?
    # Let's assume the whole text is one chapter if no headers found
    chapters.append({"title": "全文", "content": content.strip()})
else:
    # Check for preamble
    if matches[0].start() > 0:
        preamble = content[: matches[0].start()].strip()
        # If preamble is significant, add it. Usually it's title/author.
        pass

    for i, match in enumerate(matches):
        chapter_title = match.group(1).strip()

        start = match.end()
        if i < len(matches) - 1:
            end = matches[i + 1].start()
        else:
            end = len(content)

        chapter_text = content[start:end].strip()

        chapters.append({"title": chapter_title, "content": chapter_text})

# Assemble final JSON
final_data = metadata.copy()
final_data["characters"] = characters
final_data["glossary"] = glossary
final_data["chapters"] = chapters

# Write to file
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)

print(f"Successfully created {output_path}")
