#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from convert_to_bookdata import (
    create_bookdata,
    parse_text_structure,
    read_text_auto_encoding,
)

ROOT = Path(__file__).resolve().parents[1]
BOOKDATA_DIR = ROOT / "bookdata" / "2_nagon"


@dataclass(frozen=True)
class WorkSpec:
    volume: int
    title: str
    source_path: Path
    file_name: str
    alt_keywords: tuple[str, ...] = ()


WORKS: tuple[WorkSpec, ...] = (
    WorkSpec(
        volume=46,
        title="宿借り仏",
        source_path=ROOT
        / "Reading_library"
        / "納言恭平著"
        / "納言恭平著　七之助捕物帳　宿借り仏 .txt",
        file_name="七之助捕物帳_第46巻_宿借り仏.json",
    ),
    WorkSpec(
        volume=49,
        title="石となった千両箱",
        source_path=ROOT
        / "Reading_library"
        / "納言恭平著"
        / "納言恭平著 七之助捕物帳  石となった千両箱.txt",
        file_name="七之助捕物帳_第49巻_石となった千両箱.json",
    ),
    WorkSpec(
        volume=50,
        title="緋牡丹狂い",
        source_path=ROOT
        / "Reading_library"
        / "納言恭平著"
        / "納言恭平著  七之助捕物帳　第五十話  緋牡丹狂い.txt",
        file_name="七之助捕物帳_第50巻_緋牡丹狂い.json",
    ),
    WorkSpec(
        volume=51,
        title="人喰い花",
        source_path=Path(
            "/Volumes/SSD-PUTA - Data/AudioBook/05_七之助捕物帳/51.人喰い花/納言恭平著　七之助捕物帳　人喰い花.txt"
        ),
        file_name="七之助捕物帳_第51巻_人喰い花.json",
        alt_keywords=("人食い花",),
    ),
    WorkSpec(
        volume=52,
        title="白鬼",
        source_path=Path(
            "/Volumes/SSD-PUTA - Data/AudioBook/05_七之助捕物帳/52.白鬼/納言恭平著　七之助捕物帳　白鬼.txt"
        ),
        file_name="七之助捕物帳_第52巻_白鬼.json",
    ),
    WorkSpec(
        volume=53,
        title="色魔殺し",
        source_path=Path(
            "/Volumes/SSD-PUTA - Data/AudioBook/05_七之助捕物帳/53.色魔ごろし/納言恭平著　七之助捕物帳　色魔ごろし .txt"
        ),
        file_name="七之助捕物帳_第53巻_色魔殺し.json",
        alt_keywords=("色魔ごろし",),
    ),
    WorkSpec(
        volume=54,
        title="金猫銀猫",
        source_path=Path(
            "/Volumes/SSD-PUTA - Data/AudioBook/05_七之助捕物帳/54.金猫銀猫/納言恭平著　七之助捕物帳　金猫銀猫 .txt"
        ),
        file_name="七之助捕物帳_第54巻_金猫銀猫.json",
    ),
    WorkSpec(
        volume=55,
        title="熊娘",
        source_path=Path(
            "/Volumes/SSD-PUTA - Data/AudioBook/05_七之助捕物帳/55.熊娘/納言恭平著　七之助捕物帳　熊娘 .txt"
        ),
        file_name="七之助捕物帳_第55巻_熊娘.json",
    ),
    WorkSpec(
        volume=56,
        title="仇討幽霊",
        source_path=Path(
            "/Volumes/SSD-PUTA - Data/AudioBook/05_七之助捕物帳/56.仇討ち幽霊/納言恭平著　七之助捕物帳　仇討幽霊 .txt"
        ),
        file_name="七之助捕物帳_第56巻_仇討幽霊.json",
        alt_keywords=("仇討ち幽霊",),
    ),
)

KANJI_DIGITS = {
    0: "",
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
}


def number_to_kanji(value: int) -> str:
    if value <= 10:
        return "十" if value == 10 else KANJI_DIGITS[value]
    if value < 20:
        return "十" + KANJI_DIGITS[value - 10]
    tens, ones = divmod(value, 10)
    return KANJI_DIGITS[tens] + "十" + KANJI_DIGITS[ones]


def build_meta(spec: WorkSpec) -> dict[str, object]:
    keywords = [
        "七之助",
        "納言恭平",
        "捕物帳",
        "江戸",
        spec.title,
        *spec.alt_keywords,
    ]
    return {
        "genre": "Historical Fiction",
        "japanese_genre": "捕物帳",
        "sub_genre": "ミステリー",
        "setting": "江戸の町",
        "location": "江戸",
        "time_period": "江戸時代",
        "keywords": keywords,
        "themes": ["謎解き", "人情", "因果応報"],
        "emotions": ["緊張", "驚き", "痛快"],
        "synopsis": "本文収録済み。あらすじは今後追記予定。",
        "highlights": [
            "本文を章構造つきで収録",
            "七之助捕物帳の後半欠番を補完",
            "詳細メタデータは今後追記可能",
        ],
        "characters": [
            {
                "name": "七之助",
                "desc": "花川戸の御用聞。事件の真相を追う主人公。",
            },
            {
                "name": "音吉",
                "desc": "七之助を支える乾児。聞き込みや探索を担う。",
            },
        ],
        "authorProfile": {
            "name": "納言恭平",
            "desc": "江戸市井の人情と謎解きを織り合わせた捕物帳作品を多く残した作家。",
        },
    }


def create_one(spec: WorkSpec) -> Path:
    if not spec.source_path.exists():
        raise FileNotFoundError(f"Source not found: {spec.source_path}")

    text = read_text_auto_encoding(spec.source_path)
    chapters = parse_text_structure(text)
    title = f"七之助捕物帳 第{number_to_kanji(spec.volume)}巻【{spec.title}】"
    bookdata = create_bookdata(
        title=title, author="納言恭平", chapters=chapters, meta=build_meta(spec)
    )

    output_path = BOOKDATA_DIR / spec.file_name
    output_path.write_text(
        json.dumps(bookdata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_path


def main() -> int:
    BOOKDATA_DIR.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for spec in WORKS:
        created.append(create_one(spec))

    print(f"created_count: {len(created)}")
    for path in created:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
