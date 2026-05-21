# Migration Plan

## Phase 1 (Completed)

- Keep existing Python report scripts unchanged.
- Add channel-report MVP app with CSV input.
- Add diagnosis tags and export candidates.

## Phase 2

- Add file presets for multi-channel reports.
- Add stable thresholds in config file.
- Add stronger title/author/series classifiers.

## Phase 3

- Connect anthology app input directly to exported seeds.
- Add X-draft candidate payload export extensions.
- Add regression checks for diagnosis logic.

## Risk Controls

- Never commit OAuth secrets/tokens.
- Preserve legacy report scripts as source of truth for data generation.
