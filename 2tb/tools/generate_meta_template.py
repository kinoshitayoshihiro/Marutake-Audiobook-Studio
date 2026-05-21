#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
メタデータ生成ヘルパー
=====================
本文テキストからLLM用のプロンプトを生成し、
メタデータ（あらすじ・解説・作者紹介・登場人物）のテンプレートを作成します。

【使い方】
python generate_meta_template.py input.txt -o meta_template.json
python generate_meta_template.py input.txt --prompt  # LLM用プロンプトを出力
"""

import json
import argparse
from pathlib import Path


def extract_excerpt(text: str, max_chars: int = 3000) -> str:
    """本文から抜粋を取得（冒頭と末尾）"""
    lines = text.strip().split("\n")

    # 冒頭部分
    head_chars = max_chars // 2
    head = []
    char_count = 0
    for line in lines:
        if char_count + len(line) > head_chars:
            break
        head.append(line)
        char_count += len(line)

    # 末尾部分
    tail_chars = max_chars // 2
    tail = []
    char_count = 0
    for line in reversed(lines):
        if char_count + len(line) > tail_chars:
            break
        tail.insert(0, line)
        char_count += len(line)

    return "\n".join(head) + "\n\n[...中略...]\n\n" + "\n".join(tail)


def generate_llm_prompt(title: str, author: str, excerpt: str) -> str:
    """LLM用のプロンプトを生成（拡張メタデータ対応）"""
    prompt = f"""以下の小説について、読書アプリ用のメタデータをJSON形式で作成してください。

【作品情報】
タイトル: {title}
著者: {author}

【本文抜粋】
{excerpt}

【出力フォーマット】
以下のJSON形式で出力してください：

```json
{{
  // Schema.org標準プロパティ
  "genre": "Schema.org標準ジャンル（Mystery, Drama, Action, Romance など）",
  "keywords": ["検索キーワード1", "検索キーワード2", "検索キーワード3"],
  
  // 日本文学特化メタデータ
  "japanese_genre": "日本語ジャンル名（捕物帳、人情物、剣豪小説、復讐物、股旅物、職人物、浪人物など）",
  "sub_genre": ["サブジャンル1", "サブジャンル2"],
  
  // テーマタグ（複数選択可）
  "themes": [
    // 以下から該当するものを選択:
    // justice(正義), revenge(復讐), loyalty(忠義), love(恋愛), 
    // family(家族), friendship(友情), honor(名誉), survival(生存),
    // power(権力), mastery(技の追求), wandering(放浪), fate(運命),
    // supernatural(怪異), deduction(推理), bushido(武士道),
    // compassion(思いやり), tradition(伝統), freedom(自由), 
    // karma(因果応報), edo_culture(江戸文化)
  ],
  
  // 感情タグ（作品全体の雰囲気・複数選択可）
  "emotions": [
    // 以下から該当するものを選択:
    // joy(喜び), sadness(悲しみ), anger(怒り), fear(恐怖),
    // surprise(驚き), love(愛情), tension(緊張), warmth(温かさ),
    // nostalgia(郷愁), humor(笑い)
  ],
  
  // 時代設定
  "era": "時代（江戸時代、明治、現代など）",
  "year": "発表年（分かれば）",
  "setting": {{
    "period": "詳細時代区分（江戸時代初期、江戸時代中期、江戸時代後期、幕末など）",
    "location": "舞台（江戸、京都、大坂、長崎、地方など）"
  }},
  
  "synopsis": "あらすじ（200-400文字程度）",
  
  "highlights": [
    "見どころ1",
    "見どころ2",
    "見どころ3"
  ],
  
  "characters": [
    {{
      "name": "登場人物名",
      "role": "役割（主人公、ヒロイン、敵役など）",
      "description": "人物説明",
      "relationships": [
        {{"target": "関係相手", "relation": "関係性"}}
      ]
    }}
  ],
  
  "author_info": {{
    "name": "{author}",
    "reading": "著者名の読み仮名",
    "birth": "生年",
    "death": "没年（存命なら空欄）",
    "birthplace": "出身地",
    "biography": "経歴・生涯（100-200文字）",
    "style": "作風・特徴",
    "major_works": ["代表作1", "代表作2", "代表作3"]
  }}
}}
```

【ジャンル分類ガイド】
- **捕物帳**: 岡っ引き・同心が事件を解決（錢形平次、鬼平犯科帳など）
- **人情物**: 庶民の暮らしと人間関係（下町人情、商家物語など）
- **剣豪小説**: 剣の道を究める物語（宮本武蔵、剣客商売など）
- **復讐物・仇討物**: 親や主君の仇を討つ
- **股旅物**: 渡世人・博徒の旅と義理人情
- **職人物**: 職人の技と生き様
- **浪人物**: 主家を離れた浪人の物語

注意事項：
- themesとemotionsは英語キーワードで指定してください（SEO対策）
- 複数該当する場合は配列で指定
- 分からない項目は空文字列 "" または空配列 [] で
- あらすじはネタバレを避けつつ、物語の魅力が伝わるように
- 登場人物は主要人物を5-8名程度
- 人物関係は物語理解に重要なものを
- 作者情報は事実に基づいて（不明な場合は空欄に）
"""
    return prompt


def create_meta_template(title: str, author: str) -> dict:
    """空のメタデータテンプレートを生成"""
    return {
        "genre": "",
        "era": "",
        "year": "",
        "synopsis": "",
        "highlights": ["", "", ""],
        "characters": [
            {"name": "", "role": "主人公", "description": "", "relationships": []}
        ],
        "author_info": {
            "name": author,
            "reading": "",
            "birth": "",
            "death": "",
            "birthplace": "",
            "biography": "",
            "style": "",
            "major_works": [],
        },
        "keywords": [],
    }


def main():
    parser = argparse.ArgumentParser(description="メタデータ生成ヘルパー")
    parser.add_argument("input", help="入力テキストファイル")
    parser.add_argument("-o", "--output", help="出力テンプレートJSONファイル")
    parser.add_argument("--prompt", action="store_true", help="LLM用プロンプトを出力")
    parser.add_argument("--title", help="作品タイトル")
    parser.add_argument("--author", help="著者名")

    args = parser.parse_args()

    # 入力ファイル読み込み
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {args.input}")
        return 1

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    # タイトル・著者
    title = args.title or "（タイトル）"
    author = args.author or "（著者）"

    if args.prompt:
        # LLM用プロンプト出力
        excerpt = extract_excerpt(text, 4000)
        prompt = generate_llm_prompt(title, author, excerpt)
        print(prompt)
    else:
        # テンプレート出力
        template = create_meta_template(title, author)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(template, f, ensure_ascii=False, indent=2)
            print(f"✅ テンプレート出力: {args.output}")
        else:
            print(json.dumps(template, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    exit(main())
