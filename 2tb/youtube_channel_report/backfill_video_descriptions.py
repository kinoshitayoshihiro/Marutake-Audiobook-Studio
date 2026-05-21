#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable, Sequence

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

DESCRIPTION_HEADERS = [
    "description",
    "description_length",
    "has_description_synopsis",
    "has_description_characters",
    "has_description_glossary",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill YouTube snippet.description and related flags into an existing per-video CSV."
    )
    parser.add_argument("--client-secrets", default="client_secret.json")
    parser.add_argument("--token-file", default="token.json")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-csv")
    return parser.parse_args()


def chunked(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def to_bool_string(value: bool) -> str:
    return "true" if value else "false"


def load_credentials(client_secrets_path: Path, token_path: Path) -> Credentials:
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except RefreshError:
            creds = None
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
        creds = flow.run_local_server(
            port=0,
            open_browser=False,
            authorization_prompt_message="\nOpen this URL in your browser to continue OAuth:\n{url}\n",
        )
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def detect_description_sections(description: str) -> dict[str, str | int]:
    text = str(description or "").strip()
    lowered = text.lower()
    return {
        "description": text,
        "description_length": len(text),
        "has_description_synopsis": to_bool_string(
            any(marker in text for marker in ("あらすじ", "梗概", "内容紹介", "物語"))
        ),
        "has_description_characters": to_bool_string(
            any(marker in text for marker in ("登場人物", "配役", "出演", "キャラクター"))
        ),
        "has_description_glossary": to_bool_string(
            any(marker in text or marker in lowered for marker in ("用語集", "語句", "言葉の意味", "豆知識", "glossary"))
        ),
    }


def fetch_descriptions(youtube, video_ids: Sequence[str]) -> dict[str, dict[str, str | int]]:
    result: dict[str, dict[str, str | int]] = {}
    for batch in chunked(video_ids, 50):
        response = youtube.videos().list(part="snippet", id=",".join(batch), maxResults=50).execute()
        for item in response.get("items", []):
            description = item.get("snippet", {}).get("description", "")
            result[item["id"]] = detect_description_sections(description)
    return result


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    client_secrets_path = (base_dir / args.client_secrets).resolve()
    token_path = (base_dir / args.token_file).resolve()
    input_csv_path = Path(args.input_csv).resolve()
    output_csv_path = Path(args.output_csv).resolve() if args.output_csv else input_csv_path

    with input_csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
        fieldnames = list(rows[0].keys()) if rows else []

    for header in DESCRIPTION_HEADERS:
        if header not in fieldnames:
            insert_at = 2 if header == "description" else len(fieldnames)
            if header == "description":
                fieldnames.insert(insert_at, header)
            else:
                fieldnames.append(header)

    video_ids = [str(row.get("videoId", "")).strip() for row in rows if str(row.get("videoId", "")).strip()]
    creds = load_credentials(client_secrets_path, token_path)
    youtube = build("youtube", "v3", credentials=creds)
    description_map = fetch_descriptions(youtube, video_ids)

    for row in rows:
        values = description_map.get(str(row.get("videoId", "")).strip(), detect_description_sections(""))
        for key, value in values.items():
            row[key] = value

    with output_csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote: {output_csv_path}")
    print(f"Updated rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
