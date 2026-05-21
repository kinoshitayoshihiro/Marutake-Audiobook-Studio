#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

require_file() {
  local target="$1"
  if [[ ! -f "$SCRIPT_DIR/$target" ]]; then
    echo "Missing required file: $target" >&2
    exit 2
  fi
}

log "Refreshing old channel report for 七之助 metrics"
bash "$SCRIPT_DIR/run_old_channel_report.sh"

require_file "old_channel_report/youtube_video_report_last_90_days_all_videos.csv"

log "Building 七之助 channel performance report"
"$PYTHON_BIN" "$SCRIPT_DIR/build_shichinosuke_channel_performance.py"

log "Completed successfully"
