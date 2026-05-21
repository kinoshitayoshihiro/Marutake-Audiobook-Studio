#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

OUT_DIR="$SCRIPT_DIR/old_channel_report"
VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"
TOKEN_FILE="token_old_channel.json"
CLIENT_SECRETS="client_secret.json"
START_DATE="${START_DATE:-2022-01-01}"
END_DATE="${END_DATE:-$(date '+%Y-%m-%d')}"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

mkdir -p "$OUT_DIR"

log "Starting old channel report refresh"
log "Target window: $START_DATE to $END_DATE"
log "Authenticate with the old channel owner account when the Google OAuth screen appears"

"$PYTHON_BIN" youtube_video_report.py \
  --client-secrets "$CLIENT_SECRETS" \
  --token-file "$TOKEN_FILE" \
  --start-date "$START_DATE" \
  --end-date "$END_DATE" \
  --input-csv "$OUT_DIR/youtube_video_report_last_90_days.csv" \
  --all-output "$OUT_DIR/youtube_video_report_last_90_days_all_videos.csv" \
  --normal-output "$OUT_DIR/youtube_video_report_last_90_days_normal_video.csv" \
  --short-output "$OUT_DIR/youtube_video_report_last_90_days_short_candidate.csv"

if [[ $(wc -l < "$OUT_DIR/youtube_video_report_last_90_days_all_videos.csv") -le 1 ]]; then
  log "No videos were returned for the old channel in the requested window. Stopping before downstream analysis."
  exit 2
fi

"$PYTHON_BIN" build_normal_video_analysis.py \
  --client-secrets "$CLIENT_SECRETS" \
  --token-file "$TOKEN_FILE" \
  --input-csv "$OUT_DIR/youtube_video_report_last_90_days_normal_video.csv" \
  --master-output "$OUT_DIR/video_master_enriched.csv" \
  --daily-output "$OUT_DIR/video_daily_analytics.csv" \
  --daily-reach-output "$OUT_DIR/video_daily_reach.csv" \
  --growth-signals-output "$OUT_DIR/daily_growth_signals.csv" \
  --analysis-output "$OUT_DIR/analysis_ready_normal_video.csv" \
  --report-output "$OUT_DIR/analysis_ready_normal_video_report.md"

"$PYTHON_BIN" build_reach_analysis_report.py \
  --all-input "$OUT_DIR/youtube_video_report_last_90_days_all_videos.csv" \
  --normal-input "$OUT_DIR/youtube_video_report_last_90_days_normal_video.csv" \
  --report-output "$OUT_DIR/reach_analysis_report.md" \
  --opportunities-output "$OUT_DIR/reach_analysis_opportunities.csv"

"$PYTHON_BIN" build_content_strategy_reports.py \
  --analysis-input "$OUT_DIR/analysis_ready_normal_video.csv" \
  --planning-output "$OUT_DIR/content_planning_normal_video.csv" \
  --zenigata-output "$OUT_DIR/zenigata_strategy_report.md" \
  --yamamoto-output "$OUT_DIR/yamamoto_strategy_report.md"

"$PYTHON_BIN" build_next_content_ideas.py \
  --planning-input "$OUT_DIR/content_planning_normal_video.csv" \
  --opportunities-input "$OUT_DIR/reach_analysis_opportunities.csv" \
  --csv-output "$OUT_DIR/next_content_ideas.csv" \
  --md-output "$OUT_DIR/next_content_ideas.md"

"$PYTHON_BIN" build_compilation_candidates.py \
  --growth-input "$OUT_DIR/daily_growth_signals.csv" \
  --series-name "銭形平次捕物控" \
  --csv-output "$OUT_DIR/zenigata_compilation_candidates.csv" \
  --md-output "$OUT_DIR/zenigata_compilation_candidates.md"

"$PYTHON_BIN" export_channel_inventory.py \
  --client-secrets "$CLIENT_SECRETS" \
  --token-file "$TOKEN_FILE" \
  --inventory-output "$OUT_DIR/channel_upload_inventory.csv" \
  --zenigata-output "$OUT_DIR/zenigata_upload_inventory.csv" \
  --summary-output "$OUT_DIR/channel_upload_inventory_summary.md" \
  --old-report-input "$OUT_DIR/youtube_video_report_last_90_days_all_videos.csv"

"$PYTHON_BIN" build_zenigata_inventory_analysis.py \
  --input "$OUT_DIR/zenigata_upload_inventory.csv" \
  --ranked-output "$OUT_DIR/zenigata_upload_inventory_ranked.csv" \
  --summary-output "$OUT_DIR/zenigata_upload_inventory_analysis.md"

"$PYTHON_BIN" build_channel_video_archive_table.py \
  --inventory-input "$OUT_DIR/channel_upload_inventory.csv" \
  --report-input "$OUT_DIR/youtube_video_report_last_90_days_all_videos.csv" \
  --csv-output "$OUT_DIR/channel_videos_by_date.csv" \
  --md-output "$OUT_DIR/channel_videos_by_date.md"

"$PYTHON_BIN" build_author_video_rankings.py \
  --archive-input "$OUT_DIR/channel_videos_by_date.csv" \
  --report-input "$OUT_DIR/youtube_video_report_last_90_days_all_videos.csv" \
  --csv-output "$OUT_DIR/channel_videos_by_author.csv" \
  --md-output "$OUT_DIR/channel_videos_by_author.md"

log "Completed successfully"
