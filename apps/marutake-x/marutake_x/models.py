from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any


POST_STATUSES = {"draft", "reviewed", "scheduled", "posted", "skipped"}
STYLE_PRESETS = {
    "marutake_editorial": "丸竹書房編集部の落ち着いた文学的文体",
    "shichimi_personal": "七味春五郎本人の親しみある語り",
    "youtube_promo": "YouTube告知向けの明快な文体",
    "trivia_column": "雑学コラム向けの読み物調",
    "song_promo": "主題歌と音楽紹介向けの文体",
}


@dataclass
class Video:
    video_id: str
    youtube_title: str
    youtube_url: str
    publish_date: str
    work_title: str
    author: str
    series_name: str = ""
    genre: list[str] = field(default_factory=list)
    summary_short: str = ""
    characters: list[str] = field(default_factory=list)
    glossary: list[str] = field(default_factory=list)
    youtube_description: str = ""
    aftertalk_notes: str = ""
    unused_trivia_notes: str = ""
    thumbnail_catchcopy: str = ""
    account_name: str = "丸竹書房 編集部"
    video_kind: str = ""
    thumbnail_notes: str = ""
    x_drafts: list[dict[str, Any]] = field(default_factory=list)
    youtube_community_drafts: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Video":
        required = ["video_id", "youtube_title", "youtube_url", "publish_date", "work_title", "author"]
        missing = [key for key in required if not str(data.get(key, "")).strip()]
        if missing:
            raise ValueError(f"動画入力に必須項目がありません: {', '.join(missing)}")
        date.fromisoformat(str(data["publish_date"]))
        return cls(
            **{
                **{key: data.get(key, "") for key in cls.__dataclass_fields__},
                "genre": _as_list(data.get("genre")),
                "characters": _as_list(data.get("characters")),
                "glossary": _as_list(data.get("glossary")),
                "x_drafts": _as_drafts(data.get("x_drafts")),
                "youtube_community_drafts": _as_drafts(data.get("youtube_community_drafts")),
                "tags": _as_list(data.get("tags")),
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Post:
    post_id: str
    video_id: str
    post_type: str
    style: str
    text: str
    youtube_url: str
    hashtags: list[str] = field(default_factory=list)
    status: str = "draft"
    scheduled_date: str = ""
    sequence: int = 0
    thread_id: str = ""
    direct_promo: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["char_count"] = char_count(self.text, self.youtube_url, self.hashtags)
        payload["over_limit"] = payload["char_count"] > 280
        return payload


def char_count(text: str, youtube_url: str = "", hashtags: list[str] | None = None) -> int:
    parts = [text.strip()]
    if youtube_url and youtube_url not in text:
        parts.append(youtube_url)
    tags = hashtags or []
    unused_tags = [tag for tag in tags if tag and tag not in text]
    if unused_tags:
        parts.append(" ".join(unused_tags))
    return len("\n".join(part for part in parts if part))


def _as_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return [str(value).strip()]


def _as_drafts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    drafts = []
    for item in value:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        selected = bool(item.get("selected", item.get("status") in {"reviewed", "scheduled", "posted"}))
        drafts.append(
            {
                "kind": str(item.get("kind", "draft")).strip() or "draft",
                "title": str(item.get("title", "")).strip(),
                "status": str(item.get("status", "draft")).strip() or "draft",
                "selected": selected,
                "candidate": bool(item.get("candidate", not selected)),
                "scheduled_date": str(item.get("scheduled_date", "")).strip(),
                "text": text,
                "image_note": str(item.get("image_note", "")).strip(),
                "memo": str(item.get("memo", "")).strip(),
            }
        )
    return drafts
