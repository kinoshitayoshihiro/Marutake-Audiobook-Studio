#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真珠夫人（菊池寛）JSON変換スクリプト
大正時代を代表する名作長編小説

この小説は「編」と「章」の二層構造になっています：
- 編: 「奇禍」「返すべき時計」「美しき遅参者」など（全27編）
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
    # 2〜10文字の漢字・ひらがな・カタカナのみの行
    if re.match(r"^[ぁ-んァ-ン一-龥々ー]+$", stripped) and 2 <= len(stripped) <= 10:
        # 前後が空行
        prev_empty = prev_line.strip() == ""
        next_empty = next_line.strip() == ""
        if prev_empty and next_empty:
            return True
    return False


def split_sections_and_chapters(text):
    """テキストを編と章に分割"""
    lines = text.split("\n")
    sections = []
    current_section = None
    current_chapter = None
    current_content = []

    # タイトルと著者名をスキップ（最初の編「奇禍」から開始）
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip() == "奇禍":
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


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 入力ファイル（Google Driveから）
    input_file = (
        "/Users/kinoshitayoshihiro/Library/CloudStorage/"
        "GoogleDrive-shimogami88@gmail.com/マイドライブ/丸竹書房/"
        "菊池寛　真珠婦人.txt"
    )

    output_dir = os.path.join(os.path.dirname(script_dir), "bookdata")

    # 出力ディレクトリ作成
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("真珠夫人 JSON変換")
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
        "title": "真珠夫人",
        "author": "菊池寛",
        "era": "大正時代",
        "year": "1920年（大正9年）",
        "genre": ["恋愛小説", "社会小説", "人情・市井・下町"],
        "mood": "シリアス",
        "synopsis": (
            "大正時代の日本を舞台に、愛と復讐、貞操と情念が交錯する物語。\n\n"
            "新婚の信一郎は、自動車事故で瀕死の青年・青木淳と出会う。"
            "淳の懐中時計を預かった信一郎は、それを返すため唐沢家を訪れるが、"
            "そこで出会ったのは、淳の義母であり、絶世の美女・瑠璃子だった。\n\n"
            "「真珠夫人」と呼ばれる瑠璃子は、かつて父の借金のために"
            "愛する人と引き裂かれ、老富豪・唐沢子爵に嫁いだ過去を持つ。"
            "その心の奥底には、男たちへの復讐心が燃えていた。\n\n"
            "信一郎、勝平、直也——彼女に魅了された男たちの運命と、"
            "娘・美奈子の純愛を絡めて描く、菊池寛の代表作。"
        ),
        "authorProfile": {
            "name": "菊池寛",
            "birthYear": 1888,
            "deathYear": 1948,
            "biography": (
                "香川県高松市出身の小説家・劇作家・ジャーナリスト。"
                "文藝春秋社を創設し、芥川賞・直木賞を創設した。"
                "大衆文学と純文学の両方で活躍し、"
                "『真珠夫人』『貞操問答』『父帰る』などの名作を残した。"
            ),
        },
        "keywords": [
            "大正時代",
            "復讐",
            "貞操",
            "三角関係",
            "上流社会",
            "真珠夫人",
            "愛憎劇",
            "女性の生き方",
        ],
        "highlights": [
            "男たちを翻弄する絶世の美女「真珠夫人」瑠璃子の妖艶な魅力",
            "父の借金のため愛を諦めた過去と、心に秘めた復讐心",
            "信一郎、勝平、直也——三人の男たちの運命の交錯",
            "娘・美奈子と直也の純愛と、母の影",
            "大正時代の上流社会を舞台にした愛憎劇",
        ],
        "characters": [
            {
                "name": "唐沢瑠璃子",
                "reading": "からさわ るりこ",
                "role": "主人公",
                "desc": (
                    "「真珠夫人」と呼ばれる絶世の美女。"
                    "かつて父の借金のために愛する人と引き裂かれ、"
                    "老富豪・唐沢子爵に嫁いだ。"
                    "男たちを翻弄し、心の奥底で復讐を誓う。"
                ),
            },
            {
                "name": "渥美信一郎",
                "reading": "あつみ しんいちろう",
                "role": "語り手的存在",
                "desc": (
                    "三菱勤務の青年紳士。新妻・静子と幸福な新婚生活を送っていたが、"
                    "自動車事故で青木淳と出会い、懐中時計を預かったことから"
                    "瑠璃子と関わることになる。"
                ),
            },
            {
                "name": "青木淳",
                "reading": "あおき じゅん",
                "role": "瑠璃子の義理の息子",
                "desc": (
                    "唐沢子爵の先妻の子。高貴な容貌を持つ青年。"
                    "自動車事故で重傷を負い、信一郎に時計を託す。"
                    "義母・瑠璃子への複雑な感情を抱える。"
                ),
            },
            {
                "name": "杉野直也",
                "reading": "すぎの なおや",
                "role": "瑠璃子のかつての恋人",
                "desc": (
                    "瑠璃子が唐沢家に嫁ぐ前に愛し合っていた青年。"
                    "貧しさのために瑠璃子と結ばれることができなかった。"
                    "後に美奈子と出会い、運命的な恋に落ちる。"
                ),
            },
            {
                "name": "唐沢美奈子",
                "reading": "からさわ みなこ",
                "role": "瑠璃子の娘",
                "desc": (
                    "瑠璃子と唐沢子爵の間に生まれた娘。"
                    "母とは対照的に純粋で無垢な心を持つ。"
                    "直也に恋心を抱き、母との確執に苦しむ。"
                ),
            },
            {
                "name": "荘田勝平",
                "reading": "しょうだ かつへい",
                "role": "瑠璃子に執着する男",
                "desc": (
                    "成金の実業家。瑠璃子の美貌に魅せられ、"
                    "執拗に彼女を追い求める。"
                    "瑠璃子に翻弄される男たちの象徴的存在。"
                ),
            },
            {
                "name": "唐沢子爵",
                "reading": "からさわ ししゃく",
                "role": "瑠璃子の夫",
                "desc": (
                    "老富豪の貴族。瑠璃子の父の債権者であり、"
                    "その借金と引き換えに瑠璃子を妻とした。"
                ),
            },
            {
                "name": "渥美静子",
                "reading": "あつみ しずこ",
                "role": "信一郎の妻",
                "desc": (
                    "信一郎の新妻。控えめで貞淑な女性。"
                    "夫が瑠璃子と関わることに不安を感じる。"
                ),
            },
        ],
        "themes": [
            "愛と復讐",
            "貞操と情念",
            "女性の生き方と社会的制約",
            "階級社会と金銭の力",
            "母と娘の確執",
            "純愛と執着",
        ],
        "setting": {
            "time": "大正時代（1920年頃）",
            "place": "東京、箱根、湯河原など",
            "background": (
                "大正デモクラシーと呼ばれる時代。"
                "近代化が進む一方で、旧来の価値観も色濃く残る。"
                "女性の地位向上が叫ばれながらも、"
                "依然として女性は社会的・経済的に弱い立場にあった。"
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
    output_file = os.path.join(output_dir, "真珠夫人.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)

    file_size = os.path.getsize(output_file)
    print(f"\n✅ JSON出力完了: {output_file}")
    print(f"   ファイルサイズ: {file_size:,} bytes")

    # ショートコード用テキスト出力
    shortcode_file = os.path.join(output_dir, "真珠夫人_shortcode.txt")
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
