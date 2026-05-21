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

run_step() {
  local step_label="$1"
  shift
  log "$step_label"
  "$PYTHON_BIN" "$@"
}

require_file "client_secret.json"
require_file "requirements.txt"
require_file "youtube_video_report.py"
require_file "build_normal_video_analysis.py"
require_file "build_reach_analysis_report.py"
require_file "build_content_strategy_reports.py"
require_file "build_next_content_ideas.py"
require_file "build_compilation_candidates.py"
require_file "build_zenigata_seed_pipeline.py"

bootstrap_venv

log "Starting current channel report refresh"
log "If OAuth is required, open the displayed Google URL and approve access in your browser"

run_step "1/7 Base video report" youtube_video_report.py
run_step "2/7 Daily analytics and growth signals" build_normal_video_analysis.py
run_step "3/7 Reach analysis report" build_reach_analysis_report.py
run_step "4/7 Content strategy reports" build_content_strategy_reports.py
run_step "5/7 Next content ideas" build_next_content_ideas.py
run_step "6/7 Zenigata compilation candidates" build_compilation_candidates.py
run_step "7/7 Zenigata seed shortwork pipeline" build_zenigata_seed_pipeline.py

log "Completed successfully"
printf '%s\n' \
  "Updated outputs:" \
  "- youtube_video_report_last_90_days_all_videos.csv" \
  "- youtube_video_report_last_90_days_normal_video.csv" \
  "- youtube_video_report_last_90_days_short_candidate.csv" \
  "- video_master_enriched.csv" \
  "- video_daily_reach.csv" \
  "- video_daily_analytics.csv" \
  "- daily_growth_signals.csv" \
  "- analysis_ready_normal_video.csv" \
  "- analysis_ready_normal_video_report.md" \
  "- reach_analysis_report.md" \
  "- zenigata_strategy_report.md" \
  "- yamamoto_strategy_report.md" \
  "- next_content_ideas.md" \
  "- zenigata_compilation_candidates.csv" \
  "- zenigata_compilation_candidates.md" \
  "- reports/zenigata_seed_shortworks.csv" \
  "- reports/zenigata_seed_shortworks.md"
