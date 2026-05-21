#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
山本周五郎 作品深層解析スクリプト（試験版）

本文TXT → Gemini 2.0 flash → 章別あらすじ / 登場人物 / テーマ / メタファー等

使い方:
    python analyze_yamamoto_works.py
    python analyze_yamamoto_works.py --update-works   # works.jsonl にも反映する
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from google import genai

# ============================================================
# 設定
# ============================================================
GEMINI_API_KEY = "REDACTED_GOOGLE_API_KEY"

BASE = Path(__file__).resolve().parent.parent.parent  # 音本・唄本倶楽部/
TXT_DIR = BASE / "2tb" / "Reading_library" / "山本周五郎"
OUTPUT_DIR = BASE / "2tb" / "reports" / "yamamoto_deep_analysis"
WORKS_JSONL = BASE / "tools" / "yamashukan_site_builder" / "data" / "works.jsonl"

TARGET_WORKS = [
    {"title": "藤次郎の恋", "file": "山本周五郎　藤次郎の恋.txt"},
    {"title": "雨の山吹",   "file": "山本周五郎　雨の山吹.txt"},
    {"title": "武道宵節句", "file": "山本周五郎　武道宵節句.txt"},
]

CHAPTER_RE = re.compile(r'^[\s　]*([一二三四五六七八九十百]+)[\s　]*$', re.MULTILINE)
ENCODINGS = ["utf-8", "cp932", "shift_jis", "euc_jp"]


def read_text_auto(path: Path) -> str:
    """エンコーディングを自動検出してテキストを返す。"""
    for enc in ENCODINGS:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"エンコーディングを特定できませんでした: {path.name}")


# ============================================================
# Gemini 初期化
# ============================================================
client = genai.Client(api_key=GEMINI_API_KEY)


def detect_chapters(text: str) -> list[dict]:
    """漢数字の章見出し行を検出して各章のテキストを返す。"""
    matches = list(CHAPTER_RE.finditer(text))
    if not matches:
        return [{"num": "全編", "text": text}]

    chapters = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chapters.append({"num": m.group(1).strip(), "text": text[start:end].strip()})
    return chapters


def analyze_work(title: str, full_text: str, chapters: list[dict]) -> dict | None:
    chapter_outline = "\n".join(
        f"【{c['num']}】（約{len(c['text'])}文字）"
        for c in chapters
    )

    prompt = f"""あなたは時代小説の書誌・編集の専門家です。
山本周五郎の短編小説「{title}」の本文全文と章構成を読み、以下の JSON を生成してください。

---本文（{len(full_text)}文字）---
{full_text}

---章構成---
{chapter_outline}

【出力ルール】
- JSON のみを出力（Markdown コードブロック不要）
- 文字列は必ず二重引用符
- chapters の num は本文中の章番号（漢数字）をそのまま使う

{{
  "title": "{title}",
  "synopsis": "全体のあらすじ（3〜5文、日本語）",
  "chapters": [
    {{"num": "一", "summary": "この章で起こること（1〜2文）"}}
  ],
  "characters": [
    {{
      "name": "登場人物名",
      "reading": "よみがな",
      "role": "主人公 / ヒロイン / 脇役 など",
      "tags": ["属性タグ1", "属性タグ2"]
    }}
  ],
  "themes": ["テーマ1", "テーマ2", "テーマ3"],
  "mood": "作品全体の雰囲気（例: 切ない、痛快、しみじみ）",
  "metaphors": ["この作品に流れる象徴・メタファー（1〜3個）"],
  "compilation_tags": ["総集編タグ1", "総集編タグ2"],
  "search_keywords": ["検索用キーワード1", "検索用キーワード2", "検索用キーワード3", "検索用キーワード4", "検索用キーワード5"]
}}"""

    wait = 15
    for attempt in range(4):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            raw = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"  [JSON解析エラー] {e}")
            (OUTPUT_DIR / f"{title}_raw.txt").write_text(response.text, encoding="utf-8")
            return None
        except Exception as e:
            if "429" in str(e) and attempt < 3:
                print(f"  [レート制限] {wait}秒待ってリトライ ({attempt + 1}/3)...")
                time.sleep(wait)
                wait *= 2
            else:
                print(f"  [Geminiエラー] {e}")
                return None
    return None


def update_works_jsonl(result: dict) -> None:
    """works.jsonl の対象タイトルエントリに深層解析フィールドを追記する。"""
    lines = WORKS_JSONL.read_text(encoding="utf-8").splitlines()
    updated = []
    found = False

    for line in lines:
        if not line.strip():
            updated.append(line)
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            updated.append(line)
            continue

        if entry.get("title") == result["title"]:
            entry["synopsis_deep"]    = result.get("synopsis", "")
            entry["chapters"]         = result.get("chapters", [])
            # 既存の characters フィールド（旧テキスト形式）と区別
            entry["characters_deep"]  = result.get("characters", [])
            entry["themes"]           = result.get("themes", [])
            entry["mood"]             = result.get("mood", "")
            entry["metaphors"]        = result.get("metaphors", [])
            entry["compilation_tags"] = result.get("compilation_tags", [])
            entry["search_keywords"]  = result.get("search_keywords", [])
            updated.append(json.dumps(entry, ensure_ascii=False))
            found = True
        else:
            updated.append(line)

    if not found:
        print(f"  [警告] works.jsonl に「{result['title']}」が見つかりませんでした")
    else:
        WORKS_JSONL.write_text("\n".join(updated) + "\n", encoding="utf-8")
        print(f"  works.jsonl を更新しました")


def main(update_works: bool = False) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for work in TARGET_WORKS:
        title = work["title"]
        txt_path = TXT_DIR / work["file"]

        print(f"\n{'='*50}")
        print(f"処理中: {title}")

        if not txt_path.exists():
            print(f"  [スキップ] ファイルが見つかりません: {txt_path.name}")
            continue

        full_text = read_text_auto(txt_path)
        chapters = detect_chapters(full_text)
        print(f"  本文: {len(full_text):,}文字 / 章数: {len(chapters)}")

        result = analyze_work(title, full_text, chapters)
        if result is None:
            print(f"  [失敗] Gemini 解析に失敗しました")
            continue

        out_path = OUTPUT_DIR / f"{title}.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  → {out_path.relative_to(BASE)}")

        if update_works:
            update_works_jsonl(result)

        # API 制限対策
        time.sleep(5)

    print(f"\n完了。出力先: {OUTPUT_DIR.relative_to(BASE)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="山本周五郎作品深層解析（試験版）")
    parser.add_argument(
        "--update-works",
        action="store_true",
        help="解析結果を works.jsonl にも反映する",
    )
    args = parser.parse_args()
    main(update_works=args.update_works)
