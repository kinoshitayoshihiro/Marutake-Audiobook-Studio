#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

from vrew_review_helper import build_markdown_report, review_blocks


MINIMAL_TAIL_PATTERNS = (
    "のです。",
    "のでした。",
    "ました。",
    "である。",
    "だったのです。",
    "でした。",
)
MINIMAL_DANGLING_CONNECTORS = (
    "で、",
    "ので、",
    "とは、",
    "だが、",
    "ですが、",
    "けれど、",
    "けれども、",
    "から、",
)

BASE_LINE_CHARS = 22
FORBIDDEN_LINE_START_CHARS = "、。，．・：；)]｝〕〉》」』】ぁぃぅぇぉっゃゅょァィゥェォッャュョー"
FORBIDDEN_LINE_END_CHARS = "([｛〔〈《「『【"


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_source_line(raw_line: str) -> str:
    line = unicodedata.normalize("NFKC", raw_line or "")
    line = line.replace("\ufeff", "")
    # Strip Aozora-style inline editorial notes before line splitting.
    line = re.sub(r"\[\#.*?\]", "", line)
    line = re.sub(r"［#.*?］", "", line)
    line = re.sub(r"［＃.*?］", "", line)
    if re.fullmatch(r"\s*[-*_]{3,}\s*", line):
        return ""
    line = re.sub(r"^\s{0,3}#{1,6}\s*", "", line)
    return line.rstrip()


def choose_break_index(text: str, width: int = BASE_LINE_CHARS) -> int:
    if len(text) <= width:
        return len(text)
    window_start = max(1, width - 8)
    window_end = min(len(text) - 1, width + 8)
    best_index = width
    best_score = -10**9
    for index in range(window_start, window_end + 1):
        left = text[index - 1]
        right = text[index] if index < len(text) else ""
        score = -abs(width - index) * 2
        if left in "。！？":
            score += 40
        elif left in "、，":
            score += 24
        elif left in "」』】":
            score += 18
        elif left in "―—…":
            score += 10
        if right in FORBIDDEN_LINE_START_CHARS:
            score -= 20
        if left in FORBIDDEN_LINE_END_CHARS:
            score -= 20
        if re.match(r"[一-龠々ぁ-んァ-ンー]", left) and re.match(r"[一-龠々ぁ-んァ-ンー]", right):
            score -= 10
        if score > best_score:
            best_score = score
            best_index = index
    return max(1, min(len(text), best_index))


def split_clip_candidate(line: str, width: int = BASE_LINE_CHARS) -> list[str]:
    clean = compact_text(line)
    if not clean:
        return []
    chunks: list[str] = []
    current = clean
    while current:
        if len(current) <= width:
            chunks.append(current)
            break
        break_at = choose_break_index(current, width=width)
        chunks.append(current[:break_at].rstrip())
        current = current[break_at:].lstrip()
    return [chunk for chunk in chunks if chunk]


def is_minimal_tail_fragment(text: str) -> bool:
    clean = compact_text(text)
    if not clean:
        return False
    if clean in {"」", "』", "）", ")", "】", "？", "！", "――"}:
        return True
    if len(clean) <= 10 and clean.endswith(("。", "」", "』")):
        return True
    if len(clean) <= 16 and clean.endswith(MINIMAL_TAIL_PATTERNS):
        return True
    if clean in MINIMAL_TAIL_PATTERNS:
        return True
    if len(clean) <= 16 and clean.endswith(MINIMAL_DANGLING_CONNECTORS):
        return True
    return False


def merge_minimal_candidates(candidates: list[str]) -> list[str]:
    merged: list[str] = []
    for candidate in candidates:
        clean = compact_text(candidate)
        if not clean:
            continue
        if merged and is_minimal_tail_fragment(clean):
            merged[-1] = f"{merged[-1]}{clean}"
            continue
        merged.append(clean)
    return merged


def build_vrew_text(text: str) -> str:
    candidates: list[str] = []
    for raw_line in str(text or "").splitlines():
        normalized_line = normalize_source_line(raw_line)
        if not normalized_line.strip():
            continue
        for chunk in split_clip_candidate(normalized_line, width=BASE_LINE_CHARS):
            candidates.append(chunk)
    blocks = merge_minimal_candidates(candidates)
    return "\n\n".join(block for block in blocks if block.strip()).strip()


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".vrew.txt")


def default_review_json_path(output_path: Path) -> Path:
    return output_path.with_suffix(".review.json")


def default_review_md_path(output_path: Path) -> Path:
    return output_path.with_suffix(".review.md")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build minimal Vrew TXT and review reports from source text."
    )
    parser.add_argument("input", help="Path to source text or markdown")
    parser.add_argument(
        "-o",
        "--output",
        help="Output Vrew TXT path. Defaults to <input>.vrew.txt",
    )
    parser.add_argument(
        "--skip-review",
        action="store_true",
        help="Do not emit review JSON/Markdown reports.",
    )
    parser.add_argument("--json-out", help="Explicit review JSON output path")
    parser.add_argument("--md-out", help="Explicit review Markdown output path")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser() if args.output else default_output_path(input_path)

    source_text = input_path.read_text(encoding="utf-8")
    vrew_text = build_vrew_text(source_text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(vrew_text + "\n", encoding="utf-8")

    result: dict[str, object] = {
        "input": str(input_path),
        "output": str(output_path),
    }

    if not args.skip_review:
        items = review_blocks(vrew_text)
        json_out = Path(args.json_out).expanduser() if args.json_out else default_review_json_path(output_path)
        md_out = Path(args.md_out).expanduser() if args.md_out else default_review_md_path(output_path)
        json_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(
            json.dumps(
                {
                    "source": str(output_path),
                    "flagged_count": len(items),
                    "items": items,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        md_out.write_text(build_markdown_report(output_path.name, items), encoding="utf-8")
        result["review_json"] = str(json_out)
        result["review_md"] = str(md_out)
        result["flagged_count"] = len(items)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
