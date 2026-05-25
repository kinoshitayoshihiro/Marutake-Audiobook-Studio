from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import POST_STATUSES, Video


EMPTY_DB = {"videos": {}, "posts": {}, "threads": {}, "articles": {}, "calendar": []}


class JsonStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def init(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save({key: value.copy() if isinstance(value, dict) else [] for key, value in EMPTY_DB.items()})
        return self.path

    def load(self) -> dict[str, Any]:
        self.init()
        with self.path.open(encoding="utf-8") as handle:
            data = json.load(handle)
        for key, value in EMPTY_DB.items():
            data.setdefault(key, value.copy() if isinstance(value, dict) else [])
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def add_video(self, video: Video) -> Video:
        data = self.load()
        data["videos"][video.video_id] = video.to_dict()
        self.save(data)
        return video

    def video(self, video_id: str) -> Video:
        data = self.load()
        payload = data["videos"].get(video_id)
        if not payload:
            raise KeyError(f"動画が未登録です: {video_id}")
        return Video.from_mapping(payload)

    def videos(self) -> list[Video]:
        return [Video.from_mapping(item) for item in self.load()["videos"].values()]

    def replace_posts(self, video_id: str, post_type_prefix: str, posts: list[dict[str, Any]]) -> None:
        data = self.load()
        def should_keep(post: dict[str, Any]) -> bool:
            if post["video_id"] != video_id:
                return True
            if post_type_prefix == "":
                return post["post_type"] == "thread"
            return not post["post_type"].startswith(post_type_prefix)

        data["posts"] = {
            post_id: post
            for post_id, post in data["posts"].items()
            if should_keep(post)
        }
        data["posts"].update({post["post_id"]: post for post in posts})
        self.save(data)

    def upsert_posts(self, posts: list[dict[str, Any]]) -> None:
        data = self.load()
        data["posts"].update({post["post_id"]: post for post in posts})
        self.save(data)

    def posts(self, video_id: str | None = None) -> list[dict[str, Any]]:
        posts = list(self.load()["posts"].values())
        if video_id:
            posts = [post for post in posts if post["video_id"] == video_id]
        return sorted(
            posts,
            key=lambda post: (
                post.get("scheduled_date", ""),
                post["post_type"],
                int(post.get("sequence", 0) or 0),
                post["post_id"],
            ),
        )

    def status(self, post_id: str, status: str) -> dict[str, Any]:
        if status not in POST_STATUSES:
            raise ValueError(f"未対応ステータスです: {status}")
        data = self.load()
        if post_id not in data["posts"]:
            raise KeyError(f"投稿が未登録です: {post_id}")
        data["posts"][post_id]["status"] = status
        self.save(data)
        return data["posts"][post_id]

    def save_thread(self, thread_id: str, payload: dict[str, Any]) -> None:
        data = self.load()
        data["threads"][thread_id] = payload
        self.save(data)

    def save_article(self, article_id: str, payload: dict[str, Any]) -> None:
        data = self.load()
        data["articles"][article_id] = payload
        self.save(data)

    def data(self) -> dict[str, Any]:
        return self.load()
