# Channel Report MVP

This app is a CSV-first channel diagnostics tool for audiobook operations.

## Open

Recommended (localhost):

1. Sync latest report files to fixed paths:
   - `bash 2tb/youtube_channel_report/sync_reports_to_data.sh`
   - For ninjo channel: `CHANNEL=ninjo bash 2tb/youtube_channel_report/sync_reports_to_data.sh`
2. Start local server:
   - `bash apps/audiobookstudio/channel-report/serve-local.sh`
3. Open:
   - `http://localhost:3000/apps/audiobookstudio/channel-report/index.html`

The app auto-loads `data/youtube/reports/current_channel_last_90_days_all_videos.csv` on localhost.

Fallback:

- Open [index.html](/Users/kinoshitayoshihiro/Library/CloudStorage/GoogleDrive-shimogami88@gmail.com/マイドライブ/Marutake Audiobook Studio/apps/audiobookstudio/channel-report/index.html) directly and use file picker.

## Input CSV

- `youtube_video_report_last_90_days_all_videos.csv` (required)

## Tabs

- Overview
- Videos
- Hidden Gems
- Thumbnail Fix
- Description Audit
- Author / Series
- Export

## Export Outputs

- `hidden_gems.csv`
- `thumbnail_fix_candidates.csv`
- `description_audit_candidates.csv`
- `anthology_seed_candidates.csv`
- `x_repost_candidates.csv`

Each export is available as CSV and JSON.

## Notes

- Existing scripts under `2tb/youtube_channel_report/` are unchanged.
- OAuth secrets/tokens are not part of this app and must not be committed.
