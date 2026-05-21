#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
貞操問答（菊池寛）JSON変換スクリプト
昭和初期の女性の自立と貞操観念を問う長編小説

この小説は「編」と「章」の二層構造になっています：
- 編: 「金を売る」「レディ第一」「姉の愛人」など（全28編）
- 章: 各編の中で「一」「二」「三」...と番号付け
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


def is_section_title(line, prev_line, next_line):
    """編のタイトルかどうかを判定"""
    stripped = line.strip()
    # 漢数字だけの行（章番号）をスキップ
    if re.match(r"^[一二三四五六七八九十]+$", stripped):
        return False
    # 2〜8文字の漢字・ひらがな・カタカナのみの行
    if re.match(r"^[ぁ-んァ-ン一-龥々ー]+$", stripped) and 2 <= len(stripped) <= 8:
        # 前後が空行
        prev_empty = prev_line.strip() == ""
        next_empty = next_line.strip() == ""
        if prev_empty and next_empty:
            return True
    return False


def split_sections_and_chapters(text):
    """テキストを編と章に分割

    貞操問答は「編」（セクション）と「章」の二層構造
    """
    lines = text.split("\n")
    sections = []
    current_section = None
    current_chapter = None
    current_content = []

    # タイトルと著者名をスキップ
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == "金を売る":
            start_idx = i
            break

    chapter_pattern = r"^([一二三四五六七八九十]+)\s*$"

    for i in range(start_idx, len(lines)):
        line = lines[i]
        prev_line = lines[i - 1] if i > 0 else ""
        next_line = lines[i + 1] if i < len(lines) - 1 else ""
        stripped = line.strip()

        # 編のタイトル検出
        if is_section_title(line, prev_line, next_line):
            # 前の章を保存
            if current_chapter is not None and current_section is not None:
                content = "\n".join(current_content).strip()
                if content:
                    current_section["chapters"].append(
                        {"number": current_chapter, "content": content}
                    )
            # 前の編を保存
            if current_section is not None:
                sections.append(current_section)
            # 新しい編を開始
            current_section = {"title": stripped, "chapters": []}
            current_chapter = None
            current_content = []
            continue

        # 章番号の検出
        match = re.match(chapter_pattern, stripped)
        if match and current_section is not None:
            # 前の章を保存
            if current_chapter is not None:
                content = "\n".join(current_content).strip()
                if content:
                    current_section["chapters"].append(
                        {"number": current_chapter, "content": content}
                    )
            # 新しい章を開始
            current_chapter = match.group(1)
            current_content = []
        else:
            if current_chapter is not None:
                current_content.append(line)

    # 最後の章を保存
    if current_chapter is not None and current_section is not None:
        content = "\n".join(current_content).strip()
        if content:
            current_section["chapters"].append(
                {"number": current_chapter, "content": content}
            )
    # 最後の編を保存
    if current_section is not None:
        sections.append(current_section)

    return sections


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
        "百": 100,
    }

    if kanji in kanji_map:
        return kanji_map[kanji]

    # 十一〜十九、二十〜のケース
    result = 0
    temp = 0
    for char in kanji:
        if char == "十":
            if temp == 0:
                temp = 1
            result += temp * 10
            temp = 0
        elif char == "百":
            if temp == 0:
                temp = 1
            result += temp * 100
            temp = 0
        else:
            temp = kanji_map.get(char, 0)
    result += temp
    return result if result > 0 else 0


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 入力ファイル（Google Driveから）
    input_file = (
        "/Users/kinoshitayoshihiro/Library/CloudStorage/"
        "GoogleDrive-shimogami88@gmail.com/マイドライブ/丸竹書房/"
        "菊池寛　貞操問答.txt"
    )

    output_dir = os.path.join(os.path.dirname(script_dir), "bookdata")

    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("貞操問答 JSON変換")
    print("=" * 60)

    # テキスト読み込み
    if not os.path.exists(input_file):
        print(f"❌ ファイルが見つかりません: {input_file}")
        print("入力ファイルのパスを確認してください。")
        return

    text = load_text(input_file)
    print(f"ファイル読み込み完了: {len(text):,} 文字")

    # 編と章に分割
    sections = split_sections_and_chapters(text)
    print(f"検出した編数: {len(sections)}")

    total_chapters = 0
    for sec in sections:
        chapter_count = len(sec["chapters"])
        total_chapters += chapter_count
        for ch in sec["chapters"]:
            ch["content"] = clean_text(ch["content"])
        print(f"  {sec['title']}: {chapter_count}章")

    print(f"総章数: {total_chapters}")

    # JSON構造を作成
    book_data = {
        "title": "貞操問答",
        "author": "菊池寛",
        "era": "昭和初期",
        "genre": ["人情・市井・下町", "社会小説"],
        "mood": "シリアス",
        "synopsis": (
            "大正デモクラシーの余韻を残しつつも経済的不安が広がる昭和初期。"
            "裕福だった南條家は父の死後、没落の一途をたどっていた。\n\n"
            "長女の新子は、家族を支えるため家庭教師の職を得ようと決意する。"
            "紹介されたのは、上流階級の前川家。"
            "しかしそこには、プライド高く冷酷な夫人・綾子が君臨していた。\n\n"
            "貞操観念と女性の自立、家族への愛と自己犠牲。"
            "時代に翻弄されながらも誇りを持って生きようとする新子の姿を通して、"
            "女性の生き方を問う菊池寛の傑作長編。"
        ),
        "authorProfile": {
            "name": "菊池寛",
            "birthYear": 1888,
            "deathYear": 1948,
            "biography": (
                "香川県高松市出身の小説家・劇作家・ジャーナリスト。"
                "文藝春秋社を創設し、芥川賞・直木賞を創設した。"
                "大衆文学と純文学の両方で活躍し、"
                "『真珠夫人』『父帰る』などの名作を残した。"
            ),
        },
        "keywords": [
            "貞操観念",
            "女性の自立",
            "経済的困窮",
            "家庭教師",
            "昭和初期",
            "没落家族",
            "姉妹",
            "上流社会",
        ],
        "highlights": [
            "没落した名家の長女が家族を支えるため奮闘する姿",
            "上流階級の傲慢な夫人との緊張感ある対立",
            "恋人・美沢との揺れる関係と妹への不安",
            "貞操と自立を巡る時代の価値観との葛藤",
            "三姉妹それぞれの生き方の対比",
        ],
        "characters": [
            {
                "name": "南條新子",
                "reading": "なんじょう しんこ",
                "role": "主人公",
                "family": "南條家",
                "desc": (
                    "清純さと仇っぽさを併せ持つ、聡明で意志の強い女性。"
                    "家計を支えるため、前川家の家庭教師となる決意をする。"
                    "家族のために働きながらも、誇りを持って生きようとする。"
                ),
            },
            {
                "name": "南條圭子",
                "reading": "なんじょう けいこ",
                "role": "新子の姉",
                "family": "南條家",
                "desc": (
                    "家族の中で最も美しいとされる長女。"
                    "女子大に通いながら文学や演劇を愛し、新劇研究会のメンバー。"
                    "生活には無頓着で、金銭感覚が乏しく妹の新子に頼りがち。"
                ),
            },
            {
                "name": "南條美和子",
                "reading": "なんじょう みわこ",
                "role": "新子の妹",
                "family": "南條家",
                "desc": (
                    "小柄で快活、天真爛漫な性格の末っ子。"
                    "無邪気で自由奔放な性格で、姉の新子をからかうことも多い。"
                    "家の経済状況に無頓着。"
                ),
            },
            {
                "name": "南條家の母",
                "reading": "なんじょうけのはは",
                "role": "三姉妹の母",
                "family": "南條家",
                "desc": (
                    "亡夫の遺産で生活していたが、浪費癖があり経済観念に乏しい。"
                    "夫の死後も派手な暮らしを続け、家計の深刻さを理解していない。"
                ),
            },
            {
                "name": "前川準之助",
                "reading": "まえかわ じゅんのすけ",
                "role": "新子の雇い主",
                "family": "前川家",
                "desc": (
                    "四十歳過ぎの紳士。米国留学の経験があり、"
                    "レディ・ファーストの精神を持つ上品で理知的な人物。"
                    "妻の綾子に頭が上がらないが、新子に特別な感情を抱く。"
                ),
            },
            {
                "name": "前川綾子",
                "reading": "まえかわ あやこ",
                "role": "準之助の妻",
                "family": "前川家",
                "desc": (
                    "子爵家出身の女性。プライドが高く、美貌と気品を兼ね備える。"
                    "家では『女王様』のような絶対的な支配力を持ち、"
                    "家庭教師の新子を見下し冷たく接する。"
                ),
            },
            {
                "name": "前川路子",
                "reading": "まえかわ みちこ",
                "role": "準之助の妹",
                "family": "前川家",
                "desc": (
                    "新子の学友であり、家庭教師の仕事を紹介する。"
                    "親しみやすい性格で、兄の結婚生活を『妻に呪縛されている』と評し、"
                    "義姉の傲慢さを批判している。"
                ),
            },
            {
                "name": "前川小太郎",
                "reading": "まえかわ こたろう",
                "role": "前川家の長男",
                "family": "前川家",
                "desc": (
                    "十二歳の少年で、勉強が苦手。"
                    "甘やかされて育ったため、わがままで人見知りな一面がある。"
                ),
            },
            {
                "name": "前川祥子",
                "reading": "まえかわ さちこ",
                "role": "前川家の長女",
                "family": "前川家",
                "desc": "小学校三年生の女の子。元気で素直な性格で、新子にもすぐに懐く。",
            },
            {
                "name": "美沢直巳",
                "reading": "みさわ なおみ",
                "role": "新子の恋人",
                "family": "その他",
                "desc": (
                    "ヴァイオリニスト。以前は女学校の音楽教師だったが辞職し、"
                    "新音楽協会の練習生となる。新子とは長年の恋人関係だが、"
                    "結婚に踏み切れず、美和子との軽い交流が新子を不安にさせる。"
                ),
            },
            {
                "name": "逸郎",
                "reading": "いつろう",
                "role": "綾子の遠縁",
                "family": "その他",
                "desc": (
                    "夫人の母方の遠縁にあたる青年。"
                    "爽やかで礼儀正しいが、夫人の媚態に揺れる。"
                ),
            },
            {
                "name": "小池利男",
                "reading": "こいけ としお",
                "role": "新劇研究会の監督",
                "family": "その他",
                "desc": (
                    "フランス帰りの劇作家で、公演の資金繰りに悩む。"
                    "圭子が参加する『死者の群』の演出を担当。"
                ),
            },
            {
                "name": "久能",
                "reading": "くのう",
                "role": "老劇作家",
                "family": "その他",
                "desc": "新劇の先輩。圭子の演技を評価する。",
            },
            {
                "name": "重松",
                "reading": "しげまつ",
                "role": "時計屋",
                "family": "その他",
                "desc": "日本橋の時計屋で、南條家の貴重品を買い取る。小柄でずる賢い商人。",
            },
        ],
        "families": [
            {
                "name": "南條家",
                "description": (
                    "かつては裕福だったが、父の死後没落の一途をたどる。"
                    "母と三姉妹（圭子・新子・美和子）で構成される。"
                ),
            },
            {
                "name": "前川家",
                "description": (
                    "上流階級の家庭。準之助と妻の綾子、子供たち（小太郎・祥子）、"
                    "準之助の妹・路子がいる。"
                ),
            },
        ],
        "themes": [
            "女性の自立と社会進出",
            "貞操観念と時代の価値観",
            "家族の絆と自己犠牲",
            "階級社会における人間関係",
            "没落と誇り",
        ],
        "setting": {
            "time": "昭和初期（大正デモクラシーの余韻が残る時代）",
            "place": "東京",
            "background": (
                "経済的不安が広がり、女性の生き方にも大きな変化が訪れていた時代。"
                "裕福だった家庭の没落により、"
                "娘たちが家庭を支えなければならない現実が物語の背景となる。"
            ),
        },
        "sections": [],
    }

    # 編・章データを追加
    for i, sec in enumerate(sections):
        section_data = {
            "sectionNumber": i + 1,
            "sectionTitle": sec["title"],
            "chapters": [],
        }
        for ch in sec["chapters"]:
            section_data["chapters"].append(
                {"chapterNumber": ch["number"], "content": ch["content"]}
            )
        book_data["sections"].append(section_data)

    # JSON出力
    output_file = os.path.join(output_dir, "貞操問答.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)

    file_size = os.path.getsize(output_file)
    print(f"\n✅ JSON出力完了: {output_file}")
    print(f"   ファイルサイズ: {file_size:,} bytes")

    # ショートコード用テキスト出力
    shortcode_file = os.path.join(output_dir, "貞操問答_shortcode.txt")
    with open(shortcode_file, "w", encoding="utf-8") as f:
        f.write("[immersive_reader]\n")
        json.dump(book_data, f, ensure_ascii=False)
        f.write("\n[/immersive_reader]")

    print(f"✅ ショートコード出力完了: {shortcode_file}")

    # 総文字数計算
    total_chars = sum(len(ch["content"]) for sec in sections for ch in sec["chapters"])
    print(f"\n📖 総文字数: {total_chars:,} 文字")
    print(f"📚 全{len(sections)}編 {total_chapters}章")


if __name__ == "__main__":
    main()
