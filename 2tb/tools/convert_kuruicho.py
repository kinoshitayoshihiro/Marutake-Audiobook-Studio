# -*- coding: utf-8 -*-
import json
import re
import os

# Input file path
input_path = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/納言恭平著/42.七之助捕物帳　納言恭平著　狂い蝶 .txt"
output_path = (
    "/Volumes/2TB/Marutake AudioBook Library/bookdata/七之助捕物帳_狂い蝶.json"
)

# Metadata provided by user
metadata = {
    "title": "七之助捕物帳　狂い蝶",
    "author": "納言恭平",
    "genre": "時代小説",
    "japanese_genre": "捕物帳",
    "sub_genre": "ミステリー",
    "setting": "江戸",
    "location": "花川戸、中洲、蔵前、雑司ヶ谷",
    "time_period": "江戸時代（幕末）",
    "keywords": ["七之助", "捕物", "心中", "刺青", "うわばみお蝶"],
    "themes": ["正義", "偽装", "因果応報"],
    "emotions": ["驚き", "納得", "哀れ"],
    "synopsis": "花川戸の御用聞・七之助は、子分の音吉から「仙雀堂の若主人・林之助が、中洲の葦に引っかかった心中死体で見つかった」と知らされる。相手は、悪名高い女賊「うわばみお蝶」。赤いしごきで胴を縛り、抱き合ったまま――いかにも“情死”の仕立てだった。\n\nだが現場を改めた七之助は、死体が水を飲んでいないことから「川に入ったのは死後」と見抜く。さらに、お蝶の刺青が“半身”しかない。背に描かれたうわばみの胴は途中で千切れ、背景には二匹の揚羽蝶――この不自然な図柄が、七之助の胸に刺さる。\n\nやがて蔵前の水茶屋「十六夜」に、奥女中然とした美女が現れ、札差たちの賭場を堂々と荒らし、厚紙細工の蝶を残して消える。「お蝶の幽霊が出た」と江戸が騒ぐ中、七之助は“刺青の出どころ”に狙いを定める。\n\n刺青師を洗ううち、弁天町の彫定が浮上するが、直後に彫定は偽装された“首吊り”で殺される。さらに、首吊り幽霊騒ぎを餌にした張り込みから、七之助は雑司ヶ谷の寮へ踏み込み、青山弥一郎と妖艶な女を一網打尽にする。\n\n奉行所で明かされる真相――「うわばみお蝶」は一人ではなかった。瓜二つの姉妹分、お蝶とお吉。二人で“半身ずつ”の刺青を彫り、一人が大芝居を打つ同時刻に、もう一人が別の場所で目撃される。町方を翻弄するための、残酷で華やかな“二羽の毒蝶”のからくりだった。",
    "highlights": [
        "七之助の鋭い観察眼と推理",
        "「うわばみお蝶」の正体と刺青のトリック",
        "二人の「お蝶」による巧妙なアリバイ工作",
    ],
    "authorProfile": {"name": "納言恭平", "desc": "詳細不明"},
}

# Characters provided by user
characters = [
    {"name": "七之助", "desc": "花川戸の御用聞。勘と現場眼で“心中の偽装”を破る。"},
    {"name": "音吉", "desc": "七之助の子分。聞き込みの足が速く、情報嗅覚が鋭い。"},
    {"name": "お雪", "desc": "七之助の女房。日常の温度を作品に与える存在。"},
    {"name": "浜中茂平次", "desc": "八丁堀同心。七之助と組んで事件を追う。"},
    {"name": "平太郎", "desc": "浜中の手先。現場対応や連絡役。"},
    {
        "name": "林之助",
        "desc": "銀座一丁目・紙問屋「仙雀堂」の若主人。誘拐された末に殺される。",
    },
    {"name": "林吉", "desc": "仙雀堂の主。身代金を払うが息子は戻らない。"},
    {"name": "久作", "desc": "仙雀堂の番頭。死体の枕元で線香を守る。"},
    {
        "name": "うわばみお蝶（お蝶）",
        "desc": "悪名の女賊“偶像”。美貌と芝居気で一味の象徴となる。",
    },
    {
        "name": "お吉",
        "desc": "お蝶に瓜二つの女。もう一人の“うわばみお蝶”。真相の鍵を握る。",
    },
    {"name": "青山弥一郎", "desc": "御家人くずれの悪党。実権を握る“軍師役”。"},
    {"name": "仁兵衛", "desc": "蔵前の水茶屋「十六夜」の亭主。賭場荒しの顛末を語る。"},
    {"name": "彫定（ほりさだ）", "desc": "弁天町の刺青師。口止めの要として消される。"},
    {"name": "土堤金（どてきん）", "desc": "吉原土堤の刺青師。刺青師名簿の起点。"},
    {"name": "仙五郎", "desc": "内藤新宿の親分格。彫定“偽招き”の被害者側。"},
    {"name": "杢平", "desc": "仙五郎の子分。彫定の死体発見で七之助に知らせる。"},
    {"name": "札差衆（ふださししゅう）", "desc": "蔵前界隈の旦那株。賭場荒しの標的。"},
]

# Glossary provided by user
glossary_raw = [
    {"term": "御用聞", "reading": "ごようきき", "desc": "町方と通じる民間の捜査役。"},
    {"term": "庭木戸", "reading": "にわきど", "desc": "庭の出入口の小さな戸。"},
    {"term": "滅法", "reading": "めっぽう", "desc": "ひどく、非常に。"},
    {
        "term": "南蛮渡り",
        "reading": "なんばんわたり",
        "desc": "舶来品・海外由来のもの。",
    },
    {
        "term": "しごき",
        "reading": "しごき",
        "desc": "細長い帯状の布（赤いしごき＝情念の小道具として強い）。",
    },
    {"term": "癇走る", "reading": "かんばしる", "desc": "興奮して気が立つ。"},
    {"term": "吾妻橋", "reading": "あづまばし", "desc": "隅田川の橋。"},
    {
        "term": "猪牙舟",
        "reading": "ちょきぶね",
        "desc": "小型で俊敏な舟（船足の速い移動手段）。",
    },
    {
        "term": "苫小舟",
        "reading": "とまこぶね",
        "desc": "苫（とま＝むしろ）で覆った小舟。",
    },
    {"term": "もやう（繋留）", "reading": "もやう", "desc": "舟を岸に繋いで停める。"},
    {"term": "アンペラ", "reading": "あんぺら", "desc": "敷物（むしろの類）。"},
    {"term": "土左衛門", "reading": "どざえもん", "desc": "水死体の俗称。"},
    {"term": "鎌首", "reading": "かまくび", "desc": "蛇が首をもたげる姿。"},
    {
        "term": "揚羽蝶",
        "reading": "あげはちょう",
        "desc": "アゲハチョウ。作中では“二羽”が重要モチーフ。",
    },
    {
        "term": "符節を合せる",
        "reading": "ふせつをあわせる",
        "desc": "偶然がぴたり一致する。",
    },
    {"term": "呼子", "reading": "よぶこ", "desc": "合図の笛。"},
    {"term": "龕燈", "reading": "がんどう", "desc": "手持ち提灯の一種。"},
    {
        "term": "鋲打乗物",
        "reading": "びょううちのりもの",
        "desc": "装飾鋲のある格式高い駕籠。",
    },
    {
        "term": "端下",
        "reading": "はした",
        "desc": "下女・付き人の類（文脈では従者の女）。",
    },
    {"term": "挾箱", "reading": "はさみばこ", "desc": "供の者が担ぐ荷箱。"},
    {"term": "二本差", "reading": "にほんざし", "desc": "大小二本の刀を差す武士の姿。"},
    {"term": "御代参", "reading": "ごだいさん", "desc": "本人の代わりに参拝すること。"},
    {"term": "御定日", "reading": "ごじょうび", "desc": "決まった日（定例日）。"},
    {
        "term": "掏摸（すり）／かっぱらい",
        "reading": "すり／かっぱらい",
        "desc": "スリ／ひったくり。",
    },
    {
        "term": "でんぐりかえす",
        "reading": "でんぐりかえす",
        "desc": "世間をひっくり返すほど騒がせる。",
    },
    {"term": "ゆもじ", "reading": "ゆもじ", "desc": "腰巻（肌着）。"},
    {"term": "申条", "reading": "もうじょう", "desc": "申し立て・供述。"},
    {"term": "逸早く", "reading": "いちはやく", "desc": "すばやく。"},
]

# Read content
try:
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
except FileNotFoundError:
    print(f"Error: File not found at {input_path}")
    exit(1)

# Parse chapters
chapters = []
# Regex to find chapter headings like "１.中洲心中" or "２.半身蛇"
# Note: The numbers seem to be full-width characters in the text provided in attachment
chapter_pattern = re.compile(r"\n([１２３４５６７８９０]+)\.([^\n]+)\n")

# Split content by chapter pattern
parts = chapter_pattern.split(content)

# The first part is usually title/intro before the first chapter
# In the attachment: "七之助捕物帳　納言恭平著　狂い蝶\n\n\n"
# Then "１", "中洲心中", "text..."

# If the file starts with the title, we might want to skip it or put it in the first chapter if it's not caught
# Let's look at how split works: [preamble, num1, title1, text1, num2, title2, text2, ...]

current_pos = 0
matches = list(chapter_pattern.finditer(content))

if not matches:
    # No chapters found, treat whole text as one chapter
    chapters.append({"title": "全文", "content": content.strip()})
else:
    # Check for preamble
    if matches[0].start() > 0:
        preamble = content[: matches[0].start()].strip()
        # If preamble is just the title, ignore it. If it has text, maybe add as prologue?
        # For now, let's ignore the title line if it's just the title.
        pass

    for i, match in enumerate(matches):
        chapter_num = match.group(1)
        chapter_title = match.group(2).strip()

        start = match.end()
        if i < len(matches) - 1:
            end = matches[i + 1].start()
        else:
            end = len(content)

        chapter_text = content[start:end].strip()

        full_title = f"{chapter_num}.{chapter_title}"
        chapters.append({"title": full_title, "content": chapter_text})

# Assemble final JSON
final_data = metadata.copy()
final_data["characters"] = characters
final_data["glossary"] = glossary_raw
final_data["chapters"] = chapters

# Write to file
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(final_data, f, ensure_ascii=False, indent=2)

print(f"Successfully created {output_path}")
