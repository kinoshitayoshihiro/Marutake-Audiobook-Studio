#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT_DIR / "2tb" / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from zenigata_search_page_builder_impl import (  # noqa: E402
    read_text_best_effort,
    safe_filename,
    strip_aozora_text,
    subtitle_phrase_pool,
    wrap_subtitle_line,
)


DEFAULT_OUTPUT_DIR = ROOT_DIR / "2tb" / "reports" / "zenigata_vrew" / "chatfix"
DEFAULT_LINE_WIDTH = 18
DEFAULT_MAX_LINES = 3
LINE_OVERFLOW_ALLOWANCE = 4
CHAPTER_MARK_RE = re.compile(r"^[一二三四五六七八九十百上中下]+$")
SMALL_KANA = set("ぁぃぅぇぉゃゅょァィゥェォャュョッー")
FORBIDDEN_LINE_START = set("、。，．？！!)]）｝」』】〕〉》")
FORBIDDEN_LINE_END = set("([（｛「『【〔〈《")
PARTICLE_ENDINGS = set("はがをにへとでやもかの")
TAIL_FRAGMENT_PATTERNS = (
    "のです。",
    "のでした。",
    "ました。",
    "でした。",
    "だつたのです。",
)
TAIL_FRAGMENT_PREFIX_RE = re.compile(r"^(?:て|で|に|を|が|は|も|と|へ|や|の|な|だ|た|れ|して|き|く)")


def normalize_source_text(text: str, title: str) -> str:
    text_body = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    escaped_title = re.escape(title.strip())
    text_body = re.sub(
        rf"^\s*(?:野村胡堂\s*)?(?:銭形平次捕物控\s*)?(?:{escaped_title}\s*)?(?:[一二三四五六七八九十百上中下]\s*)?",
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
        if plain in {"野村胡堂", "銭形平次捕物控", stripped_title, f"銭形平次捕物控{stripped_title}"}:
            continue
        if CHAPTER_MARK_RE.fullmatch(plain):
            continue
        cleaned_lines.append(plain)
    normalized = "\n".join(cleaned_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def flatten_block(block: str) -> str:
    return re.sub(r"\s+", "", str(block or ""))


def collapse_blocks_for_vrew_import(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    collapsed_blocks: list[str] = []
    for block in re.split(r"\n\s*\n", normalized):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if lines:
            collapsed_blocks.append("".join(lines))
    return "\n\n".join(collapsed_blocks).strip()


def split_mixed_narration_dialogue(block: str) -> list[str]:
    plain = flatten_block(block)
    if not plain:
        return []
    segments: list[str] = []
    cursor = 0
    for match in re.finditer(r"[「『][^」』]*[」』]", plain):
        prefix = plain[cursor:match.start()].strip()
        if prefix:
            segments.append(prefix)
        quoted = match.group(0).strip()
        if quoted:
            segments.append(quoted)
        cursor = match.end()
    suffix = plain[cursor:].strip()
    if suffix:
        segments.append(suffix)
    return segments or [plain]


def split_text_for_chatfix(text: str) -> list[str]:
    source = re.sub(r"\s+", " ", str(text or "")).strip()
    if not source:
        return []
    sentences: list[str] = []
    buf: list[str] = []
    quote_depth = 0
    open_quotes = set("「『（")
    close_quotes = set("」』）")
    terminals = set("。！？?!")
    for index, ch in enumerate(source):
        buf.append(ch)
        if ch in open_quotes:
            quote_depth += 1
        elif ch in close_quotes and quote_depth > 0:
            quote_depth -= 1
        next_ch = source[index + 1] if index + 1 < len(source) else ""
        if ch in terminals:
            if quote_depth == 0:
                sentence = "".join(buf).strip()
                if sentence:
                    sentences.append(sentence)
                buf = []
            elif next_ch in close_quotes:
                continue
        elif ch in close_quotes and buf:
            prev_ch = source[index - 1] if index > 0 else ""
            if prev_ch in terminals and quote_depth == 0:
                sentence = "".join(buf).strip()
                if sentence:
                    sentences.append(sentence)
                buf = []
    if buf:
        sentence = "".join(buf).strip()
        if sentence:
            sentences.append(sentence)
    return sentences


def choose_meaning_break(text: str, width: int) -> int:
    clean = str(text or "").strip()
    if len(clean) <= width:
        return len(clean)
    target = min(width, len(clean) - 1)
    upper = min(len(clean) - 1, width + LINE_OVERFLOW_ALLOWANCE)
    lower = max(1, target - 18)

    # Prefer a hard sentence boundary first, then a comma near the limit.
    for punctuations in ("。！？?!", "、，；："):
        for index in range(upper, lower - 1, -1):
            if clean[index - 1] not in punctuations:
                continue
            right = clean[index:].lstrip()
            if right and right[0] not in FORBIDDEN_LINE_START and right[0] not in SMALL_KANA:
                return index

    best_index = upper
    best_score = -10**9
    for index in range(lower, upper + 1):
        left = clean[:index].rstrip()
        right = clean[index:].lstrip()
        if not left or not right:
            continue
        left_last = left[-1]
        right_first = right[0]
        left_prev = left[-2] if len(left) >= 2 else ""
        score = -abs(len(left) - target) * 3
        if left_last in "。！？?!":
            score += 60
        elif left_last in "、，；：":
            score += 28
        elif left_last in PARTICLE_ENDINGS and left_prev and not re.match(r"[ぁ-んァ-ヶー]", left_prev):
            score += 22
        elif left_last in "てしで":
            score += 10
        if right_first in FORBIDDEN_LINE_START or right_first in SMALL_KANA:
            score -= 45
        if left_last in FORBIDDEN_LINE_END:
            score -= 35
        if re.match(r"[ぁ-んァ-ヶー]", left_last) and re.match(r"[ぁ-んァ-ヶー]", right_first):
            score -= 32
        elif re.match(r"[一-龠々]", left_last) and re.match(r"[一-龠々]", right_first):
            score -= 18
        elif re.match(r"[一-龠々ぁ-んァ-ヶー]", left_last) and re.match(r"[一-龠々ぁ-んァ-ヶー]", right_first):
            score -= 12
        if len(right) <= 3:
            score -= 12
        if len(left) <= 5:
            score -= 18
        if score > best_score:
            best_score = score
            best_index = index
    return max(1, best_index)


def enforce_line_width(lines: list[str], width: int) -> list[str]:
    normalized: list[str] = []
    for raw_line in lines:
        remaining = str(raw_line or "").strip()
        while remaining:
            if len(remaining) <= width + LINE_OVERFLOW_ALLOWANCE:
                normalized.append(remaining)
                break
            split_at = choose_meaning_break(remaining, width)
            left = remaining[:split_at].rstrip()
            right = remaining[split_at:].lstrip()
            if not left or not right:
                split_at = min(len(remaining) - 1, width + LINE_OVERFLOW_ALLOWANCE)
                left = remaining[:split_at].rstrip()
                right = remaining[split_at:].lstrip()
            normalized.append(left)
            remaining = right
    return normalized


def split_lines_to_blocks(lines: list[str], width: int, max_lines: int) -> list[str]:
    blocks: list[str] = []
    max_block_chars = width * max_lines
    current_lines: list[str] = []
    current_chars = 0
    for next_line in lines:
        next_chars = len(next_line)
        if current_lines and (
            len(current_lines) >= max_lines
            or current_chars + next_chars > max_block_chars
        ):
            blocks.append("\n".join(current_lines))
            current_lines = []
            current_chars = 0
        current_lines.append(next_line)
        current_chars += next_chars
    if current_lines:
        blocks.append("\n".join(current_lines))

    min_tail_chars = 12
    while len(blocks) >= 2:
        last_lines = blocks[-1].split("\n")
        prev_lines = blocks[-2].split("\n")
        last_chars = sum(len(line) for line in last_lines)
        if last_chars > min_tail_chars or len(prev_lines) <= 1 or len(last_lines) >= max_lines:
            break
        moved_line = prev_lines.pop()
        candidate_lines = [moved_line, *last_lines]
        candidate_chars = sum(len(line) for line in candidate_lines)
        if candidate_chars > max_block_chars:
            break
        blocks[-2] = "\n".join(prev_lines)
        blocks[-1] = "\n".join(candidate_lines)
        if not blocks[-2].strip():
            blocks.pop(-2)
            break
    return blocks


def is_short_tail_fragment_block(text: str, prev_text: str) -> bool:
    clean = flatten_block(text)
    prev_clean = flatten_block(prev_text)
    if not clean or not prev_clean or len(clean) > 10:
        return False
    if prev_clean[-1] in "。！？?!」』）】":
        return False
    if len(clean) <= 2:
        return True
    if clean.endswith(TAIL_FRAGMENT_PATTERNS):
        return True
    return bool(TAIL_FRAGMENT_PREFIX_RE.match(clean)) and clean[-1] in "。！？?!」』"


def rebalance_tail_fragments(blocks: list[str], width: int, max_lines: int) -> list[str]:
    if not blocks:
        return []
    rebalanced: list[str] = []
    for block in blocks:
        if rebalanced and is_short_tail_fragment_block(block, rebalanced[-1]):
            merged = flatten_block(rebalanced.pop()) + flatten_block(block)
            merged_lines = enforce_line_width([merged], width=width)
            rebalanced.extend(split_lines_to_blocks(merged_lines, width=width, max_lines=max_lines))
            continue
        rebalanced.append(block)
    return rebalanced


def wrap_narration_block(text: str, width: int, max_lines: int) -> list[str]:
    clean = str(text or "").strip()
    if not clean:
        return []
    if len(clean) <= width:
        return [clean]
    if len(clean) <= width * max_lines:
        split_at = choose_meaning_break(clean, width)
        left = clean[:split_at].rstrip()
        right = clean[split_at:].lstrip()
        if left and right:
            return [left, right]
    return wrap_subtitle_line(clean, width=width)


def wrap_dialogue_block(text: str, width: int) -> list[str]:
    clean = str(text or "").strip()
    if not clean:
        return []
    if len(clean) <= width:
        return [clean]
    lines: list[str] = []
    remaining = clean
    while remaining:
        if len(remaining) <= width:
            lines.append(remaining)
            break
        split_at = choose_meaning_break(remaining, width)
        left = remaining[:split_at].rstrip()
        right = remaining[split_at:].lstrip()
        if not left or not right:
            lines.extend(wrap_subtitle_line(remaining, width=width, prefer_dialogue=True))
            break
        lines.append(left)
        remaining = right
    return lines


def render_fragment_blocks(
    fragment: str,
    *,
    width: int,
    max_lines: int,
    phrases: set[str],
) -> list[str]:
    clean = str(fragment or "").strip()
    if not clean:
        return []
    prefer_dialogue = clean.startswith(("「", "『"))
    lines = (
        wrap_dialogue_block(clean, width=width)
        if prefer_dialogue
        else wrap_narration_block(clean, width=width, max_lines=max_lines)
    )
    if not lines:
        return []
    lines = enforce_line_width(lines, width=width)
    return split_lines_to_blocks(lines, width=width, max_lines=max_lines)


def semantic_chatfix_subtitle_text(
    text: str,
    *,
    title: str,
    width: int = 22,
    max_lines: int = 2,
) -> str:
    phrases = subtitle_phrase_pool(title)
    blocks: list[str] = []
    for sentence in split_text_for_chatfix(text):
        for piece in split_mixed_narration_dialogue(sentence):
            blocks.extend(
                render_fragment_blocks(
                    piece,
                    width=width,
                    max_lines=max_lines,
                    phrases=phrases,
                )
            )
    blocks = rebalance_tail_fragments(blocks, width=width, max_lines=max_lines)
    return "\n\n".join(block for block in blocks if block.strip()).strip()


def build_assets(
    title: str,
    source_path: Path,
    output_dir: Path,
    *,
    suffix: str,
    width: int,
    max_lines: int,
    collapse_block_lines: bool,
) -> Path:
    source_text = read_text_best_effort(str(source_path))
    cleaned = strip_aozora_text(source_text, title)
    cleaned = normalize_source_text(cleaned, title)
    subtitle_text = semantic_chatfix_subtitle_text(
        cleaned,
        title=title,
        width=width,
        max_lines=max_lines,
    )
    if collapse_block_lines:
        subtitle_text = collapse_blocks_for_vrew_import(subtitle_text)
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = f"{safe_filename(title)}{suffix}"
    txt_path = output_dir / f"{base_name}.txt"
    txt_path.write_text(subtitle_text, encoding="utf-8")
    return txt_path


def main() -> int:
    parser = argparse.ArgumentParser(description="銭形平次作品のChat後工程版字幕素材を生成します。")
    parser.add_argument("source_path", help="元本文のパス")
    parser.add_argument("--title", required=True, help="作品名")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="出力先ディレクトリ")
    parser.add_argument("--suffix", default="_chatfix_v4", help="出力ファイル名の接尾辞")
    parser.add_argument("--width", type=int, default=DEFAULT_LINE_WIDTH, help="1行の目安文字数")
    parser.add_argument("--max-lines", type=int, default=DEFAULT_MAX_LINES, help="1ブロックの最大行数")
    parser.add_argument(
        "--collapse-block-lines",
        action="store_true",
        help="Vrew投入用に、各ブロック内の物理改行を潰して1クリップ1行へ畳み込みます。",
    )
    args = parser.parse_args()

    source_path = Path(args.source_path).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"source not found: {source_path}")

    txt_path = build_assets(
        title=str(args.title).strip(),
        source_path=source_path,
        output_dir=output_dir,
        suffix=str(args.suffix),
        width=int(args.width),
        max_lines=int(args.max_lines),
        collapse_block_lines=bool(args.collapse_block_lines),
    )
    print(txt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
