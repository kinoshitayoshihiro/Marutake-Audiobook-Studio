from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from marutake_x.checks import duplicate_report
from marutake_x.exporters import posts_csv
from marutake_x.generators import calendar, generate_posts, generate_thread, post_payloads
from marutake_x.models import Video, char_count
from marutake_x.providers import DummyProvider
from marutake_x.store import JsonStore


def sample_video() -> Video:
    return Video.from_mapping(
        {
            "video_id": "video-001",
            "youtube_title": "山本周五郎 花匂う",
            "youtube_url": "https://www.youtube.com/watch?v=example",
            "publish_date": "2026-05-22",
            "work_title": "花匂う",
            "author": "山本周五郎",
            "series_name": "山本周五郎アワー",
            "genre": ["人情物"],
            "summary_short": "静かな誇りを描く一作。",
            "characters": ["主人公"],
            "glossary": ["江戸の暮らし"],
            "unused_trivia_notes": "江戸の面目は小さな所作にも出る。",
            "tags": ["#朗読", "#山本周五郎"],
        }
    )


class MarutakeXTests(unittest.TestCase):
    def test_video_registration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonStore(Path(temp) / "db.json")
            store.add_video(sample_video())
            self.assertEqual(store.video("video-001").work_title, "花匂う")

    def test_post_generation_has_requested_core_drafts(self) -> None:
        posts = generate_posts(sample_video(), DummyProvider(), "marutake_editorial")
        by_type: dict[str, int] = {}
        for post in posts:
            by_type[post.post_type] = by_type.get(post.post_type, 0) + 1
        self.assertEqual(by_type["publish_notice"], 3)
        self.assertEqual(by_type["work_intro"], 3)
        self.assertEqual(by_type["trivia"], 5)
        self.assertEqual(by_type["youtube_community"], 1)

    def test_character_count_includes_url_and_hashtags(self) -> None:
        self.assertEqual(char_count("投稿", "https://x.test", ["#朗読"]), len("投稿\nhttps://x.test\n#朗読"))

    def test_csv_export_contains_review_columns(self) -> None:
        text = posts_csv(post_payloads(generate_posts(sample_video(), DummyProvider(), "youtube_promo"))[:1])
        self.assertIn("post_id,video_id,scheduled_date,post_type,status", text)
        self.assertIn("char_count", text)

    def test_status_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            store = JsonStore(Path(temp) / "db.json")
            store.add_video(sample_video())
            posts = post_payloads(generate_posts(sample_video(), DummyProvider(), "marutake_editorial"))
            store.replace_posts("video-001", "", posts)
            changed = store.status(posts[0]["post_id"], "reviewed")
            self.assertEqual(changed["status"], "reviewed")

    def test_calendar_uses_first_thread_post(self) -> None:
        video = sample_video()
        _, thread_posts = generate_thread(video, DummyProvider(), "trivia_column")
        items = calendar(video, post_payloads(thread_posts))
        thread_item = [item for item in items if item["post_type"] == "thread"][0]
        self.assertEqual(thread_item["post_id"], thread_posts[0].post_id)

    def test_duplicate_report_flags_promo_runs(self) -> None:
        report = duplicate_report(
            [
                {
                    "post_id": f"post-{index}",
                    "scheduled_date": f"2026-05-2{index}",
                    "youtube_url": "https://www.youtube.com/watch?v=example",
                    "text": "同じ入口 文案",
                    "hashtags": ["#朗読"],
                    "direct_promo": True,
                }
                for index in range(1, 4)
            ]
        )
        self.assertTrue(report["same_youtube_url_runs"])
        self.assertTrue(report["same_opening_patterns"])
        self.assertTrue(report["direct_promo_runs"])


if __name__ == "__main__":
    unittest.main()
