#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
読書アプリ用 BookData 変換ツール
================================
本文テキストファイルをJSON形式に変換します。

【章タイトル認識ルール】
1. 前後に空行がある1行のセンテンス
2. 「第○章」「その○」「○編」「○部」などのパターン
3. 階層構造（章→節）にも対応

【使い方】
python convert_to_bookdata.py input.txt -o output.json
python convert_to_bookdata.py input.txt --meta meta.json -o output.json
"""

import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple


# =====================================
# 章タイトル判定パターン
# =====================================

# 明示的な章タイトルパターン（優先度高）
CHAPTER_PATTERNS = [
    # 「第○章」「第○編」「第○部」「第○話」「第○回」
    r"^第[一二三四五六七八九十百千〇零]+[章編部話回節篇]",
    r"^第\d+[章編部話回節篇]",
    # 「その一」「その1」
    r"^その[一二三四五六七八九十]+",
    r"^その\d+",
    # 「一」「二」などの漢数字のみ（短い）
    r"^[一二三四五六七八九十]+$",
    # 全角数字のみ（１、２…）
    r"^[０-９]+$",
    # 半角数字のみ（1、2…）
    r"^[0-9]+$",
    # 「（一）」「（1）」
    r"^[（\(][一二三四五六七八九十\d]+[）\)]",
    # 「前編」「後編」「上」「中」「下」
    r"^[前中後上下]編?$",
    # 「序」「序章」「終章」「エピローグ」「プロローグ」
    r"^(序章?|終章|エピローグ|プロローグ|結び|あとがき|はじめに)$",
]

# サブ章（節）パターン
SUB_CHAPTER_PATTERNS = [
    r"^その[一二三四五六七八九十\d]+",
    r"^[一二三四五六七八九十]+$",
    r"^[（\(][一二三四五六七八九十\d]+[）\)]$",
]


def read_text_auto_encoding(path: Path) -> str:
    """複数候補の文字コードで読み込む（Shift-JIS/CP932対策）"""
    raw = path.read_bytes()
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis", "euc_jp"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp932", errors="replace")


def is_explicit_chapter_title(line: str) -> bool:
    """明示的な章タイトルパターンにマッチするか"""
    line = line.strip()
    for pattern in CHAPTER_PATTERNS:
        if re.match(pattern, line):
            return True
    return False


def is_sub_chapter_title(line: str) -> bool:
    """サブ章（節）パターンにマッチするか"""
    line = line.strip()
    for pattern in SUB_CHAPTER_PATTERNS:
        if re.match(pattern, line):
            return True
    return False


def is_potential_chapter_title(line: str, prev_empty: bool, next_empty: bool) -> bool:
    """
    章タイトルの可能性があるか判定

    条件:
    1. 前後に空行がある
    2. 1行のセンテンス（改行なし）
    3. 長すぎない（30文字以下）
    4. 句読点で終わらない（本文ではない）
    """
    line = line.strip()

    if not line:
        return False

    # 明示的パターンは空行関係なく認識
    if is_explicit_chapter_title(line):
        return True

    # 前後に空行がない場合は章タイトルではない
    if not (prev_empty and next_empty):
        return False

    # 長すぎる行は本文
    if len(line) > 30:
        return False

    # 句読点で終わる行は本文
    if line.endswith(("。", "、", "」", "…", "――", "！", "？")):
        return False

    # 「」で囲まれている場合は会話文（本文）
    if line.startswith("「") and line.endswith("」"):
        return False

    return True


def parse_text_structure(text: str) -> List[Dict]:
    """
    テキストを解析して章構造を抽出

    Returns:
        [
            {
                "title": "章タイトル",
                "sub_title": "節タイトル（あれば）",
                "content": "本文"
            },
            ...
        ]
    """
    lines = text.split("\n")
    chapters = []

    current_chapter = {"title": "", "sub_title": "", "content": ""}
    content_buffer = []

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 前後の空行チェック
        prev_empty = (i == 0) or (lines[i - 1].strip() == "")
        next_empty = (i == len(lines) - 1) or (lines[i + 1].strip() == "")

        # 章タイトル判定
        if is_potential_chapter_title(stripped, prev_empty, next_empty):
            # 現在のバッファを保存
            if content_buffer or current_chapter["title"]:
                current_chapter["content"] = "\n".join(content_buffer).strip()
                if current_chapter["title"] or current_chapter["content"]:
                    chapters.append(current_chapter.copy())
                content_buffer = []

            # 新しい章を開始
            # 連続する章タイトル（階層構造）をチェック
            if is_explicit_chapter_title(stripped) and not is_sub_chapter_title(
                stripped
            ):
                # メイン章タイトル
                current_chapter = {"title": stripped, "sub_title": "", "content": ""}

                # 次の行もタイトルかチェック（階層構造）
                j = i + 1
                while j < len(lines) and lines[j].strip() == "":
                    j += 1
                if j < len(lines):
                    next_line = lines[j].strip()
                    next_prev_empty = (lines[j - 1].strip() == "") if j > 0 else True
                    next_next_empty = (j == len(lines) - 1) or (
                        lines[j + 1].strip() == ""
                    )
                    if is_sub_chapter_title(next_line) or is_potential_chapter_title(
                        next_line, next_prev_empty, next_next_empty
                    ):
                        current_chapter["sub_title"] = next_line
                        i = j  # スキップ

            elif is_sub_chapter_title(stripped):
                # サブ章（節）タイトル - 既存の章に追加
                if current_chapter["title"]:
                    current_chapter["sub_title"] = stripped
                else:
                    current_chapter = {
                        "title": stripped,
                        "sub_title": "",
                        "content": "",
                    }
            else:
                # その他の章タイトル
                current_chapter = {"title": stripped, "sub_title": "", "content": ""}

        elif stripped:
            # 本文
            content_buffer.append(line)

        i += 1

    # 最後のバッファを保存
    if content_buffer or current_chapter["title"]:
        current_chapter["content"] = "\n".join(content_buffer).strip()
        if current_chapter["title"] or current_chapter["content"]:
            chapters.append(current_chapter)

    return chapters


def format_content_for_json(content: str) -> str:
    """
    本文をJSON用にフォーマット
    - 連続する空行を1つに
    - 適切な改行を維持
    """
    # 連続する空行を1つに
    content = re.sub(r"\n{3,}", "\n\n", content)
    return content.strip()


def merge_chapters_with_hierarchy(chapters: List[Dict]) -> List[Dict]:
    """
    章構造を整理し、空の章をマージ

    - 本文のない章は次の章にマージ
    - 重複するタイトルを整理
    """
    if not chapters:
        return chapters

    merged = []
    pending_title = ""

    for i, ch in enumerate(chapters):
        # 本文がない章
        if not ch["content"].strip():
            # サブタイトルもない場合は次の章のメインタイトルとして保留
            if not ch["sub_title"]:
                pending_title = ch["title"]
            continue

        # 本文がある章
        new_ch = ch.copy()

        # 保留中のタイトルがあれば適用
        if pending_title:
            # 現在のタイトルがサブ章パターンの場合、保留タイトルをメインに
            if is_sub_chapter_title(new_ch["title"]):
                new_ch["sub_title"] = new_ch["title"]
                new_ch["title"] = pending_title
            # 同じタイトルの場合は無視
            elif pending_title != new_ch["title"]:
                # 保留タイトルをメインタイトルとして使用
                new_ch["sub_title"] = (
                    new_ch["title"]
                    if new_ch["title"] != pending_title
                    else new_ch["sub_title"]
                )
                new_ch["title"] = pending_title
            pending_title = ""

        merged.append(new_ch)

    return merged


def create_bookdata(
    title: str, author: str, chapters: List[Dict], meta: Optional[Dict] = None
) -> Dict:
    """
    読書アプリ用のbookdataを生成
    """
    # 章構造を整理（空の章を除外）
    chapters = merge_chapters_with_hierarchy(chapters)

    # 本文を結合
    content_parts = []
    for ch in chapters:
        if ch["title"]:
            content_parts.append(f"\n\n{ch['title']}\n")
        if ch["sub_title"]:
            content_parts.append(f"\n{ch['sub_title']}\n")
        if ch["content"]:
            content_parts.append(ch["content"])

    full_content = "\n".join(content_parts)
    full_content = format_content_for_json(full_content)

    # 基本データ（アプリ表示互換 + SEOメタデータ）
    chapter_items = []
    for ch in chapters:
        if not (ch.get("title") or ch.get("sub_title") or ch.get("content")):
            continue

        chapter_title = (ch.get("title") or "").strip()
        sub_title = (ch.get("sub_title") or "").strip()
        if chapter_title and sub_title and sub_title != chapter_title:
            chapter_title = f"{chapter_title}\n{sub_title}"
        elif not chapter_title and sub_title:
            chapter_title = sub_title

        chapter_items.append(
            {
                "title": chapter_title or "本文",
                "content": (ch.get("content") or "").strip(),
            }
        )

    bookdata = {
        "title": title,
        "author": author,
        # SEO/分類
        "genre": "",
        "japanese_genre": "",
        "sub_genre": "",
        "setting": "",
        "location": "",
        "time_period": "",
        "keywords": [],
        "themes": [],
        "emotions": [],
        # 既存フィールド
        "synopsis": "",
        "highlights": [],
        "characters": [],
        "authorProfile": {
            "name": author,
            "desc": "",
        },
        # アプリ表示は chapters[].content を前提
        "chapters": chapter_items,
        # 互換用（全文）
        "content": full_content,
        # 後方互換（旧スキーマも残す）
        "era": "",
        "year": "",
        "setting_detail": {
            "period": "",
            "location": "",
        },
        "author_info": {
            "name": author,
            "reading": "",
            "biography": "",
            "style": "",
            "major_works": [],
        },
    }

    # メタデータをマージ（後方互換性を保ちつつ）
    if meta:
        for key, value in meta.items():
            if key in bookdata:
                if isinstance(bookdata[key], dict) and isinstance(value, dict):
                    bookdata[key].update(value)
                elif isinstance(bookdata[key], list) and isinstance(value, list):
                    bookdata[key] = value
                elif value:  # 空でない値のみ上書き
                    bookdata[key] = value
            else:
                # 新しいフィールドも受け入れる（拡張性）
                bookdata[key] = value

    return bookdata


def extract_title_author(text: str) -> Tuple[str, str]:
    """
    テキストの冒頭からタイトルと著者を抽出

    期待フォーマット:
    山本周五郎著　立春なみだ橋
    または
    著者名　作品タイトル
    """
    lines = [ln.strip() for ln in text.split("\n")]
    non_empty = [ln for ln in lines[:15] if ln]

    title = ""
    author = ""

    # パターン1: 複数行（シリーズ名 / 作品名 / 著者）
    if len(non_empty) >= 3:
        possible_series, possible_work, possible_author = (
            non_empty[0],
            non_empty[1],
            non_empty[2],
        )
        if len(possible_author) <= 20 and all(
            ch not in possible_author for ch in ("。", "、", "「", "」")
        ):
            author = possible_author
            title = f"{possible_series} {possible_work}".strip()
            return title, author

    # パターン2: 「著」を含む行
    for line in non_empty[:10]:
        if "著" in line:
            parts = re.split(r"著\s*", line)
            if len(parts) >= 2:
                author = parts[0].strip()
                title = parts[1].strip()
                return title, author

    # パターン3: 全角スペース区切り（著者　作品）
    for line in non_empty[:10]:
        # 会話行は除外（誤検出対策）
        if line.startswith("「"):
            continue
        if "　" in line:
            parts = [p.strip() for p in line.split("　") if p.strip()]
            if len(parts) >= 2:
                author = parts[0]
                title = parts[1]
                return title, author

    # パターン4: 先頭1行だけ（タイトルのみ）
    if non_empty:
        title = non_empty[0]

    return title, author


def main():
    parser = argparse.ArgumentParser(
        description="本文テキストを読書アプリ用JSONに変換",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python convert_to_bookdata.py 立春なみだ橋.txt -o bookdata.json
  python convert_to_bookdata.py 立春なみだ橋.txt --meta meta.json -o bookdata.json
  python convert_to_bookdata.py 立春なみだ橋.txt --title "立春なみだ橋" --author "山本周五郎"

メタデータJSON例 (meta.json):
{
  "genre": "時代小説",
  "era": "江戸時代",
  "synopsis": "あらすじ...",
  "highlights": ["見どころ1", "見どころ2"],
  "characters": [...],
  "author_info": {...}
}
        """,
    )
    parser.add_argument("input", help="入力テキストファイル")
    parser.add_argument("-o", "--output", help="出力JSONファイル")
    parser.add_argument("--meta", help="メタデータJSONファイル（あらすじ・解説など）")
    parser.add_argument("--title", help="作品タイトル（省略時は自動検出）")
    parser.add_argument("--author", help="著者名（省略時は自動検出）")
    parser.add_argument("--debug", action="store_true", help="章構造をデバッグ出力")

    args = parser.parse_args()

    # 入力ファイル読み込み
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {args.input}")
        return 1

    text = read_text_auto_encoding(input_path)

    # タイトル・著者の取得
    if args.title and args.author:
        title, author = args.title, args.author
    else:
        detected_title, detected_author = extract_title_author(text)
        title = args.title or detected_title or "無題"
        author = args.author or detected_author or "不明"

    # 先頭ヘッダ（タイトル/著者行）を本文から除外（右門捕物帖などの形式対策）
    try:
        lines = text.splitlines()
        non_empty_idx = [i for i, ln in enumerate(lines) if ln.strip()]
        if len(non_empty_idx) >= 3:
            i1, i2, i3 = non_empty_idx[0], non_empty_idx[1], non_empty_idx[2]
            header_series = lines[i1].strip()
            header_work = lines[i2].strip()
            header_author = lines[i3].strip()
            if (
                detected_title
                and detected_author
                and detected_title.strip() == f"{header_series} {header_work}".strip()
                and detected_author.strip() == header_author
            ):
                cut = i3 + 1
                while cut < len(lines) and lines[cut].strip() == "":
                    cut += 1
                text = "\n".join(lines[cut:])
    except Exception:
        pass

    print(f"📖 タイトル: {title}")
    print(f"✍️  著者: {author}")

    # テキスト解析
    chapters = parse_text_structure(text)
    print(f"📑 検出された章: {len(chapters)}")

    if args.debug:
        print("\n【章構造】")
        for i, ch in enumerate(chapters):
            print(f"  {i+1}. {ch['title']}")
            if ch["sub_title"]:
                print(f"      └─ {ch['sub_title']}")
            print(f"      本文: {len(ch['content'])}文字")

    # メタデータ読み込み
    meta = None
    if args.meta:
        meta_path = Path(args.meta)
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            print(f"📋 メタデータ読み込み: {args.meta}")

    # bookdata生成
    bookdata = create_bookdata(title, author, chapters, meta)

    # 出力
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(bookdata, f, ensure_ascii=False, indent=2)
        print(f"✅ 出力完了: {args.output}")
    else:
        # 標準出力
        print("\n" + "=" * 50)
        print(json.dumps(bookdata, ensure_ascii=False, indent=2))

    return 0


if __name__ == "__main__":
    exit(main())
