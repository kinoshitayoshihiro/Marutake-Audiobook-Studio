#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT_DIR / "2tb" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from zenigata_search_page_builder_impl import (  # noqa: E402
    TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES,
    build_vrew_subtitle_text,
    read_text_best_effort,
    safe_filename,
    strip_aozora_text,
)


DEFAULT_RULES_PATH = ROOT_DIR / "tools" / "yamashukan_site_builder" / "data" / "subtitle_rules.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "2tb" / "reports" / "yamamoto_vrew"
CHAPTER_MARK_RE = re.compile(r"^[一二三四五六七八九十百上中下]+$")


def load_title_phrases(title: str, rules_path: Path) -> set[str]:
    if not rules_path.exists():
        return set()
    try:
        payload = json.loads(rules_path.read_text(encoding="utf-8"))
    except Exception:
        return set()
    works = payload.get("works") if isinstance(payload, dict) else None
    if not isinstance(works, dict):
        return set()
    phrases = set()
    for key, value in works.items():
        if str(key).strip() != title or not isinstance(value, dict):
            continue
        for phrase in value.get("no_break_phrases", []):
            clean = str(phrase).strip()
            if clean:
                phrases.add(clean)
    return phrases


def normalize_source_text(text: str, title: str) -> str:
    text_body = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    escaped_title = re.escape(title.strip())
    text_body = re.sub(
        rf"^\s*(?:山本周五郎\s*)?(?:{escaped_title}\s*)?(?:[一二三四五六七八九十百上中下]\s*)?",
        "",
        text_body,
        count=1,
    )
    lines = text_body.split("\n")
    cleaned_lines: list[str] = []
    stripped_title = title.strip()
    for line in lines:
        plain = line.replace("\u3000", "").strip()
        if not plain:
            cleaned_lines.append("")
            continue
        if plain in {"山本周五郎", stripped_title, f"山本周五郎{stripped_title}"}:
            continue
        if CHAPTER_MARK_RE.fullmatch(plain):
            continue
        cleaned_lines.append(plain)
    normalized = "\n".join(cleaned_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def collapse_blocks_for_vrew_import(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    collapsed_blocks: list[str] = []
    for block in re.split(r"\n\s*\n", normalized):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines:
            collapsed_blocks.append("".join(lines))
    return "\n\n".join(collapsed_blocks).strip()


def build_assets(
    title: str,
    source_path: Path,
    output_dir: Path,
    rules_path: Path,
    *,
    suffix: str,
    collapse_block_lines: bool,
    collapse_only: bool,
) -> dict[str, str]:
    source_text = read_text_best_effort(str(source_path))
    if collapse_only:
        subtitle_text = source_text
    else:
        cleaned = strip_aozora_text(source_text, title)
        cleaned = normalize_source_text(cleaned, title)

        title_phrases = load_title_phrases(title, rules_path)
        if title_phrases:
            TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES[title] = set(title_phrases)

        subtitle_text = build_vrew_subtitle_text(cleaned, title=title)
    if collapse_block_lines:
        subtitle_text = collapse_blocks_for_vrew_import(subtitle_text)

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{safe_filename(title)}{suffix}"
    txt_path = output_dir / f"{base_name}.txt"
    txt_path.write_text(subtitle_text, encoding="utf-8")
    return {
        "subtitle_text_name": txt_path.name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="山本周五郎作品のVrew向け字幕素材を生成します。")
    parser.add_argument("source_path", help="元本文のパス")
    parser.add_argument("--title", required=True, help="作品名")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="出力先ディレクトリ")
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="subtitle_rules.json のパス")
    parser.add_argument("--suffix", default="", help="出力ファイル名の接尾辞")
    parser.add_argument(
        "--collapse-block-lines",
        action="store_true",
        help="Vrew投入用に、各ブロック内の物理改行を潰して1クリップ1行へ畳み込みます。",
    )
    parser.add_argument(
        "--collapse-only",
        action="store_true",
        help="入力を既存のVrewテキストとして扱い、再分割せずにブロック内改行だけを潰します。",
    )
    args = parser.parse_args()

    source_path = Path(args.source_path).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    rules_path = Path(args.rules).expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"source not found: {source_path}")

    assets = build_assets(
        title=str(args.title).strip(),
        source_path=source_path,
        output_dir=output_dir,
        rules_path=rules_path,
        suffix=str(args.suffix),
        collapse_block_lines=bool(args.collapse_block_lines),
        collapse_only=bool(args.collapse_only),
    )

    print(output_dir / assets["subtitle_text_name"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())