#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_VREW_NO_BREAK_PHRASES = {
    "親分",
    "岡っ引",
    "下っ引",
    "御用聞",
    "御用聞き",
}
TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES: dict[str, set[str]] = {}
DEFAULT_VREW_FORBIDDEN_LINE_START = set("、。，．？！!)]）｝」』】〕〉》ぁぃぅぇぉゃゅょァィゥェォャュョッー")
DEFAULT_VREW_FORBIDDEN_LINE_END = set("([（｛「『【〔〈《")
DEFAULT_VREW_LINE_OVERFLOW_ALLOWANCE = 4
DEFAULT_VREW_PARTICLE_ENDINGS = set("はがをにへとでやもかの")
TAIL_FRAGMENT_PATTERNS = (
    "のです。",
    "のでした。",
    "ました。",
    "である。",
    "だったのです。",
    "でした。",
)
TAIL_FRAGMENT_PREFIX_RE = re.compile(r"^(?:て|で|に|を|が|は|も|と|へ|や|の|な|だ|た|れ|られ|して|され|き|けれ|ません|でした)")
AOZORA_GAIJI_MARKER_RE = re.compile(r"\[GAIJI:([^\]]+)\]")
KNOWN_AOZORA_GAIJI = {
    "二の字点": "々",
    "「螢」の「虫」に代えて「火」": "熒",
    "「番＋おおざと」": "鄱",
    "「さんずい＋（扮のつくり／皿）」": "湓",
    "「てへん＋宛」": "捥",
    "「木＋霸」": "欛",
    "「革＋稻のつくり」": "鞱",
    "「怨」の「心」に代えて「皿」": "盌",
}


def read_text_best_effort(path_text: str) -> str:
    clean = str(path_text or "").strip()
    if not clean:
        return ""
    target = Path(clean)
    if not target.is_absolute():
        target = ROOT / clean
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16le", "utf-16be", "cp932", "shift_jis"):
        try:
            return target.read_text(encoding=encoding)
        except OSError:
            return ""
        except UnicodeDecodeError:
            continue
    try:
        return target.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def restore_known_aozora_gaiji(text: str) -> str:
    def replace_marker(match: re.Match[str]) -> str:
        payload = str(match.group(1) or "")
        description = payload.split("|", 1)[0].strip()
        return KNOWN_AOZORA_GAIJI.get(description, match.group(0))

    return AOZORA_GAIJI_MARKER_RE.sub(replace_marker, str(text or ""))


def strip_aozora_text(
    text: str,
    title: str,
    *,
    author_names: tuple[str, ...] = (),
    series_titles: tuple[str, ...] = (),
) -> str:
    clean = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    clean = restore_known_aozora_gaiji(clean)
    clean = re.sub(r"(?s)-{20,}\n.*?\n-{20,}", "", clean, count=1)
    clean = clean.replace("｜", "")
    for series_title in series_titles:
        if series_title:
            clean = clean.replace(series_title, "")
    clean = re.sub(r"《[^》]+》", "", clean)
    clean = re.sub(r"［＃[^\]]+］", "", clean)
    clean = re.split(r"(?m)^底本：", clean, maxsplit=1)[0]
    clean = re.split(r"(?m)^入力：", clean, maxsplit=1)[0]
    clean = re.split(r"入力、校正、制作にあたったのは", clean, maxsplit=1)[0]
    lines: list[str] = []
    header_skip = {title, *author_names, *series_titles}
    for index, raw_line in enumerate(clean.split("\n")):
        line = raw_line.strip()
        if index < 8 and line in header_skip:
            continue
        if re.fullmatch(r"【第[一二三四五六七八九十百]+回】", line):
            continue
        if re.fullmatch(r"[一二三四五六七八九十百]+", line):
            continue
        if line.startswith("青空文庫"):
            continue
        lines.append(raw_line)
    clean = "\n".join(lines)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()


def safe_filename(value: str, max_len: int = 80) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "_", value or "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        text = "untitled"
    return text[:max_len].strip().replace(" ", "_")


def contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3040-\u30ff\u3400-\u9fff]", str(text or "")))


def subtitle_phrase_pool(title: str = "") -> set[str]:
    pool = set(DEFAULT_VREW_NO_BREAK_PHRASES)
    if title:
        pool.update(TITLE_SPECIFIC_VREW_NO_BREAK_PHRASES.get(str(title).strip(), set()))
    return pool


def breaks_no_break_phrase(text: str, break_index: int, phrases: set[str] | None = None) -> bool:
    source = str(text or "")
    if not source or break_index <= 0 or break_index >= len(source):
        return False
    pool = subtitle_phrase_pool()
    if phrases:
        pool.update(str(phrase).strip() for phrase in phrases if str(phrase).strip())
    for phrase in pool:
        start = 0
        while True:
            found = source.find(phrase, start)
            if found < 0:
                break
            if found < break_index < found + len(phrase):
                return True
            start = found + len(phrase)
    return False


def choose_subtitle_break(
    text: str,
    target: int,
    *,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> int:
    clean = str(text or "")
    if len(clean) <= target:
        return len(clean)
    upper = min(len(clean) - 1, target + DEFAULT_VREW_LINE_OVERFLOW_ALLOWANCE)
    lower = max(1, target - 18)

    for punctuations in ("。！？?!", "、，；：…"):
        for index in range(upper, lower - 1, -1):
            if clean[index - 1] not in punctuations:
                continue
            right = clean[index:].lstrip()
            if right and right[0] not in DEFAULT_VREW_FORBIDDEN_LINE_START:
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
        if left_last in "。！？?!」』":
            score += 60
        elif left_last in "、，；：…":
            score += 28
        elif clean[index:index + 2] == "――":
            score += 20
        elif left_last in "）」』】":
            score += 12
        elif left_last in DEFAULT_VREW_PARTICLE_ENDINGS and left_prev and not re.match(r"[ぁ-んァ-ヶー]", left_prev):
            score += 22
        elif left_last in "てしで":
            score += 10
        if right_first in DEFAULT_VREW_FORBIDDEN_LINE_START:
            score -= 45
        if left_last in DEFAULT_VREW_FORBIDDEN_LINE_END:
            score -= 35
        if breaks_no_break_phrase(clean, index, phrases):
            score -= 60
        if contains_cjk(left_last + right_first):
            if re.match(r"[ぁ-んァ-ヶー]", left_last) and re.match(r"[ぁ-んァ-ヶー]", right_first):
                score -= 32
            if re.match(r"[一-龠々]", left_last) and re.match(r"[一-龠々]", right_first):
                score -= 18
            if re.match(r"[一-龠々ぁ-んァ-ヶー]", left_last) and re.match(r"[一-龠々ぁ-んァ-ヶー]", right_first):
                score -= 12
        if len(right) <= 3:
            score -= 12
        if len(left) <= 5:
            score -= 18
        if prefer_dialogue:
            if left_last in "、，。！？?!」』":
                score += 16
            if right_first in "とがもはをにへで":
                score -= 6
        if score > best_score:
            best_score = score
            best_index = index
    best_index = max(1, best_index)
    while best_index < len(clean) and clean[best_index] in DEFAULT_VREW_FORBIDDEN_LINE_START:
        best_index += 1
    return min(len(clean), best_index)


def rebalance_forbidden_line_starts(
    lines: list[str],
    *,
    width: int,
    max_lines: int,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> list[str]:
    if not lines:
        return []

    rebalanced = [str(line or "").strip() for line in lines if str(line or "").strip()]
    if not rebalanced:
        return []

    index = 1
    while index < len(rebalanced):
        current = rebalanced[index]
        if not current or current[0] not in DEFAULT_VREW_FORBIDDEN_LINE_START:
            index += 1
            continue

        moved = []
        cursor = 0
        while cursor < len(current) and current[cursor] in DEFAULT_VREW_FORBIDDEN_LINE_START:
            moved.append(current[cursor])
            cursor += 1

        if not moved:
            index += 1
            continue

        candidate_prev = f"{rebalanced[index - 1]}{''.join(moved)}"
        candidate_rest = current[cursor:].lstrip()

        if len(candidate_prev) <= width + DEFAULT_VREW_LINE_OVERFLOW_ALLOWANCE:
            rebalanced[index - 1] = candidate_prev
            if candidate_rest:
                rebalanced[index] = candidate_rest
                index += 1
            else:
                rebalanced.pop(index)
            continue

        merged_text = f"{rebalanced[index - 1]}{current}"
        wrapped = enforce_line_width(
            wrap_subtitle_line(
                merged_text,
                width=width,
                phrases=phrases,
                prefer_dialogue=prefer_dialogue,
            ),
            width=width,
            phrases=phrases,
            prefer_dialogue=prefer_dialogue,
        )
        wrapped = [line for line in wrapped if line]
        if fits_subtitle_block(wrapped, width, max_lines):
            rebalanced[index - 1:index + 1] = wrapped
            index = max(1, index - 1)
            continue

        index += 1

    return rebalanced


def wrap_subtitle_line(
    text: str,
    width: int = 22,
    *,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    chunks: list[str] = []
    remaining = clean
    while remaining:
        if len(remaining) <= width + DEFAULT_VREW_LINE_OVERFLOW_ALLOWANCE:
            chunks.append(remaining)
            break
        split_at = choose_subtitle_break(
            remaining,
            width,
            phrases=phrases,
            prefer_dialogue=prefer_dialogue,
        )
        chunk = remaining[:split_at].rstrip()
        remaining = remaining[split_at:].lstrip()
        if not chunk:
            chunk = remaining[:width]
            remaining = remaining[width:]
        chunks.append(chunk)
    return chunks


def subtitle_block_char_count(lines: list[str]) -> int:
    return sum(len(line) for line in lines)


def fits_subtitle_block(lines: list[str], width: int, max_lines: int) -> bool:
    return bool(lines) and len(lines) <= max_lines and subtitle_block_char_count(lines) <= width * max_lines


def enforce_line_width(
    lines: list[str],
    *,
    width: int,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> list[str]:
    normalized: list[str] = []
    for raw_line in lines:
        remaining = str(raw_line or "").strip()
        while remaining:
            if len(remaining) <= width + DEFAULT_VREW_LINE_OVERFLOW_ALLOWANCE:
                normalized.append(remaining)
                break
            split_at = choose_subtitle_break(
                remaining,
                width,
                phrases=phrases,
                prefer_dialogue=prefer_dialogue,
            )
            left = remaining[:split_at].rstrip()
            right = remaining[split_at:].lstrip()
            if not left or not right:
                split_at = min(len(remaining) - 1, width + DEFAULT_VREW_LINE_OVERFLOW_ALLOWANCE)
                left = remaining[:split_at].rstrip()
                right = remaining[split_at:].lstrip()
            normalized.append(left)
            remaining = right
    return normalized


def split_lines_to_blocks(lines: list[str], *, width: int, max_lines: int) -> list[str]:
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
        last_chars = subtitle_block_char_count(last_lines)
        if last_chars > min_tail_chars or len(prev_lines) <= 1 or len(last_lines) >= max_lines:
            break
        moved_line = prev_lines.pop()
        candidate_lines = [moved_line, *last_lines]
        if subtitle_block_char_count(candidate_lines) > max_block_chars:
            break
        blocks[-2] = "\n".join(prev_lines)
        blocks[-1] = "\n".join(candidate_lines)
        if not blocks[-2].strip():
            blocks.pop(-2)
            break
    return blocks


def is_short_tail_fragment_block(text: str, prev_text: str) -> bool:
    clean = re.sub(r"\s+", "", str(text or "")).strip()
    prev_clean = re.sub(r"\s+", "", str(prev_text or "")).strip()
    if not clean or not prev_clean or len(clean) > 10:
        return False
    if prev_clean[-1] in "。！？?!」』）】":
        return False
    if len(clean) <= 2:
        return True
    if clean.endswith(TAIL_FRAGMENT_PATTERNS):
        return True
    return bool(TAIL_FRAGMENT_PREFIX_RE.match(clean)) and clean[-1] in "。！？?!」』"


def split_long_subtitle_fragment(
    text: str,
    target_chars: int,
    *,
    phrases: set[str] | None = None,
    prefer_dialogue: bool = False,
) -> list[str]:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    fragments: list[str] = []
    remaining = clean
    while remaining:
        if len(remaining) <= target_chars:
            fragments.append(remaining)
            break
        split_at = choose_subtitle_break(
            remaining,
            target_chars,
            phrases=phrases,
            prefer_dialogue=prefer_dialogue,
        )
        fragment = remaining[:split_at].rstrip()
        remaining = remaining[split_at:].lstrip()
        if not fragment:
            fragment = remaining[:target_chars]
            remaining = remaining[target_chars:]
        fragments.append(fragment)
    return fragments


def split_for_subtitle_blocks(
    sentence: str,
    target_chars: int,
    *,
    phrases: set[str] | None = None,
) -> list[str]:
    clean = re.sub(r"\s+", " ", str(sentence or "")).strip()
    if not clean:
        return []
    fragments: list[str] = []
    quote_pattern = re.compile(r"[「『（【][^」』）】]*[」』）】]?")
    attribution_pattern = re.compile(r"^\s*(と[^。！？?!]*?[、。！？?!])")
    cursor = 0
    for match in quote_pattern.finditer(clean):
        prefix = clean[cursor:match.start()].strip()
        if prefix:
            prefix_parts = [part.strip() for part in re.split(r"(?<=[、，。！？])", prefix) if part.strip()]
            for part in prefix_parts or [prefix]:
                fragments.extend(split_long_subtitle_fragment(part, target_chars, phrases=phrases))
        quoted = match.group(0).strip()
        suffix_cursor = match.end()
        suffix_match = attribution_pattern.match(clean[suffix_cursor:])
        if suffix_match:
            quoted = f"{quoted}{suffix_match.group(1).strip()}"
            suffix_cursor += len(suffix_match.group(0))
        if quoted:
            fragments.extend(
                split_long_subtitle_fragment(
                    quoted,
                    target_chars,
                    phrases=phrases,
                    prefer_dialogue=True,
                )
            )
        cursor = suffix_cursor
    suffix = clean[cursor:].strip()
    if suffix:
        suffix_parts = [part.strip() for part in re.split(r"(?<=[、，。！？])", suffix) if part.strip()]
        for part in suffix_parts or [suffix]:
            fragments.extend(split_long_subtitle_fragment(part, target_chars, phrases=phrases))
    return [fragment for fragment in fragments if fragment]


def split_japanese_sentences(text: str) -> list[str]:
    normalized = re.sub(r"[ \t\u3000]+", " ", str(text or ""))
    normalized = re.sub(r"([」』])(?=[^\s」』、。，！？?!])", r"\1\n", normalized)
    chunks: list[str] = []
    current: list[str] = []
    index = 0
    quote_depth = 0
    paren_depth = 0

    def next_significant_char(start_index: int) -> str:
        cursor = start_index
        while cursor < len(normalized) and normalized[cursor].isspace():
            cursor += 1
        return normalized[cursor] if cursor < len(normalized) else ""

    while index < len(normalized):
        char = normalized[index]
        current.append(char)
        if char in "「『":
            quote_depth += 1
        elif char in "（【":
            paren_depth += 1
        if char in "。！？?!":
            if index + 1 < len(normalized) and normalized[index + 1] in "」』":
                index += 1
                current.append(normalized[index])
                if quote_depth > 0:
                    quote_depth -= 1
                if next_significant_char(index + 1) != "と":
                    chunk = "".join(current).strip()
                    if chunk:
                        chunks.append(chunk)
                    current = []
            elif index + 1 < len(normalized) and normalized[index + 1] in "）】":
                index += 1
                current.append(normalized[index])
                if paren_depth > 0:
                    paren_depth -= 1
                if quote_depth == 0 and paren_depth == 0 and next_significant_char(index + 1) != "と":
                    chunk = "".join(current).strip()
                    if chunk:
                        chunks.append(chunk)
                    current = []
            elif quote_depth == 0 and paren_depth == 0:
                chunk = "".join(current).strip()
                if chunk:
                    chunks.append(chunk)
                current = []
        elif char in "」』":
            if quote_depth > 0:
                quote_depth -= 1
            prev_char = normalized[index - 1] if index > 0 else ""
            next_char = normalized[index + 1] if index + 1 < len(normalized) else ""
            if prev_char not in "。！？?!" and (not next_char or next_char.isspace()) and next_significant_char(index + 1) != "と":
                chunk = "".join(current).strip()
                if chunk:
                    chunks.append(chunk)
                current = []
        elif char in "）】":
            if paren_depth > 0:
                paren_depth -= 1
            prev_char = normalized[index - 1] if index > 0 else ""
            next_char = normalized[index + 1] if index + 1 < len(normalized) else ""
            if quote_depth == 0 and paren_depth == 0 and prev_char in "。！？?!" and (not next_char or next_char.isspace()) and next_significant_char(index + 1) != "と":
                chunk = "".join(current).strip()
                if chunk:
                    chunks.append(chunk)
                current = []
        index += 1

    tail = "".join(current).strip()
    if tail:
        chunks.append(tail)

    sentences: list[str] = []
    for chunk in chunks:
        clean = re.sub(r"\s+", " ", chunk).strip()
        clean = re.sub(r"^[一二三四五六七八九十百上中下]+\s+", "", clean)
        clean = clean.strip()
        if not clean:
            continue
        if any(
            marker in clean
            for marker in (
                "テキスト中に現れる記号",
                "入力者注",
                "青空文庫",
                "ボランティア",
                "底本",
                "入力、校正、制作",
            )
        ):
            continue
        sentences.append(clean)

    return sentences


def postprocess_subtitle_blocks(
    blocks: list[str],
    *,
    width: int,
    max_lines: int,
    phrases: set[str] | None = None,
) -> list[str]:
    if not blocks:
        return []
    terminals = set("。！？?!」』）】")
    openers = set("「『（【")
    processed = [block.strip() for block in blocks if block and block.strip()]
    changed = True
    while changed:
        changed = False
        merged: list[str] = []
        index = 0
        while index < len(processed):
            current = processed[index]
            if index + 1 < len(processed):
                nxt = processed[index + 1]
                current_plain = current.replace("\n", "")
                next_plain = nxt.replace("\n", "")
                can_merge_short_tail = (
                    len(nxt.splitlines()) == 1
                    and len(next_plain) <= 12
                    and current_plain
                    and next_plain
                    and current_plain[-1] not in terminals
                    and next_plain[0] not in openers
                )
                if can_merge_short_tail:
                    combined = f"{current_plain}{next_plain}"
                    wrapped = enforce_line_width(
                        wrap_subtitle_line(
                            combined,
                            width=width,
                            phrases=phrases,
                            prefer_dialogue=combined.startswith(("「", "『")),
                        ),
                        width=width,
                        phrases=phrases,
                        prefer_dialogue=combined.startswith(("「", "『")),
                    )
                    if fits_subtitle_block(wrapped, width, max_lines):
                        merged.append("\n".join(wrapped))
                        index += 2
                        changed = True
                        continue
            merged.append(current)
            index += 1
        processed = merged

    rebalanced: list[str] = []
    for block in processed:
        if rebalanced and is_short_tail_fragment_block(block, rebalanced[-1]):
            combined = re.sub(r"\s+", "", rebalanced.pop()) + re.sub(r"\s+", "", block)
            merged_lines = enforce_line_width(
                wrap_subtitle_line(
                    combined,
                    width=width,
                    phrases=phrases,
                    prefer_dialogue=combined.startswith(("「", "『")),
                ),
                width=width,
                phrases=phrases,
                prefer_dialogue=combined.startswith(("「", "『")),
            )
            rebalanced.extend(split_lines_to_blocks(merged_lines, width=width, max_lines=max_lines))
            continue
        block_lines = rebalance_forbidden_line_starts(
            block.split("\n"),
            width=width,
            max_lines=max_lines,
            phrases=phrases,
            prefer_dialogue=block.startswith(("「", "『", "（")),
        )
        if fits_subtitle_block(block_lines, width, max_lines):
            rebalanced.append("\n".join(block_lines))
        else:
            rebalanced.extend(split_lines_to_blocks(block_lines, width=width, max_lines=max_lines))
    return rebalanced


def build_vrew_subtitle_text(
    text: str,
    line_width: int = 22,
    max_lines: int = 2,
    *,
    title: str = "",
) -> str:
    sentences = split_japanese_sentences(text)
    blocks: list[str] = []
    target_chars = line_width * max_lines
    phrase_pool = subtitle_phrase_pool(title)
    for sentence in sentences:
        pending = ""
        source_parts = split_for_subtitle_blocks(sentence, target_chars, phrases=phrase_pool) or [sentence]
        for fragment in source_parts:
            proposal = f"{pending}{fragment}" if pending else fragment
            prefer_dialogue = proposal.startswith(("「", "『", "（"))
            wrapped = enforce_line_width(
                wrap_subtitle_line(
                    proposal,
                    width=line_width,
                    phrases=phrase_pool,
                    prefer_dialogue=prefer_dialogue,
                ),
                width=line_width,
                phrases=phrase_pool,
                prefer_dialogue=prefer_dialogue,
            )
            if fits_subtitle_block(wrapped, line_width, max_lines):
                pending = proposal
                continue
            if pending:
                pending_dialogue = pending.startswith(("「", "『", "（"))
                cue_lines = enforce_line_width(
                    wrap_subtitle_line(
                        pending,
                        width=line_width,
                        phrases=phrase_pool,
                        prefer_dialogue=pending_dialogue,
                    ),
                    width=line_width,
                    phrases=phrase_pool,
                    prefer_dialogue=pending_dialogue,
                )
                if cue_lines:
                    blocks.extend(split_lines_to_blocks(cue_lines, width=line_width, max_lines=max_lines))
                pending = fragment
            else:
                fragment_dialogue = fragment.startswith(("「", "『", "（"))
                hard_wrapped = enforce_line_width(
                    wrap_subtitle_line(
                        fragment,
                        width=line_width,
                        phrases=phrase_pool,
                        prefer_dialogue=fragment_dialogue,
                    ),
                    width=line_width,
                    phrases=phrase_pool,
                    prefer_dialogue=fragment_dialogue,
                )
                blocks.extend(split_lines_to_blocks(hard_wrapped, width=line_width, max_lines=max_lines))
                pending = ""
        if pending:
            pending_dialogue = pending.startswith(("「", "『", "（"))
            cue_lines = enforce_line_width(
                wrap_subtitle_line(
                    pending,
                    width=line_width,
                    phrases=phrase_pool,
                    prefer_dialogue=pending_dialogue,
                ),
                width=line_width,
                phrases=phrase_pool,
                prefer_dialogue=pending_dialogue,
            )
            blocks.extend(split_lines_to_blocks(cue_lines, width=line_width, max_lines=max_lines))
    blocks = postprocess_subtitle_blocks(
        blocks,
        width=line_width,
        max_lines=max_lines,
        phrases=phrase_pool,
    )
    return "\n\n".join(block for block in blocks if block.strip()).strip()