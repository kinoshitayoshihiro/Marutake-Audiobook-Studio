#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path


def read_text_guess_encoding(path: Path) -> str:
    # 第3巻はcp932が正解だが、他巻と共通の安全策として推定読み込みを維持する
    for enc in ("utf-8", "utf-8-sig", "cp932", "shift_jis"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def is_blank(line: str) -> bool:
    return line.strip() == ""


def split_chapters_from_headings(text: str) -> list[dict]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    nonempty_indices = [i for i, line in enumerate(lines) if not is_blank(line)]
    if not nonempty_indices:
        return []

    main_title_index = nonempty_indices[0]

    headings: list[tuple[int, str]] = []

    # 第3巻は冒頭に「猿小僧」という非インデントの章題があり、他の章題形式と異なるため特別扱い
    if len(nonempty_indices) >= 2:
        i = nonempty_indices[1]
        candidate_raw = lines[i]
        candidate = candidate_raw.strip()
        looks_like_heading = (
            i > main_title_index
            and len(candidate) <= 12
            and not candidate.startswith("「")
            and i - 1 >= 0
            and is_blank(lines[i - 1])
            and i + 1 < len(lines)
            and is_blank(lines[i + 1])
        )
        if looks_like_heading:
            headings.append((i, candidate))

    def indented_heading_at(i: int) -> str | None:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            return None
        if i <= main_title_index:
            return None
        if i - 1 >= 0 and not is_blank(lines[i - 1]):
            return None
        if i + 1 < len(lines) and not is_blank(lines[i + 1]):
            return None

        # Count leading IDEOGRAPHIC SPACE (U+3000)
        lead = 0
        for ch in raw:
            if ch == "\u3000":
                lead += 1
            else:
                break

        if lead < 1:
            return None
        if stripped.startswith("「"):
            return None
        if len(stripped) > 30:
            return None
        return stripped

    for i in range(len(lines)):
        h = indented_heading_at(i)
        if h:
            headings.append((i, h))

    headings.sort(key=lambda x: x[0])

    if not headings:
        body = "\n".join(lines[main_title_index + 1 :]).strip("\n")
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
        / "納言恭平　七之助捕物帳　第三巻.txt"
    )
    out = workspace / "bookdata" / "七之助捕物帳_第03巻_十手黑星.json"

    text = read_text_guess_encoding(src)
    chapters = split_chapters_from_headings(text)

    data = {
        "title": "七之助捕物帳　第03巻　十手黑星",
        "author": "納言恭平",
        "genre": "Historical Fiction",
        "japanese_genre": "時代小説",
        "sub_genre": "捕物帳",
        "setting": "江戸の町（花川戸の岡っ引き稼業、怪盗『猿小僧』の探索、火事場での救出劇と捕物の人情葛藤）",
        "location": "花川戸、湯島天神下、京橋・日本橋界隈、町火消しの火事場、河岸（橋の上）",
        "time_period": "江戸時代",
        "keywords": [
            "七之助",
            "音吉",
            "猿小僧",
            "怪按摩",
            "御府内絵図",
            "十手",
            "火事場",
            "お雪",
            "人助け",
            "黒星（敗北）",
        ],
        "themes": [
            "追跡と知略",
            "正義と人情の板挟み",
            "悪党の中の善",
            "罪と救い",
            "名誉と後悔",
        ],
        "emotions": [
            "緊張",
            "驚き",
            "高揚",
            "切なさ",
            "ほろ苦さ",
        ],
        "synopsis": "江戸を騒がす怪盗『猿小僧』の新たな仕事に備え、花川戸の御用聞・七之助は御府内絵図から次の狙い場を割り出し、乾児の音吉と先回りの網を張る。笛を吹く怪按摩の怪しい動きの先で事件は火事場へ転じ、逃げ遅れた少女お雪を救うため、一人の男が炎へ飛び込む。見事な救出の直後、七之助はその“英雄”こそ猿小僧だと見抜くが、人助けに無我夢中だった相手へ十手を向けきれず、取り逃す黒星を喫する。人情と御用のあいだで揺れながらも、七之助は次こそ必ず猿小僧を御用にすると誓う。",
        "highlights": [
            "御府内絵図に事件地点を朱で囲い、次の狙いを推理する七之助の作戦",
            "『怪按摩』として人混みに紛れる猿小僧と、張り込みの駆け引き",
            "火事場の混乱での救出劇――炎の中へ飛び込む“英雄”の鮮烈さ",
            "猿小僧の正体判明と、御用聞として手が出せない七之助の苦い葛藤",
        ],
        "characters": [
            {
                "name": "七之助",
                "desc": "花川戸の御用聞。地図と勘で先回りし、猿小僧を追うが、人情の前で十手が鈍る。",
            },
            {
                "name": "音吉",
                "desc": "七之助の乾児。現場の匂いを嗅ぎ、親分の動きを支えるが、御用と情の線引きに悩む。",
            },
            {
                "name": "猿小僧",
                "desc": "江戸を騒がす怪盗。怪按摩に化けて潜み、火事場では少女を救う一面も見せる。",
            },
            {
                "name": "お雪",
                "desc": "火事で二階に逃げ遅れた少女。猿小僧に救い出され、物語の転回点となる。",
            },
            {
                "name": "お雪の母",
                "desc": "火事場で娘の名を叫び、半狂乱で飛び込もうとする母親。救出後に恩人へ感謝を捧げる。",
            },
        ],
        "glossary": [
            {
                "term": "猿小僧",
                "reading": "さるこぞう",
                "desc": "屋根や塀を猿のように渡ると噂される怪盗。現金だけを狙い、江戸を騒がす。",
            },
            {
                "term": "按摩",
                "reading": "あんま",
                "desc": "あん摩を生業とする者。作中では変装の手段として用いられる。",
            },
            {
                "term": "御用聞",
                "reading": "ごようきき",
                "desc": "町方の捜査に協力する岡っ引き。七之助の稼業。",
            },
            {
                "term": "十手",
                "reading": "じって",
                "desc": "捕物に用いる道具。御用聞が権威の印のように携える。",
            },
            {
                "term": "御府内絵図",
                "reading": "ごふないえず",
                "desc": "江戸市中の地図。七之助は過去の犯行地点を結んで次の狙いを推理する。",
            },
            {
                "term": "黒星",
                "reading": "くろぼし",
                "desc": "勝負の負けや失敗のこと。七之助は猿小僧を取り逃して“黒星”と感じる。",
            },
            {
                "term": "火事場",
                "reading": "かじば",
                "desc": "火災現場。混乱と人命救助が交錯し、捕物の判断を難しくする舞台となる。",
            },
        ],
        "authorProfile": {
            "name": "納言恭平",
            "desc": "捕物帳・時代小説を多く手掛けた作家。事件の謎解きに加え、江戸の市井の情と“御用”の矜持がぶつかる苦味を描く語り口に特徴がある。",
        },
        "chapters": chapters,
    }

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"chapters: {len(chapters)}")


if __name__ == "__main__":
    main()
