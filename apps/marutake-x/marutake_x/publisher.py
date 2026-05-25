from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import char_count
from .store import JsonStore
from .x_client import XPostClient


PUBLISHABLE_STATUSES = {"reviewed", "scheduled"}


def import_x_drafts(store: JsonStore, video_id: str, selected_only: bool = True) -> list[dict[str, Any]]:
    video = store.video(video_id)
    existing_posts = {post["post_id"]: post for post in store.posts(video_id)}
    posts: list[dict[str, Any]] = []
    for index, draft in enumerate(video.x_drafts, start=1):
        if selected_only and not draft.get("selected"):
            continue
        post = {
            "post_id": _draft_post_id(video.video_id, draft, index),
            "video_id": video.video_id,
            "scheduled_date": str(draft.get("scheduled_date", "")),
            "post_type": str(draft.get("kind", "draft")),
            "status": str(draft.get("status", "draft")),
            "style": "curated",
            "text": str(draft["text"]),
            "youtube_url": video.youtube_url if draft.get("kind") == "single" else "",
            "hashtags": video.tags if draft.get("kind") == "single" else [],
            "char_count": char_count(str(draft["text"]), video.youtube_url if draft.get("kind") == "single" else "", video.tags if draft.get("kind") == "single" else []),
            "over_limit": char_count(str(draft["text"]), video.youtube_url if draft.get("kind") == "single" else "", video.tags if draft.get("kind") == "single" else []) > 280,
            "sequence": index,
            "thread_id": f"{video.video_id}-curated-thread" if draft.get("kind") == "thread" else "",
            "direct_promo": draft.get("kind") == "single",
            "source": "x_drafts",
            "title": str(draft.get("title", "")),
            "memo": str(draft.get("memo", "")),
        }
        existing = existing_posts.get(post["post_id"], {})
        if existing.get("x_post_id"):
            post.update(
                {
                    "status": existing.get("status", "posted"),
                    "x_post_id": existing.get("x_post_id", ""),
                    "x_post_url": existing.get("x_post_url", ""),
                    "posted_at": existing.get("posted_at", ""),
                    "posted_text": existing.get("posted_text", ""),
                }
            )
        posts.append(post)
    store.upsert_posts(posts)
    return posts


def publish_post(
    store: JsonStore,
    post_id: str,
    client: XPostClient,
    dry_run: bool = True,
    allow_over_limit: bool = False,
    reply_to_post_id: str = "",
) -> dict[str, Any]:
    data = store.data()
    if post_id not in data["posts"]:
        raise KeyError(f"投稿が未登録です: {post_id}")
    post = data["posts"][post_id]
    composed = compose_x_text(post)
    _validate_publishable(post, composed, allow_over_limit)
    if dry_run:
        return {
            "dry_run": True,
            "post_id": post_id,
            "text": composed,
            "char_count": len(composed),
            "reply_to_post_id": reply_to_post_id,
        }
    response = client.create_post(composed, reply_to_post_id)
    x_post_id = _response_post_id(response)
    post.update(
        {
            "status": "posted",
            "x_post_id": x_post_id,
            "x_post_url": f"https://x.com/i/web/status/{x_post_id}" if x_post_id else "",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "posted_text": composed,
        }
    )
    store.save(data)
    return {"dry_run": False, "post_id": post_id, "x_post_id": x_post_id, "response": response}


def publish_thread(
    store: JsonStore,
    video_id: str,
    client: XPostClient,
    dry_run: bool = True,
    allow_over_limit: bool = False,
) -> list[dict[str, Any]]:
    posts = [
        post
        for post in store.posts(video_id)
        if post.get("post_type") == "thread" and post.get("status") in PUBLISHABLE_STATUSES
    ]
    posts.sort(key=lambda post: int(post.get("sequence", 0) or 0))
    if not posts:
        raise ValueError("投稿可能な reviewed/scheduled のXツリーがありません")
    results = []
    reply_to = ""
    for post in posts:
        result = publish_post(store, str(post["post_id"]), client, dry_run=dry_run, allow_over_limit=allow_over_limit, reply_to_post_id=reply_to)
        results.append(result)
        if not dry_run:
            reply_to = str(result.get("x_post_id", ""))
    return results


def compose_x_text(post: dict[str, Any]) -> str:
    parts = [str(post.get("text", "")).strip()]
    youtube_url = str(post.get("youtube_url", "")).strip()
    if youtube_url and youtube_url not in parts[0]:
        parts.append(youtube_url)
    hashtags = [str(tag).strip() for tag in post.get("hashtags", []) if str(tag).strip()]
    unused_tags = [tag for tag in hashtags if tag not in "\n".join(parts)]
    if unused_tags:
        parts.append(" ".join(unused_tags))
    return "\n".join(part for part in parts if part)


def _validate_publishable(post: dict[str, Any], text: str, allow_over_limit: bool) -> None:
    status = str(post.get("status", "draft"))
    if status not in PUBLISHABLE_STATUSES:
        raise ValueError(f"reviewed または scheduled の投稿だけX投稿できます: {post.get('post_id')} は {status}")
    if post.get("x_post_id"):
        raise ValueError(f"すでにX投稿済みです: {post.get('post_id')} -> {post.get('x_post_id')}")
    if not text:
        raise ValueError("本文が空の投稿はX投稿できません")
    if len(text) > 280 and not allow_over_limit:
        raise ValueError(f"280字を超えています: {len(text)}字。必要なら --allow-over-limit を明示してください")


def _response_post_id(response: dict[str, Any]) -> str:
    data = response.get("data")
    if isinstance(data, dict):
        return str(data.get("id", ""))
    return ""


def _draft_post_id(video_id: str, draft: dict[str, Any], index: int) -> str:
    kind = str(draft.get("kind", "draft")).replace(" ", "-")
    return f"curated_{video_id}_{index:02d}_{kind}"
