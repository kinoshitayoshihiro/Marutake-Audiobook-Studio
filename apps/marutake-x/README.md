# marutake-x

`marutake-x` is a review-first local CLI for turning Marutake YouTube audiobook materials into X drafts.
It stores video inputs, draft posts, threads, long-form article drafts, calendars, and post review statuses in a local JSON file.
The initial release does not post to X. The default account voice is **丸竹書房 編集部**.

## Scope

- Register audiobook video material from YAML or JSON.
- Generate X drafts, a 5 to 8 post thread, a long-form article draft, and a calendar.
- Track `draft`, `reviewed`, `scheduled`, `posted`, and `skipped`.
- Export Markdown, CSV, and JSON for manual review or reservation tooling.
- Check X text length and draft repetition signals. Use `--status reviewed,scheduled,posted` when you want to inspect only drafts that are actually moving toward publication.
- Keep LLM and X research behind provider interfaces.

## Setup

Python 3.11 or newer is enough for the default `DummyProvider`.

```bash
cd apps/marutake-x
python3 -m marutake_x init
python3 -m marutake_x add-video samples/yamamoto-video.yaml
```

Installable console entrypoint:

```bash
python3 -m pip install -e .
marutake-x list
```

`OpenAIProvider` is optional. It uses the OpenAI Responses API through the `openai` Python package and `OPENAI_API_KEY`.
Copy values from `.env.example` into the local environment when using it. Do not commit secrets.

## Input

The sample YAML is [samples/yamamoto-video.yaml](samples/yamamoto-video.yaml). Required fields are:

- `video_id`
- `youtube_title`
- `youtube_url`
- `publish_date`
- `work_title`
- `author`

Use UTF-8. `youtube_description`, `aftertalk_notes`, and `unused_trivia_notes` may be multiline text.

## Commands

```bash
python3 -m marutake_x init
python3 -m marutake_x add-video samples/yamamoto-video.yaml
python3 -m marutake_x generate-posts yamamoto-nioi-001 --style marutake_editorial
python3 -m marutake_x generate-thread yamamoto-nioi-001 --style trivia_column
python3 -m marutake_x generate-article yamamoto-nioi-001 --type edo_trivia
python3 -m marutake_x calendar yamamoto-nioi-001
python3 -m marutake_x export yamamoto-nioi-001 --format markdown --out sample.md
python3 -m marutake_x export yamamoto-nioi-001 --format csv --out posts.csv
python3 -m marutake_x export yamamoto-nioi-001 --format json --out bundle.json
python3 -m marutake_x list
python3 -m marutake_x status POST_ID reviewed
python3 -m marutake_x check-duplicates
python3 -m marutake_x check-duplicates --status reviewed,scheduled,posted
```

Use `--db path/to/db.json` before the subcommand to isolate a project or test run.

## Output

CSV export columns:

```text
post_id,video_id,scheduled_date,post_type,status,text,youtube_url,hashtags,char_count
```

Markdown exports contain video material, posts, threads, article drafts, and the calendar. Each post carries a character count and a 280 character warning flag in JSON/Markdown exports.

## Providers

LLM providers:

- `DummyProvider`: deterministic local draft templates. Default.
- `OpenAIProvider`: optional draft rewriting provider.
- Future: `HermesGrokProvider`, `LocalLLMProvider`.

Research providers:

- `NoopResearchProvider`: local query suggestions and risk notes.
- `HermesXSearchProvider`: present as an unimplemented stub.

```bash
python3 -m marutake_x suggest-queries yamamoto-nioi-001
python3 -m marutake_x research yamamoto-nioi-001 --provider noop
python3 -m marutake_x research yamamoto-nioi-001 --provider hermes-x-search
```

Hermes/Grok research remains optional. X search should inform original drafts; it must not copy third-party X posts into output.

## Planned Extensions

- A lightweight web UI for video material entry and review queues.
- Provider-backed draft refinement and source-aware fact checking.
- Optional Hermes Agent / Grok research adapter.
- Optional reservation export adapters.
- X API posting only after a separate approval-focused design pass.
