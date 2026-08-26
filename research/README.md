# Research Index

Deep-research notes for genflow-miner. All facts in these documents carry a
verification status: `verified` (checked against a primary source or probed
live on 2026-08-26) or `unverified` (secondary source or not yet probed).

| Document | Content |
|---|---|
| `reddit-scraping-quickstart.md` | How to get Reddit data the compliant way: PRAW setup, free-tier limits, read-only patterns, archives, terms-of-service constraints |
| `extraction-methods.md` | Full taxonomy of extraction methods (official API, wrappers, JSON endpoints, HTML scraping, SaaS, archives, RSS), integrated from the operator survey with 2026 corrections |
| `targeting-v1.md` | v1 target subreddits for ComfyUI 3D-asset and generative-video workflows, keyword sets, and the collection plan |

## Decisions locked so far

1. Use PRAW (Python). Do not use snoowrap (JavaScript, archived).
2. Use the official free-tier API for live data. Do not scrape HTML or
   unauthenticated JSON endpoints.
3. Use Arctic Shift for history, PullPush as secondary, PRAW for the recent
   window.
4. v1 scope: 3D assets and generative video, from the Stable Diffusion and
   ComfyUI communities.
