# marutake-x

`marutake-x` is a review-first local CLI for turning Marutake YouTube audiobook materials into X drafts.
It stores video inputs, draft posts, threads, long-form article drafts, calendars, and post review statuses in a local JSON file.
Live X posting is available only through explicit reviewed-post commands. The default account voice is **丸竹書房 編集部**.

## Scope

- Register audiobook video material from YAML or JSON.
- Register completed hand-written drafts from ChatGPT or editorial review as reusable posting material.
- Manage X single posts, X thread parts, and YouTube community posts separately.
- Generate X drafts, a 5 to 8 post thread, a long-form article draft, and a calendar.
- Track `draft`, `reviewed`, `scheduled`, `posted`, and `skipped`.
- Export Markdown, CSV, and JSON for manual review or reservation tooling.
- Check X text length and draft repetition signals. Use `--status reviewed,scheduled,posted` when you want to inspect only drafts that are actually moving toward publication.
- Publish reviewed X posts through the X API after an explicit `--live` command.
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

Live X posting is optional. It uses the X API v2 `POST /2/tweets` endpoint with a user access token that has `tweet.write` permission.
Use OAuth 2.0 Authorization Code Flow with PKCE to obtain `MARUTAKE_X_USER_ACCESS_TOKEN`.
Keep `.env` local only; it is ignored by Git.

## Input

The sample YAML is [samples/yamamoto-video.yaml](samples/yamamoto-video.yaml). Required fields are:

- `video_id`
- `youtube_title`
- `youtube_url`
- `publish_date`
- `work_title`
- `author`

Use UTF-8. `youtube_description`, `aftertalk_notes`, and `unused_trivia_notes` may be multiline text.

Optional editorial-material fields:

- `account_name`: posting account label. Defaults to `丸竹書房 編集部`.
- `video_kind`: video format, such as `まとめ聞き・長編朗読`.
- `thumbnail_notes`: thumbnail layout notes.
- `x_drafts`: completed X single/thread text managed for manual posting.
- `youtube_community_drafts`: completed YouTube community text managed for copy and paste.

Draft rows support `kind`, `title`, `status`, `selected`, `candidate`, `scheduled_date`, `text`, `image_note`, and `memo`.
Use `selected: true` for the current posting plan and `candidate: true` for reserve copy.

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
python3 -m marutake_x import-x-drafts yamamoto-nioi-001
python3 -m marutake_x publish-x POST_ID
python3 -m marutake_x publish-x POST_ID --live
python3 -m marutake_x publish-x-thread yamamoto-nioi-001 --live
python3 -m marutake_x x-oauth-url --client-id CLIENT_ID
python3 -m marutake_x x-oauth-token --code AUTHORIZATION_CODE
python3 -m marutake_x x-oauth-refresh --client-id CLIENT_ID --refresh-token REFRESH_TOKEN
```

Use `--db path/to/db.json` before the subcommand to isolate a project or test run.

## X OAuth Setup

Create and configure the app in the [X Developer Portal](https://developer.x.com/en/portal/dashboard).

1. Open the X Developer Portal and select your Project/App.
2. Enable OAuth 2.0.
3. Set App permissions to read and write.
4. Set Type of App to a public client for local CLI use, unless you intentionally manage a confidential client secret.
5. Add this callback URL:

```text
http://127.0.0.1:8765/callback
```

The posting flow needs these scopes:

```text
tweet.read tweet.write users.read offline.access
```

Generate the OAuth authorization URL:

```bash
python3 -m marutake_x x-oauth-url \
  --client-id YOUR_X_OAUTH2_CLIENT_ID \
  --redirect-uri http://127.0.0.1:8765/callback
```

Open the printed URL in a browser, approve the app, and copy the `code` parameter from the redirected callback URL.
The callback can fail to load in the browser if no local web server is running; that is fine as long as the address bar contains `code=...` and `state=...`.

Exchange the authorization code for tokens:

```bash
python3 -m marutake_x x-oauth-token \
  --code AUTHORIZATION_CODE_FROM_CALLBACK \
  --state STATE_FROM_CALLBACK
```

By default this writes the returned values into local `.env`:

```text
MARUTAKE_X_USER_ACCESS_TOKEN=...
MARUTAKE_X_REFRESH_TOKEN=...
```

`.env` is ignored by Git. Do not paste real tokens into `.env.example`, README, sample JSON, commit messages, or chat.
`.env.example` intentionally contains variable names only.

If the access token expires, refresh it:

```bash
python3 -m marutake_x x-oauth-refresh \
  --client-id YOUR_X_OAUTH2_CLIENT_ID \
  --refresh-token YOUR_SAVED_MARUTAKE_X_REFRESH_TOKEN
```

For a confidential client, add `--client-secret YOUR_CLIENT_SECRET` to `x-oauth-token` and `x-oauth-refresh`.
Do not commit the client secret.

## X Posting Flow

The app is intentionally review-gated:

1. Register or generate draft material.
2. Export Markdown and read the actual copy.
3. Mark only approved posts as `reviewed` or `scheduled`.
4. Run `publish-x POST_ID` without `--live` to preview the exact text.
5. Run `publish-x POST_ID --live` to create the X Post.

For hand-written `x_drafts`, first import the selected drafts into the post database:

```bash
python3 -m marutake_x import-x-drafts nagai-zaka-summary-vol-1
python3 -m marutake_x publish-x curated_nagai-zaka-summary-vol-1_01_single
python3 -m marutake_x publish-x curated_nagai-zaka-summary-vol-1_01_single --live
```

`publish-x-thread VIDEO_ID --live` posts reviewed thread rows in sequence and replies each later post to the previous X post.
The command refuses `draft`, `skipped`, already-posted, empty, or over-280-character posts unless `--allow-over-limit` is explicitly supplied.

Dry-run never posts to X:

```bash
python3 -m marutake_x --db .marutake-x/kumokiri-posting.json publish-x-thread kumokiri-enmacho-tree-2026-05-25
```

After human review, `--live` posts to X using `MARUTAKE_X_USER_ACCESS_TOKEN` from `.env` or the environment:

```bash
python3 -m marutake_x --db .marutake-x/kumokiri-posting.json publish-x-thread kumokiri-enmacho-tree-2026-05-25 --live
```

## ながい坂 第一巻 投稿テスト

The initial hand-posting sample is [samples/nagai-zaka-volume-1.json](samples/nagai-zaka-volume-1.json).
It contains the X single notice, a 5-post X thread, and YouTube community variants for pre-publish, publish-day, aftertalk, comments, and the 2021 legacy-note copy.

```bash
python3 -m marutake_x --db .marutake-x/nagai-zaka-test.json init
python3 -m marutake_x --db .marutake-x/nagai-zaka-test.json add-video samples/nagai-zaka-volume-1.json
python3 -m marutake_x --db .marutake-x/nagai-zaka-test.json export nagai-zaka-summary-vol-1 --format markdown --out samples/nagai-zaka-volume-1-posting-pack.md
```

Before real posting, replace the placeholder `youtube_url` and adjust `publish_date` in the sample JSON.
The workflow remains manual: copy from the Markdown pack into X or YouTube Studio after human review.
If you use live X posting, keep the same human-review step and only post rows that have been marked `reviewed` or `scheduled`.

## Output

CSV export columns:

```text
post_id,video_id,scheduled_date,post_type,status,text,youtube_url,hashtags,char_count
```

Markdown exports contain video material, selected/candidate editorial drafts, generated posts, threads, article drafts, and the calendar. Each post carries a character count and a 280 character warning flag in JSON/Markdown exports.
Editorial drafts are emitted in fenced `text` blocks for direct copy and paste.

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
