from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path


def read_text_guess_encoding(path: Path) -> str:
    for enc in ("utf-8", "shift_jis", "cp932"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


KANJI_NUMS = [
    "一",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "十一",
]


def split_chapters(text: str):
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    chapter_indices: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if s in KANJI_NUMS:
            chapter_indices.append((i, s))

    if not chapter_indices:
        raise RuntimeError("章見出し（一、二…）が見つかりませんでした")

    chapters = []
    for idx, (start_i, title) in enumerate(chapter_indices):
        content_start = start_i + 1
        content_end = (
            chapter_indices[idx + 1][0]
            if idx + 1 < len(chapter_indices)
            else len(lines)
        )
        content_lines = lines[content_start:content_end]

        # Leading blank lines: keep minimal (preserve one if present)
        while content_lines and content_lines[0].strip() == "":
            content_lines.pop(0)
        # Trim trailing whitespace-only lines
        while content_lines and content_lines[-1].strip() == "":
            content_lines.pop()

        content = "\n".join(content_lines).rstrip("\n")
        chapters.append({"title": title, "content": content})

    return chapters


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    src = repo_root / "Reading_library" / "山本周五郎" / "山本周五郎　山茶花帖.txt"
    dst = repo_root / "bookdata" / "山茶花帖.json"

    text = read_text_guess_encoding(src)
    chapters = split_chapters(text)

    data = OrderedDict(
        [
            ("title", "山茶花帖"),
            ("author", "山本周五郎"),
            ("genre", "Historical Fiction"),
            ("japanese_genre", "時代小説"),
            ("sub_genre", "人情・恋愛短編"),
            (
                "setting",
                "城下町の料亭（芸妓の世界）と禅寺・持光寺の山茶花、藩政改革をめぐる対立",
            ),
            (
                "location",
                "城下町（地名不明）、松葉ヶ丘の持光寺、料亭『桃井』、川岸の料亭『西源』",
            ),
            ("time_period", "江戸時代（推定）"),
            (
                "keywords",
                [
                    "八重（八重次）",
                    "結城新一郎",
                    "山茶花",
                    "持光寺",
                    "桃井",
                    "西源",
                    "継ぎ棹三味線",
                    "城代家老",
                    "御改革",
                    "桑島儀兵衛",
                ],
            ),
            (
                "themes",
                [
                    "身分差と尊厳",
                    "自己犠牲と愛",
                    "貧しさの記憶",
                    "人に支えられて生きるという自覚",
                    "政治と私情の衝突",
                ],
            ),
            (
                "emotions",
                [
                    "切なさ",
                    "温かさ",
                    "緊張",
                    "救い",
                    "余韻",
                ],
            ),
            (
                "synopsis",
                "料亭『桃井』の抱え芸妓・八重は、酒癖の悪い客に形見の三味線を踏み折られる。場を収めた若侍・結城新一郎は、やがて亡母の継ぎ棹三味線を八重に託し、寺の山茶花を写す八重の素顔と、座敷の八重次という現実のあいだに静かに縁を結ぶ。だが新一郎は城代家老の跡取りで、藩政改革をめぐる対立の矢面に立たされていた。外伯父・桑島儀兵衛は二人の仲が政治の火種になると諭し、八重は愛する人を守るため身を退く決断をする。山茶花を写し続けた歳月の末、思いがけない形で再会と約束が訪れる人情短編。",
            ),
            (
                "highlights",
                [
                    "形見の三味線を踏み折られる衝撃の導入",
                    "持光寺の白い山茶花が“慰め”として繰り返し現れる描写",
                    "継ぎ棹三味線を託す新一郎の静かな優しさ",
                    "西源の離れで起こる対立と立合いの緊迫",
                    "桑島儀兵衛の『人は多くの者に支えられて生きる』という説諭",
                    "養女縁組を経た先に、約束が回収される終盤",
                ],
            ),
            (
                "characters",
                [
                    {
                        "name": "八重（八重次）",
                        "desc": "料亭『桃井』の抱え芸妓。幼少の貧しさを背負いながら、仮名文字や和学、絵を学び、持光寺の山茶花を写すことを心の支えにしている。結城新一郎と惹かれ合い、愛と身の振り方のはざまで揺れる。",
                    },
                    {
                        "name": "結城新一郎",
                        "desc": "『結城』と呼ばれる若侍。城代家老の跡取りで、人品と威があり静かな情の深さを持つ。八重に継ぎ棹三味線を託し、将来の約束を語るが、藩政改革をめぐる対立に巻き込まれる。",
                    },
                    {
                        "name": "井村",
                        "desc": "五人組の若侍の一人。酒癖が悪く、八重の三味線を踏み折るなど乱暴を働く。後に新一郎を取り巻く対立の一端としても現れる。",
                    },
                    {
                        "name": "桑島儀兵衛",
                        "desc": "新一郎の外伯父。西源での騒動を収め、八重に厳しく諭して身を退く決断を促す。冷酷に見えるが、社会の理と新一郎の立場を守ろうとする。",
                    },
                    {
                        "name": "桃井のおもん",
                        "desc": "料亭『桃井』の主婦（故人）。八重に仮名文字や生活の手ほどきをし、形見の三味線を残す。",
                    },
                    {
                        "name": "桃井の平助",
                        "desc": "料亭『桃井』の主。おもん亡き後、八重に目をかけるが細やかなところまでは気が回らない。",
                    },
                    {
                        "name": "松室春樹",
                        "desc": "七番町裏の歌の師匠。八重に伊勢物語などの講義をする。",
                    },
                    {
                        "name": "越梅の宗石（隠居）",
                        "desc": "大きな絹物問屋『越梅』の隠居で俳名は宗石。八重を養女に迎え、静かな生活の場を与える。",
                    },
                    {
                        "name": "もよ",
                        "desc": "宗石の妻女。明るく世話好きで、八重の新生活を支える。",
                    },
                ],
            ),
            (
                "glossary",
                [
                    {
                        "term": "山茶花",
                        "reading": "さざんか",
                        "desc": "冬に白い花を咲かせる花木。八重にとって慰めと記憶の象徴となる。",
                    },
                    {
                        "term": "芸妓",
                        "reading": "げいぎ",
                        "desc": "座敷で唄や三味線などを務める芸人の女性。",
                    },
                    {
                        "term": "料亭",
                        "reading": "りょうてい",
                        "desc": "料理と座敷遊びを提供する店。本文では『桃井』『西源』が舞台。",
                    },
                    {
                        "term": "三味線",
                        "reading": "しゃみせん",
                        "desc": "撥で弾く弦楽器。八重の形見の品であり、縁を結ぶ道具でもある。",
                    },
                    {
                        "term": "撥",
                        "reading": "ばち",
                        "desc": "三味線を弾くための道具。",
                    },
                    {
                        "term": "天神",
                        "reading": "てんじん",
                        "desc": "三味線の棹の先端部分。",
                    },
                    {
                        "term": "継ぎ棹",
                        "reading": "つぎざお",
                        "desc": "棹を分割して継げる三味線。持ち運びに便利で高価な品も多い。",
                    },
                    {
                        "term": "小判",
                        "reading": "こばん",
                        "desc": "江戸期の金貨。井村が投げ出すが、新一郎は受け取らせない。",
                    },
                    {
                        "term": "禅刹",
                        "reading": "ぜんさつ",
                        "desc": "禅宗の寺。持光寺は永平寺系の禅寺として描かれる。",
                    },
                    {
                        "term": "矢立硯",
                        "reading": "やたてすずり",
                        "desc": "携帯用の筆記具。八重が山茶花を写す際に用いる。",
                    },
                    {
                        "term": "白描",
                        "reading": "はくびょう",
                        "desc": "墨線だけで描く描法。八重は山茶花の写生を白描で描き溜める。",
                    },
                    {
                        "term": "部屋住",
                        "reading": "へやずみ",
                        "desc": "家督を継ぐ前の身分で、家中ではまだ役につかない立場。",
                    },
                    {
                        "term": "城代家老",
                        "reading": "じょうだいがろう",
                        "desc": "城を預かる重臣職。新一郎の家がその役目にある。",
                    },
                    {
                        "term": "御改革",
                        "reading": "ごかいかく",
                        "desc": "藩の政治改革。新旧勢力の対立の原因となる。",
                    },
                    {
                        "term": "中老",
                        "reading": "ちゅうろう",
                        "desc": "藩政の要職の一つ。作中では命令を伝える職として登場する。",
                    },
                    {
                        "term": "大寄合",
                        "reading": "おおよりあい",
                        "desc": "藩内の上級家臣の家格・役の一つとして語られる。",
                    },
                ],
            ),
            (
                "authorProfile",
                {
                    "name": "山本周五郎",
                    "desc": "1903年（明治36年）- 1967年（昭和42年）。山梨県生まれの小説家。本名・清水三十六。武士や庶民の情と矜持を、温かさと厳しさを併せ持つ筆で描く。本作は、芸妓の八重が『山茶花』を心の拠り所に、愛と身の分をめぐって決断する人情短編。",
                },
            ),
            ("chapters", chapters),
        ]
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Quick sanity output
    print(f"WROTE: {dst}")
    print(f"chapters: {len(chapters)}")


if __name__ == "__main__":
    main()
