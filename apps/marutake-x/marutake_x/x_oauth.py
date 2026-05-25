from __future__ import annotations

import base64
import hashlib
import json
import secrets
import string
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
DEFAULT_SCOPES = ["tweet.read", "tweet.write", "users.read", "offline.access"]
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/callback"


def create_authorization_url(
    client_id: str,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scopes: list[str] | None = None,
    state: str | None = None,
    state_file: str | Path | None = None,
) -> dict[str, str]:
    if not client_id.strip():
        raise ValueError("client_id が必要です")
    requested_scopes = scopes or DEFAULT_SCOPES
    verifier = _code_verifier()
    challenge = _code_challenge(verifier)
    oauth_state = state or secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(requested_scopes),
        "state": oauth_state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    payload = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(requested_scopes),
        "state": oauth_state,
        "code_verifier": verifier,
        "code_challenge_method": "S256",
        "authorize_url": url,
    }
    if state_file:
        target = Path(state_file)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def exchange_authorization_code(
    code: str,
    client_id: str,
    redirect_uri: str,
    code_verifier: str,
    client_secret: str = "",
) -> dict[str, Any]:
    if not code.strip():
        raise ValueError("authorization code が必要です")
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }
    return _token_request(data, client_id, client_secret)


def refresh_access_token(refresh_token: str, client_id: str, client_secret: str = "") -> dict[str, Any]:
    if not refresh_token.strip():
        raise ValueError("refresh_token が必要です")
    data = {
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
        "client_id": client_id,
    }
    return _token_request(data, client_id, client_secret)


def load_oauth_state(path: str | Path) -> dict[str, str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("OAuth state file を解釈できません")
    return {str(key): str(value) for key, value in data.items()}


def token_env_values(token_response: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    if token_response.get("access_token"):
        values["MARUTAKE_X_USER_ACCESS_TOKEN"] = str(token_response["access_token"])
    if token_response.get("refresh_token"):
        values["MARUTAKE_X_REFRESH_TOKEN"] = str(token_response["refresh_token"])
    return values


def redacted_token_response(token_response: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(token_response)
    for key in ["access_token", "refresh_token"]:
        if key in redacted:
            redacted[key] = _redact(str(redacted[key]))
    return redacted


def _token_request(data: dict[str, str], client_id: str, client_secret: str = "") -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode("utf-8")
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if client_secret:
        raw = f"{client_id}:{client_secret}".encode("utf-8")
        headers["Authorization"] = f"Basic {base64.b64encode(raw).decode('ascii')}"
    request = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"X OAuth token request failed: HTTP {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"X OAuth token request failed: {exc.reason}") from exc
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise RuntimeError("X OAuth token response を解釈できません")
    return parsed


def _code_verifier() -> str:
    alphabet = string.ascii_letters + string.digits + "-._~"
    return "".join(secrets.choice(alphabet) for _ in range(64))


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _redact(value: str) -> str:
    if len(value) <= 12:
        return "***"
    return f"{value[:6]}...{value[-4:]}"
