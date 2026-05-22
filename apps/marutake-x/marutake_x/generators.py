from __future__ import annotations

import hashlib
from datetime import date, timedelta
from typing import Iterable

from .models import Post, Video
from .providers import LLMProvider


POST_PLAN = [
    ("publish_notice", "公開告知", 3, 0, True),
    ("work_intro", "作品紹介", 3, 1, False),
    ("trivia", "雑学", 5, 2, False),
    ("author_note", "作者解説", 2, 5, False),
    ("character_intro", "登場人物紹介", 2, 2, False),
    ("scene_note", "名場面紹介", 2, 3, False),
    ("weekend_roundup", "週末まとめ", 2, 7, True),
    ("youtube_community", "YouTubeコミュニティ", 1, 0, True),
    ("short_notice", "短尺告知", 1, 1, True),
    ("song_intro", "主題歌紹介", 1, 4, True),
]

CALENDAR_OFFSETS = {
    "publish_notice": 0,
    "work_intro": 1,
    "trivia": 2,
    "thread": 3,
    "character_intro": 3,
    "author_note": 5,
    "weekend_roundup": 7,
    "repost": 14,
}


def generate_posts(video: Video, provider: LLMProvider, style: str) -> list[Post]:
    posts: list[Post] = []
    for post_type, label, count, offset, direct in POST_PLAN:
        for variant in range(1, count + 1):
            base = _post_text(video, post_type, label, variant)
            text = provider.rewrite(base, video, style, post_type)
            posts.append(
                Post(
                    post_id=_id("post", video.video_id, post_type, str(variant), style),
                    video_id=video.video_id,
                    post_type=post_type,
                    style=style,
                    text=text,
                    youtube_url=video.youtube_url if direct else "",
                    hashtags=_hashtags(video, post_type),
                    scheduled_date=_scheduled(video.publish_date, offset),
                    sequence=variant,
                    direct_promo=direct,
                )
            )
    return posts


def generate_thread(video: Video, provider: LLMProvider, style: str) -> tuple[str, list[Post]]:
    thread_id = _id("thread", video.video_id, style)
    characters = _pick(video.characters, "登場人物の気配")
    trivia = _pick(_notes(video.unused_trivia_notes), _pick(_notes(video.aftertalk_notes), "作品背景"))
    bases = [
        f"今夜の朗読は『{video.work_title}』。{video.thumbnail_catchcopy or video.summary_short}",
        f"短く言えば、{video.summary_short or video.work_title + 'の物語です。'}",
        f"{video.author}がこの一作で描くのは、{_genre_text(video)}の奥にある人の選択です。",
        f"見どころは {characters}。声で追うと関係の揺れが立ち上がります。",
        f"編集メモから一つ。{trivia}",
        "読む時間とは別に、耳で聴くと場面の間合いが残る作品です。",
        f"朗読はこちら。\n{video.youtube_url}",
    ]
    posts = []
    for index, base in enumerate(bases, start=1):
        posts.append(
            Post(
                post_id=_id("post", thread_id, str(index)),
                video_id=video.video_id,
                post_type="thread",
                style=style,
                text=provider.rewrite(base, video, style, f"thread-{index}"),
                youtube_url=video.youtube_url if index == len(bases) else "",
                hashtags=_hashtags(video, "thread") if index == len(bases) else [],
                scheduled_date=_scheduled(video.publish_date, CALENDAR_OFFSETS["thread"]),
                sequence=index,
                thread_id=thread_id,
                direct_promo=index == len(bases),
            )
        )
    return thread_id, posts


def generate_article(video: Video, provider: LLMProvider, article_type: str, style: str) -> dict[str, str]:
    source_notes = "\n\n".join(note for note in [video.aftertalk_notes, video.unused_trivia_notes] if note)
    type_labels = {
        "work_commentary": "作品解説",
        "author_commentary": "作者解説",
        "edo_trivia": "江戸雑学",
        "sengoku_background": "戦国時代背景",
        "reading_afterword": "朗読後記",
        "song_making": "主題歌制作後記",
    }
    label = type_labels.get(article_type, article_type)
    draft = (
        f"# {label} | {video.work_title}\n\n"
        f"{video.author}『{video.work_title}』を、朗読公開後の編集メモから振り返ります。\n\n"
        f"## 作品の入口\n\n{video.summary_short or video.youtube_description}\n\n"
        f"## メモから残したいこと\n\n{source_notes or '背景メモを追記してください。'}\n\n"
        f"## 朗読への導線\n\n声で聴くことで、場面の呼吸と人物の距離が残ります。\n"
        f"{video.youtube_url}\n"
    )
    body = provider.rewrite(draft, video, style, f"article-{article_type}")
    return {
        "article_id": _id("article", video.video_id, article_type, style),
        "video_id": video.video_id,
        "article_type": article_type,
        "style": style,
        "title": f"{label} | {video.work_title}",
        "body": body,
    }


def calendar(video: Video, posts: Iterable[dict[str, object]]) -> list[dict[str, str]]:
    selected: dict[str, dict[str, object]] = {}
    for post in posts:
        post_type = str(post["post_type"])
        current = selected.get(post_type)
        # Candidate rows sort independently of calendar slots; keep the first sequence.
        if current is None or int(post.get("sequence", 0) or 0) < int(current.get("sequence", 0) or 0):
            selected[post_type] = post
    items: list[dict[str, str]] = []
    for post_type, label in [
        ("publish_notice", "公開当日: 動画告知"),
        ("work_intro", "翌日: あらすじ紹介"),
        ("trivia", "2日後: 雑学投稿"),
        ("thread", "3日後: ツリー投稿"),
        ("author_note", "5日後: 作者解説"),
        ("weekend_roundup", "7日後: 週末まとめ"),
        ("repost", "14日後: 再掲・総集編誘導"),
    ]:
        post = selected.get(post_type)
        items.append(
            {
                "video_id": video.video_id,
                "scheduled_date": _scheduled(video.publish_date, CALENDAR_OFFSETS[post_type]),
                "post_type": post_type,
                "label": label,
                "post_id": str(post.get("post_id", "")) if post else "",
                "status": str(post.get("status", "draft")) if post else "draft",
            }
        )
    return items


def post_payloads(posts: Iterable[Post]) -> list[dict[str, object]]:
    return [post.to_dict() for post in posts]


def _post_text(video: Video, post_type: str, label: str, variant: int) -> str:
    character = _pick(video.characters, "人物たち")
    glossary = _pick(video.glossary, "時代の手触り")
    trivia = _pick(_notes(video.unused_trivia_notes), _pick(_notes(video.aftertalk_notes), "編集メモ"))
    aftertalk = _pick(_notes(video.aftertalk_notes), "朗読後の余韻")
    summary = video.summary_short or f"{video.author}『{video.work_title}』の朗読です。"
    account = "丸竹書房 編集部"
    openings = {
        "publish_notice": [
            f"{account}より新着朗読のお知らせです。{video.author}『{video.work_title}』を公開しました。\n{summary}",
            f"本日の朗読は、{video.author}『{video.work_title}』。\n{video.thumbnail_catchcopy or '声でたどる一作'}。夜の作業時間や、眠る前のひとときにどうぞ。",
            f"『{video.work_title}』公開しました。\n派手な宣伝より、まずは作品の呼吸をそのままお届けします。{summary}",
        ],
        "work_intro": [
            f"作品紹介。{video.author}『{video.work_title}』は、{summary}",
            f"聴く前の入口として。『{video.work_title}』には、{_genre_text(video)}ならではの静かな余韻があります。",
            f"今回の一作を短く言えば、{summary} 朗読では、言葉の間に残る感情を大切にしています。",
        ],
        "trivia": [
            f"編集部メモ。{trivia}",
            f"作品の脇に残った雑学を一つ。{trivia}",
            f"『{video.work_title}』の背景から。{trivia}",
            f"耳で聴いたあとに調べたくなる点。{glossary}。物語の背景を知ると、人物の所作が少し違って見えてきます。",
            f"アフタートークに入りきらなかった余白から。{trivia}",
        ],
        "author_note": [
            f"{video.author}は、事件や筋だけでなく、人が踏みとどまる瞬間を描きます。『{video.work_title}』にも、その目線が静かに残ります。",
            f"作者紹介。{video.author}『{video.work_title}』では、{_genre_text(video)}を通して人物の輪郭が浮かびます。説明しすぎないところが、耳で聴くとよく効きます。",
        ],
        "character_intro": [
            f"人物紹介。{character}が『{video.work_title}』の場面を動かします。筋を追うだけでなく、人物の沈黙に耳を澄ませたい一作です。",
            f"登場人物を一人たどるだけで、物語の見え方が変わります。今回は {character}。朗読では、その距離感を丁寧に追っています。",
        ],
        "scene_note": [
            f"名場面メモ。{summary} 朗読では、台詞よりも“間”が効く場面があります。",
            f"『{video.work_title}』の見どころは、説明より先に人物の気持ちが届く瞬間です。静かな場面ほど、声にすると奥行きが出ます。",
        ],
        "weekend_roundup": [
            f"週末の朗読候補に。{video.author}『{video.work_title}』。\n{summary}",
            f"今週の音本から『{video.work_title}』。落ち着いて聴ける時間にどうぞ。{account}より。",
        ],
        "youtube_community": [f"新しい朗読を公開しました。\n\n{summary}\n\nアフタートークでは、{aftertalk}についても少し触れています。ご感想もお待ちしています。"],
        "short_notice": [f"短く入口だけ。『{video.work_title}』の朗読はこちらから。\n{video.thumbnail_catchcopy or summary}"],
        "song_intro": [f"作品の余韻を音でも。『{video.work_title}』に寄せた主題歌・音のメモです。物語のあとに残る感情を、別の角度からたどります。"],
    }
    lines = openings[post_type]
    body = lines[(variant - 1) % len(lines)]
    if post_type in {"publish_notice", "weekend_roundup", "youtube_community", "short_notice", "song_intro"}:
        body = f"{body}\n{video.youtube_url}"
    return body

def _hashtags(video: Video, post_type: str) -> list[str]:
    base = list(video.tags[:3])
    if post_type in {"publish_notice", "weekend_roundup", "short_notice"} and "#朗読" not in base:
        base.append("#朗読")
    return base


def _notes(text: str) -> list[str]:
    return [line.strip(" -") for line in text.splitlines() if line.strip(" -")]


def _pick(values: list[str], fallback: str) -> str:
    return values[0] if values else fallback


def _genre_text(video: Video) -> str:
    return "・".join(video.genre) if video.genre else "物語"


def _scheduled(publish_date: str, offset: int) -> str:
    return (date.fromisoformat(publish_date) + timedelta(days=offset)).isoformat()


def _id(*parts: str) -> str:
    digest = hashlib.sha1(":".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{parts[0]}_{digest}"
