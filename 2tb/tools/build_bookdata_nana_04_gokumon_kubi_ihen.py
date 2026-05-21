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


def split_chapters_from_section_headings(text: str) -> list[dict]:
    """Split by headings like: '■　　一、夏草'"""

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Locate story title line "獄門首異変" (used as book title, not a chapter)
    story_title_idx = None
    for i, line in enumerate(lines[:200]):
        if line.strip() == "獄門首異変":
            story_title_idx = i
            break

    # Headings: ■ + (kanji numerals) + 、 + title
    sec_re = re.compile(r"^\s*■\s*(?P<title>[一二三四五六七八九十百千]+、.*)\s*$")

    headings: list[tuple[int, str]] = []
    for i, raw in enumerate(lines):
        m = sec_re.match(raw)
        if not m:
            continue
        title = m.group("title").strip()
        headings.append((i, title))

    if not headings:
        # Fallback: treat whole text as one chapter (after story title if present)
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
        chapters.append(
            {"title": title, "content": "\n".join(content_lines).strip("\n")}
        )

    return chapters


def main() -> None:
    workspace = Path(__file__).resolve().parents[1]

    src = (
        workspace
        / "Reading_library"
        / "納言恭平著"
        / "納言恭平　七之助捕物帳　第四巻.txt"
    )
    out = workspace / "bookdata" / "七之助捕物帳_第04巻_獄門首異変.json"

    text = read_text_guess_encoding(src)
    chapters = split_chapters_from_section_headings(text)

    data = {
        "title": "七之助捕物帳　第04巻　獄門首異変",
        "author": "納言恭平",
        "genre": "Historical Fiction",
        "japanese_genre": "時代小説",
        "sub_genre": "捕物帳",
        "setting": "江戸の町（向島の辺鄙な土地での首の発見、与力屋敷からの依頼、矢場の聞き込み、鈴ヶ森の獄門台と寺の秘密）",
        "location": "向島（寺島村あたり）、花川戸、八丁堀与力屋敷、芝神明境内（矢場）、鈴ヶ森（獄門台）、谷中（松雲寺）",
        "time_period": "江戸時代",
        "keywords": [
            "七之助",
            "音吉",
            "獄門首",
            "生首",
            "小十郎",
            "成瀬陣左衛門",
            "矢場",
            "曙のお粂",
            "鈴ヶ森",
            "松雲寺",
        ],
        "themes": [
            "真相の追究",
            "裏社会の掟",
            "人情と正義",
            "失踪と追跡",
            "寺に隠された秘密",
        ],
        "emotions": [
            "不気味さ",
            "緊張",
            "驚き",
            "焦燥",
            "痛快",
        ],
        "synopsis": "向島の外れで生首が見つかり、花川戸の御用聞・七之助と乾児の音吉は嫌でも事件の渦中へ引き込まれる。与力・成瀬陣左衛門の屋敷から呼び出され、探索の糸口は“失踪した小十郎”と、獄門台（鈴ヶ森）周辺に出入りする怪しい影へ繋がっていく。矢場での聞き込みでは音吉が独壇場となり、矢場女・曙のお粂の動きが鍵を握ることが判明。やがて七之助はお粂を御用にし、谷中の松雲寺へと踏み込んで、寺に隠された秘密を暴き、獄門首異変のからくりを解き明かす。",
        "highlights": [
            "向島の荒地での“生首”発見が呼ぶ戦慄の導入",
            "与力成瀬陣左衛門の依頼で動き出す御用の筋立て",
            "芝神明の矢場での聞き込み――音吉の機転が光る場面",
            "曙のお粂の逮捕から松雲寺の秘密へ雪崩れ込む終盤",
        ],
        "characters": [
            {
                "name": "七之助",
                "desc": "花川戸の御用聞。生首騒ぎの背後を追い、矢場や寺へと足を運んで真相に迫る。",
            },
            {
                "name": "音吉",
                "desc": "七之助の乾児。大騒ぎで事件を持ち込みつつ、矢場での聞き込みでは主役級の働きを見せる。",
            },
            {
                "name": "成瀬陣左衛門",
                "desc": "八丁堀の与力。先代又五郎の縁もあり、七之助に探索の手を回して協力する。",
            },
            {
                "name": "曙のお粂",
                "desc": "矢場に出入りする女。事件の周辺をうろつき、七之助に御用となって松雲寺の秘密へ繋がる。",
            },
            {
                "name": "小十郎",
                "desc": "失踪した人物。生首騒ぎとともに名が挙がり、事件の鍵として追われる。",
            },
            {
                "name": "真海",
                "desc": "谷中松雲寺の若い住職。寺の内情が事件の終盤で焦点となる。",
            },
        ],
        "glossary": [
            {
                "term": "獄門",
                "reading": "ごくもん",
                "desc": "重罪人の首を晒す刑罰・処置。作中では獄門台周辺の出来事が事件名の由来となる。",
            },
            {
                "term": "生首",
                "reading": "なまくび",
                "desc": "切り落とされた首。事件の発端として発見され、騒動を呼ぶ。",
            },
            {
                "term": "与力",
                "reading": "よりき",
                "desc": "町奉行配下の役人。成瀬陣左衛門のように岡っ引きへ探索を依頼する立場。",
            },
            {
                "term": "矢場",
                "reading": "やば",
                "desc": "弓矢を射て遊ぶ場。人が集まるため聞き込みの舞台になる。",
            },
            {
                "term": "自身番",
                "reading": "じしんばん",
                "desc": "町内の警備・連絡拠点。引っ立てや詮議の拠点として登場する。",
            },
            {
                "term": "鈴ヶ森",
                "reading": "すずがもり",
                "desc": "江戸の処刑場の一つとして知られる場所。獄門台が事件の要所になる。",
            },
            {
                "term": "松雲寺",
                "reading": "しょううんじ",
                "desc": "谷中鰻縄手にある小寺。終盤で寺の秘密が暴かれる舞台。",
            },
        ],
        "authorProfile": {
            "name": "納言恭平",
            "desc": "捕物帳・時代小説を多く手掛けた作家。江戸の市井を舞台に、怪異めいた噂（獄門首）を現実のからくりへ着地させる推理と人情描写に特徴がある。",
        },
        "chapters": chapters,
    }

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"chapters: {len(chapters)}")


if __name__ == "__main__":
    main()
