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

from vrew_subtitle_core import (  # noqa: E402
    TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES,
    build_vrew_subtitle_text,
    read_text_best_effort,
    safe_filename,
    strip_aozora_text,
)


DEFAULT_RULES_PATH = ROOT_DIR / "tools" / "yamashukan_site_builder" / "data" / "subtitle_rules.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "2tb" / "reports" / "yoshikawa_vrew"
CHAPTER_MARK_RE = re.compile(r"^(?:[一二三四五六七八九十百上中下]+|序|跋)$")
PART_STEM_RE = re.compile(r"^[0-9]{2}_[0-9]{2}\s+")


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
    lines = text_body.split("\n")
    cleaned_lines: list[str] = []
    stripped_title = title.strip()
    for index, line in enumerate(lines):
        plain = line.replace("\u3000", "").strip()
        if not plain:
            cleaned_lines.append("")
            continue
        if index < 12 and plain in {"吉川英治", stripped_title, f"吉川英治{stripped_title}"}:
            continue
        if CHAPTER_MARK_RE.fullmatch(plain):
            cleaned_lines.append(plain)
            continue
        cleaned_lines.append(line.strip())
    normalized = "\n".join(cleaned_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def stem_label(path: Path) -> str:
    stem = path.stem.strip()
    stem = PART_STEM_RE.sub("", stem)
    return stem or path.stem


def default_display_title(base_title: str, source_path: Path) -> str:
    part_label = stem_label(source_path)
    if part_label == base_title:
        return base_title
    return f"{base_title} {part_label}".strip()


def build_assets(
    *,
    title: str,
    source_path: Path,
    output_dir: Path,
    rules_path: Path,
    filename_base: str | None = None,
) -> dict[str, str | int]:
    source_text = read_text_best_effort(str(source_path))
    cleaned = strip_aozora_text(
        source_text,
        title,
        author_names=("吉川英治",),
    )
    cleaned = normalize_source_text(cleaned, title)

    title_phrases = load_title_phrases(title, rules_path)
    if title_phrases:
        TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES[title] = set(title_phrases)

    subtitle_text = build_vrew_subtitle_text(cleaned, title=title)

    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = safe_filename(filename_base or title)
    txt_path = output_dir / f"{base_name}.txt"

    txt_path.write_text(subtitle_text + "\n", encoding="utf-8")

    return {
        "source": str(source_path),
        "subtitle_text": str(txt_path),
    }


def build_many_assets(source_path: Path, title: str, output_dir: Path, rules_path: Path) -> list[dict[str, str | int]]:
    if source_path.is_file():
        return [
            build_assets(
                title=title,
                source_path=source_path,
                output_dir=output_dir,
                rules_path=rules_path,
                filename_base=default_display_title(title, source_path),
            )
        ]

    source_files = sorted(path for path in source_path.glob("*.txt") if path.is_file())
    if not source_files:
        raise FileNotFoundError(f"no txt files found: {source_path}")

    collection_output_dir = output_dir / safe_filename(title)
    results: list[dict[str, str | int]] = []
    for text_path in source_files:
        results.append(
            build_assets(
                title=title,
                source_path=text_path,
                output_dir=collection_output_dir,
                rules_path=rules_path,
                filename_base=text_path.stem,
            )
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="吉川英治作品のVrew向け字幕素材を生成します。")
    parser.add_argument("source_path", help="元本文のパス。ファイルでもディレクトリでも可")
    parser.add_argument("--title", help="作品名。省略時はファイル名またはディレクトリ名")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="出力先ディレクトリ")
    parser.add_argument("--rules", default=str(DEFAULT_RULES_PATH), help="subtitle_rules.json のパス")
    args = parser.parse_args()

    source_path = Path(args.source_path).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    rules_path = Path(args.rules).expanduser().resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"source not found: {source_path}")

    title = str(args.title or source_path.stem or source_path.name).strip()
    results = build_many_assets(source_path, title, output_dir, rules_path)
    print(json.dumps({"count": len(results), "items": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())