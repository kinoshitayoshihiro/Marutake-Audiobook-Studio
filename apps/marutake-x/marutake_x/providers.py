from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .models import STYLE_PRESETS, Video


class LLMProvider(ABC):
    @abstractmethod
    def rewrite(self, draft: str, video: Video, style: str, purpose: str) -> str:
        """Return a draft for review. Providers must not post to X."""


class DummyProvider(LLMProvider):
    def rewrite(self, draft: str, video: Video, style: str, purpose: str) -> str:
        return draft.strip()


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str | None = None):
        self.model = model or os.getenv("MARUTAKE_X_OPENAI_MODEL", "gpt-5.2")

    def rewrite(self, draft: str, video: Video, style: str, purpose: str) -> str:
        try:
            from openai import OpenAI  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError("OpenAIProviderには openai パッケージが必要です") from exc
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY が未設定です")
        response = OpenAI().responses.create(
            model=self.model,
            instructions=(
                "You draft Japanese social posts for human review. "
                "Do not claim that anything was posted or scheduled. "
                f"Style: {STYLE_PRESETS.get(style, style)}."
            ),
            input=(
                f"Purpose: {purpose}\n"
                f"Work: {video.work_title}\nAuthor: {video.author}\n"
                f"Summary: {video.summary_short}\nDraft:\n{draft}\n"
                "Return only the revised Japanese draft."
            ),
        )
        return response.output_text.strip()


class ResearchProvider(ABC):
    @abstractmethod
    def research(self, video: Video) -> dict[str, object]:
        """Return research notes. Providers must not copy X posts verbatim."""


class NoopResearchProvider(ResearchProvider):
    def research(self, video: Video) -> dict[str, object]:
        return {
            "provider": "noop",
            "queries": suggest_queries(video),
            "topics": [],
            "risks": ["外部リサーチ未実行。投稿前に固有名詞と引用範囲を確認してください。"],
            "use_words": [video.author, video.work_title],
            "avoid_words": ["未確認のトレンド便乗", "原文の長い転載"],
        }


@dataclass
class HermesXSearchProvider(ResearchProvider):
    configured: bool = False

    def research(self, video: Video) -> dict[str, object]:
        return {
            "provider": "hermes-x-search",
            "implemented": False,
            "configured": self.configured,
            "queries": suggest_queries(video),
            "topics": [],
            "risks": [
                "Hermes X Search 呼び出しは未実装です。",
                "X投稿をそのまま転載せず、話題の傾向だけを利用してください。",
            ],
            "use_words": [video.author, video.series_name or video.work_title],
            "avoid_words": ["未確認の炎上語", "権利確認前の引用"],
        }


def suggest_queries(video: Video) -> list[str]:
    seeds = [
        f"{video.author} 朗読",
        video.work_title,
        video.series_name,
        "時代小説 オーディオブック",
        "睡眠用 朗読",
        "作業用 朗読",
    ]
    genre = " ".join(video.genre)
    if "捕物" in genre or "銭形" in video.series_name:
        seeds.extend(["銭形平次", "江戸 雑学"])
    if "戦国" in genre or "吉川" in video.author:
        seeds.extend(["吉川英治 新書太閤記", "戦国 時代背景"])
    if "主題歌" in genre or "歌" in genre:
        seeds.extend(["AI主題歌", "SUNO AI 日本語曲"])
    return [seed for seed in dict.fromkeys(seed.strip() for seed in seeds) if seed]


def llm_provider(name: str) -> LLMProvider:
    if name == "dummy":
        return DummyProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ValueError(f"未対応LLM providerです: {name}")


def research_provider(name: str) -> ResearchProvider:
    if name == "noop":
        return NoopResearchProvider()
    if name == "hermes-x-search":
        return HermesXSearchProvider()
    raise ValueError(f"未対応Research providerです: {name}")
