#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path


def read_text_guess_encoding(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def is_blank(line: str) -> bool:
    return line.strip() == ""


def split_chapters_from_numbered_headings(text: str) -> list[dict]:
    """Split by headings like: '一、鬼瓦異变'."""

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Locate story title line "業平御殿" (used as book title, not a chapter)
    story_title_idx = None
    for i, line in enumerate(lines[:250]):
        if line.strip() == "業平御殿":
            story_title_idx = i
            break

    head_re = re.compile(r"^\s*(?P<title>[一二三四五六七八九十百千]+、[^\n]+)\s*$")

    def is_heading(i: int) -> bool:
        raw = lines[i]
        if raw.strip().startswith("■"):
            return False
        m = head_re.match(raw)
        if not m:
            return False
        prev_blank = True if i == 0 else is_blank(lines[i - 1])
        next_blank = True if i + 1 >= len(lines) else is_blank(lines[i + 1])
        if not (prev_blank and next_blank):
            return False
        title = m.group("title").strip()
        return 1 <= len(title) <= 30

    headings: list[tuple[int, str]] = []
    for i in range(len(lines)):
        if not is_heading(i):
            continue
        title = head_re.match(lines[i]).group("title").strip()  # type: ignore[union-attr]
        headings.append((i, title))

    if not headings:
        start = (story_title_idx + 1) if story_title_idx is not None else 0
        body = "\n".join(lines[start:]).strip("\n")
        return [{"title": "本文", "content": body}]

    chapters: list[dict] = []
    for idx, (start_i, title) in enumerate(headings):
        end_i = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        content_lines = lines[start_i + 1 : end_i]
        while content_lines and is_blank(content_lines[0]):
            content_lines.pop(0)
        while content_lines and is_blank(content_lines[-1]):
            content_lines.pop()
        chapters.append({"title": title, "content": "\n".join(content_lines).strip("\n")})

    return chapters


def main() -> None:
    workspace = Path(__file__).resolve().parents[1]

    src = workspace / "Reading_library" / "納言恭平著" / "納言恭平　七之助捕物帳　第六巻.txt"
    out = workspace / "bookdata" / "七之助捕物帳_第06巻_第6巻.json"

    text = read_text_guess_encoding(src)
    chapters = split_chapters_from_numbered_headings(text)

    data = {
        "title": "七之助捕物帳　第06巻　業平御殿",
        "author": "納言恭平",
        "genre": "Historical Fiction",
        "japanese_genre": "時代小説",
        "sub_genre": "捕物帳",
        "setting": "江戸・業平河岸の旗本秋月家（通称『業平御殿』）。棟飾りの鬼瓦盗難を端緒に、空屋敷での怪死体や島破り一味の影が絡み、鬼瓦に隠された小判の秘密へ辿り着く。",
        "location": "業平河岸（秋月屋敷）、横川、深川（八名川町）、中之郷瓦町（瓦焼場）、吾妻橋・回向院周辺",
        "time_period": "江戸時代（幕末）",
        "keywords": [
            "七之助",
            "音吉",
            "成瀬陣左衛門",
            "秋月隼人",
            "杵塚円四郎",
            "鬼瓦",
            "業平御殿",
            "河童の平三",
            "若葉",
            "銀釵",
            "小判",
        ],
        "themes": [
            "隠し財産と欲望",
            "因業の報い",
            "罪と贖い",
            "機転と張り込み",
            "市井の正義",
        ],
        "emotions": [
            "緊張",
            "驚き",
            "憤り",
            "哀愁",
            "痛快",
        ],
        "synopsis": "八丁堀与力・成瀬陣左衛門の口利きで、七之助は業平河岸の旗本秋月家から“表沙汰にできぬ”鬼瓦盗難の内密詮議を請け負う。屋敷の調べの最中、近くの空屋敷で島破り一味の男が殺され、手掛かりとなる平打の銀釵が見つかる。七之助は銀釵を餌に張り込みを仕掛け、現れた女――元吉原の花魁・若葉を追い詰める。やがて鬼瓦に隠されていた小判の秘密と、五年前の因縁（さんまの源次郎と秋月家の悪評）が明かされ、鬼瓦盗難と怪死体事件は意外な形で収束する。",
        "highlights": [
            "業平御殿の棟飾り“鬼瓦”盗難という奇妙な依頼",
            "空屋敷で見つかる怪死体と、瓦片の手掛かり",
            "平打の銀釵を使った張り込みと、若葉の浮上",
            "花川戸義勇隊の“火事騒ぎ”での捕り物芝居",
            "鬼瓦を砕いて現れる小判――秘密の暴露",
        ],
        "characters": [
            {"name": "七之助", "desc": "花川戸の御用聞。鬼瓦盗難の内密詮議を請け、銀釵を餌に真相へ迫る。"},
            {"name": "音吉", "desc": "七之助の乾児。銀釵を拾い、花川戸義勇隊を動かすなど場を回す。"},
            {"name": "成瀬陣左衛門", "desc": "八丁堀与力。秋月家の内密詮議を七之助に取り次ぐ。"},
            {"name": "杵塚円四郎", "desc": "秋月家用人。鬼瓦盗難の相談役として七之助に協力する。"},
            {"name": "秋月隼人", "desc": "業平河岸の旗本。因業な悪評のある家の主で、鬼瓦事件の中心にいる。"},
            {"name": "浜中茂平次", "desc": "廻り同心。空屋敷の殺人現場で検視を指揮する。"},
            {"name": "若葉", "desc": "元吉原稲葉楼の花魁。島破り一味として江戸に戻り、鬼瓦の秘密に関与する。"},
            {"name": "河童の平三", "desc": "島破りの手配犯の一人。空屋敷で殺され、事件の糸口となる。"},
        ],
        "glossary": [
            {"term": "鬼瓦", "reading": "おにがわら", "desc": "屋根の棟端を飾る瓦。秋月屋敷の象徴であり、事件の鍵となる。"},
            {"term": "釵", "reading": "さい", "desc": "髪飾りの一種。作中では平打の銀釵が手掛かりとして用いられる。"},
            {"term": "島破り", "reading": "しまやぶり", "desc": "流刑地からの脱走。作中では島脱けの一味が事件に関わる。"},
            {"term": "瓦焼場", "reading": "かわらやきば", "desc": "瓦を焼く窯場。過去の事件（追い込み）と鬼瓦の秘密を繋ぐ場所。"},
            {"term": "花川戸義勇隊", "reading": "はなかわどぎゆうたい", "desc": "音吉が隊長格となって若者たちをまとめた一団。捕り物の芝居で動く。"},
            {"term": "与力", "reading": "よりき", "desc": "町奉行配下の役人。成瀬陣左衛門がその一人として登場する。"},
            {"term": "小判", "reading": "こばん", "desc": "金貨。鬼瓦の中に隠されていた財の正体。"},
        ],
        "authorProfile": {
            "name": "納言恭平",
            "desc": "捕物帳・時代小説を多く手掛けた作家。奇談めいた導入（鬼瓦盗難）から、市井の機転と人情で決着させる筋立てに特徴がある。",
        },
        "chapters": chapters,
    }

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"chapters: {len(chapters)}")


if __name__ == "__main__":
    main()
