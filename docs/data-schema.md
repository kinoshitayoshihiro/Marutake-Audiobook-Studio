# Data Schema

## Input

- `youtube_video_report_last_90_days_all_videos.csv`

Required columns:

- `videoId`
- `title`
- `publishedAt`
- `views`
- `estimatedMinutesWatched`
- `averageViewDuration`
- `impressions`
- `impressionCtr`
- `duration_seconds`
- `is_short_candidate`
- `content_type_bucket`
- `has_description_synopsis`
- `has_description_characters`
- `has_description_glossary`

## Internal Model

See [channel-report-types.md](/Users/kinoshitayoshihiro/Library/CloudStorage/GoogleDrive-shimogami88@gmail.com/マイドライブ/Marutake%20Audiobook%20Studio/packages/shared-types/channel-report-types.md).

## Export

Common columns:

- `videoId`
- `title`
- `author`
- `series`
- `views`
- `estimatedMinutesWatched`
- `averageViewDuration`
- `impressions`
- `impressionCtr`
- `diagnosisTags`
- `recommendedActions`
- `anthologySeedScore`
