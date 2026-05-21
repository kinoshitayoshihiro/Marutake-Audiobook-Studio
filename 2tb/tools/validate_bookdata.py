#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path

EXPECTED_KEYS = [
    "title",
    "author",
    "genre",
    "japanese_genre",
    "sub_genre",
    "setting",
    "location",
    "time_period",
    "keywords",
    "themes",
    "emotions",
    "synopsis",
    "highlights",
    "characters",
    "glossary",
    "authorProfile",
    "chapters",
]


def fail(message: str) -> None:
    print(f"NG: {message}")
    raise SystemExit(1)


def assert_is_str(value, field: str) -> None:
    if not isinstance(value, str):
        fail(f"{field} must be str (got {type(value).__name__})")


def assert_is_str_list(value, field: str) -> None:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        fail(f"{field} must be list[str]")


def assert_list_of_dicts(value, field: str) -> None:
    if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
        fail(f"{field} must be list[dict]")


def validate(path: Path) -> None:
    if not path.exists():
        fail(f"file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"invalid JSON: {exc}")

    if not isinstance(data, dict):
        fail("top-level must be an object")

    keys = list(data.keys())
    missing = [k for k in EXPECTED_KEYS if k not in data]
    extra = [k for k in keys if k not in EXPECTED_KEYS]

    print(f"file: {path}")
    print(f"keys: {len(keys)}")
    print(f"missing: {missing}")
    print(f"extra: {extra}")
    print(f"order_ok: {keys == EXPECTED_KEYS}")

    if missing:
        fail(f"missing keys: {missing}")
    if extra:
        fail(f"extra keys: {extra}")

    # Primitive fields
    for field in [
        "title",
        "author",
        "genre",
        "japanese_genre",
        "sub_genre",
        "setting",
        "location",
        "time_period",
        "synopsis",
    ]:
        assert_is_str(data[field], field)

    for field in ["keywords", "themes", "emotions", "highlights"]:
        assert_is_str_list(data[field], field)

    # authorProfile
    author_profile = data["authorProfile"]
    if not isinstance(author_profile, dict):
        fail("authorProfile must be an object")
    if set(author_profile.keys()) != {"name", "desc"}:
        fail("authorProfile must have keys: name, desc")
    assert_is_str(author_profile.get("name"), "authorProfile.name")
    assert_is_str(author_profile.get("desc"), "authorProfile.desc")

    # characters
    characters = data["characters"]
    assert_list_of_dicts(characters, "characters")
    for i, ch in enumerate(characters):
        if set(ch.keys()) != {"name", "desc"}:
            fail(f"characters[{i}] must have keys: name, desc")
        assert_is_str(ch.get("name"), f"characters[{i}].name")
        assert_is_str(ch.get("desc"), f"characters[{i}].desc")

    # glossary
    glossary = data["glossary"]
    assert_list_of_dicts(glossary, "glossary")
    for i, item in enumerate(glossary):
        if set(item.keys()) != {"term", "reading", "desc"}:
            fail(f"glossary[{i}] must have keys: term, reading, desc")
        assert_is_str(item.get("term"), f"glossary[{i}].term")
        assert_is_str(item.get("reading"), f"glossary[{i}].reading")
        assert_is_str(item.get("desc"), f"glossary[{i}].desc")

    # chapters
    chapters = data["chapters"]
    assert_list_of_dicts(chapters, "chapters")
    for i, chap in enumerate(chapters):
        if set(chap.keys()) != {"title", "content"}:
            fail(f"chapters[{i}] must have keys: title, content")
        assert_is_str(chap.get("title"), f"chapters[{i}].title")
        assert_is_str(chap.get("content"), f"chapters[{i}].content")

    print(f"chapters: {len(chapters)}")
    print(f"characters: {len(characters)}")
    print(f"glossary: {len(glossary)}")
    print("OK")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: validate_bookdata.py <path-to-bookdata.json>")
        raise SystemExit(2)

    validate(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
