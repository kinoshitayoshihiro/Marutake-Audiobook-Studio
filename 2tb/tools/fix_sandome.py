import json
import os

file_path = (
    "/Volumes/2TB/Marutake AudioBook Library/bookdata/赤ひげ診療譚_三度目の正直.json"
)

# Data from user prompt
synopsis = "むじな長屋に暮らす、職人佐八。労咳で死も間際になりながら、長屋の住人への施しをやめない。佐八の度を超した献身は何に起因するのか？　下町に暮らす極貧な庶民の治療を通じて、成長していく見習医員の姿を、今回も描きだします——"

characters_raw = """
新出去定(赤ひげ)……小石川養生所の医長。
保本登……長崎へ遊学後、江戸へ戻り、小石川養生所の医員見習となる。
森半太夫……養生所の見習医員。登の同僚。赤ひげを尊敬している。
お雪……養生所の賄所で働く。森を慕っている。
津川玄三……養生所の医員。登と交替して養生所を出る。
保本良庵……登の父。町医者。
保本八重……登の母。
天野源伯……幕府の表御番医(法印)。登の後援者。
天野ちぐさ……登の許婚者。登の遊学中に他の男と駆落ちをする。
天野まさを……ちぐさの妹。
ゆみ……富豪の娘。狂気で人を殺め養生所の離れに隔離されている。
お杉……ゆみの付添い女中。
お初……養生所の女中
竹造……養生所の小者。
佐八……輻屋の職人。末期の労咳患者。
おなか……別れた佐八の妻
太吉……おなかの息子
治兵衛……むじな長屋の差配
おこと……治兵衛の妻
平吉……佐八の友人にして、むじな長屋の住人
お松……むじな長屋の住人
川本靭負……松平壱岐守の家老
岩橋隼人……用人
"""

glossary_raw = """
黙許……モッキョ・黙認
二丁……一丁は、約109メートル
定火消……明暦の大火を教訓につくられた防火組織。はじめは四組で、のちに増えたが、大名火消、町火消の整備とともに縮小、元の四組にもどる。
厚味……コウミ・味がこってりしておいしいこと。ごちそう。
貪食……ドンショク・がつがつ喰らうこと。むさぼりくうこと
塵芥……ジンカイ
義絶……ギゼツ・肉親との関係を断つこと
そぞろ……こころがおちつかない、そわそわすること
籠絡……ロウラク・巧みに手なずけて、自分の思い通りに操ること
因業……インゴウ・頑固で思いやりのないこと
二合五勺……コナカラ・一升の四分の一。0.45リットル
"""


def parse_characters(text):
    chars = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("……")
        if len(parts) >= 2:
            name = parts[0].strip()
            desc = parts[1].strip()
            chars.append({"name": name, "desc": desc})
        elif len(parts) == 1:
            # Handle lines that might not have the separator or are just names
            chars.append({"name": line.strip(), "desc": ""})
    return chars


def parse_glossary(text):
    gloss = []
    for line in text.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("……")
        if len(parts) >= 2:
            term = parts[0].strip()
            rest = parts[1].strip()
            # Try to split reading and desc by '・'
            subparts = rest.split("・")
            if len(subparts) >= 2:
                reading = subparts[0].strip()
                desc = "・".join(subparts[1:]).strip()
            else:
                reading = rest
                desc = ""  # Or maybe the whole thing is reading? Or desc?
                # Looking at input: "塵芥……ジンカイ" -> reading=ジンカイ, desc=""
                # "黙許……モッキョ・黙認" -> reading=モッキョ, desc=黙認

            gloss.append({"term": term, "reading": reading, "desc": desc})
    return gloss


# Read existing file
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Update data
data["synopsis"] = synopsis
data["characters"] = parse_characters(characters_raw)
data["glossary"] = parse_glossary(glossary_raw)

# Write back
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Updated {file_path}")
