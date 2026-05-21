#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import gzip
import io
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
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

MASTER_EXTRA_HEADERS = [
    "snippet.tags",
    "snippet.categoryId",
    "snippet.defaultAudioLanguage",
    "contentDetails.caption",
    "contentDetails.definition",
    "contentDetails.dimension",
    "contentDetails.licensedContent",
    "contentDetails.projection",
    "status.embeddable",
    "status.madeForKids",
    "statistics.viewCount",
    "statistics.likeCount",
    "statistics.commentCount",
]

DAILY_HEADERS = [
    "date",
    "video_id",
    "views",
    "watch_time_minutes",
    "average_view_duration_seconds",
    "average_view_duration_percentage",
    "impressions",
    "impression_ctr",
    "views_per_impression",
    "watch_time_minutes_per_impression",
    "live_or_on_demand",
    "subscribed_status",
    "data_sources",
]

DAILY_REACH_HEADERS = [
    "date",
    "video_id",
    "impressions",
    "impression_ctr",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build enriched and analysis-ready CSVs for normal videos using "
            "YouTube Data API and YouTube Reporting API."
        )
    )
    parser.add_argument(
        "--client-secrets",
        default="client_secret.json",
        help="Path to OAuth client secrets JSON.",
    )
    parser.add_argument(
        "--token-file",
        default="token.json",
        help="Path to stored OAuth token JSON.",
    )
    parser.add_argument(
        "--input-csv",
        default="youtube_video_report_last_90_days_normal_video.csv",
        help="Existing normal video CSV used as the base video list.",
    )
    parser.add_argument(
        "--master-output",
        default="video_master_enriched.csv",
        help="Output path for the enriched video master CSV.",
    )
    parser.add_argument(
        "--daily-output",
        default="video_daily_analytics.csv",
        help="Output path for per-video daily analytics CSV.",
    )
    parser.add_argument(
        "--analysis-output",
        default="analysis_ready_normal_video.csv",
        help="Output path for the joined daily analysis CSV.",
    )
    parser.add_argument(
        "--report-output",
        default="analysis_ready_normal_video_report.md",
        help="Output path for the markdown summary report.",
    )
    parser.add_argument(
        "--daily-reach-output",
        default="video_daily_reach.csv",
        help="Output path for per-video daily reach CSV.",
    )
    parser.add_argument(
        "--growth-signals-output",
        default="daily_growth_signals.csv",
        help="Output path for growth signal CSV.",
    )
    return parser.parse_args()


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


def parse_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_boolish(value) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value in (None, ""):
        return ""
    return str(value).lower()


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    normalized = str(value).strip()
    if len(normalized) == 8 and normalized.isdigit():
        normalized = f"{normalized[0:4]}-{normalized[4:6]}-{normalized[6:8]}"
    try:
        return date.fromisoformat(normalized[:10])
    except ValueError:
        return None


def chunked(items: Sequence[str], size: int) -> Iterable[Sequence[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def parse_header_name(header: object) -> str:
    if isinstance(header, dict):
        return str(header.get("name", "") or "")
    return str(header or "")


def format_http_error(exc: HttpError) -> str:
    details = getattr(exc, "error_details", None)
    if details:
        return str(details)
    try:
        content = exc.content.decode("utf-8", errors="replace")
    except Exception:
        content = str(exc)
    return content or str(exc)


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
            raise SystemExit(
                "client_secret.json not found. Place the OAuth client JSON at the "
                "specified path."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secrets_path),
            SCOPES,
        )
        creds = flow.run_local_server(
            port=0,
            open_browser=False,
            authorization_prompt_message=(
                "\nOpen this URL in your browser to continue OAuth:\n{url}\n"
            ),
        )

    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def load_base_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if (row.get("videoId") or "").strip()]


def fetch_video_master(youtube, video_ids: Sequence[str]) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for batch in chunked(video_ids, 50):
        response = youtube.videos().list(
            part="snippet,contentDetails,status,statistics",
            id=",".join(batch),
            maxResults=50,
        ).execute()
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            content_details = item.get("contentDetails", {})
            status = item.get("status", {})
            statistics = item.get("statistics", {})
            tags = snippet.get("tags") or []
            result[item["id"]] = {
                "snippet.tags": " | ".join(tags),
                "snippet.categoryId": str(snippet.get("categoryId", "") or ""),
                "snippet.defaultAudioLanguage": str(
                    snippet.get("defaultAudioLanguage", "") or ""
                ),
                "contentDetails.caption": str(
                    content_details.get("caption", "") or ""
                ),
                "contentDetails.definition": str(
                    content_details.get("definition", "") or ""
                ),
                "contentDetails.dimension": str(
                    content_details.get("dimension", "") or ""
                ),
                "contentDetails.licensedContent": parse_boolish(
                    content_details.get("licensedContent")
                ),
                "contentDetails.projection": str(
                    content_details.get("projection", "") or ""
                ),
                "status.embeddable": parse_boolish(status.get("embeddable")),
                "status.madeForKids": parse_boolish(status.get("madeForKids")),
                "statistics.viewCount": str(statistics.get("viewCount", "") or ""),
                "statistics.likeCount": str(statistics.get("likeCount", "") or ""),
                "statistics.commentCount": str(
                    statistics.get("commentCount", "") or ""
                ),
            }
    return result


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


def find_or_create_reporting_job(
    reporting,
    report_type_id: str,
) -> tuple[str, bool]:
    for job in list_all_reporting_jobs(reporting):
        if job.get("reportTypeId") == report_type_id:
            return job["id"], False

    job = (
        reporting.jobs()
        .create(
            body={
                "reportTypeId": report_type_id,
                "name": f"{report_type_id} auto-created",
            }
        )
        .execute()
    )
    return job["id"], True


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
    candidates = [
        report_type["id"]
        for report_type in list_all_report_types(reporting)
        if report_type.get("id", "").startswith("channel_reach_basic_")
    ]
    if not candidates:
        raise SystemExit(
            "No channel reach report type is available for this account in the "
            "YouTube Reporting API."
        )
    return sorted(candidates)[-1]


def list_job_reports(reporting, job_id: str) -> List[Dict[str, str]]:
    reports: List[Dict[str, str]] = []
    page_token = None
    while True:
        response = (
            reporting.jobs()
            .reports()
            .list(
                jobId=job_id,
                pageToken=page_token,
            )
            .execute()
        )
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


def pick_first_key(row: Dict[str, str], candidates: Sequence[str]) -> str:
    for key in candidates:
        if key in row:
            return key
    return ""


def parse_reporting_rows(csv_text: str) -> List[Dict[str, str]]:
    parsed_rows: List[Dict[str, str]] = []
    reader = csv.DictReader(io.StringIO(csv_text))
    for source_row in reader:
        if not source_row:
            continue

        date_key = pick_first_key(source_row, ["day", "date"])
        video_key = pick_first_key(source_row, ["video_id", "video"])
        views_key = pick_first_key(source_row, ["views"])
        watch_key = pick_first_key(
            source_row,
            [
                "watch_time_minutes",
                "estimated_minutes_watched",
                "estimated_watch_time_minutes",
            ],
        )
        avg_seconds_key = pick_first_key(
            source_row,
            [
                "average_view_duration_seconds",
                "average_view_duration",
            ],
        )
        avg_pct_key = pick_first_key(
            source_row,
            [
                "average_view_duration_percentage",
                "average_view_percentage",
            ],
        )
        live_key = pick_first_key(
            source_row,
            [
                "live_or_on_demand",
                "live_or_on_demand_detail",
            ],
        )
        subscribed_key = pick_first_key(
            source_row,
            [
                "subscribed_status",
                "subscribed_status_detail",
            ],
        )

        normalized = {
            "date": (source_row.get(date_key, "") or "")[:10],
            "video_id": source_row.get(video_key, "") or "",
            "views": source_row.get(views_key, "") or "",
            "watch_time_minutes": source_row.get(watch_key, "") or "",
            "average_view_duration_seconds": source_row.get(avg_seconds_key, "") or "",
            "average_view_duration_percentage": source_row.get(avg_pct_key, "") or "",
            "impressions": "",
            "impression_ctr": "",
            "views_per_impression": "",
            "watch_time_minutes_per_impression": "",
            "live_or_on_demand": source_row.get(live_key, "") or "",
            "subscribed_status": source_row.get(subscribed_key, "") or "",
            "data_sources": "reporting_api",
        }
        if normalized["date"] and normalized["video_id"]:
            parsed_rows.append(normalized)
    return parsed_rows


def query_analytics_rows(
    analytics,
    *,
    start_date: date,
    end_date: date,
    metrics: Sequence[str],
    dimensions: str = "day,video",
    sort: str = "day,video",
    filters: str | None = None,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    start_index = 1
    max_results = 200

    while True:
        response = (
            analytics.reports()
            .query(
                ids="channel==MINE",
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics=",".join(metrics),
                dimensions=dimensions,
                sort=sort,
                filters=filters,
                maxResults=max_results,
                startIndex=start_index,
            )
            .execute()
        )

        header_names = [
            parse_header_name(header) for header in response.get("columnHeaders", [])
        ]
        result_rows = response.get("rows", [])
        for values in result_rows:
            rows.append(dict(zip(header_names, values)))

        if len(result_rows) < max_results:
            break
        start_index += max_results

    return rows


def fetch_daily_analytics_rows(
    analytics,
    start_date: date,
    end_date: date,
    video_ids: Sequence[str],
) -> List[Dict[str, str]]:
    normalized_rows: List[Dict[str, str]] = []
    for batch in chunked(list(video_ids), 200):
        if not batch:
            continue
        source_rows = query_analytics_rows(
            analytics,
            start_date=start_date,
            end_date=end_date,
            metrics=[
                "views",
                "estimatedMinutesWatched",
                "averageViewDuration",
                "averageViewPercentage",
            ],
            dimensions="day,video",
            sort="day,video",
            filters=f"video=={','.join(batch)}",
        )

        for source_row in source_rows:
            row = {
                "date": str(source_row.get("day", "") or "")[:10],
                "video_id": str(source_row.get("video", "") or ""),
                "views": str(source_row.get("views", "") or ""),
                "watch_time_minutes": str(
                    source_row.get("estimatedMinutesWatched", "") or ""
                ),
                "average_view_duration_seconds": str(
                    source_row.get("averageViewDuration", "") or ""
                ),
                "average_view_duration_percentage": str(
                    source_row.get("averageViewPercentage", "") or ""
                ),
                "impressions": "",
                "impression_ctr": "",
                "views_per_impression": "",
                "watch_time_minutes_per_impression": "",
                "live_or_on_demand": "",
                "subscribed_status": "",
                "data_sources": "analytics_api",
            }
            if row["date"] and row["video_id"]:
                normalized_rows.append(row)

    return normalized_rows


def fetch_daily_reach_rows(
    analytics,
    start_date: date,
    end_date: date,
    video_ids: Sequence[str],
) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for batch in chunked(list(video_ids), 200):
        if not batch:
            continue
        source_rows = query_analytics_rows(
            analytics,
            start_date=start_date,
            end_date=end_date,
            metrics=[
                "videoThumbnailImpressions",
                "videoThumbnailImpressionsClickRate",
            ],
            dimensions="day,video",
            sort="day,video",
            filters=f"video=={','.join(batch)}",
        )

        for source_row in source_rows:
            row = {
                "date": str(source_row.get("day", "") or "")[:10],
                "video_id": str(source_row.get("video", "") or ""),
                "impressions": str(
                    source_row.get("videoThumbnailImpressions", "") or ""
                ),
                "impression_ctr": str(
                    source_row.get("videoThumbnailImpressionsClickRate", "") or ""
                ),
            }
            if row["date"] and row["video_id"]:
                rows.append(row)
    return rows


def aggregate_reporting_rows(
    rows: Sequence[Dict[str, str]],
) -> List[Dict[str, str]]:
    aggregated: Dict[tuple[str, str], Dict[str, object]] = {}
    for row in rows:
        key = (row["date"], row["video_id"])
        bucket = aggregated.setdefault(
            key,
            {
                "date": row["date"],
                "video_id": row["video_id"],
                "views": 0.0,
                "watch_time_minutes": 0.0,
                "avg_duration_num": 0.0,
                "avg_duration_den": 0.0,
                "avg_pct_num": 0.0,
                "avg_pct_den": 0.0,
                "live_values": set(),
                "subscribed_values": set(),
            },
        )

        views = parse_float(row.get("views")) or 0.0
        watch_time_minutes = parse_float(row.get("watch_time_minutes")) or 0.0
        avg_duration_seconds = parse_float(row.get("average_view_duration_seconds"))
        avg_view_pct = parse_float(row.get("average_view_duration_percentage"))
        live_value = row.get("live_or_on_demand", "")
        subscribed_value = row.get("subscribed_status", "")

        bucket["views"] += views
        bucket["watch_time_minutes"] += watch_time_minutes
        if avg_duration_seconds is not None and views > 0:
            bucket["avg_duration_num"] += avg_duration_seconds * views
            bucket["avg_duration_den"] += views
        if avg_view_pct is not None and views > 0:
            bucket["avg_pct_num"] += avg_view_pct * views
            bucket["avg_pct_den"] += views
        if live_value:
            bucket["live_values"].add(live_value)
        if subscribed_value:
            bucket["subscribed_values"].add(subscribed_value)

    normalized_rows: List[Dict[str, str]] = []
    for bucket in aggregated.values():
        avg_duration = safe_div(bucket["avg_duration_num"], bucket["avg_duration_den"])
        avg_pct = safe_div(bucket["avg_pct_num"], bucket["avg_pct_den"])
        live_values = sorted(bucket["live_values"])
        subscribed_values = sorted(bucket["subscribed_values"])
        normalized_rows.append(
            {
                "date": str(bucket["date"]),
                "video_id": str(bucket["video_id"]),
                "views": str(int(bucket["views"])) if bucket["views"] else "",
                "watch_time_minutes": normalize_number(bucket["watch_time_minutes"]),
                "average_view_duration_seconds": normalize_number(avg_duration),
                "average_view_duration_percentage": normalize_number(avg_pct),
                "impressions": "",
                "impression_ctr": "",
                "views_per_impression": "",
                "watch_time_minutes_per_impression": "",
                "live_or_on_demand": (
                    live_values[0]
                    if len(live_values) == 1
                    else ("mixed" if live_values else "")
                ),
                "subscribed_status": (
                    subscribed_values[0]
                    if len(subscribed_values) == 1
                    else ("mixed" if subscribed_values else "")
                ),
                "data_sources": "reporting_api",
            }
        )

    normalized_rows.sort(key=lambda row: (row["date"], row["video_id"]))
    return normalized_rows


def fetch_daily_reporting_reach_rows(
    reporting,
) -> tuple[List[Dict[str, str]], List[str]]:
    warnings: List[str] = []
    report_type_id = select_reach_report_type_id(reporting)
    job_id, created = find_or_create_reporting_job(reporting, report_type_id)
    if created:
        warnings.append(
            "A new channel reach reporting job was created. Reports may take 24-48 hours to appear."
        )

    reports = list_job_reports(reporting, job_id)
    if not reports:
        warnings.append(
            "No downloadable channel reach reports are available for this account yet."
        )
        return [], warnings

    rows: List[Dict[str, str]] = []
    for report in reports:
        csv_text = download_report_csv_text(reporting, report["downloadUrl"])
        reader = csv.DictReader(io.StringIO(csv_text))
        report_start = str(report.get("startTime", "") or "")[:10]
        for source_row in reader:
            if not source_row:
                continue
            date_key = pick_first_key(source_row, ["day", "date"])
            video_key = pick_first_key(source_row, ["video_id", "video"])
            impressions_key = pick_first_key(
                source_row,
                ["video_thumbnail_impressions", "videoThumbnailImpressions"],
            )
            ctr_key = pick_first_key(
                source_row,
                [
                    "video_thumbnail_impressions_ctr",
                    "video_thumbnail_impressions_click_rate",
                    "videoThumbnailImpressionsClickRate",
                ],
            )
            row = {
                "date": ((source_row.get(date_key, "") or report_start)[:10]),
                "video_id": source_row.get(video_key, "") or "",
                "impressions": source_row.get(impressions_key, "") or "",
                "impression_ctr": source_row.get(ctr_key, "") or "",
            }
            if row["date"] and row["video_id"] and row["impressions"]:
                rows.append(row)

    deduped: Dict[tuple[str, str], Dict[str, str]] = {}
    for row in rows:
        deduped[(row["date"], row["video_id"])] = row

    normalized_rows = sorted(
        deduped.values(),
        key=lambda row: (row["date"], row["video_id"]),
    )
    return normalized_rows, warnings


def merge_daily_rows(
    analytics_rows: Sequence[Dict[str, str]],
    reach_rows: Sequence[Dict[str, str]],
    reporting_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, str]]:
    merged: Dict[tuple[str, str], Dict[str, str]] = {}

    def ensure_row(row: Dict[str, str]) -> Dict[str, str]:
        key = (row.get("date", ""), row.get("video_id", ""))
        bucket = merged.setdefault(
            key,
            {header: "" for header in DAILY_HEADERS},
        )
        bucket["date"] = key[0]
        bucket["video_id"] = key[1]
        return bucket

    for row in reporting_rows:
        bucket = ensure_row(row)
        for key in [
            "views",
            "watch_time_minutes",
            "average_view_duration_seconds",
            "average_view_duration_percentage",
            "live_or_on_demand",
            "subscribed_status",
        ]:
            if row.get(key, ""):
                bucket[key] = row[key]
        bucket["data_sources"] = "reporting_api"

    for row in analytics_rows:
        bucket = ensure_row(row)
        for key in [
            "views",
            "watch_time_minutes",
            "average_view_duration_seconds",
            "average_view_duration_percentage",
        ]:
            if row.get(key, ""):
                bucket[key] = row[key]
        sources = {value for value in bucket["data_sources"].split("+") if value}
        sources.add("analytics_api")
        bucket["data_sources"] = "+".join(sorted(sources))

    for row in reach_rows:
        bucket = ensure_row(row)
        if row.get("impressions", ""):
            bucket["impressions"] = row["impressions"]
        if row.get("impression_ctr", ""):
            bucket["impression_ctr"] = row["impression_ctr"]
        sources = {value for value in bucket["data_sources"].split("+") if value}
        sources.add("reach_api")
        bucket["data_sources"] = "+".join(sorted(sources))

    normalized_rows: List[Dict[str, str]] = []
    for row in merged.values():
        views = parse_float(row.get("views"))
        watch_time_minutes = parse_float(row.get("watch_time_minutes"))
        impressions = parse_float(row.get("impressions"))
        row["views_per_impression"] = normalize_number(
            safe_div(views or 0.0, impressions or 0.0)
        )
        row["watch_time_minutes_per_impression"] = normalize_number(
            safe_div(watch_time_minutes or 0.0, impressions or 0.0)
        )
        normalized_rows.append(row)

    normalized_rows.sort(key=lambda row: (row["date"], row["video_id"]))
    return normalized_rows


def fetch_daily_reporting_rows(
    reporting,
    report_type_id: str = "channel_basic_a3",
) -> tuple[List[Dict[str, str]], List[str]]:
    warnings: List[str] = []
    job_id, created = find_or_create_reporting_job(reporting, report_type_id)
    if created:
        warnings.append(
            "A new channel_basic_a3 reporting job was created. Reports may take "
            "24-48 hours to appear, and backfill is limited by YouTube."
        )

    reports = list_job_reports(reporting, job_id)
    if not reports:
        warnings.append(
            "No downloadable channel_basic_a3 reports are available for this "
            "account yet."
        )
        return [], warnings

    rows: List[Dict[str, str]] = []
    for report in reports:
        csv_text = download_report_csv_text(reporting, report["downloadUrl"])
        rows.extend(parse_reporting_rows(csv_text))

    return aggregate_reporting_rows(rows), warnings


def write_csv(
    output_path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Dict[str, object]],
) -> None:
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: normalize_number(row.get(key)) for key in fieldnames})


def build_master_rows(
    base_rows: Sequence[Dict[str, str]],
    metadata_by_video_id: Dict[str, Dict[str, str]],
) -> tuple[List[str], List[Dict[str, str]]]:
    headers = list(base_rows[0].keys()) if base_rows else ["videoId"]
    for header in MASTER_EXTRA_HEADERS:
        if header not in headers:
            headers.append(header)

    rows: List[Dict[str, str]] = []
    for base_row in base_rows:
        row = dict(base_row)
        metadata = metadata_by_video_id.get(base_row["videoId"], {})
        for header in MASTER_EXTRA_HEADERS:
            row[header] = metadata.get(header, "")
        rows.append(row)
    return headers, rows


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.replace("\u3000", " ")).strip()


def classify_series(title: str) -> tuple[str, str]:
    original = normalize_title(title)

    if any(marker in original for marker in ["MusicVideo", "ミュージックビデオ", "主題歌"]):
        return "主題歌/MV", ""

    if "銭形平次捕物控" in original:
        return "銭形平次捕物控", ""
    if "七之助捕物帳" in original:
        return "七之助捕物帳", ""
    if "池田大助捕物帳" in original:
        return "池田大助捕物帳", ""

    if any(marker in original for marker in ["怪談", "小泉八雲", "雪女", "耳無し芳一", "ろくろ首", "お貞", "乳母桜", "おしどり", "葬られたる秘密", "かけひき"]):
        sub = "八雲" if "小泉八雲" in original or any(
            marker in original
            for marker in ["雪女", "耳無し芳一", "ろくろ首", "お貞", "乳母桜", "おしどり", "葬られたる秘密", "かけひき"]
        ) else "その他"
        return "怪談", sub

    if any(
        marker in original
        for marker in [
            "山本周五郎",
            "日本婦道記",
            "浪人三部作",
            "浪人一代男",
            "浪人走馬灯",
            "ながい坂",
            "菊千代抄",
            "初蕾",
            "七日七夜",
            "赤緒の草鞋",
            "不断草",
        ]
    ):
        if any(marker in original for marker in ["日本婦道記", "墨丸", "横笛", "梅咲きぬ", "箭竹", "藪の蔭", "二十三年"]):
            return "山本周五郎", "日本婦道記"
        if any(marker in original for marker in ["浪人三部作", "浪人一代男", "浪人走馬灯", "七日七夜", "赤緒の草鞋", "不断草"]):
            return "山本周五郎", "浪人もの"
        if any(marker in original for marker in ["ながい坂", "菊千代抄", "初蕾"]):
            return "山本周五郎", "長編まとめ"
        return "山本周五郎", "その他"

    return "その他", ""


def extract_series_name(title: str) -> str:
    parent, _ = classify_series(title)
    return parent


def classify_video_format(title: str) -> str:
    normalized = normalize_title(title)
    if "第一集" in normalized:
        return "第一集"
    if "三部作" in normalized:
        return "三部作"
    if any(marker in normalized for marker in ["総集編", "傑作選", "まとめ", "一挙", "一気", "完全版", "三つの事件"]):
        return "総集編/傑作選"
    if "長編朗読連載" in normalized or (
        any(marker in normalized for marker in ["ながい坂", "お部屋様お退屈"])
        and any(marker in normalized for marker in ["第一巻", "第二巻", "第三巻", "第四巻", "第五話"])
    ):
        return "長編連載"
    if any(marker in normalized for marker in ["聴くドラマ", "一人でドラマ"]):
        return "聴くドラマ/一人でドラマ"
    if any(marker in normalized for marker in ["睡眠", "作業用", "睡眠導入", "BGM"]):
        return "睡眠・作業用"
    return "単話"


def escape_md(value: object) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ").strip()


def safe_div(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def merge_analysis_rows(
    base_rows: Sequence[Dict[str, str]],
    master_rows: Sequence[Dict[str, str]],
    daily_rows: Sequence[Dict[str, str]],
) -> tuple[List[str], List[Dict[str, object]]]:
    base_by_video_id = {row["videoId"]: row for row in base_rows}
    master_by_video_id = {row["videoId"]: row for row in master_rows}

    base_headers = list(base_rows[0].keys()) if base_rows else ["videoId"]
    base_only_headers = [
        header for header in base_headers if header not in DAILY_HEADERS
    ]
    master_only_headers = [
        header
        for header in (master_rows[0].keys() if master_rows else [])
        if header not in base_headers and header not in DAILY_HEADERS
    ]
    analysis_headers = (
        DAILY_HEADERS
        + ["series_name", "series_sub", "video_format"]
        + base_only_headers
        + master_only_headers
    )

    rows: List[Dict[str, object]] = []
    if daily_rows:
        for daily_row in daily_rows:
            video_id = daily_row["video_id"]
            base = base_by_video_id.get(video_id, {})
            master = master_by_video_id.get(video_id, {})
            title = base.get("title") or master.get("title") or ""
            series_name, series_sub = classify_series(title)
            merged: Dict[str, object] = {
                key: daily_row.get(key, "") for key in DAILY_HEADERS
            }
            merged["series_name"] = series_name
            merged["series_sub"] = series_sub
            merged["video_format"] = classify_video_format(title)
            for header in base_only_headers:
                merged[header] = base.get(header, "")
            for header in master_only_headers:
                merged[header] = master.get(header, "")
            rows.append(merged)
    else:
        for master_row in master_rows:
            video_id = master_row["videoId"]
            base = base_by_video_id.get(video_id, {})
            title = base.get("title") or master_row.get("title") or ""
            series_name, series_sub = classify_series(title)
            merged: Dict[str, object] = {key: "" for key in DAILY_HEADERS}
            merged["video_id"] = video_id
            merged["series_name"] = series_name
            merged["series_sub"] = series_sub
            merged["video_format"] = classify_video_format(title)
            for header in base_only_headers:
                merged[header] = base.get(header, "")
            for header in master_only_headers:
                merged[header] = master_row.get(header, "")
            rows.append(merged)

    rows.sort(key=lambda row: (row["date"], row["video_id"]))
    return analysis_headers, rows


def build_growth_signal_rows(
    analysis_rows: Sequence[Dict[str, object]],
    master_rows: Sequence[Dict[str, str]],
) -> List[Dict[str, object]]:
    if not analysis_rows:
        return []

    published_date_by_video_id: Dict[str, date] = {}
    title_by_video_id: Dict[str, str] = {}
    parent_by_video_id: Dict[str, str] = {}
    sub_by_video_id: Dict[str, str] = {}
    format_by_video_id: Dict[str, str] = {}
    for row in master_rows:
        video_id = row.get("videoId", "")
        if not video_id:
            continue
        title = row.get("title", "")
        parent, sub = classify_series(title)
        published_date_by_video_id[video_id] = parse_iso_date(row.get("publishedAt"))
        title_by_video_id[video_id] = title
        parent_by_video_id[video_id] = parent
        sub_by_video_id[video_id] = sub
        format_by_video_id[video_id] = classify_video_format(title)

    per_video_days: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    max_row_date: date | None = None
    for row in analysis_rows:
        video_id = str(row.get("video_id", "") or "")
        row_date = parse_iso_date(str(row.get("date", "") or ""))
        if not video_id or not row_date:
            continue
        if max_row_date is None or row_date > max_row_date:
            max_row_date = row_date
        per_video_days[video_id].append(
            {
                "date": row_date,
                "views": parse_float(str(row.get("views", "") or "")) or 0.0,
                "watch_time_minutes": parse_float(
                    str(row.get("watch_time_minutes", "") or "")
                )
                or 0.0,
                "impressions": parse_float(str(row.get("impressions", "") or "")) or 0.0,
                "impression_ctr": parse_float(
                    str(row.get("impression_ctr", "") or "")
                ),
            }
        )

    def sum_metric(items: Sequence[Dict[str, object]], key: str) -> float:
        return sum(float(item.get(key, 0.0) or 0.0) for item in items)

    def weighted_ctr(items: Sequence[Dict[str, object]]) -> float | None:
        impressions = sum_metric(items, "impressions")
        if impressions <= 0:
            return None
        ctr_weighted_sum = 0.0
        for item in items:
            ctr = item.get("impression_ctr")
            item_impressions = float(item.get("impressions", 0.0) or 0.0)
            if ctr is None or item_impressions <= 0:
                continue
            ctr_weighted_sum += float(ctr) * item_impressions
        return safe_div(ctr_weighted_sum, impressions)

    signal_rows: List[Dict[str, object]] = []
    for video_id, day_rows in per_video_days.items():
        published_date = published_date_by_video_id.get(video_id)
        if not published_date:
            continue

        sorted_rows = sorted(day_rows, key=lambda item: item["date"])
        last_date = sorted_rows[-1]["date"]
        age_days = (last_date - published_date).days + 1

        first_3d = [
            row for row in sorted_rows if published_date <= row["date"] <= published_date + timedelta(days=2)
        ]
        first_7d = [
            row for row in sorted_rows if published_date <= row["date"] <= published_date + timedelta(days=6)
        ]
        first_14d = [
            row for row in sorted_rows if published_date <= row["date"] <= published_date + timedelta(days=13)
        ]

        if max_row_date:
            last_7d = [
                row for row in sorted_rows if max_row_date - timedelta(days=6) <= row["date"] <= max_row_date
            ]
            prev_7d = [
                row
                for row in sorted_rows
                if max_row_date - timedelta(days=13) <= row["date"] < max_row_date - timedelta(days=6)
            ]
        else:
            last_7d = []
            prev_7d = []

        first_3d_impressions = sum_metric(first_3d, "impressions")
        first_7d_impressions = sum_metric(first_7d, "impressions")
        first_14d_impressions = sum_metric(first_14d, "impressions")
        last_7d_impressions = sum_metric(last_7d, "impressions")
        prev_7d_impressions = sum_metric(prev_7d, "impressions")
        last_7d_views = sum_metric(last_7d, "views")
        prev_7d_views = sum_metric(prev_7d, "views")
        last_7d_watch = sum_metric(last_7d, "watch_time_minutes")

        signal_score = (
            (weighted_ctr(last_7d) or 0.0) * 1000.0
            + (safe_div(last_7d_impressions, 7.0) or 0.0)
            + (safe_div(last_7d_watch, max(last_7d_impressions, 1.0)) or 0.0) * 100.0
        )

        signal_rows.append(
            {
                "video_id": video_id,
                "title": title_by_video_id.get(video_id, ""),
                "series_name": parent_by_video_id.get(video_id, "その他"),
                "series_sub": sub_by_video_id.get(video_id, ""),
                "video_format": format_by_video_id.get(video_id, "単話"),
                "publishedAt": published_date.isoformat(),
                "data_last_date": last_date.isoformat(),
                "age_days": age_days,
                "first_3d_impressions": first_3d_impressions,
                "first_7d_impressions": first_7d_impressions,
                "first_14d_impressions": first_14d_impressions,
                "first_7d_ctr": weighted_ctr(first_7d),
                "last_7d_impressions": last_7d_impressions,
                "prev_7d_impressions": prev_7d_impressions,
                "impression_growth_rate_7d": safe_div(
                    last_7d_impressions - prev_7d_impressions,
                    prev_7d_impressions,
                ),
                "last_7d_views": last_7d_views,
                "prev_7d_views": prev_7d_views,
                "view_growth_rate_7d": safe_div(
                    last_7d_views - prev_7d_views,
                    prev_7d_views,
                ),
                "last_7d_watch_time_minutes": last_7d_watch,
                "last_7d_ctr": weighted_ctr(last_7d),
                "last_7d_views_per_impression": safe_div(
                    last_7d_views,
                    last_7d_impressions,
                ),
                "last_7d_watch_time_minutes_per_impression": safe_div(
                    last_7d_watch,
                    last_7d_impressions,
                ),
                "signal_score": signal_score,
            }
        )

    signal_rows.sort(
        key=lambda row: (
            float(row.get("signal_score") or 0.0),
            float(row.get("last_7d_impressions") or 0.0),
        ),
        reverse=True,
    )
    return signal_rows


def build_markdown_report(
    analysis_rows: Sequence[Dict[str, object]],
    master_rows: Sequence[Dict[str, str]],
    available_start: date | None,
    available_end: date | None,
    growth_signal_rows: Sequence[Dict[str, object]] | None = None,
) -> str:
    published_date_by_video_id: Dict[str, date] = {}
    title_by_video_id: Dict[str, str] = {}
    parent_by_video_id: Dict[str, str] = {}
    sub_by_video_id: Dict[str, str] = {}
    format_by_video_id: Dict[str, str] = {}
    for row in master_rows:
        video_id = row.get("videoId", "")
        if not video_id:
            continue
        title = row.get("title", "")
        parent, sub = classify_series(title)
        published_date_by_video_id[video_id] = parse_iso_date(row.get("publishedAt"))
        title_by_video_id[video_id] = title
        parent_by_video_id[video_id] = parent
        sub_by_video_id[video_id] = sub
        format_by_video_id[video_id] = classify_video_format(title)

    aggregate_by_video: Dict[str, Dict[str, object]] = {}
    parent_totals: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"videos": 0, "views": 0.0, "watch_time_minutes": 0.0}
    )
    sub_totals: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"videos": 0, "views": 0.0, "watch_time_minutes": 0.0}
    )
    format_totals: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {
            "videos": 0,
            "views": 0.0,
            "watch_time_minutes": 0.0,
            "avg_view_pct_weighted_num": 0.0,
            "avg_view_pct_weighted_den": 0.0,
        }
    )

    def register_video(
        video_id: str,
        title: str,
        parent: str,
        sub: str,
        video_format: str,
        views: float,
        watch_time_minutes: float,
        avg_view_pct: float | None,
        first_7d_views: float = 0.0,
    ) -> None:
        aggregate_by_video[video_id] = {
            "title": title,
            "series_parent": parent,
            "series_sub": sub,
            "video_format": video_format,
            "views": views,
            "watch_time_minutes": watch_time_minutes,
            "avg_view_pct_weighted_num": (avg_view_pct or 0.0) * views,
            "avg_view_pct_weighted_den": views if avg_view_pct is not None else 0.0,
            "first_7d_views": first_7d_views,
        }
        parent_totals[parent]["videos"] += 1
        parent_totals[parent]["views"] += views
        parent_totals[parent]["watch_time_minutes"] += watch_time_minutes
        sub_label = f"{parent} > {sub or '全般'}"
        sub_totals[sub_label]["videos"] += 1
        sub_totals[sub_label]["views"] += views
        sub_totals[sub_label]["watch_time_minutes"] += watch_time_minutes
        format_totals[video_format]["videos"] += 1
        format_totals[video_format]["views"] += views
        format_totals[video_format]["watch_time_minutes"] += watch_time_minutes
        if avg_view_pct is not None and views > 0:
            format_totals[video_format]["avg_view_pct_weighted_num"] += avg_view_pct * views
            format_totals[video_format]["avg_view_pct_weighted_den"] += views

    if analysis_rows:
        per_video: Dict[str, Dict[str, object]] = {}
        for row in analysis_rows:
            video_id = str(row.get("video_id", "") or "")
            if not video_id:
                continue
            title = title_by_video_id.get(video_id, str(row.get("title", "") or ""))
            parent = parent_by_video_id.get(video_id, "その他")
            sub = sub_by_video_id.get(video_id, "")
            video_format = format_by_video_id.get(video_id, "単話")
            views = parse_float(str(row.get("views", "") or "")) or 0.0
            watch_time_minutes = parse_float(str(row.get("watch_time_minutes", "") or "")) or 0.0
            avg_view_pct = parse_float(str(row.get("average_view_duration_percentage", "") or ""))
            row_date = parse_iso_date(str(row.get("date", "") or ""))
            bucket = per_video.setdefault(
                video_id,
                {
                    "title": title,
                    "parent": parent,
                    "sub": sub,
                    "video_format": video_format,
                    "views": 0.0,
                    "watch_time_minutes": 0.0,
                    "avg_view_pct_weighted_num": 0.0,
                    "avg_view_pct_weighted_den": 0.0,
                    "first_7d_views": 0.0,
                },
            )
            bucket["views"] += views
            bucket["watch_time_minutes"] += watch_time_minutes
            if avg_view_pct is not None and views > 0:
                bucket["avg_view_pct_weighted_num"] += avg_view_pct * views
                bucket["avg_view_pct_weighted_den"] += views
            published_date = published_date_by_video_id.get(video_id)
            if published_date and row_date and published_date <= row_date <= published_date + timedelta(days=6):
                bucket["first_7d_views"] += views

        for video_id, bucket in per_video.items():
            avg_pct = safe_div(bucket["avg_view_pct_weighted_num"], bucket["avg_view_pct_weighted_den"])
            register_video(
                video_id,
                str(bucket["title"]),
                str(bucket["parent"]),
                str(bucket["sub"]),
                str(bucket["video_format"]),
                float(bucket["views"]),
                float(bucket["watch_time_minutes"]),
                avg_pct,
                float(bucket["first_7d_views"]),
            )
    else:
        for row in master_rows:
            video_id = row.get("videoId", "")
            if not video_id:
                continue
            title = row.get("title", "")
            parent, sub = classify_series(title)
            video_format = classify_video_format(title)
            views = parse_float(row.get("views")) or 0.0
            watch_time_minutes = parse_float(row.get("estimatedMinutesWatched")) or 0.0
            avg_view_duration = parse_float(row.get("averageViewDuration"))
            duration_seconds = parse_int(row.get("duration_seconds"))
            avg_view_pct = None
            if avg_view_duration is not None and duration_seconds:
                avg_view_pct = (avg_view_duration / duration_seconds) * 100
            register_video(
                video_id,
                title,
                parent,
                sub,
                video_format,
                views,
                watch_time_minutes,
                avg_view_pct,
            )

    def top_rows(metric_key: str) -> List[Dict[str, object]]:
        sortable = []
        for video_id, bucket in aggregate_by_video.items():
            row = dict(bucket)
            row["video_id"] = video_id
            if metric_key == "avg_view_pct":
                row["metric"] = safe_div(
                    row["avg_view_pct_weighted_num"],
                    row["avg_view_pct_weighted_den"],
                ) or 0.0
            else:
                row["metric"] = float(row.get(metric_key, 0.0))
            sortable.append(row)
        sortable.sort(key=lambda row: row["metric"], reverse=True)
        return sortable[:20]

    def ranking_rows(source: Dict[str, Dict[str, float]], label_key: str) -> List[Dict[str, object]]:
        rows: List[Dict[str, object]] = []
        for label, bucket in source.items():
            rows.append(
                {
                    label_key: label,
                    "videos": int(bucket["videos"]),
                    "views": bucket["views"],
                    "watch_time_minutes": bucket["watch_time_minutes"],
                }
            )
        rows.sort(key=lambda row: row["watch_time_minutes"], reverse=True)
        return rows

    top_watch_time = top_rows("watch_time_minutes")
    top_avg_pct = top_rows("avg_view_pct")
    top_first_7d = top_rows("first_7d_views")
    parent_rows = ranking_rows(parent_totals, "series_parent")
    sub_rows = ranking_rows(sub_totals, "series_sub")

    format_rows = []
    for video_format, bucket in format_totals.items():
        format_rows.append(
            {
                "video_format": video_format,
                "videos": int(bucket["videos"]),
                "views": bucket["views"],
                "watch_time_minutes": bucket["watch_time_minutes"],
                "average_view_duration_percentage": safe_div(
                    bucket["avg_view_pct_weighted_num"],
                    bucket["avg_view_pct_weighted_den"],
                ),
            }
        )
    format_rows.sort(key=lambda row: row["watch_time_minutes"], reverse=True)

    total_watch_time = sum(float(row["watch_time_minutes"]) for row in aggregate_by_video.values())
    total_views = sum(float(row["views"]) for row in aggregate_by_video.values())
    top3_watch_share = safe_div(sum(float(row["metric"]) for row in top_watch_time[:3]), total_watch_time)
    top3_titles = " / ".join(escape_md(row["title"]) for row in top_watch_time[:3])
    top_retention_title = escape_md(top_avg_pct[0]["title"]) if top_avg_pct else ""
    top_retention_value = top_avg_pct[0]["metric"] if top_avg_pct else None
    top_parent_name = escape_md(parent_rows[0]["series_parent"]) if parent_rows else ""
    top_parent_watch_time = parent_rows[0]["watch_time_minutes"] if parent_rows else 0.0
    format_map = {row["video_format"]: row for row in format_rows}
    single_row = format_map.get("単話")

    lines: List[str] = []
    lines.append("# normal_video 運用レポート")
    lines.append("")
    lines.append("## 期間と前提")
    lines.append("")
    lines.append(f"- 対象動画数: {len(aggregate_by_video)}")
    lines.append(f"- 合計 views: {total_views:,.0f}")
    lines.append(f"- 合計 watch_time_minutes: {total_watch_time:,.1f}")
    if available_start and available_end:
        lines.append(f"- 日次データ取得期間: {available_start.isoformat()} から {available_end.isoformat()}")
    else:
        lines.append("- 日次データ取得期間: 日次 analytics / reach データ未取得")
    if not analysis_rows:
        lines.append("- 注記: 日次データ未取得のため、視聴時間・完読率・シリーズ比較は既存 normal_video.csv の累積値ベース")
    lines.append("")

    lines.append("## 運用サマリー")
    lines.append("")
    if top3_watch_share is not None:
        lines.append(f"- 視聴時間の上位3本で全体の {top3_watch_share * 100:,.1f}% を占有")
    if top3_titles:
        lines.append(f"- 視聴時間の主力3本: {top3_titles}")
    if top_retention_title and top_retention_value is not None:
        lines.append(f"- 完読率トップは `{top_retention_title}` で {top_retention_value:,.2f}%")
    if top_parent_name:
        lines.append(f"- 親シリーズ最大の柱は `{top_parent_name}` で watch_time_minutes {top_parent_watch_time:,.1f}")
    if single_row:
        lines.append(f"- `単話` の総 watch_time_minutes は {single_row['watch_time_minutes']:,.1f}")
    lines.append("")

    def append_video_table(title: str, rows: Sequence[Dict[str, object]], metric_label: str, formatter) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"| 順位 | video_id | タイトル | 親シリーズ | サブシリーズ | {metric_label} |")
        lines.append("| --- | --- | --- | --- | --- | ---: |")
        for index, row in enumerate(rows, start=1):
            lines.append(
                f"| {index} | {escape_md(row['video_id'])} | {escape_md(row['title'])} | {escape_md(row['series_parent'])} | {escape_md(row['series_sub'] or '全般')} | {formatter(row['metric'])} |"
            )
        lines.append("")

    def append_group_table(title: str, rows: Sequence[Dict[str, object]], label_key: str) -> None:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| 区分 | 動画数 | views | watch_time_minutes | 1本あたり watch_time_minutes |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for row in rows:
            per_video_watch = safe_div(row["watch_time_minutes"], row["videos"]) or 0.0
            lines.append(
                f"| {escape_md(row[label_key])} | {row['videos']} | {row['views']:,.0f} | {row['watch_time_minutes']:,.1f} | {per_video_watch:,.1f} |"
            )
        lines.append("")

    append_video_table("視聴時間上位20本", top_watch_time, "watch_time_minutes", lambda value: f"{value:,.1f}")
    append_video_table("完読率 average_view_duration_percentage 上位20本", top_avg_pct, "avg_view_duration_pct", lambda value: f"{value:,.2f}")

    lines.append("## インプレッション伸長シグナル上位20本")
    lines.append("")
    if growth_signal_rows:
        lines.append("| 順位 | video_id | タイトル | 親シリーズ | フォーマット | last_7d_impr | growth_7d | last_7d_ctr | watch/impr |")
        lines.append("| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |")
        for index, row in enumerate(growth_signal_rows[:20], start=1):
            growth_rate = row.get("impression_growth_rate_7d")
            growth_text = f"{float(growth_rate) * 100:,.1f}%" if growth_rate is not None else ""
            ctr = row.get("last_7d_ctr")
            ctr_text = f"{float(ctr) * 100:,.2f}%" if ctr is not None else ""
            watch_per_impr = row.get("last_7d_watch_time_minutes_per_impression")
            watch_text = f"{float(watch_per_impr):,.3f}" if watch_per_impr is not None else ""
            lines.append(
                f"| {index} | {escape_md(row['video_id'])} | {escape_md(row['title'])} | {escape_md(row['series_name'])} | {escape_md(row['video_format'])} | {float(row.get('last_7d_impressions') or 0.0):,.0f} | {growth_text} | {ctr_text} | {watch_text} |"
            )
    else:
        lines.append("日次 analytics / reach データが未取得のため、インプレッション伸長シグナルは未算出です。")
    lines.append("")

    lines.append("## 初動7日が強い動画上位20本")
    lines.append("")
    if analysis_rows:
        lines.append("| 順位 | video_id | タイトル | 親シリーズ | サブシリーズ | first_7d_views |")
        lines.append("| --- | --- | --- | --- | --- | ---: |")
        for index, row in enumerate(top_first_7d, start=1):
            lines.append(
                f"| {index} | {escape_md(row['video_id'])} | {escape_md(row['title'])} | {escape_md(row['series_parent'])} | {escape_md(row['series_sub'] or '全般')} | {row['metric']:,.0f} |"
            )
    else:
        lines.append("日次 analytics / reach データが未取得のため、初動7日ランキングは未算出です。")
    lines.append("")

    append_group_table("親シリーズ別ランキング", parent_rows, "series_parent")
    append_group_table("サブシリーズ別ランキング", sub_rows, "series_sub")

    lines.append("## フォーマット別ランキング")
    lines.append("")
    lines.append("| フォーマット | 動画数 | views | watch_time_minutes | 1本あたり watch_time_minutes | average_view_duration_percentage |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: |")
    for row in format_rows:
        per_video_watch = safe_div(row["watch_time_minutes"], row["videos"]) or 0.0
        avg_pct = row["average_view_duration_percentage"]
        avg_pct_text = f"{avg_pct:,.2f}" if avg_pct is not None else ""
        lines.append(
            f"| {escape_md(row['video_format'])} | {row['videos']} | {row['views']:,.0f} | {row['watch_time_minutes']:,.1f} | {per_video_watch:,.1f} | {avg_pct_text} |"
        )
    lines.append("")

    yamamoto_rows = [row for row in sub_rows if str(row["series_sub"]).startswith("山本周五郎 >")]
    kaidan_rows = [row for row in sub_rows if str(row["series_sub"]).startswith("怪談 >")]
    append_group_table("山本周五郎内訳", yamamoto_rows, "series_sub")
    append_group_table("怪談内訳", kaidan_rows, "series_sub")

    lines.append("## 運用メモ")
    lines.append("")
    if parent_rows:
        lines.append(f"- まず伸ばすべき親シリーズ軸は `{escape_md(parent_rows[0]['series_parent'])}` です。")
    if yamamoto_rows:
        lines.append(f"- 山本周五郎は `{escape_md(yamamoto_rows[0]['series_sub'])}` が現状トップです。")
    if kaidan_rows:
        lines.append(f"- 怪談は `{escape_md(kaidan_rows[0]['series_sub'])}` に寄っています。")
    if top_avg_pct:
        lines.append(f"- 完読率上位の訴求は `{escape_md(top_avg_pct[0]['title'])}` 周辺を基準に再利用できます。")
    if not analysis_rows:
        lines.append("- 初動7日や伸び続ける動画の分析は、日次 analytics / reach 取得後に同じスクリプトを再実行してください。")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    base_dir = Path(__file__).resolve().parent
    client_secrets_path = (base_dir / args.client_secrets).resolve()
    token_path = (base_dir / args.token_file).resolve()
    input_csv_path = (base_dir / args.input_csv).resolve()
    master_output_path = (base_dir / args.master_output).resolve()
    daily_output_path = (base_dir / args.daily_output).resolve()
    daily_reach_output_path = (base_dir / args.daily_reach_output).resolve()
    growth_signals_output_path = (base_dir / args.growth_signals_output).resolve()
    analysis_output_path = (base_dir / args.analysis_output).resolve()
    report_output_path = (base_dir / args.report_output).resolve()

    if not input_csv_path.exists():
        raise SystemExit(f"Input CSV not found: {input_csv_path}")

    try:
        base_rows = load_base_rows(input_csv_path)
        creds = load_credentials(client_secrets_path, token_path)
        youtube = build("youtube", "v3", credentials=creds)
        analytics = build("youtubeAnalytics", "v2", credentials=creds)
        reporting = build("youtubereporting", "v1", credentials=creds)

        video_ids = [row["videoId"] for row in base_rows]
        metadata_by_video_id = fetch_video_master(youtube, video_ids) if video_ids else {}
        master_headers, master_rows = build_master_rows(base_rows, metadata_by_video_id)
        published_dates = [
            value
            for value in (parse_iso_date(row.get("publishedAt")) for row in base_rows)
            if value
        ]
        analytics_start_date = min(published_dates) if published_dates else date.today() - timedelta(days=89)
        analytics_end_date = date.today()

        warnings: List[str] = []
        daily_reporting_rows, reporting_warnings = fetch_daily_reporting_rows(reporting)
        warnings.extend(reporting_warnings)
        daily_reporting_reach_rows, reporting_reach_warnings = fetch_daily_reporting_reach_rows(
            reporting
        )
        warnings.extend(reporting_reach_warnings)

        try:
            daily_analytics_rows = fetch_daily_analytics_rows(
                analytics,
                analytics_start_date,
                analytics_end_date,
                video_ids,
            )
        except HttpError as exc:
            daily_analytics_rows = []
            warnings.append(
                "Daily Analytics API query failed for "
                f"`views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage` "
                f"with dimensions `day,video`: {format_http_error(exc)} "
                "Falling back to channel_basic_a3 data where available."
            )

        daily_reach_rows = daily_reporting_reach_rows
        if not daily_reach_rows:
            try:
                daily_reach_rows = fetch_daily_reach_rows(
                    analytics,
                    analytics_start_date,
                    analytics_end_date,
                    video_ids,
                )
            except HttpError as exc:
                daily_reach_rows = []
                warnings.append(
                    "Daily reach query failed for "
                    f"`videoThumbnailImpressions,videoThumbnailImpressionsClickRate` "
                    f"with dimensions `day,video`: {format_http_error(exc)} "
                    "`video_daily_reach.csv` and reach columns in daily analytics may remain blank."
                )

        daily_rows = merge_daily_rows(
            daily_analytics_rows,
            daily_reach_rows,
            daily_reporting_rows,
        )
        analysis_headers, analysis_rows = merge_analysis_rows(
            base_rows,
            master_rows,
            daily_rows,
        )

        write_csv(master_output_path, master_headers, master_rows)
        write_csv(daily_reach_output_path, DAILY_REACH_HEADERS, daily_reach_rows)
        write_csv(daily_output_path, DAILY_HEADERS, daily_rows)
        write_csv(analysis_output_path, analysis_headers, analysis_rows)
        growth_signal_rows = build_growth_signal_rows(analysis_rows, master_rows)
        if growth_signal_rows:
            write_csv(
                growth_signals_output_path,
                list(growth_signal_rows[0].keys()),
                growth_signal_rows,
            )
        else:
            write_csv(growth_signals_output_path, ["video_id"], [])

        available_dates = [
            parse_iso_date(str(row.get("date", "") or "")) for row in daily_rows
        ]
        available_dates = [value for value in available_dates if value]
        available_start = min(available_dates) if available_dates else None
        available_end = max(available_dates) if available_dates else None
        report_text = build_markdown_report(
            analysis_rows,
            master_rows,
            available_start,
            available_end,
            growth_signal_rows,
        )
        report_output_path.write_text(report_text, encoding="utf-8")
    except HttpError as exc:
        detail = exc.error_details if hasattr(exc, "error_details") else str(exc)
        print(f"API error: {detail}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"File error: {exc!r}", file=sys.stderr)
        return 1

    for message in warnings:
        print(f"Warning: {message}", file=sys.stderr)

    print(f"Master CSV: {master_output_path}")
    print(f"Daily Reach CSV: {daily_reach_output_path}")
    print(f"Daily CSV: {daily_output_path}")
    print(f"Growth Signals CSV: {growth_signals_output_path}")
    print(f"Analysis CSV: {analysis_output_path}")
    print(f"Markdown report: {report_output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
