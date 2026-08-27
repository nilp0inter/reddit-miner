# Research Index

Deep-research notes for reddit-miner. All facts in these documents carry a
verification status: `verified` (checked against a primary source or probed
live on 2026-08-26) or `unverified` (secondary source or not yet probed).

| Document | Content |
|---|---|
| `reddit-scraping-quickstart.md` | How to get Reddit data the compliant way: PRAW setup, free-tier limits, read-only patterns, archives, terms-of-service constraints |
| `extraction-methods.md` | Full taxonomy of extraction methods (official API, wrappers, JSON endpoints, HTML scraping, SaaS, archives, RSS), integrated from the operator survey with 2026 corrections |
| `minimax-h3-readiness-assessment.md` | Worked example: using reddit-miner to collect MiniMax H3 video knowledge — one deployment, not the system's scope |

## Decisions locked so far

1. Use PRAW (Python). Do not use snoowrap (JavaScript, archived).
2. Use the official free-tier API for live data. Do not scrape HTML or
   unauthenticated JSON endpoints.
3. Use Arctic Shift for history, PullPush as secondary, PRAW for the recent
   window.
4. Scope is domain-neutral. Topics are operator-chosen — keyword searches inside any subreddit or whole-subreddit monitoring — so the same collector serves programming, hardware, gaming, finance, creative, or any other community. Domain targeting lives in the operator's chosen topics, not in the system's defaults.
