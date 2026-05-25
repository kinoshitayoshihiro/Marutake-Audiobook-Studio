from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Protocol

from .envfile import load_env_file


class XPostClient(Protocol):
    def create_post(self, text: str, reply_to_post_id: str = "") -> dict[str, Any]:
        """Create an X Post and return the API response."""


class XApiClient:
    def __init__(self, access_token: str | None = None, endpoint: str | None = None):
        load_env_file()
        self.access_token = access_token or os.getenv("MARUTAKE_X_USER_ACCESS_TOKEN") or os.getenv("X_USER_ACCESS_TOKEN")
        self.endpoint = endpoint or os.getenv("MARUTAKE_X_POST_ENDPOINT", "https://api.x.com/2/tweets")
        if not self.access_token:
            raise RuntimeError("MARUTAKE_X_USER_ACCESS_TOKEN または X_USER_ACCESS_TOKEN が未設定です")

    def create_post(self, text: str, reply_to_post_id: str = "") -> dict[str, Any]:
        body: dict[str, Any] = {"text": text}
        if reply_to_post_id:
            body["reply"] = {"in_reply_to_tweet_id": reply_to_post_id}
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"X API投稿に失敗しました: HTTP {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"X API投稿に失敗しました: {exc.reason}") from exc
        data = json.loads(response_body)
        if not isinstance(data, dict):
            raise RuntimeError("X APIレスポンスを解釈できません")
        return data
