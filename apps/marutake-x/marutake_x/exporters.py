from __future__ import annotations

import csv
import io
import json
from typing import Any

from .models import Video, char_count


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
    selected_x = [draft for draft in video.x_drafts if draft.get("selected")]
    candidate_x = [draft for draft in video.x_drafts if not draft.get("selected")]
    selected_youtube = [draft for draft in video.youtube_community_drafts if draft.get("selected")]
    candidate_youtube = [draft for draft in video.youtube_community_drafts if not draft.get("selected")]
    lines = [
        f"# 投稿素材パック | {video.work_title}",
        "",
        "## 動画情報",
        "",
        f"- 作者: {video.author}",
        f"- シリーズ: {video.series_name or '-'}",
        f"- 動画種別: {video.video_kind or '-'}",
        f"- 発信名義: {video.account_name or '-'}",
        f"- サムネイルコピー: {video.thumbnail_catchcopy or '-'}",
        f"- サムネイル構成: {video.thumbnail_notes or '-'}",
        f"- 公開日: {video.publish_date}",
        f"- URL: {video.youtube_url}",
        f"- あらすじ: {video.summary_short or '-'}",
        "",
        "## 採用X文案",
        "",
    ]
    for index, draft in enumerate(selected_x, start=1):
        lines.extend(_draft_block(index, draft, video.youtube_url, video.tags))
    if candidate_x:
        lines.extend(["## 候補X文案", ""])
        for index, draft in enumerate(candidate_x, start=1):
            lines.extend(_draft_block(index, draft, video.youtube_url, video.tags))
    lines.extend(["## 採用YouTubeコミュニティ文案", ""])
    for index, draft in enumerate(selected_youtube, start=1):
        lines.extend(_draft_block(index, draft, "", []))
    if candidate_youtube:
        lines.extend(["## 候補YouTubeコミュニティ文案", ""])
        for index, draft in enumerate(candidate_youtube, start=1):
            lines.extend(_draft_block(index, draft, "", []))
    lines.extend(
        [
            "## 生成投稿案",
            "",
        ]
    )
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


def _draft_block(index: int, draft: dict[str, Any], youtube_url: str, hashtags: list[str]) -> list[str]:
    title = draft.get("title") or draft.get("kind") or f"draft-{index}"
    markers = []
    if draft.get("selected"):
        markers.append("selected")
    if draft.get("candidate"):
        markers.append("candidate")
    if draft.get("scheduled_date"):
        markers.append(str(draft["scheduled_date"]))
    marker_text = f" | {' / '.join(markers)}" if markers else ""
    lines = [
        f"### {index}. {title} | {draft.get('kind', 'draft')} | {draft.get('status', 'draft')}{marker_text}",
        "",
        "```text",
        draft["text"],
        "```",
        "",
        f"文字数目安: {char_count(draft['text'], youtube_url, hashtags)}",
        "",
    ]
    if draft.get("image_note"):
        lines.extend([f"画像メモ: {draft['image_note']}", ""])
    if draft.get("memo"):
        lines.extend([f"運用メモ: {draft['memo']}", ""])
    return lines
