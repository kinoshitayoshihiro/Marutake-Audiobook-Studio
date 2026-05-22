from __future__ import annotations

import re
from collections import Counter
from itertools import groupby
from typing import Iterable


def duplicate_report(posts: Iterable[dict[str, object]]) -> dict[str, list[str]]:
    rows = sorted(posts, key=lambda post: (str(post.get("scheduled_date", "")), str(post.get("post_id", ""))))
    urls = _url_runs(rows)
    patterns = _pattern_runs(rows)
    hashtag_counts = Counter(tag for post in rows for tag in post.get("hashtags", []) if tag)
    tags = [f"{tag}: {count}回" for tag, count in hashtag_counts.items() if count >= 5]
    promos = _promo_runs(rows)
    return {
        "same_youtube_url_runs": urls,
        "same_opening_patterns": patterns,
        "overused_hashtags": tags,
        "direct_promo_runs": promos,
    }


def has_findings(report: dict[str, list[str]]) -> bool:
    return any(report.values())


def _url_runs(posts: list[dict[str, object]]) -> list[str]:
    findings = []
    for url, group in groupby(posts, key=lambda post: str(post.get("youtube_url", ""))):
        rows = [post for post in group if url]
        if len(rows) >= 2:
            findings.append(f"{url}: 連続{len(rows)}件")
    return findings


def _pattern_runs(posts: list[dict[str, object]]) -> list[str]:
    buckets: dict[str, list[str]] = {}
    for post in posts:
        key = _opening_key(str(post.get("text", "")))
        if key:
            buckets.setdefault(key, []).append(str(post.get("post_id", "")))
    return [f"{key}: {len(ids)}件" for key, ids in buckets.items() if len(ids) >= 3]


def _promo_runs(posts: list[dict[str, object]]) -> list[str]:
    findings = []
    run: list[str] = []
    for post in posts:
        if bool(post.get("direct_promo")):
            run.append(str(post.get("post_id", "")))
            continue
        if len(run) >= 3:
            findings.append(f"直接宣伝が連続{len(run)}件: {', '.join(run)}")
        run = []
    if len(run) >= 3:
        findings.append(f"直接宣伝が連続{len(run)}件: {', '.join(run)}")
    return findings


def _opening_key(text: str) -> str:
    line = text.strip().splitlines()[0] if text.strip() else ""
    line = re.sub(r"[『』「」【】。、,.!！?？\s]+", "", line)
    return line[:18]
