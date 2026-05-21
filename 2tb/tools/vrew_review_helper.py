#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TAIL_PATTERNS = (
    "のです。",
    "のでした。",
    "ました。",
    "である。",
    "だったのです。",
    "でした。",
)
CONNECTOR_ENDINGS = (
    "で、",
    "ので、",
    "とは、",
    "だが、",
    "ですが、",
    "けれど、",
    "けれども、",
    "から、",
)
TURNING_POINT_MARKERS = (
    "、――",
    "、だが",
    "、しかし",
    "、ところが",
    "、それに",
    "、すると",
    "、が、",
)
BASE_LINE_CHARS = 22
PREFERRED_MAX_LINES = 2
SOFT_OVERLONG_CHARS = BASE_LINE_CHARS * PREFERRED_MAX_LINES + 1  # 45
HIGH_PRIORITY_OVERLONG_CHARS = 60
MUST_SPLIT_CHARS = 70
TAIL_FRAGMENT_MAX_CHARS = 18
TAIL_FRAGMENT_STRICT_MAX_CHARS = 10
TAIL_FRAGMENT_PREFIX_RE = re.compile(r"^(?:て|で|に|を|が|は|も|と|へ|や|の|から|より|な|だ|た|れ|られ|して|され|き|けれ|ません|でした)")
SINGLE_KANJI_FRAGMENT_RE = re.compile(r"^[一-龠々]{1,2}[ぁ-んァ-ンー]*[。！？?!]?$")
TAIL_FRAGMENT_TERMINALS = set("。！？?!」』）】")
OKURIGANA_PREFIX_RE = re.compile(r"^[ぁ-んァ-ンー]+")


def compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def is_short_tail_fragment(text: str, prev_text: str = "") -> bool:
    clean = compact_text(text)
    if not clean or len(clean) > TAIL_FRAGMENT_MAX_CHARS:
        return False
    prev_clean = compact_text(prev_text)
    prev_last = prev_clean[-1] if prev_clean else ""
    starts_like_continuation = bool(TAIL_FRAGMENT_PREFIX_RE.match(clean))
    prev_not_terminal = bool(prev_last and prev_last not in TAIL_FRAGMENT_TERMINALS)
    if not prev_not_terminal:
        return False
    if len(clean) <= 2:
        return True
    if SINGLE_KANJI_FRAGMENT_RE.match(clean):
        return True
    if starts_like_continuation and len(clean) <= 8:
        return True
    if len(clean) <= TAIL_FRAGMENT_STRICT_MAX_CHARS and clean.endswith(TAIL_PATTERNS):
        return True
    return False


def okurigana_split_kind(prev_text: str, text: str) -> str:
    prev_clean = compact_text(prev_text)
    clean = compact_text(text)
    if not prev_clean or not clean:
        return ""
    prev_last = prev_clean[-1]
    if prev_last in TAIL_FRAGMENT_TERMINALS:
        return ""
    if not re.match(r"[一-龠々]", prev_last):
        return ""
    match = OKURIGANA_PREFIX_RE.match(clean)
    if not match:
        return ""
    prefix = match.group(0)
    if len(prefix) <= 2:
        return "okurigana_split_short"
    return "okurigana_split_long"


def issue_kinds(text: str, prev_text: str = "") -> list[str]:
    clean = compact_text(text)
    issues: list[str] = []
    if not clean:
        return issues
    if clean in {"」", "』", "）", ")", "】", "？", "！", "――"}:
        issues.append("quote_closer")
    if is_short_tail_fragment(clean, prev_text):
        issues.append("tail_fragment")
    if clean.endswith(CONNECTOR_ENDINGS):
        issues.append("dangling_connector")
    if any(marker in clean for marker in TURNING_POINT_MARKERS):
        issues.append("turning_point")
    okurigana_issue = okurigana_split_kind(prev_text, clean)
    if okurigana_issue:
        issues.append(okurigana_issue)
    length = len(clean)
    if length >= HIGH_PRIORITY_OVERLONG_CHARS:
        issues.append("high_priority_overlong")
    if length >= MUST_SPLIT_CHARS:
        issues.append("must_split")
    return issues


def review_blocks(text: str) -> list[dict]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    results: list[dict] = []
    for index, block in enumerate(blocks, start=1):
        prev_text = blocks[index - 2] if index > 1 else ""
        issues = issue_kinds(block, prev_text)
        if not issues:
            continue
        clean = compact_text(block)
        results.append(
            {
                "block_index": index,
                "issue_types": issues,
                "text": block,
                "char_count": len(clean),
                "prev_text": prev_text,
                "next_text": blocks[index] if index < len(blocks) else "",
            }
        )
    return results


def build_markdown_report(source_name: str, items: list[dict]) -> str:
    lines = [
        f"# Vrew Review: {source_name}",
        "",
        f"- flagged blocks: `{len(items)}`",
        f"- review focus: `tail_fragment / dangling_connector / turning_point / quote_closer / okurigana_split / 60字以上`",
        f"- display rule: `基本1行 / 最大2行 / 端数処理しきれない場合のみ3行許可`",
        f"- high priority overlong: `{HIGH_PRIORITY_OVERLONG_CHARS}字以上`",
        f"- must split: `{MUST_SPLIT_CHARS}字以上`",
        "",
    ]
    if not items:
        lines.append("No review items found.")
        lines.append("")
        return "\n".join(lines)
    for item in items:
        lines.extend(
            [
                f"## Block {item['block_index']}",
                "",
                f"- issue_types: `{', '.join(item['issue_types'])}`",
                f"- char_count: `{item['char_count']}`",
                f"- text: `{item['text']}`",
                f"- prev_text: `{item['prev_text']}`",
                f"- next_text: `{item['next_text']}`",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect Vrew subtitle blocks that likely need AI postprocessing.")
    parser.add_argument("input", help="Path to Vrew TXT")
    parser.add_argument("--json-out", help="Output JSON path")
    parser.add_argument("--md-out", help="Output Markdown path")
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    text = input_path.read_text(encoding="utf-8")
    items = review_blocks(text)

    payload = {
        "source": str(input_path),
        "flagged_count": len(items),
        "items": items,
    }

    if args.json_out:
        json_path = Path(args.json_out).expanduser()
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.md_out:
        md_path = Path(args.md_out).expanduser()
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(build_markdown_report(input_path.name, items), encoding="utf-8")

    print(json.dumps({"flagged_count": len(items)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
