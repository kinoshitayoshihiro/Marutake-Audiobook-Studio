#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]

ZENIGATA_KEYWORDS = ["銭形平次", "平次捕物控"]

INVENTORY_HEADERS = [
    "videoId",
    "title",
    "publishedAt",
    "privacyStatus",
    "uploadStatus",
    "duration",
    "definition",
    "caption",
    "viewCount",
    "likeCount",
    "commentCount",
    "is_zenigata_title",
    "in_old_report",
    "playlist_position",
    "source_channel_id",
    "source_channel_title",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a full uploads inventory for the authenticated YouTube channel.")
    parser.add_argument("--client-secrets", default="client_secret.json")
    parser.add_argument("--token-file", default="token_old_channel.json")
    parser.add_argument("--inventory-output", default="old_channel_report/channel_upload_inventory.csv")
    parser.add_argument("--zenigata-output", default="old_channel_report/zenigata_upload_inventory.csv")
    parser.add_argument("--summary-output", default="old_channel_report/channel_upload_inventory_summary.md")
    parser.add_argument("--old-report-input", default="old_channel_report/youtube_video_report_last_90_days_all_videos.csv")
    return parser.parse_args()


def normalize_number(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def escape_md(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def chunked(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


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
            backup_path = token_path.with_suffix(f"{token_path.suffix}.revoked")
            try:
                if backup_path.exists():
                    backup_path.unlink()
                token_path.replace(backup_path)
            except OSError:
                pass
            creds = None
    if not creds or not creds.valid:
        if not client_secrets_path.exists():
            raise SystemExit("client_secret.json not found.")
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
        creds = flow.run_local_server(
            port=0,
            open_browser=False,
            authorization_prompt_message=("\nOpen this URL in your browser to continue OAuth:\n{url}\n"),
        )
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def load_old_report_video_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            (row.get("videoId") or "").strip()
            for row in csv.DictReader(handle)
            if (row.get("videoId") or "").strip()
        }


def fetch_channel_info(youtube):
    response = youtube.channels().list(part="snippet,contentDetails,statistics", mine=True).execute()
    items = response.get("items", [])
    if not items:
        raise SystemExit("No YouTube channel found for the authenticated account.")
    item = items[0]
    return {
        "channel_id": item["id"],
        "channel_title": item["snippet"]["title"],
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"].get("uploads", ""),
        "stats": item.get("statistics", {}),
    }


def fetch_upload_video_ids(youtube, playlist_id: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    page_token = None
    position = 0
    while True:
        response = youtube.playlistItems().list(
            part="contentDetails,snippet,status",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in response.get("items", []):
            content = item.get("contentDetails", {})
            snippet = item.get("snippet", {})
            video_id = content.get("videoId")
            if not video_id:
                continue
            rows.append(
                {
                    "videoId": video_id,
                    "playlist_position": position,
                    "playlist_publishedAt": snippet.get("publishedAt", ""),
                    "playlist_title": snippet.get("title", ""),
                }
            )
            position += 1
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return rows


def fetch_video_details(youtube, video_ids: Sequence[str]) -> Dict[str, Dict[str, object]]:
    result: Dict[str, Dict[str, object]] = {}
    for batch in chunked(list(video_ids), 50):
        response = youtube.videos().list(
            part="snippet,contentDetails,status,statistics",
            id=",".join(batch),
            maxResults=50,
        ).execute()
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            status = item.get("status", {})
            content = item.get("contentDetails", {})
            stats = item.get("statistics", {})
            result[item["id"]] = {
                "title": snippet.get("title", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "privacyStatus": status.get("privacyStatus", ""),
                "uploadStatus": status.get("uploadStatus", ""),
                "duration": content.get("duration", ""),
                "definition": content.get("definition", ""),
                "caption": content.get("caption", ""),
                "viewCount": stats.get("viewCount", ""),
                "likeCount": stats.get("likeCount", ""),
                "commentCount": stats.get("commentCount", ""),
            }
    return result


def is_zenigata_title(title: str) -> bool:
    normalized = title or ""
    return any(keyword in normalized for keyword in ZENIGATA_KEYWORDS)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=INVENTORY_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_number(row.get(key)) for key in INVENTORY_HEADERS})


def write_summary(path: Path, *, channel_info: Dict[str, object], rows: List[Dict[str, object]], zenigata_rows: List[Dict[str, object]]) -> None:
    privacy_counts = Counter(row.get("privacyStatus", "") for row in rows)
    old_report_count = sum(1 for row in rows if row.get("in_old_report") == "true")
    lines = ["# Channel Upload Inventory", ""]
    lines.append(f"- channel_id: `{channel_info['channel_id']}`")
    lines.append(f"- channel_title: {channel_info['channel_title']}")
    lines.append(f"- channel_statistics.videoCount: {channel_info['stats'].get('videoCount', '')}")
    lines.append(f"- uploads_playlist_items: {len(rows)}")
    lines.append(f"- old_report_overlap: {old_report_count}")
    lines.append(f"- zenigata_title_matches: {len(zenigata_rows)}")
    lines.append("")
    lines.append("## Privacy Breakdown")
    lines.append("")
    for key, count in sorted(privacy_counts.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"- {key or '(blank)'}: {count}")
    lines.append("")
    lines.append("## Zenigata Sample")
    lines.append("")
    lines.append("| videoId | privacy | in_old_report | title |")
    lines.append("| --- | --- | --- | --- |")
    for row in zenigata_rows[:30]:
        lines.append(
            f"| {row['videoId']} | {escape_md(row.get('privacyStatus', ''))} | {escape_md(row.get('in_old_report', ''))} | {escape_md(row.get('title', ''))} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    base_dir = Path(__file__).resolve().parent
    client_secrets_path = (base_dir / args.client_secrets).resolve()
    token_path = (base_dir / args.token_file).resolve()
    inventory_output_path = (base_dir / args.inventory_output).resolve()
    zenigata_output_path = (base_dir / args.zenigata_output).resolve()
    summary_output_path = (base_dir / args.summary_output).resolve()
    old_report_input_path = (base_dir / args.old_report_input).resolve()

    creds = load_credentials(client_secrets_path, token_path)
    youtube = build("youtube", "v3", credentials=creds)
    channel_info = fetch_channel_info(youtube)
    uploads_rows = fetch_upload_video_ids(youtube, channel_info["uploads_playlist"])
    details_by_video_id = fetch_video_details(youtube, [row["videoId"] for row in uploads_rows])
    old_report_video_ids = load_old_report_video_ids(old_report_input_path)

    inventory_rows: List[Dict[str, object]] = []
    for upload_row in uploads_rows:
        video_id = upload_row["videoId"]
        details = details_by_video_id.get(video_id, {})
        title = str(details.get("title") or upload_row.get("playlist_title") or "")
        inventory_rows.append(
            {
                "videoId": video_id,
                "title": title,
                "publishedAt": details.get("publishedAt") or upload_row.get("playlist_publishedAt") or "",
                "privacyStatus": details.get("privacyStatus", ""),
                "uploadStatus": details.get("uploadStatus", ""),
                "duration": details.get("duration", ""),
                "definition": details.get("definition", ""),
                "caption": details.get("caption", ""),
                "viewCount": details.get("viewCount", ""),
                "likeCount": details.get("likeCount", ""),
                "commentCount": details.get("commentCount", ""),
                "is_zenigata_title": "true" if is_zenigata_title(title) else "false",
                "in_old_report": "true" if video_id in old_report_video_ids else "false",
                "playlist_position": upload_row.get("playlist_position", ""),
                "source_channel_id": channel_info["channel_id"],
                "source_channel_title": channel_info["channel_title"],
            }
        )

    zenigata_rows = [row for row in inventory_rows if row["is_zenigata_title"] == "true"]
    write_csv(inventory_output_path, inventory_rows)
    write_csv(zenigata_output_path, zenigata_rows)
    write_summary(summary_output_path, channel_info=channel_info, rows=inventory_rows, zenigata_rows=zenigata_rows)

    print(f"Channel inventory CSV: {inventory_output_path}")
    print(f"Zenigata inventory CSV: {zenigata_output_path}")
    print(f"Summary report: {summary_output_path}")
    print(f"uploads_playlist_items: {len(inventory_rows)}")
    print(f"zenigata_title_matches: {len(zenigata_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
