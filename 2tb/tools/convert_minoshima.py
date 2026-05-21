import json
import re
import os


def convert_minoshima():
    input_file = "tools/箕島の大喧嘩.txt"
    output_file = "bookdata/箕島の大喧嘩.json"

    # Read the file
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Clean lines
    lines = [line.rstrip() for line in lines]

    # Extract metadata
    # Line 0: 山本周五郎著　箕島の大喧嘩

    first_line = lines[0].strip()
    if "著" in first_line:
        parts = first_line.split("著")
        author = parts[0].strip()
        title = parts[1].strip()
        # Remove full-width space if present at start of title
        title = title.lstrip("　").lstrip()
    else:
        # Fallback
        author = "山本周五郎"
        title = "箕島の大喧嘩"

    print(f"Title: {title}")
    print(f"Author: {author}")

    # Parse content
    chapters = []
    current_section_title = ""
    current_chapter = None

    # Regex for chapter titles (Kanji numbers like その一, その二...)
    chapter_pattern = re.compile(r"^その[一二三四五六七八九十]+$")

    # Skip metadata lines
    start_index = 1

    for i in range(start_index, len(lines)):
        line = lines[i].rstrip()

        if not line.strip():
            continue

        # Check if it's a chapter title
        if chapter_pattern.match(line.strip()):
            # Save previous chapter if exists
            if current_chapter:
                current_chapter["content"] = "\n".join(current_chapter["content"])
                chapters.append(current_chapter)

            # Start new chapter
            # Combine section title with chapter title if section exists
            chapter_title = line.strip()
            if current_section_title:
                chapter_title = f"{current_section_title} {chapter_title}"

            current_chapter = {"title": chapter_title, "content": []}
            print(f"Found Chapter: {chapter_title}")

        # Check if it's a section title
        # Logic: Not a chapter title, not starting with space/quote
        elif (
            not line.startswith("　")
            and not line.startswith("「")
            and not line.startswith(" ")
        ):
            # It's likely a section title

            # Close current chapter if exists (though usually section starts after a chapter ends)
            if current_chapter:
                current_chapter["content"] = "\n".join(current_chapter["content"])
                chapters.append(current_chapter)
                current_chapter = None

            current_section_title = line.strip()
            print(f"Found Section: {current_section_title}")

        else:
            # Content
            if current_chapter:
                current_chapter["content"].append(line.strip())
            else:
                # Content before first chapter?
                pass

    # Add last chapter
    if current_chapter:
        current_chapter["content"] = "\n".join(current_chapter["content"])
        chapters.append(current_chapter)

    # Create final JSON structure
    book_data = {
        "title": title,
        "author": author,
        "synopsis": "甲州の貸元・藤生の文吉と沼田の紋兵衛は対立していた。文吉の子分・銀太や金太らが敵方へ殴り込みをかける中、「蒟蒻の清太」と呼ばれる臆病者の清太郎が紛れ込む。実は彼は凄腕の剣客であり、その正体には両家の因縁が関わっていた。ヤクザ同士の抗争と、その裏にある人間ドラマを描く。",
        "authorProfile": {
            "name": author,
            "desc": "庶民の哀歓や人間愛を描いた時代小説の名手。『樅ノ木は残った』『赤ひげ診療譚』など。",
        },
        "characters": [
            {
                "name": "蒟蒻の清太（清太郎）",
                "desc": "藤生一家の客分。普段は臆病者を装っているが、実は剣の達人。",
            },
            {
                "name": "小松村の銀太",
                "desc": "藤生一家の幹部。「向う不見」の異名を持つ暴れん坊。",
            },
            {"name": "横手の金太", "desc": "藤生一家の幹部。銀太の相棒的存在。"},
            {"name": "藤生の文吉", "desc": "甲州の貸元。温厚な性格。"},
            {"name": "沼田の紋兵衛", "desc": "文吉と対立する貸元。"},
            {"name": "お絹", "desc": "文吉の一人娘。清太に惹かれている。"},
            {
                "name": "櫓の権次",
                "desc": "沼田一家の貸元。藤生の縄張りを荒らす。",
            },
            {
                "name": "石谷道十郎",
                "desc": "沼田一家の用心棒。「血みどろ道十郎」と呼ばれる剣客。",
            },
        ],
        "chapters": chapters,
    }
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write JSON
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(book_data, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {output_file}")

    # Validation
    print("\n=== JSON Structure Validation ===")
    print(f"Title: {book_data['title']}")
    print(f"Author: {book_data['author']}")
    print(f"Chapters: {len(book_data['chapters'])}")
    if book_data["chapters"]:
        print(f"  First Chapter: {book_data['chapters'][0]['title']}")
        print(f"  Last Chapter: {book_data['chapters'][-1]['title']}")


if __name__ == "__main__":
    convert_minoshima()
