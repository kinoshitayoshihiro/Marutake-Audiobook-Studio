# Integration Audit

## Scope

- `2tb/*.py`
- `2tb/*.php`
- `2tb/youtube_channel_report/*.py`
- `2tb/tools/*.py`
- shell runners under `2tb/youtube_channel_report/*.sh`

## Findings

1. YouTube reporting scripts already provide:
   - per-video metrics
   - metadata/description audit fields
   - inventory and strategy reports
2. Current outputs are CSV/MD heavy and suitable for a UI ingestion layer.
3. Channel operations are now split by token + output directory:
   - `old_channel_report`
   - `ninjo_channel_report`

## Reuse Strategy

- Keep current Python ingestion/export scripts as-is.
- Add a CSV-first UI app (`apps/audiobookstudio/channel-report`) to normalize, diagnose, and export actionable candidates.
- Feed `anthology_seed_candidates.csv` into anthology workflows.

## Legacy vs Migration

- Legacy keep: all scripts in `2tb/youtube_channel_report` and `2tb/tools`.
- Migrate first: report interpretation and diagnostics logic into `packages/channel-report-engine`.
