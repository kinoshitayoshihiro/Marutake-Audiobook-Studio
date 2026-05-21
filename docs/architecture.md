# Architecture

## Target Structure

```text
apps/audiobookstudio/channel-report/
packages/channel-report-engine/
packages/youtube-analytics/
packages/shared-types/
data/youtube/reports/
data/youtube/exports/
```

## Runtime Flow

1. Ingest CSV from report runners.
2. Normalize rows into `VideoReport`.
3. Diagnose and tag videos.
4. Render operator views (Overview, Hidden Gems, Fix queues).
5. Export candidate lists for downstream apps.

## Boundaries

- `packages/youtube-analytics`: CSV parsing and serialization.
- `packages/channel-report-engine`: diagnosis tags, scores, grouping.
- `apps/audiobookstudio/channel-report`: UI and operator interactions.

## Upstream / Downstream

- Upstream: `youtube_video_report.py` and related report scripts.
- Downstream: anthology builder, X draft generation, description improvement workflow.
