from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .checks import duplicate_report, has_findings
from .exporters import export_bundle, posts_csv
from .generators import calendar, generate_article, generate_posts, generate_thread, post_payloads
from .input_loader import load_mapping
from .models import STYLE_PRESETS, Video
from .publisher import import_x_drafts, publish_post, publish_thread
from .providers import llm_provider, research_provider, suggest_queries
from .store import JsonStore
from .x_client import XApiClient


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    store = JsonStore(args.db)
    try:
        return int(args.func(store, args))
    except (KeyError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def cmd_init(store: JsonStore, args: argparse.Namespace) -> int:
    print(f"initialized: {store.init()}")
    return 0


def cmd_add_video(store: JsonStore, args: argparse.Namespace) -> int:
    video = store.add_video(Video.from_mapping(load_mapping(args.input)))
    print(f"video registered: {video.video_id} | {video.author}『{video.work_title}』")
    return 0


def cmd_list(store: JsonStore, args: argparse.Namespace) -> int:
    for video in store.videos():
        print(f"{video.video_id}\t{video.publish_date}\t{video.author}\t{video.work_title}")
    return 0


def cmd_generate_posts(store: JsonStore, args: argparse.Namespace) -> int:
    video = store.video(args.video_id)
    posts = post_payloads(generate_posts(video, llm_provider(args.provider), args.style))
    store.replace_posts(video.video_id, "", posts)
    over = [post for post in posts if post["over_limit"]]
    print(f"generated posts: {len(posts)} | 280字超警告: {len(over)}")
    for post in posts:
        print(f"{post['post_id']}\t{post['post_type']}\t{post['char_count']}字\t{post['scheduled_date']}")
    return 0


def cmd_generate_thread(store: JsonStore, args: argparse.Namespace) -> int:
    video = store.video(args.video_id)
    thread_id, posts = generate_thread(video, llm_provider(args.provider), args.style)
    payloads = post_payloads(posts)
    store.replace_posts(video.video_id, "thread", payloads)
    store.save_thread(thread_id, {"thread_id": thread_id, "video_id": video.video_id, "style": args.style, "posts": payloads})
    print(f"generated thread: {thread_id} | {len(payloads)} posts")
    for post in payloads:
        warning = " warning:280字超" if post["over_limit"] else ""
        print(f"{post['sequence']}\t{post['char_count']}字{warning}\t{post['post_id']}")
    return 0


def cmd_generate_article(store: JsonStore, args: argparse.Namespace) -> int:
    video = store.video(args.video_id)
    article = generate_article(video, llm_provider(args.provider), args.type, args.style)
    store.save_article(article["article_id"], article)
    print(article["body"])
    return 0


def cmd_calendar(store: JsonStore, args: argparse.Namespace) -> int:
    video = store.video(args.video_id)
    posts = store.posts(video.video_id)
    if not posts:
        posts = post_payloads(generate_posts(video, llm_provider("dummy"), "marutake_editorial"))
        store.replace_posts(video.video_id, "", posts)
    items = calendar(video, posts)
    data = store.data()
    data["calendar"] = [item for item in data["calendar"] if item["video_id"] != video.video_id] + items
    store.save(data)
    for item in items:
        print(f"{item['scheduled_date']}\t{item['label']}\t{item['status']}\t{item['post_id'] or '-'}")
    return 0


def cmd_export(store: JsonStore, args: argparse.Namespace) -> int:
    text = export_bundle(store.data(), store.video(args.video_id), args.format)
    _emit(text, args.out)
    return 0


def cmd_status(store: JsonStore, args: argparse.Namespace) -> int:
    post = store.status(args.post_id, args.status)
    print(f"status updated: {post['post_id']} -> {post['status']}")
    return 0


def cmd_duplicates(store: JsonStore, args: argparse.Namespace) -> int:
    posts = store.posts(args.video_id)
    if args.status:
        allowed = {item.strip() for item in args.status.split(",") if item.strip()}
        posts = [post for post in posts if str(post.get("status", "draft")) in allowed]
    report = duplicate_report(posts)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if has_findings(report) and args.strict else 0


def cmd_import_x_drafts(store: JsonStore, args: argparse.Namespace) -> int:
    posts = import_x_drafts(store, args.video_id, selected_only=not args.include_candidates)
    print(f"imported X drafts: {len(posts)}")
    for post in posts:
        warning = " warning:280字超" if post.get("over_limit") else ""
        print(f"{post['post_id']}\t{post['post_type']}\t{post['status']}\t{post['char_count']}字{warning}")
    return 0


def cmd_publish_x(store: JsonStore, args: argparse.Namespace) -> int:
    client = XApiClient() if args.live else _DryRunXClient()
    result = publish_post(store, args.post_id, client, dry_run=not args.live, allow_over_limit=args.allow_over_limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_publish_x_thread(store: JsonStore, args: argparse.Namespace) -> int:
    client = XApiClient() if args.live else _DryRunXClient()
    results = publish_thread(store, args.video_id, client, dry_run=not args.live, allow_over_limit=args.allow_over_limit)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def cmd_research(store: JsonStore, args: argparse.Namespace) -> int:
    report = research_provider(args.provider).research(store.video(args.video_id))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def cmd_queries(store: JsonStore, args: argparse.Namespace) -> int:
    for query in suggest_queries(store.video(args.video_id)):
        print(query)
    return 0


def _emit(text: str, output: str | None) -> None:
    if output:
        Path(output).write_text(text, encoding="utf-8")
        print(f"wrote: {output}", file=sys.stderr)
        return
    print(text, end="")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marutake-x", description="丸竹書房のレビュー前提X運用CLI")
    parser.add_argument("--db", default=".marutake-x/db.json", help="ローカルJSON DBパス")
    sub = parser.add_subparsers(dest="command")
    _sub(sub, "init", cmd_init)
    add_video = _sub(sub, "add-video", cmd_add_video)
    add_video.add_argument("input", help="動画YAMLまたはJSON")
    _sub(sub, "list", cmd_list)

    posts = _video_sub(sub, "generate-posts", cmd_generate_posts)
    _provider_options(posts)
    thread = _video_sub(sub, "generate-thread", cmd_generate_thread)
    _provider_options(thread, default_style="trivia_column")
    article = _video_sub(sub, "generate-article", cmd_generate_article)
    article.add_argument(
        "--type",
        default="work_commentary",
        choices=["work_commentary", "author_commentary", "edo_trivia", "sengoku_background", "reading_afterword", "song_making"],
    )
    _provider_options(article)
    _video_sub(sub, "calendar", cmd_calendar)
    export = _video_sub(sub, "export", cmd_export)
    export.add_argument("--format", default="markdown", choices=["markdown", "csv", "json"])
    export.add_argument("--out", help="書き出し先")
    status = _sub(sub, "status", cmd_status)
    status.add_argument("post_id")
    status.add_argument("status")
    duplicate = _sub(sub, "check-duplicates", cmd_duplicates)
    duplicate.add_argument("--video-id")
    duplicate.add_argument("--strict", action="store_true")
    duplicate.add_argument("--status", help="確認対象ステータス。例: reviewed,scheduled,posted。未指定なら全件")
    import_drafts = _video_sub(sub, "import-x-drafts", cmd_import_x_drafts)
    import_drafts.add_argument("--include-candidates", action="store_true", help="candidate文案もDB投稿として取り込む")
    publish_x = _sub(sub, "publish-x", cmd_publish_x)
    publish_x.add_argument("post_id")
    publish_x.add_argument("--live", action="store_true", help="実際にXへ投稿する。未指定ならdry-run")
    publish_x.add_argument("--allow-over-limit", action="store_true", help="280字超でも送信を許可する")
    publish_thread = _video_sub(sub, "publish-x-thread", cmd_publish_x_thread)
    publish_thread.add_argument("--live", action="store_true", help="実際にXへツリー投稿する。未指定ならdry-run")
    publish_thread.add_argument("--allow-over-limit", action="store_true", help="280字超でも送信を許可する")
    research = _video_sub(sub, "research", cmd_research)
    research.add_argument("--provider", default="noop", choices=["noop", "hermes-x-search"])
    _video_sub(sub, "suggest-queries", cmd_queries)
    return parser


def _sub(sub: Any, name: str, func: Any) -> argparse.ArgumentParser:
    parser = sub.add_parser(name)
    parser.set_defaults(func=func)
    return parser


def _video_sub(sub: Any, name: str, func: Any) -> argparse.ArgumentParser:
    parser = _sub(sub, name, func)
    parser.add_argument("video_id")
    return parser


def _provider_options(parser: argparse.ArgumentParser, default_style: str = "marutake_editorial") -> None:
    parser.add_argument("--style", default=default_style, choices=sorted(STYLE_PRESETS))
    parser.add_argument("--provider", default="dummy", choices=["dummy", "openai"])


class _DryRunXClient:
    def create_post(self, text: str, reply_to_post_id: str = "") -> dict[str, Any]:
        return {"data": {"id": "dry-run", "text": text}, "reply_to_post_id": reply_to_post_id}


if __name__ == "__main__":
    raise SystemExit(main())
