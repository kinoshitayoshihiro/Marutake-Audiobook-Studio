#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

CHANNEL="${CHANNEL:-current}"
if [[ "$CHANNEL" == "ninjo" ]]; then
  SRC_DIR="$SCRIPT_DIR/ninjo_channel_report"
elif [[ "$CHANNEL" == "current" ]]; then
  SRC_DIR="$SCRIPT_DIR/old_channel_report"
else
  echo "Unsupported CHANNEL: $CHANNEL (use current|ninjo)" >&2
  exit 2
fi

REPORTS_DIR="$ROOT_DIR/data/youtube/reports"
INV_DIR="$ROOT_DIR/data/youtube/inventory"
AUTHOR_DIR="$ROOT_DIR/data/youtube/by-author"

mkdir -p "$REPORTS_DIR" "$INV_DIR" "$AUTHOR_DIR"

cp "$SRC_DIR/youtube_video_report_last_90_days_all_videos.csv" "$REPORTS_DIR/current_channel_last_90_days_all_videos.csv"
cp "$SRC_DIR/youtube_video_report_last_90_days_normal_video.csv" "$REPORTS_DIR/current_channel_last_90_days_normal_video.csv"
cp "$SRC_DIR/youtube_video_report_last_90_days_short_candidate.csv" "$REPORTS_DIR/current_channel_last_90_days_short_candidate.csv"
cp "$SRC_DIR/channel_upload_inventory.csv" "$INV_DIR/current_channel_upload_inventory.csv"
cp "$SRC_DIR/channel_videos_by_author.csv" "$AUTHOR_DIR/current_channel_videos_by_author.csv"

echo "Synced report set from: $SRC_DIR"
echo "  -> $REPORTS_DIR"
echo "  -> $INV_DIR"
echo "  -> $AUTHOR_DIR"
