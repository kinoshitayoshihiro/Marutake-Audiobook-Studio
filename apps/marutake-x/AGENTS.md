# marutake-x

- Keep the default workflow review-first. Do not add automatic X posting without an explicit request.
- Store local operational state under `.marutake-x/` or a user-specified `--db` JSON path.
- Provider integrations must stay behind `LLMProvider` or `ResearchProvider`.
- Export formats are operator-facing artifacts. Preserve UTF-8 Japanese text and human-readable Markdown.
