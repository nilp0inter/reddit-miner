# genflow-miner

A long-running, read-only Reddit collector for ComfyUI and Stable Diffusion
workflow knowledge. It periodically searches saved topics, stores new threads
and useful comments in SQLite, and exposes an MCP queue for AI distillation.

The v1 focus is 3D assets and generative video. See `research/` for the source
research and target communities.

## Design

- Python 3.10+ with PRAW and the official Reddit Data API.
- One SQLite database. Reddit IDs (`t3_...` and `t1_...`) deduplicate threads
  and comments.
- One collector thread in the MCP server process. It polls enabled topics at a
  configurable interval.
- Streamable HTTP MCP on `127.0.0.1` only. The endpoint is `/mcp`.
- No HTML scraping, undocumented `.json` endpoints, hashes, analytics, or
  score-based ranking.
- NSFW submissions (`over_18`) and their comments are excluded before storage.

The collector stores text needed for distillation: title, body, permalink,
subreddit, creation time, item type, and matching topic. It does not store
scores, subscriber counts, or author analytics.

## Install

```sh
uv sync
```

Create a Reddit script application at `https://www.reddit.com/prefs/apps`.
Set its read-only OAuth credentials:

```sh
export REDDIT_CLIENT_ID='...'
export REDDIT_CLIENT_SECRET='...'
export REDDIT_USER_AGENT='linux:genflow-miner:v0.1 (by u/YOUR_USERNAME)'
```

`REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` are required. A username and
password are not required because the collector uses PRAW read-only mode.

## Run

```sh
uv run genflow-miner \
  --db genflow-miner.sqlite3 \
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
    "genflow-miner": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

## MCP tools

### `add_search_topic`

Add a topic for the collector to poll.

```json
{
  "name": "comfyui-3d",
  "query": "TRELLIS OR Hunyuan3D",
  "subreddit": "comfyui"
}
```

`subreddit` defaults to `all`. Names are unique. The result is:

```json
{
  "topic": {
    "name": "comfyui-3d",
    "query": "TRELLIS OR Hunyuan3D",
    "subreddit": "comfyui"
  }
}
```

### `list_search_topics`

Inspect every saved query.

```json
{}
```

The result is one object with a `topics` list. Each topic includes its name,
query, subreddit, enabled state, and creation time.

### `get_unprocessed_results`

Get queued threads and comments for distillation.

```json
{
  "limit": 20
}
```

The result is one object with an `items` list. This operation atomically marks
returned items as delivered. It is at-most-once: if a distiller crashes after
this call, those items are not automatically returned again.

## Collection behavior

Each poll searches every enabled topic in its configured subreddit. Matching
submissions and non-deleted comments enter the queue only once. Repeated polls
can add new comments from a still-matching thread. A failure for one topic is
logged, then the collector continues with the other topics and later polls.

Start with narrow queries that describe useful workflow knowledge. Examples:

- `TRELLIS OR Hunyuan3D` in `comfyui`
- `WanVideo OR LTX-Video OR HunyuanVideo` in `StableDiffusion`
- `workflow JSON OR custom node` in `comfyui`

`unstable_diffusion` is allowed as a topic source, but the collector excludes
submissions marked NSFW.

## Verify

```sh
uv run pytest -q
```

The test suite uses fake Reddit objects. It does not need live Reddit
credentials or network access. It covers persistence, deduplication, the
polling loop, per-topic failures, and all three MCP tools.

## Research

- `research/reddit-scraping-quickstart.md` — PRAW and API access decisions.
- `research/extraction-methods.md` — integrated extraction-method survey.
- `research/targeting-v1.md` — ComfyUI, Stable Diffusion, 3D, and video target
  queries.
