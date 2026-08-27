# reddit-miner

A long-running, read-only Reddit collector for community and power-user knowledge. Configure topics as keyword searches or whole-subreddit monitors, store new threads and useful comments in SQLite, and expose an MCP queue for AI distillation.

Domain-neutral: the same collector works for programming, gaming, hardware, finance, or any other community. See `research/` for methodology notes and a worked example.

## Design

- Python 3.10+ with PRAW and the official Reddit Data API.
- One SQLite database. Reddit IDs (`t3_...` and `t1_...`) deduplicate threads and comments.
- One collector thread in the MCP server process. It polls enabled topics at a configurable interval.
- Streamable HTTP MCP on `127.0.0.1` only. The endpoint is `/mcp`.
- No HTML scraping, undocumented `.json` endpoints, hashes, analytics, or score-based ranking.
- NSFW status is preserved as `is_nsfw`. The collector does not discard items based on Reddit's `over_18` flag.
- Reddit-hosted images and videos download to `--media-dir`. SQLite records their internal paths, but MCP never exposes those paths.
- Outbound links from post bodies, comments, and link-post URLs are extracted, deduped, and stored as plain strings. They are never fetched, so the collector cannot be turned into an SSRF proxy.

The collector stores text needed for distillation: title, body, permalink, subreddit, creation time, item type, matching topic, outbound links, and media references. It does not store scores, subscriber counts, or author analytics. Downloaded image and video bytes live in the local media directory, not in SQLite BLOB columns.

## Install

```sh
uv sync
```

### Nix

Run the application from the current checkout:

```sh
nix run .
```

Run the application directly from GitHub:

```sh
nix run github:nilp0inter/reddit-miner
```

Build the package without running it:

```sh
nix build .#reddit-miner
```

Create a Reddit script application at `https://www.reddit.com/prefs/apps`.
Set its read-only OAuth credentials:

```sh
export REDDIT_CLIENT_ID='...'
export REDDIT_CLIENT_SECRET='...'
export REDDIT_USER_AGENT='linux:reddit-miner:v0.2 (by u/YOUR_USERNAME)'
```

`REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` are required. A username and password are not required because the collector uses PRAW read-only mode.

## Run

```sh
uv run reddit-miner \
  --db reddit-miner.sqlite3 \
  --media-dir reddit-media \
  --poll-interval 600 \
  --host 127.0.0.1 \
  --port 8000
```

The process runs until interrupted. It listens at:

```text
http://127.0.0.1:8000/mcp
```

A generic Streamable HTTP MCP client configuration uses that URL:

```json
{
  "mcpServers": {
    "reddit-miner": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## MCP tools

### `add_topic`

Add a topic for the collector to poll. When `query` is omitted the topic monitors every new post in the subreddit; when given it searches that subreddit. `subreddit` defaults to `all`. Names are unique.

Search-topic example:

```json
{
  "name": "python-asyncio",
  "query": "asyncio OR uvloop",
  "subreddit": "Python"
}
```

Monitor-topic example (no `query`):

```json
{
  "name": "r-python-new",
  "subreddit": "Python"
}
```

ComfyUI workflow example (any domain works):

```json
{
  "name": "comfyui-3d",
  "query": "TRELLIS OR Hunyuan3D",
  "subreddit": "comfyui"
}
```

The result is:

```json
{
  "topic": {
    "name": "python-asyncio",
    "query": "asyncio OR uvloop",
    "subreddit": "Python"
  }
}
```

A `null` `query` in the result means the topic monitors all new posts.

### `list_topics`

Inspect every saved topic.

```json
{}
```

The result is one object with a `topics` list. Each topic includes its name, query (`null` for monitors), subreddit, enabled state, and creation time.

### `remove_topic`

Delete a saved topic. Collected items keep their `topic_name` as a historical label.

```json
{
  "name": "python-asyncio"
}
```

### `set_topic_enabled`

Enable or disable polling for a topic without deleting it.

```json
{
  "name": "python-asyncio",
  "enabled": false
}
```

### `get_unprocessed_results`

Get queued threads and comments for distillation.

```json
{
  "limit": 20
}
```

The result is one object with an `items` list. This operation atomically marks returned items as delivered. It is at-most-once: if a distiller crashes after this call, those items are not automatically returned again.

Each item includes `is_nsfw` and a `links` list (external URLs extracted from that submission or comment; Reddit links and Reddit-hosted media URLs are excluded). Clients can make their own content-scope decision without hidden collection-time exclusion.

Items with stored media include a `media` list. Each entry has an ID, MIME type, and a `media://<id>` URI. It never includes a local filesystem path.

### Media resources

Read `media://<id>` through the MCP resource API to receive the image or video bytes. The collector downloads only HTTPS media hosted by Reddit-owned media domains. This prevents a Reddit link post from making the collector fetch an arbitrary local or private-network URL.

## Collection behavior

Each poll visits every enabled topic in its configured subreddit. A search topic calls `subreddit.search(query)`, a monitor topic calls `subreddit.new()`. Matching submissions and non-deleted comments enter the queue only once. Repeated polls can add new comments from a still-matching thread. Reddit-hosted submission images and videos download once and appear as MCP media resources. Outbound links found in post selftext, comment bodies, and link-post URLs are extracted and attached to each item as `links`. A failure for one topic or media download is logged, then the collector continues with the other topics and later polls.

Start with narrow queries for knowledge-heavy topics or monitor a whole community when volume allows. Examples:

- `asyncio OR uvloop` in `Python`
- `mechanical keyboard OR keycaps` in `MechanicalKeyboards` (monitor `r/MechanicalKeyboards` new posts: omit `query`)
- `TRELLIS OR Hunyuan3D` in `comfyui` (domain-specific example)

Use `set_topic_enabled` to pause a noisy topic and `remove_topic` to retire it. Items already collected remain queryable through `get_unprocessed_results` until claimed.

## Verify

```sh
uv run pytest -q
```

The test suite uses fake Reddit objects. It does not need live Reddit credentials or network access. It covers persistence, deduplication, the polling loop, per-topic failures, topic lifecycle, monitor mode, outbound links, MCP tools, downloaded media, and binary MCP resource reads.

## Research

- `research/reddit-scraping-quickstart.md` — PRAW and API access decisions.
- `research/extraction-methods.md` — integrated extraction-method survey.
- `research/minimax-h3-readiness-assessment.md` — worked example: using reddit-miner to collect MiniMax H3 video knowledge (one deployment, not the system's scope).
