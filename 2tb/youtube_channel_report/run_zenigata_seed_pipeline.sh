#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="${VENV_DIR:-$SCRIPT_DIR/.venv}"
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

log() {
  printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

require_file() {
  local path="$1"
  if [[ ! -f "$path" ]]; then
    printf 'Missing required file: %s\n' "$path" >&2
    exit 1
  fi
}

bootstrap_venv() {
  if [[ -x "$PYTHON_BIN" ]]; then
    return
  fi

  log "Creating virtual environment"
  python3 -m venv "$VENV_DIR"

  log "Upgrading pip"
  "$PYTHON_BIN" -m pip install --upgrade pip

  log "Installing requirements"
  "$PIP_BIN" install -r requirements.txt
}

require_file "requirements.txt"
require_file "build_zenigata_seed_pipeline.py"
require_file "youtube_video_report_last_90_days_all_videos.csv"
require_file "daily_growth_signals.csv"

bootstrap_venv

log "Running Zenigata seed shortwork pipeline"
"$PYTHON_BIN" build_zenigata_seed_pipeline.py

log "Completed successfully"
printf '%s\n' \
  "Updated outputs:" \
  "- reports/zenigata_seed_shortworks.csv" \
  "- reports/zenigata_seed_shortworks.md" \
  "- reports/zenigata_seed_<核作品>_candidates.csv" \
  "- reports/zenigata_seed_<核作品>_review.md" \
  "- reports/zenigata_bundle_feedback_log.csv"
