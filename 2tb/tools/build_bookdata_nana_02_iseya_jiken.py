#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
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


def split_chapters_from_indented_headings(text: str) -> list[dict]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    nonempty_indices = [i for i, line in enumerate(lines) if not is_blank(line)]
    if not nonempty_indices:
        return []

    main_title_index = nonempty_indices[0]

    def heading_at(i: int) -> str | None:
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
        if len(stripped) > 20:
            return None
        return stripped

    headings: list[tuple[int, str]] = []
    for i in range(len(lines)):
        h = heading_at(i)
        if h:
            headings.append((i, h))

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
        / "納言恭平　七之助捕物帳　第二巻.txt"
    )
    out = workspace / "bookdata" / "七之助捕物帳_第02巻_伊勢屋事件.json"

    text = read_text_guess_encoding(src)
    chapters = split_chapters_from_indented_headings(text)

    data = {
        "title": "七之助捕物帳　第02巻　伊勢屋事件",
        "author": "納言恭平",
        "genre": "Historical Fiction",
        "japanese_genre": "時代小説",
        "sub_genre": "捕物帳",
        "setting": "江戸（神田・柳島の囲い屋敷、紙問屋伊勢屋の失踪と替え玉騒動、墓場荒しとは別種の陰謀）",
        "location": "神田永富町、柳島（妙見様近くの寮）、日本橋田所町（伊勢屋）、深川蛤町、染井（植木屋植半の離屋）",
        "time_period": "江戸時代",
        "keywords": [
            "七之助",
            "音吉",
            "伊勢屋吉兵衛",
            "番頭勝蔵",
            "柳島",
            "化狸",
            "替え玉",
            "双生児",
            "植木屋植半",
            "囲い寮",
        ],
        "themes": [
            "欲望と裏切り",
            "身代わり（替え玉）",
            "嫉妬と共犯",
            "弱みにつけ込む悪党",
            "真相の暴露",
        ],
        "emotions": ["不気味さ", "緊張", "驚き", "怒り", "痛快"],
        "synopsis": "柳島の寮で女主人お松が殺されたはずなのに、数日後に平然と生きている姿を見た――大工兼吉の証言から、七之助と音吉は“化狸”の噂の裏にある事件を追う。女中お糸の宿下り、紙問屋伊勢屋吉兵衛の失踪、そして番頭勝蔵の不可解な動きが一本に繋がり、寮では替え玉が使われていた疑いが濃くなる。やがて明らかになるのは、お松と瓜二つの女お竹、勝蔵と植木屋植半の共謀、そして身代わりを迫られ幽閉された吉兵衛の存在。七之助は闇夜の張り込みと一気の踏み込みで悪党を追い詰め、双生児のからくりを暴いて伊勢屋事件を決着させる。",
        "highlights": [
            "『殺されたはずの女が生きている』という化狸めいた導入",
            "伊勢屋主人失踪と、内密の探索依頼が絡む展開",
            "替え玉・双生児という仕掛けが解けていく推理の面白さ",
            "染井の離屋への踏み込みと、悪党確保の決着",
        ],
        "characters": [
            {
                "name": "七之助",
                "desc": "花川戸の御用聞。噂話の裏にある筋を嗅ぎ分け、現場を押さえて事件を解く。",
            },
            {
                "name": "音吉",
                "desc": "七之助の乾児。張り込みや聞き込みで動き回り、危ない目にもよく遭う。",
            },
            {
                "name": "兼吉",
                "desc": "神田永富町の若い大工。柳島の寮で殺しを目撃し、化狸の噂の火種となる。",
            },
            {
                "name": "お糸",
                "desc": "柳島の寮の女中。兼吉と懇になり、騒動の周辺に巻き込まれる。",
            },
            {
                "name": "お松",
                "desc": "柳島の寮の女主人（前身は羽織芸者）。事件の中心人物。",
            },
            {
                "name": "伊勢屋吉兵衛",
                "desc": "日本橋田所町の紙問屋伊勢屋の主人。失踪の裏で身代わりを迫られる。",
            },
            {
                "name": "勝蔵",
                "desc": "伊勢屋の番頭。探索依頼の顔で近づくが、裏で糸を引く悪党。",
            },
            {
                "name": "お竹",
                "desc": "お松に瓜二つの女。替え玉として寮に入り込み、共謀に加担する。",
            },
            {
                "name": "植半",
                "desc": "植木屋。お竹の情夫で、勝蔵と共謀して吉兵衛を追い詰める。",
            },
        ],
        "glossary": [
            {
                "term": "化狸",
                "reading": "ばけだぬき",
                "desc": "狸の化け術。作中では『死んだはずの女が生きている』噂の比喩として語られる。",
            },
            {
                "term": "囲い",
                "reading": "かこい",
                "desc": "囲い者（妾など）を住まわせる寮。事件の舞台となる。",
            },
            {
                "term": "替え玉",
                "reading": "かえだま",
                "desc": "本人の代わりに似た者を立てること。本作のトリックの核。",
            },
            {
                "term": "双生児",
                "reading": "そうせいじ",
                "desc": "双子。本作では瓜二つの見た目が計略に利用される。",
            },
            {
                "term": "張り込み",
                "reading": "はりこみ",
                "desc": "現場周辺で待ち伏せして動きを捕捉する捜査。",
            },
            {
                "term": "辻駕籠",
                "reading": "つじかご",
                "desc": "町中で客待ちする簡易な駕籠。移送に使われる。",
            },
            {
                "term": "自身番",
                "reading": "じしんばん",
                "desc": "町内の警備・連絡拠点。岡っ引きが協力を求める場所。",
            },
            {
                "term": "離屋",
                "reading": "はなれ",
                "desc": "母屋から離れた小屋。幽閉や密談の場として用いられる。",
            },
        ],
        "authorProfile": {
            "name": "納言恭平",
            "desc": "捕物帳・時代小説を多く手掛けた作家。江戸の市井を舞台に、噂と実相のズレを推理でほどく構成に定評がある。",
        },
        "chapters": chapters,
    }

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"chapters: {len(chapters)}")


if __name__ == "__main__":
    main()
