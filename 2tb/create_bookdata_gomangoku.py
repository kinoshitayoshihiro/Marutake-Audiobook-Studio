import json
import re
import os

# メタデータ
metadata = {
    "title": "五万石の弟子",
    "author": "山本周五郎",
    "genre": "時代小説",
    "japanese_genre": "武家もの",
    "sub_genre": "人情",
    "setting": "伊勢ノ国一志郡久居",
    "location": "久居城下",
    "time_period": "江戸時代中期（寛延二年）",
    "keywords": ["剣術", "師範", "主君", "教育", "五万石"],
    "themes": ["真の教育", "主従の絆", "武士の矜持"],
    "emotions": ["感動", "清々しさ", "尊敬"],
    "synopsis": "伊勢久居藩の剣術師範・乗松弥五郎は、実戦を想定した妥協のない厳しい指導で知られていた。しかし、新しく着任した相師範・滝川治部の穏やかで親切な指導に門人たちが次々と移籍し、弥五郎の道場は閑古鳥が鳴く。自身の指導法に自信を持ちつつも、門人が減ることに責任を感じた弥五郎は、治部との試合を望む。試合を通じて弥五郎が悟ったこと、そして主君・藤堂和泉守高豊が彼に見せた粋な計らいとは。",
    "highlights": [
        "弥五郎の厳格だが真剣な指導風景",
        "弥五郎と治部の立会いと、そこでの弥五郎の心の変化",
        "ラストシーンでの主君・高豊の言葉「余は一人で五万石じゃ」",
    ],
    "characters": [
        {
            "name": "乗松弥五郎",
            "desc": "鹿島神流の剣士。伊勢久居藩の剣術師範。実戦本位の厳しい指導を行う。",
        },
        {
            "name": "藤堂和泉守高豊",
            "desc": "久居藩主。五万石の大名。武道を愛し、弥五郎の腕を見込んでいる。",
        },
        {
            "name": "滝川治部",
            "desc": "新任の相師範。諏訪流。穏やかで親切な指導を行い、門人からの人気が高い。",
        },
        {"name": "かなえ", "desc": "弥五郎の妻。弥五郎を支える心優しい女性。"},
        {"name": "筈見長門", "desc": "久居藩の老職。弥五郎の理解者であり、世話役。"},
    ],
    "glossary": [
        {
            "term": "青眼",
            "reading": "せいがん",
            "desc": "剣道の構えの一つ。刀の切っ先を相手の目の高さにつける構え。",
        },
        {
            "term": "素面素籠手",
            "reading": "すめんすごて",
            "desc": "面や籠手などの防具をつけない状態。",
        },
        {
            "term": "木偶",
            "reading": "でく",
            "desc": "木の人形。転じて、役に立たない人や気の利かない人のたとえ。",
        },
        {
            "term": "理合",
            "reading": "りあい",
            "desc": "物事の道理や理屈。剣道における技の理屈。",
        },
        {
            "term": "位取",
            "reading": "くらいどり",
            "desc": "相手に対する気位や構え。優位な位置を占めること。",
        },
        {
            "term": "柾",
            "reading": "まさき",
            "desc": "ニシキギ科の常緑低木。生垣によく使われる。",
        },
        {
            "term": "肝煎",
            "reading": "きもいり",
            "desc": "世話をすること。仲介や斡旋を行う人。",
        },
        {
            "term": "拝揖",
            "reading": "はいゆう",
            "desc": "両手を組み合わせておじぎをすること。",
        },
    ],
    "authorProfile": {
        "name": "山本周五郎",
        "desc": "日本の小説家。庶民の哀歓や武士の苦衷を描いた時代小説で知られる。代表作に『樅ノ木は残った』『赤ひげ診療譚』など。",
    },
    "chapters": [],
}

# テキストファイルの読み込み
file_path = "/Volumes/2TB/Marutake AudioBook Library/Reading_library/山本周五郎/山本周五郎　五万石の弟子.txt"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 章ごとの分割
# "その一", "その二" ... で分割する
parts = re.split(r"(その[一二三四五])", text)

chapters = []

# parts[0] はタイトルなどが入っている可能性がある
# parts[1] = "その一", parts[2] = 本文, parts[3] = "その二", parts[4] = 本文 ...

for i in range(1, len(parts), 2):
    title = parts[i].strip()
    content = parts[i + 1].strip()
    chapters.append({"title": title, "content": content})

metadata["chapters"] = chapters

# JSONファイルへの書き出し
output_path = "/Volumes/2TB/Marutake AudioBook Library/bookdata/五万石の弟子.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"Created {output_path}")
