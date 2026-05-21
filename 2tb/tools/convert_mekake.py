import json
import re
import os


def convert_mekake():
    input_file = "tools/妾の貞操.txt"
    output_file = "bookdata/妾の貞操.json"

    # Read the file
    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Clean lines
    lines = [line.rstrip() for line in lines]

    # Extract metadata
    # Assuming first few lines are title/author
    # Line 0: 錢形平次捕物控
    # Line 1: 妾の貞操
    # Line 2: 野村胡堂

    series_title = lines[0].strip()
    main_title = lines[1].strip()
    author = lines[2].strip()

    full_title = f"{series_title} {main_title}"

    print(f"Title: {full_title}")
    print(f"Author: {author}")

    # Parse content
    chapters = []
    current_chapter = None

    # Regex for chapter titles (Kanji numbers like 一, 二, 三...)
    chapter_pattern = re.compile(r"^[一二三四五六七八九十]+$")

    # Skip metadata lines
    start_index = 3

    for i in range(start_index, len(lines)):
        line = lines[i].strip()

        if not line:
            continue

        # Check if it's a chapter title
        if chapter_pattern.match(line):
            # Save previous chapter if exists
            if current_chapter:
                # Join content list into a single string with newlines
                current_chapter["content"] = "\n".join(current_chapter["content"])
                chapters.append(current_chapter)

            # Start new chapter
            current_chapter = {"title": line, "content": []}
            print(f"Found Chapter: {line}")
        else:
            # Add content to current chapter
            if current_chapter:
                current_chapter["content"].append(line)
            else:
                # Content before first chapter?
                pass

    # Add last chapter
    if current_chapter:
        current_chapter["content"] = "\n".join(current_chapter["content"])
        chapters.append(current_chapter)

    # Create final JSON structure
    book_data = {
        "title": main_title,
        "author": author,
        "synopsis": "人入稼業の加賀屋勘兵衛と妾のお関が寝る離れ屋に火が放たれた。雨戸の敷居には水が流され凍りついており、二人は焼き殺されそうになる。辛くも脱出した二人だが、今度は味噌汁に毒が。銭形平次は、勘兵衛の妻お角、お関の元許婚の雪五郎、そして店の若い者たちの中に犯人がいると睨み捜査を開始する。",
        "authorProfile": {
            "name": author,
            "desc": "代表作『銭形平次捕物控』で知られる小説家。音楽評論家としても活動し、あらえびすの筆名でも有名。",
        },
        "characters": [
            {
                "name": "銭形平次",
                "desc": "神田明神下の岡っ引き。投げ銭を得意とする名探偵。",
            },
            {"name": "八五郎", "desc": "平次の子分。通称ガラッ八。"},
            {"name": "加賀屋勘兵衛", "desc": "人入稼業の大親分。女好きで強欲。"},
            {"name": "お関", "desc": "勘兵衛の妾。元は小間物問屋の娘。"},
            {
                "name": "お角",
                "desc": "勘兵衛の妻。極度の潔癖症で夫を嫌っている。",
            },
            {"name": "雪五郎", "desc": "彫物師。お関の元許婚。"},
            {"name": "喜次郎", "desc": "加賀屋の若い者。35歳。"},
            {"name": "有松", "desc": "加賀屋の若い者。力自慢。"},
            {"name": "七之助", "desc": "加賀屋の若い者。23歳。"},
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
    convert_mekake()
