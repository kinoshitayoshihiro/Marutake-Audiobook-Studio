from __future__ import annotations

import csv
import io
import json
from typing import Any

from .models import Video


CSV_HEADERS = [
    "post_id",
    "video_id",
    "scheduled_date",
    "post_type",
    "status",
    "text",
    "youtube_url",
    "hashtags",
    "char_count",
]


def export_bundle(data: dict[str, Any], video: Video, output_format: str) -> str:
    posts = [post for post in data["posts"].values() if post["video_id"] == video.video_id]
    threads = [thread for thread in data["threads"].values() if thread["video_id"] == video.video_id]
    articles = [article for article in data["articles"].values() if article["video_id"] == video.video_id]
    calendar = [item for item in data["calendar"] if item["video_id"] == video.video_id]
    if output_format == "markdown":
        return _markdown(video, posts, threads, articles, calendar)
    if output_format == "csv":
        return _csv(posts)
    if output_format == "json":
        return json.dumps(
            {"video": video.to_dict(), "posts": posts, "threads": threads, "articles": articles, "calendar": calendar},
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    raise ValueError(f"未対応出力形式です: {output_format}")


def posts_csv(posts: list[dict[str, Any]]) -> str:
    return _csv(posts)


def _csv(posts: list[dict[str, Any]]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=CSV_HEADERS, extrasaction="ignore")
    writer.writeheader()
    for post in posts:
        row = {**post, "hashtags": " ".join(post.get("hashtags", []))}
        writer.writerow(row)
    return handle.getvalue()


def _markdown(
    video: Video,
    posts: list[dict[str, Any]],
    threads: list[dict[str, Any]],
    articles: list[dict[str, Any]],
    calendar: list[dict[str, Any]],
) -> str:
    lines = [
        f"# X運用メモ | {video.work_title}",
        "",
        "## 動画情報",
        "",
        f"- 作者: {video.author}",
        f"- シリーズ: {video.series_name or '-'}",
        f"- 公開日: {video.publish_date}",
        f"- URL: {video.youtube_url}",
        f"- あらすじ: {video.summary_short or '-'}",
        "",
        "## 投稿案",
        "",
    ]
    for post in posts:
        warning = " 警告: 280字超" if post.get("over_limit") else ""
        lines.extend(
            [
                f"### {post['post_type']} | {post['post_id']} | {post['status']}{warning}",
                "",
                str(post["text"]),
                "",
                f"文字数: {post.get('char_count', 0)}",
                "",
            ]
        )
    lines.extend(["## ツリー投稿", ""])
    for thread in threads:
        lines.append(f"### {thread['thread_id']}")
        for post in thread["posts"]:
            lines.append(f"{post['sequence']}. {post['text']} ({post['char_count']}字)")
        lines.append("")
    lines.extend(["## 長文記事", ""])
    for article in articles:
        lines.extend([f"### {article['title']}", "", article["body"], ""])
    lines.extend(["## 投稿カレンダー", "", "| 日付 | 種別 | 状態 | 投稿ID |", "| --- | --- | --- | --- |"])
    for item in calendar:
        lines.append(f"| {item['scheduled_date']} | {item['label']} | {item['status']} | {item['post_id'] or '-'} |")
    return "\n".join(lines).strip() + "\n"
