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
    """Split by headings like: '一、小名木川'.

    We keep the heading line as chapter.title and the following block as chapter.content.
    """

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    # Locate story title line "さかさ天一坊" (used as book title, not a chapter)
    story_title_idx = None
    for i, line in enumerate(lines[:250]):
        if line.strip() == "さかさ天一坊":
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
        # Avoid accidental matches in running text: require blank line around (common in these texts)
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

    src = workspace / "Reading_library" / "納言恭平著" / "納言恭平　七之助捕物帳　第五巻.txt"
    out = workspace / "bookdata" / "七之助捕物帳_第05巻_第5巻.json"

    text = read_text_guess_encoding(src)
    chapters = split_chapters_from_numbered_headings(text)

    data = {
            "title": "七之助捕物帳　第05巻　さかさ天一坊",
        "author": "納言恭平",
        "genre": "Historical Fiction",
        "japanese_genre": "時代小説",
        "sub_genre": "捕物帳",
        "setting": "江戸の市井（深川・森下町・小名木川周辺）。浪人・早川軍記が“大名の落胤”として担がれた狂言騒ぎと、娘を守ろうとする駕籠舁の策、さらに押借強盗（黒頭巾組）の影が交錯する。",
        "location": "深川（森下町・猿江町）、小名木川、菊川橋、御材木蔵周辺、横網町、四谷大木戸（回想）",
        "time_period": "江戸時代（幕末）",
        "keywords": [
            "七之助",
            "音吉",
            "さかさ天一坊",
            "早川軍記",
            "久保寺鍋之助",
            "落胤",
            "飯田侯",
            "小名木川",
            "身投げ",
            "辰吉",
            "黒頭巾組",
        ],
        "themes": [
            "虚実と狂言",
            "家族を守る決断",
            "人の弱さと後悔",
            "噂と真相",
            "市井の正義",
        ],
        "emotions": [
            "滑稽さ",
            "緊張",
            "哀愁",
            "驚き",
            "安堵",
        ],
        "synopsis": "花川戸の御用聞・七之助は、深川で起きた“さかさ天一坊”騒ぎに首を突っ込む。浪人・早川軍記が大名の落胤だと信じ込まされた一件の裏には、妹を悪浪人から救いたい駕籠舁・辰吉の思いと、得体の知れぬ侍・久保寺鍋之助の仕掛けた込み入った芝居があった。七之助は軍記の素振りを見張り、仕舞屋の母娘の秘密に踏み込みながら、狂言の筋書をほどいていく。さらに押借強盗（黒頭巾組）の余興的な挿話が、事件の背景に不穏な影を落とす。",
        "highlights": [
            "小名木川での身投げ騒ぎから始まる不穏な導入",
            "“さかさ天一坊”の噂を追って早川軍記へ迫る七之助",
            "仕舞屋の女おとくの叱責と、娘お半をめぐる真相",
            "駕籠舁・辰吉の告白で明かされる狂言の筋書",
            "黒頭巾組（青木弥太郎）に繋がる挿話で幕を引く終章",
        ],
        "characters": [
            {"name": "七之助", "desc": "花川戸の御用聞。噂話に見える“さかさ天一坊”騒ぎの裏を読み、狂言の筋を解きほぐす。"},
            {"name": "音吉", "desc": "七之助の乾児。聞き込みと張り込みで走り回り、親分の捜査を支える。"},
            {"name": "早川軍記", "desc": "深川森下町の浪人。女たちを食いものにしていたが、大名落胤の狂言に担がれ失墜する。"},
            {"name": "辰吉", "desc": "駕籠舁。妹お半を軍記の毒牙から救うため、相棒とともに狂言に加担する。"},
            {"name": "熊", "desc": "辰吉の相棒。十五夜の晩に小名木川で居合わせ、狂言の計画にも関わる。"},
            {"name": "おとく", "desc": "仕舞屋の女。娘お半の身を案じ、軍記を厳しくはねつける。"},
            {"name": "お半", "desc": "おとくの娘。軍記に惹かれて身を投げかけるが、周囲の動きで運命が変わる。"},
            {"name": "久保寺鍋之助", "desc": "得体の知れない侍。辰吉らに知恵を貸し、軍記を担ぐ込み入った芝居を仕掛ける。"},
        ],
        "glossary": [
            {"term": "天一坊", "reading": "てんいちぼう", "desc": "将軍の落胤を名乗ったとされる人物の名。作中では“落胤騒ぎ”の俗称として引かれる。"},
            {"term": "落胤", "reading": "らくいん", "desc": "身分ある人物の庶子。軍記が“飯田侯の落胤”として担がれる。"},
            {"term": "宗十郎頭巾", "reading": "そうじゅうろうずきん", "desc": "顔を隠す頭巾の一種。張り込みや忍びの場面で用いられる。"},
            {"term": "陸尺", "reading": "ろくしゃく", "desc": "駕籠かきや人足などの装束・呼称。狂言の芝居で扮装させられる。"},
            {"term": "押借", "reading": "おしがり", "desc": "名目を立てて押し入って金品を奪う強盗。黒頭巾組の荒事として語られる。"},
            {"term": "新徴組", "reading": "しんちょうぐみ", "desc": "幕末に編成された隊の一つ。作中では“くずれ”が徒党を組んだとされる。"},
            {"term": "牢問", "reading": "ろうもん", "desc": "牢内での取り調べ・拷問。黒頭巾組の首領の強情さを語るくだりで出る。"},
        ],
        "authorProfile": {
            "name": "納言恭平",
            "desc": "捕物帳・時代小説を多く手掛けた作家。江戸の市井を舞台に、噂や芝居めいた騒動を人情と推理で収束させる筋立てに特徴がある。",
        },
        "chapters": chapters,
    }

    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    print(f"chapters: {len(chapters)}")


if __name__ == "__main__":
    main()
