# genflow-miner

Research and tooling for mining generative-media workflows from Reddit.

**v1 target:** the Stable Diffusion / ComfyUI communities on Reddit, where users
compile ComfyUI workflows and techniques for generating 3D assets and video
assets (all kinds of generative video).

**Status:** research phase. No collector code yet.

## Repository layout

| Path | Content |
|---|---|
| `research/README.md` | Index of all research notes |
| `research/reddit-scraping-quickstart.md` | Verified quickstart: PRAW, free-tier limits, setup, archives, legal context |
| `research/extraction-methods.md` | Survey of every Reddit data-extraction method, with 2026 status corrections |
| `research/targeting-v1.md` | v1 target subreddits, keywords, and collection plan |

## Tooling decisions (from research)

- **Collector language:** Python.
- **Wrapper:** PRAW 8.0.3 (active, Python 3.10+). Not snoowrap — that is a
  JavaScript wrapper, archived in 2024.
- **Access:** official Reddit Data API, free user tier, 100 queries per minute
  with OAuth. The unauthenticated `.json` endpoint path is dead (403).
- **Historical backfill:** Arctic Shift dumps; recent top-up via PullPush and
  PRAW.
- **Everything read-only against Reddit.** No vote, post, or moderation calls.
