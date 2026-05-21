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

    # Find the first non-empty line as main title, but chapters start after that.
    nonempty_indices = [i for i, line in enumerate(lines) if not is_blank(line)]
    if not nonempty_indices:
        return []

    main_title_index = nonempty_indices[0]

    def heading_at(i: int) -> str | None:
        raw = lines[i]
        stripped = raw.strip()
        if not stripped:
            return None

        # Heuristic: headings are short, surrounded by blank lines, and visually indented.
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
        if len(stripped) > 12:
            return None
        return stripped

    # Collect heading indices
    headings: list[tuple[int, str]] = []
    for i in range(len(lines)):
        h = heading_at(i)
        if h:
            headings.append((i, h))

    if not headings:
        # Fallback: treat whole text (minus the very first title line) as a single chapter
        body = "\n".join(lines[main_title_index + 1 :]).strip("\n")
        return [{"title": "本文", "content": body}]

    chapters: list[dict] = []
    for idx, (start_i, title) in enumerate(headings):
        end_i = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        content_lines = lines[start_i + 1 : end_i]
        # Trim leading/trailing blank lines
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
        / "納言恭平　七之助捕物帳　第一巻.txt"
    )
    out = workspace / "bookdata" / "七之助捕物帳_第01巻_生きていた小町娘.json"

    text = read_text_guess_encoding(src)
    chapters = split_chapters_from_indented_headings(text)

    data = {
        "title": "七之助捕物帳　第01巻　生きていた小町娘",
        "author": "納言恭平",
        "genre": "Historical Fiction",
        "japanese_genre": "時代小説",
        "sub_genre": "捕物帳",
        "setting": "江戸の町（花川戸の岡っ引き稼業、船宿吉野屋、柳橋の芸者、墓地荒らし事件）",
        "location": "花川戸、今戸河岸（船宿・吉野屋）、谷中・妙心寺墓地、牛込岩戸町、柳橋、向島",
        "time_period": "江戸時代",
        "keywords": [
            "七之助",
            "音吉",
            "藤兵衛（木菟）",
            "銀釵",
            "墓場荒し",
            "吉野屋のお絹",
            "人形師・円谷貞山",
            "柳橋・君鶴",
            "妙心寺",
            "初めての御用",
        ],
        "themes": [
            "嫉妬と執着",
            "恋と破滅",
            "死者への執念",
            "責任と成長",
            "真相の解明",
        ],
        "emotions": ["緊張", "驚き", "戦慄", "哀愁", "痛快"],
        "synopsis": "花川戸の御用聞・七之助の乾児音吉は、今戸河岸の船宿『吉野屋』で亡くなった娘お絹の棺に納められたはずの銀釵を手に入れる。墓場荒しの噂が立つなか、八丁堀の手先気取りの御用聞・藤兵衛（木菟）が先回りして寺男を縛り上げるが、肝心の仏は墓から消えていた。七之助は『死骸まで持ち去る』異様さに色のもつれを嗅ぎ取り、人形師・円谷貞山の家へ踏み込む。隠し部屋で見つかったお絹そっくりの人形と、吊られた貞山の死体――。嫉妬が生んだ地獄絵の真相を、七之助は“御用はじめ”の一件として解き明かす。",
        "highlights": [
            "棺に入れたはずの銀釵が出回る導入の不穏さ",
            "墓から“仏ごと消える”怪事件と、物盗りでは説明できない違和感",
            "人形師の屋敷に隠されたからくり部屋と、お絹そっくりの人形",
            "嫉妬と恋の三角関係が暴く真相、七之助の初仕事としての決着",
        ],
        "characters": [
            {
                "name": "七之助",
                "desc": "花川戸の御用聞。名人又五郎の跡を継ぐが道楽者で、今回が“御用はじめ”となる。",
            },
            {
                "name": "音吉",
                "desc": "七之助の乾児。聞き込みと地の利に強く、銀釵の出所を突き止める。",
            },
            {
                "name": "藤兵衛（木菟）",
                "desc": "神田雉子町の御用聞。手柄を狙って先回りし、七之助と張り合う。",
            },
            {
                "name": "久米三",
                "desc": "藤兵衛の配下。音吉と因縁があり、銀釵をめぐって衝突する。",
            },
            {
                "name": "吉野屋善吉",
                "desc": "今戸河岸の船宿『吉野屋』主人。娘お絹を亡くし、墓荒しに怯える。",
            },
            {
                "name": "お絹",
                "desc": "吉野屋の娘。銀釵を愛用していたが急死し、事件の中心となる。",
            },
            {
                "name": "円谷貞山",
                "desc": "江戸でも一流とされる若い人形師。秘密の部屋と不審死が鍵になる。",
            },
            {
                "name": "君鶴",
                "desc": "柳橋の芸者。貞山とお絹をめぐる嫉妬が事件の背景にある。",
            },
        ],
        "glossary": [
            {
                "term": "銀釵",
                "reading": "ぎんさい",
                "desc": "髪に挿すかんざし。ここではお絹の形見で、事件の手がかりとなる。",
            },
            {
                "term": "御用聞",
                "reading": "ごようきき",
                "desc": "町方の捜査に協力する岡っ引き。",
            },
            {
                "term": "十手",
                "reading": "じって",
                "desc": "捕物に用いる道具。御用聞が権威の印のように携える。",
            },
            {
                "term": "捕縄",
                "reading": "とりなわ",
                "desc": "相手を絡め取るための縄。七之助の得意技として描かれる。",
            },
            {
                "term": "墓場荒し",
                "reading": "はかばあらし",
                "desc": "墓を掘り返して盗みや死体損壊を行う行為。",
            },
            {
                "term": "質流れ",
                "reading": "しちながれ",
                "desc": "質入れされた品が期限内に請け出されず、質屋の所有になること。",
            },
            {
                "term": "柳橋",
                "reading": "やなぎばし",
                "desc": "花街として知られる土地。君鶴の属する世界の舞台。",
            },
            {
                "term": "向島",
                "reading": "むこうじま",
                "desc": "隅田川東岸の行楽地。作中では花見の場面で余韻を結ぶ。",
            },
        ],
        "authorProfile": {
            "name": "納言恭平",
            "desc": "捕物帳・時代小説を多く手掛けた作家。江戸の市井と人情、推理の面白さを織り交ぜた語り口に特徴がある。",
        },
        "chapters": chapters,
    }

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"chapters: {len(chapters)}")


if __name__ == "__main__":
    main()
