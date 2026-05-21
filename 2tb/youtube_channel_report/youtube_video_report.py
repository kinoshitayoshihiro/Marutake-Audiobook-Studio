#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]

CORE_ANALYTICS_METRICS = [
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
]

MEMBERSHIP_KEYWORDS = [
    "メンバー限定",
    "メンバーシップ",
    "members only",
    "member only",
]

FINAL_HEADERS = [
    "videoId",
    "title",
    "description",
    "description_length",
    "has_description_synopsis",
    "has_description_characters",
    "has_description_glossary",
    "publishedAt",
    "views",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "impressions",
    "impressionCtr",
    "contentDetails.duration",
    "status.privacyStatus",
    "status.uploadStatus",
    "snippet.liveBroadcastContent",
    "duration_seconds",
    "is_short_candidate",
    "is_live_related",
    "is_public",
    "is_unlisted",
    "is_private",
    "content_type_bucket",
    "membership_flag",
    "membership_rule_source",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build enriched per-video YouTube CSV reports using Analytics, "
            "Data API, and Reporting API reach data."
        )
    )
    parser.add_argument("--client-secrets", default="client_secret.json")
    parser.add_argument("--token-file", default="token.json")
    parser.add_argument("--input-csv", default="youtube_video_report_last_90_days.csv")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--all-output", default="youtube_video_report_last_90_days_all_videos.csv")
    parser.add_argument("--normal-output", default="youtube_video_report_last_90_days_normal_video.csv")
    parser.add_argument("--short-output", default="youtube_video_report_last_90_days_short_candidate.csv")
    parser.add_argument("--membership-overrides", default="membership_overrides.csv")
    return parser.parse_args()


def parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid date: {value}. Expected YYYY-MM-DD.") from exc


def resolve_date_range(args: argparse.Namespace) -> tuple[date, date]:
    end_date = parse_iso_date(args.end_date) if args.end_date else date.today()
    start_date = parse_iso_date(args.start_date) if args.start_date else end_date - timedelta(days=args.days - 1)
    if start_date > end_date:
        raise SystemExit("start-date must be on or before end-date.")
    return start_date, end_date


def normalize_number(value):
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def parse_float(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def to_bool_string(value: bool) -> str:
    return "true" if value else "false"


def detect_description_sections(description: str) -> dict[str, bool | int]:
    text = str(description or "").strip()
    if not text:
        return {
            "description_length": 0,
            "has_description_synopsis": False,
            "has_description_characters": False,
            "has_description_glossary": False,
        }
    synopsis_patterns = [
        r"あらすじ",
        r"梗概",
        r"内容紹介",
        r"物語",
    ]
    character_patterns = [
        r"登場人物",
        r"配役",
        r"出演",
        r"キャラクター",
    ]
    glossary_patterns = [
        r"用語集",
        r"語句",
        r"言葉の意味",
        r"豆知識",
    ]
    return {
        "description_length": len(text),
        "has_description_synopsis": any(re.search(pattern, text) for pattern in synopsis_patterns),
        "has_description_characters": any(re.search(pattern, text) for pattern in character_patterns),
        "has_description_glossary": any(re.search(pattern, text) for pattern in glossary_patterns),
    }


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


def parse_duration_seconds(duration: str) -> int | None:
    if not duration or not duration.startswith("P"):
        return None
    days = hours = minutes = seconds = 0
    number = ""
    in_time = False
    for char in duration[1:]:
        if char == "T":
            in_time = True
            continue
        if char.isdigit():
            number += char
            continue
        if not number:
            continue
        value = int(number)
        number = ""
        if char == "D":
            days = value
        elif char == "H":
            hours = value
        elif char == "M" and in_time:
            minutes = value
        elif char == "S":
            seconds = value
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def load_membership_overrides(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    overrides: Dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            video_id = (row.get("videoId") or "").strip()
            membership_flag = (row.get("membership_flag") or "").strip()
            if video_id and membership_flag:
                overrides[video_id] = membership_flag
    return overrides


def load_existing_base_rows(path: Path) -> Dict[str, Dict[str, object]]:
    if not path.exists():
        return {}
    rows: Dict[str, Dict[str, object]] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            video_id = (row.get("videoId") or "").strip()
            if not video_id:
                continue
            rows[video_id] = {
                "videoId": video_id,
                "title": row.get("title", ""),
                "publishedAt": row.get("publishedAt", ""),
                "views": parse_float(row.get("views")),
                "estimatedMinutesWatched": parse_float(row.get("estimatedMinutesWatched")),
                "averageViewDuration": parse_float(row.get("averageViewDuration")),
                "impressions": parse_float(row.get("impressions")),
                "impressionCtr": parse_float(row.get("impressionCtr")),
            }
    return rows


def fetch_channel_context(youtube) -> Dict[str, str]:
    response = youtube.channels().list(part="snippet,contentDetails", mine=True).execute()
    items = response.get("items", [])
    if not items:
        raise SystemExit("No YouTube channel found for the authenticated account.")
    item = items[0]
    return {
        "title": item["snippet"].get("title", ""),
        "uploads_playlist": item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads", ""),
    }


def fetch_upload_video_ids(youtube, playlist_id: str) -> List[str]:
    if not playlist_id:
        return []
    video_ids: List[str] = []
    page_token = None
    while True:
        response = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in response.get("items", []):
            video_id = item.get("contentDetails", {}).get("videoId", "")
            if video_id:
                video_ids.append(video_id)
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return video_ids


def fetch_core_analytics_rows(analytics, start_date: date, end_date: date) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    start_index = 1
    while True:
        response = (
            analytics.reports()
            .query(
                ids="channel==MINE",
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics=",".join(CORE_ANALYTICS_METRICS),
                dimensions="video",
                sort="-views",
                maxResults=200,
                startIndex=start_index,
            )
            .execute()
        )
        result_rows = response.get("rows", [])
        for row in result_rows:
            rows.append(
                {
                    "videoId": row[0],
                    "views": row[1],
                    "estimatedMinutesWatched": row[2],
                    "averageViewDuration": row[3],
                }
            )
        if len(result_rows) < 200:
            break
        start_index += 200
    return rows


def fetch_core_analytics_rows_for_video_ids(
    analytics,
    start_date: date,
    end_date: date,
    video_ids: Sequence[str],
    batch_size: int = 100,
) -> List[Dict[str, object]]:
    rows_by_video_id: Dict[str, Dict[str, object]] = {}
    for batch in chunked(list(video_ids), batch_size):
        response = (
            analytics.reports()
            .query(
                ids="channel==MINE",
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics=",".join(CORE_ANALYTICS_METRICS),
                dimensions="video",
                filters=f"video=={','.join(batch)}",
                maxResults=min(len(batch), 200),
            )
            .execute()
        )
        for row in response.get("rows", []):
            rows_by_video_id[row[0]] = {
                "videoId": row[0],
                "views": row[1],
                "estimatedMinutesWatched": row[2],
                "averageViewDuration": row[3],
            }
    return list(rows_by_video_id.values())


def build_base_rows(
    analytics,
    input_csv_path: Path,
    start_date: date,
    end_date: date,
    candidate_video_ids: Sequence[str] | None = None,
) -> List[Dict[str, object]]:
    analytics_rows = (
        fetch_core_analytics_rows_for_video_ids(analytics, start_date, end_date, candidate_video_ids)
        if candidate_video_ids
        else fetch_core_analytics_rows(analytics, start_date, end_date)
    )
    existing_rows = load_existing_base_rows(input_csv_path)
    for row in analytics_rows:
        existing = existing_rows.get(str(row["videoId"]), {})
        row["title"] = existing.get("title", "")
        row["publishedAt"] = existing.get("publishedAt", "")
        row["impressions"] = existing.get("impressions")
        row["impressionCtr"] = existing.get("impressionCtr")
    return analytics_rows


def fetch_video_metadata(youtube, video_ids: Sequence[str]) -> Dict[str, Dict[str, str]]:
    metadata_by_video_id: Dict[str, Dict[str, str]] = {}
    for batch in chunked(video_ids, 50):
        response = youtube.videos().list(part="snippet,contentDetails,status", id=",".join(batch), maxResults=50).execute()
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            status = item.get("status", {})
            metadata_by_video_id[item["id"]] = {
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "publishedAt": snippet.get("publishedAt", ""),
                "snippet.liveBroadcastContent": snippet.get("liveBroadcastContent", ""),
                "contentDetails.duration": content_details.get("duration", ""),
                "status.privacyStatus": status.get("privacyStatus", ""),
                "status.uploadStatus": status.get("uploadStatus", ""),
            }
    return metadata_by_video_id


def list_all_reporting_jobs(reporting) -> List[Dict[str, str]]:
    jobs: List[Dict[str, str]] = []
    page_token = None
    while True:
        response = reporting.jobs().list(pageToken=page_token).execute()
        jobs.extend(response.get("jobs", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return jobs


def list_all_report_types(reporting) -> List[Dict[str, str]]:
    report_types: List[Dict[str, str]] = []
    page_token = None
    while True:
        response = reporting.reportTypes().list(pageToken=page_token).execute()
        report_types.extend(response.get("reportTypes", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return report_types


def select_reach_report_type_id(reporting) -> str:
    candidates = [t["id"] for t in list_all_report_types(reporting) if t.get("id", "").startswith("channel_reach_basic_")]
    if not candidates:
        raise SystemExit("No channel reach report type is available for this account.")
    return sorted(candidates)[-1]


def find_or_create_reach_job(reporting, report_type_id: str) -> tuple[str, bool]:
    for job in list_all_reporting_jobs(reporting):
        if job.get("reportTypeId") == report_type_id:
            return job["id"], False
    job = reporting.jobs().create(body={"reportTypeId": report_type_id, "name": f"Reach report {report_type_id}"}).execute()
    return job["id"], True


def list_job_reports(reporting, job_id: str, start_date: date, end_date: date) -> List[Dict[str, str]]:
    reports: List[Dict[str, str]] = []
    page_token = None
    start_time = f"{start_date.isoformat()}T00:00:00Z"
    end_time = f"{(end_date + timedelta(days=1)).isoformat()}T00:00:00Z"
    while True:
        response = reporting.jobs().reports().list(
            jobId=job_id,
            pageToken=page_token,
            startTimeAtOrAfter=start_time,
            startTimeBefore=end_time,
        ).execute()
        reports.extend(response.get("reports", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return reports


def download_report_csv_text(reporting, download_url: str) -> str:
    request = reporting.media().download(resourceName=" ")
    request.uri = download_url
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request, chunksize=-1)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    payload = buffer.getvalue()
    if payload[:2] == b"\x1f\x8b":
        payload = gzip.decompress(payload)
    return payload.decode("utf-8-sig")


def aggregate_reach_by_video_id(reporting, start_date: date, end_date: date) -> tuple[Dict[str, Dict[str, float]], List[str]]:
    warnings: List[str] = []
    report_type_id = select_reach_report_type_id(reporting)
    job_id, job_created = find_or_create_reach_job(reporting, report_type_id)
    if job_created:
        warnings.append("A new YouTube Reporting API reach job was created. Reports may take 24-48 hours to appear.")
    reports = list_job_reports(reporting, job_id, start_date, end_date)
    if not reports:
        warnings.append("No downloadable reach reports are available yet for the requested date range.")
        return {}, warnings
    reach_by_video_id: Dict[str, Dict[str, float]] = {}
    for report in reports:
        csv_text = download_report_csv_text(reporting, report["downloadUrl"])
        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            video_id = row.get("video_id", "")
            impressions_raw = row.get("video_thumbnail_impressions", "")
            ctr_raw = row.get("video_thumbnail_impressions_ctr", "")
            if not video_id or not impressions_raw:
                continue
            impressions = float(impressions_raw)
            ctr_value = float(ctr_raw) if ctr_raw else 0.0
            bucket = reach_by_video_id.setdefault(video_id, {"impressions": 0.0, "ctr_weighted_sum": 0.0})
            bucket["impressions"] += impressions
            bucket["ctr_weighted_sum"] += impressions * ctr_value
    aggregated: Dict[str, Dict[str, float]] = {}
    for video_id, bucket in reach_by_video_id.items():
        impressions = bucket["impressions"]
        aggregated[video_id] = {
            "impressions": impressions,
            "impressionCtr": bucket["ctr_weighted_sum"] / impressions if impressions else 0.0,
        }
    return aggregated, warnings


def classify_membership(video_id: str, title: str, description: str, overrides: Dict[str, str]) -> tuple[str, str]:
    if video_id in overrides:
        return overrides[video_id], "manual_override"
    title_lower = title.lower()
    description_lower = description.lower()
    for keyword in MEMBERSHIP_KEYWORDS:
        keyword_lower = keyword.lower()
        if keyword_lower in title_lower:
            return "suspected_member_only", "title_keyword"
        if keyword_lower in description_lower:
            return "suspected_member_only", "description_keyword"
    return "unknown", ""


def enrich_rows(
    base_rows: Sequence[Dict[str, object]],
    metadata_by_video_id: Dict[str, Dict[str, str]],
    reach_by_video_id: Dict[str, Dict[str, float]],
    membership_overrides: Dict[str, str],
) -> List[Dict[str, object]]:
    enriched_rows: List[Dict[str, object]] = []
    for base_row in base_rows:
        video_id = str(base_row["videoId"])
        metadata = metadata_by_video_id.get(video_id, {})
        title = metadata.get("title") or str(base_row.get("title", "") or "")
        description = metadata.get("description", "")
        published_at = metadata.get("publishedAt") or str(base_row.get("publishedAt", "") or "")
        duration_iso = metadata.get("contentDetails.duration", "")
        duration_seconds = parse_duration_seconds(duration_iso)
        privacy_status = metadata.get("status.privacyStatus", "")
        upload_status = metadata.get("status.uploadStatus", "")
        live_broadcast_content = metadata.get("snippet.liveBroadcastContent", "")
        is_short_candidate = duration_seconds is not None and duration_seconds <= 180
        is_live_related = live_broadcast_content in {"live", "upcoming"}
        if is_short_candidate:
            content_type_bucket = "short_candidate"
        elif is_live_related:
            content_type_bucket = "live_related"
        else:
            content_type_bucket = "normal_video"
        membership_flag, membership_rule_source = classify_membership(video_id, title, description, membership_overrides)
        reach = reach_by_video_id.get(video_id, {})
        impressions = reach.get("impressions", base_row.get("impressions"))
        impression_ctr = reach.get("impressionCtr", base_row.get("impressionCtr"))
        description_sections = detect_description_sections(description)
        enriched_rows.append({
            "videoId": video_id,
            "title": title,
            "description": description,
            "description_length": description_sections["description_length"],
            "has_description_synopsis": to_bool_string(bool(description_sections["has_description_synopsis"])),
            "has_description_characters": to_bool_string(bool(description_sections["has_description_characters"])),
            "has_description_glossary": to_bool_string(bool(description_sections["has_description_glossary"])),
            "publishedAt": published_at,
            "views": base_row.get("views"),
            "estimatedMinutesWatched": base_row.get("estimatedMinutesWatched"),
            "averageViewDuration": base_row.get("averageViewDuration"),
            "impressions": impressions,
            "impressionCtr": impression_ctr,
            "contentDetails.duration": duration_iso,
            "status.privacyStatus": privacy_status,
            "status.uploadStatus": upload_status,
            "snippet.liveBroadcastContent": live_broadcast_content,
            "duration_seconds": duration_seconds if duration_seconds is not None else "",
            "is_short_candidate": to_bool_string(is_short_candidate),
            "is_live_related": to_bool_string(is_live_related),
            "is_public": to_bool_string(privacy_status == "public"),
            "is_unlisted": to_bool_string(privacy_status == "unlisted"),
            "is_private": to_bool_string(privacy_status == "private"),
            "content_type_bucket": content_type_bucket,
            "membership_flag": membership_flag,
            "membership_rule_source": membership_rule_source,
        })
    return enriched_rows


def write_csv(output_path: Path, rows: Sequence[Dict[str, object]]) -> None:
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=FINAL_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_number(row.get(key)) for key in FINAL_HEADERS})


def main() -> int:
    args = parse_args()
    start_date, end_date = resolve_date_range(args)
    base_dir = Path(__file__).resolve().parent
    client_secrets_path = (base_dir / args.client_secrets).resolve()
    token_path = (base_dir / args.token_file).resolve()
    input_csv_path = (base_dir / args.input_csv).resolve()
    all_output_path = (base_dir / args.all_output).resolve()
    normal_output_path = (base_dir / args.normal_output).resolve()
    short_output_path = (base_dir / args.short_output).resolve()
    membership_overrides_path = (base_dir / args.membership_overrides).resolve()
    try:
        creds = load_credentials(client_secrets_path, token_path)
        youtube = build("youtube", "v3", credentials=creds)
        analytics = build("youtubeAnalytics", "v2", credentials=creds)
        reporting = build("youtubereporting", "v1", credentials=creds)
        channel_context = fetch_channel_context(youtube)
        channel_title = channel_context["title"]
        upload_video_ids = fetch_upload_video_ids(youtube, channel_context.get("uploads_playlist", ""))
        base_rows = build_base_rows(analytics, input_csv_path, start_date, end_date, upload_video_ids)
        video_ids = [str(row["videoId"]) for row in base_rows]
        metadata_by_video_id = fetch_video_metadata(youtube, video_ids) if video_ids else {}
        membership_overrides = load_membership_overrides(membership_overrides_path)
        reach_by_video_id, warnings = aggregate_reach_by_video_id(reporting, start_date, end_date)
        enriched_rows = enrich_rows(base_rows, metadata_by_video_id, reach_by_video_id, membership_overrides)
        all_rows = enriched_rows
        normal_rows = [row for row in enriched_rows if row["content_type_bucket"] == "normal_video"]
        short_rows = [row for row in enriched_rows if row["content_type_bucket"] == "short_candidate"]
        write_csv(all_output_path, all_rows)
        write_csv(normal_output_path, normal_rows)
        write_csv(short_output_path, short_rows)
    except HttpError as exc:
        detail = exc.error_details if hasattr(exc, "error_details") else str(exc)
        print(f"API error: {detail}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc!r}", file=sys.stderr)
        return 1
    for message in warnings:
        print(f"Warning: {message}", file=sys.stderr)
    print(f"Enriched export completed for '{channel_title}': {len(all_rows)} videos from {start_date.isoformat()} to {end_date.isoformat()}.")
    print(f"All videos CSV: {all_output_path}")
    print(f"Normal videos CSV: {normal_output_path}")
    print(f"Short candidate CSV: {short_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
