# Methods to Extract Data and Knowledge from Reddit Subreddits

Integrated 2026-08-26. Base: operator-provided survey document (full taxonomy
below, preserved). Corrections in the "2026 status" blocks come from live
verification and current primary sources; they override the survey text where
the two disagree.

## 2026 corrections summary (read this first)

| Method | Survey says | Verified 2026 status | Verdict |
|---|---|---|---|
| Official Data API | ~100 QPM free tier | Unchanged. Still 100 QPM OAuth. | Use |
| PRAW | Standard Python wrapper | Active, v8.0.3, Python 3.10+. | Use |
| Snoowrap | Primary JS wrapper | Repository archived 2024, dead (issue #330). | Drop |
| `.json` endpoints | Works, ~10 req/min unauth | Returns 403 unauthenticated since 2025-2026. | Dead |
| old.reddit HTML scraping | Works with throttle | Possible but ToS-hostile; Reddit v. Perplexity (motion to dismiss rejected 2026-07-31) makes it legally live territory. | Avoid |
| Browser automation | Works, heavy | Same legal exposure as HTML scraping. | Avoid |
| SaaS scrapers (Apify etc.) | Viable, paid | Viable; compliance shifted onto the provider. | Optional |
| Browser extensions | Manual export | Still fine for ad-hoc manual thread exports. | Optional |
| CLI scrapers (ScrapiReddit, YARS) | Built on public JSON/HTML | Break with the 403 wall; unmaintained path. | Avoid |
| Pushshift | "Availability varies" | Dead since 2023. Successors: Arctic Shift (dumps 2005-2024, API) and PullPush (~15 req/min soft). | Use successors |
| BigQuery public datasets | fh-bigquery tables | Largely stale historical mirrors; Arctic Shift dumps supersede them. | Skip |
| RSS/Atom feeds | Available, metadata only | Verified live 2026-08-26 (HTTP 200), but aggressive per-IP 429 throttling observed. Change detector only. | Optional |

## Overview

The survey covers the main ways to extract data and knowledge from Reddit,
with a focus on subreddits, from the official Data API to unofficial JSON
endpoints, HTML scraping, archival datasets, and third-party platforms. It
weighs reliability, rate limits, legal/ToS alignment, and implementation
complexity.

## Official Reddit Data API

Reddit exposes a formal Data API that reads and writes posts, comments, votes,
and other entities via authenticated requests. The modern API requires
registration, acceptance of the Developer Terms and Data API Terms, and OAuth
2 authentication for all clients.

### Capabilities and entities

The API treats Reddit objects as typed IDs ("things"): `t3_` for posts, `t1_`
for comments, `t5_` for subreddits. Typical use cases: streaming new posts
from a subreddit, fetching comment trees, posting content, moderation actions.

### Access, rate limits, and terms

Developers register an application, obtain client credentials, and follow the
Data API terms, including commercial-use restrictions. Free clients are capped
at roughly 100 queries per minute per OAuth client ID over a rolling window.
Commercial use requires explicit written approval and potentially a paid
agreement (reported near $12,000/month entry point in 2026).

## High-level API wrappers

### Python: PRAW

PRAW wraps the official API and handles authentication, rate-limiting, and
object modeling. Read-only mode needs client ID, client secret, and a user
agent. A fully authorized script also passes username and password. PRAW
iterates `subreddit.hot()`, fetches submission comments, or posts content,
while respecting Reddit's API rules and back-off requirements.

**2026 status:** PRAW 8.0.3, Python 3.10+, actively maintained under the
praw-dev organization. Install with `uv add praw`. For async environments use
`asyncpraw` (official, same features).

### JavaScript: Snoowrap and similar

Snoowrap is a fully featured JavaScript wrapper providing a Promise-based
asynchronous interface for Node and browser contexts. After initialization
with client credentials, it exposes `getUser()`, subreddit listing accessors,
and voting or commenting actions.

**2026 status:** dead. The repository was archived by its author in 2024; the
project's own issue tracker declared it "almost dead" (issue #330) before
that. For JavaScript, call the OAuth API directly or use a maintained
library. For genflow-miner (Python), snoowrap is out of scope.

## Unofficial JSON endpoints (the `.json` trick)

Appending `.json` to a Reddit URL historically exposed the page data without
API keys, for example `https://www.reddit.com/r/programming/.json`, at around
10 requests per minute unauthenticated.

**2026 status:** dead. Unauthenticated requests to these endpoints now return
403. Multiple independent reports from late 2025 through 2026 confirm the
block. Do not build on this path.

## HTML scraping (new and old Reddit)

### Old Reddit HTML (old.reddit.com)

`old.reddit.com` serves server-rendered pages with minimal JavaScript. A
typical workflow uses `requests` with a realistic User-Agent plus
BeautifulSoup to parse listings, threads, and user pages. Search results and
deep comment trees are more heavily rate-limited and may need residential IPs
to avoid 403/429 responses. Layout changes make scrapers brittle.

### New Reddit and DOM-based tools

Scrapers targeting the modern UI automate a browser (Selenium, ChromeDriver)
and read the DOM after load. One public example collects posts from
r/MachineLearning with Selenium into SQLite.

**2026 status (both):** technically possible, legally hostile. Reddit's
robots.txt disallows unauthenticated crawlers, and Reddit v. Perplexity
(October 2025 filing; motion to dismiss rejected 2026-07-31) puts
"industrial-scale" scraping and terms-of-access violations in active
litigation. genflow-miner must not use HTML scraping.

## Third-party scrapers and no-code platforms

### SaaS scrapers (Apify and similar)

Managed scrapers accept subreddit URLs or search terms and deliver structured
JSON/CSV/Excel, hiding API keys and proxy rotation behind a service layer.
One Apify actor supports posts, comments, user profiles, and subreddit
metadata with sort and comment-depth options, and export integrations such as
n8n or Zapier. Pricing is on the order of a few dollars per 1,000 results.

**2026 status:** viable if budget exists; the provider contractually handles
compliance. Not needed for genflow-miner v1 — the free API covers our volume.

### Browser extensions for quick exports

Extensions parse the loaded DOM of a thread and export comments (body, author,
score, timestamp, depth, subreddit, awards, permalinks) to CSV or JSON.
No rate limits beyond the browser session. Good for ad-hoc manual exports of
individual threads.

## Dedicated non-API scraper libraries

ScrapiReddit ("complete Reddit scraper without API keys", CLI and library)
and YARS (Python, `requests`-based, built on public `.json` endpoints) wrap
the unofficial surfaces into reusable pipelines.

**2026 status:** these inherit the `.json` 403 wall and HTML-scraping
exposure. Avoid.

## Historical and bulk datasets

### Pushshift

The Pushshift.io Reddit API (built by the r/datasets moderation team) provided
enhanced search, aggregation, and analytics over archived submissions and
comments: `https://api.pushshift.io/reddit/comment/search`,
`/reddit/submission/search`, and a per-post comment-ID listing.

**2026 status:** dead since 2023. Successors:

- **Arctic Shift** — maintained archive with dumps (2005 to early 2024), an
  API, and a web interface: https://github.com/ArthurHeitmann/arctic_shift
- **PullPush** — Pushshift-like search API, ~15 requests/minute soft limit,
  ~30 hard, ~1,000/hour long-term: https://pullpush.io/

### Google BigQuery public Reddit datasets

Pushshift-derived tables (`fh-bigquery.reddit_posts.*`,
`fh-bigquery.reddit_comments.*`) allowed SQL over hundreds of millions of
posts, filterable by subreddit and date, with comment-post joins on
`link_id`.

**2026 status:** these mirrors are stale (the classic era ended around 2015;
later refreshes are partial). Arctic Shift dumps supersede them for coverage
and freshness. Skip.

## Scraping via RSS/Atom feeds

Subreddit feeds (`/.rss`) remain available without authentication and provide
title, link, author, and timestamp — post-level metadata, not comment trees.

**2026 status:** verified live 2026-08-26 (HTTP 200 for r/comfyui and
r/StableDiffusionUI). Aggressive per-IP 429 throttling observed under light
probing. Use as a cheap change detector to trigger API collection, nothing
more.

## Comparison of main approaches

| Method | Auth / keys | Scale and limits | Data depth | Maintenance | ToS alignment |
|---|---|---|---|---|---|
| Official Data API (raw) | App registration, OAuth client ID/secret | Free tier ~100 QPM; stricter for commercial | Full posts, comments, votes, moderation | Stable, versioned | Covered by Developer and Data API Terms |
| PRAW / Snoowrap | Same as official API | Same as official API; library manages limits | Rich object access | PRAW active; snoowrap archived | Wrappers follow API rules automatically |
| `.json` endpoints | None | Was ~10 req/min unauth; now 403 | Structured listings, posts, comments | Dead | Undocumented; now blocked |
| HTML scraping (old.reddit) | None; HTTP + User-Agent | IP-reputation sensitive; needs throttling/proxies | Anything visible in HTML | High; brittle | robots.txt and ToS hostile; litigated |
| Browser automation | None; browser session | Heavy; low concurrency | Full DOM | High; UI breakage | Same as HTML scraping |
| SaaS scrapers | SaaS API key | Proxy rotation; large scale | Configurable | Outsourced | Provider handles compliance |
| Pushshift / BigQuery archives | None for public access | Historical scale; not real-time | Rich historic metadata | Medium; maintainer-dependent | Independent archives |
| Browser extensions | None; user browser | Manual; per-page | Detailed thread comments | Low for users | Client-side over loaded pages |
| RSS/Atom feeds | None | Lightweight monitoring | Post metadata only | Low; stable format | Longstanding public interface |

## Choosing an approach (genflow-miner decisions)

1. Live data: official Data API through PRAW. Read-only. (Long-term
   compliant path.)
2. Historical bulk: Arctic Shift dumps, PullPush as secondary.
3. Change detection: RSS feeds, optional.
4. Excluded: `.json` endpoints (dead), HTML scraping and browser automation
   (ToS-hostile, litigated), SaaS scrapers (unnecessary cost), stale BigQuery
   mirrors.

## Legal, ethical, and practical considerations

Review Reddit's Developer Terms, Data API Terms, and Responsible Builder
Policy before starting, especially restrictions on commercial use and
redistribution of content. Use honest User-Agents, cache responses to avoid
refetching, and avoid aggressive parallelism. Extracted data is
user-generated content: handle it with respect for user expectations and
applicable law, especially for large-scale analysis of specific communities
or individuals.

## References

1. Reddit API Overview — https://developers.reddit.com/docs/capabilities/server/reddit-api
2. Reddit Data API Wiki — https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki
3. Scrape Reddit Without the API (2026) — https://creatorcrawl.com/blog/how-to-scrape-reddit-without-api/
4. How to Scrape Reddit Without the API (dev.to) — https://dev.to/odeeb/how-to-scrape-reddit-without-the-api-after-the-2023-price-changes-3nhm
5. How to Scrape Reddit Without API: 4 No-Key Methods — https://www.redditcommentscraper.com/article-scrape-reddit-without-api.html
6. Reddit API wiki — https://www.reddit.com/wiki/api
7. PRAW Read-Only Reddit Instances — https://praw.readthedocs.io/en/stable/getting_started/quick_start.html
8. PRAW README — https://github.com/praw-dev/praw/blob/main/README.rst
9. PRAW 8.0.3 Quick Start — https://praw.readthedocs.io/en/latest/getting_started/quick_start.html
10. snoowrap repository (archived) — https://github.com/not-an-aardvark/snoowrap
11. snoowrap "This project is almost dead" (issue #330) — https://github.com/not-an-aardvark/snoowrap/issues/330
12. Web-Scraping-Reddit (Selenium example) — https://github.com/casper-hansen/Web-Scraping-Reddit
13. Apify Reddit Scraper — https://apify.com/harshmaur/reddit-scraper
14. ScrapiReddit — https://github.com/rodneykeilson/ScrapiReddit
15. YARS — https://github.com/datavorous/yars
16. Pushshift Documentation — https://reddit-api.readthedocs.io/_/downloads/en/latest/pdf/
17. r/bigquery datasets wiki — https://www.reddit.com/r/bigquery/wiki/datasets/
18. Reddit full post history on BigQuery — https://www.reddit.com/r/bigquery/comments/3mv82i/dataset_reddits_full_post_history_shared_on/
19. Arctic Shift — https://github.com/ArthurHeitmann/arctic_shift
20. PullPush — https://pullpush.io/
21. Unauthenticated JSON 403 reports — https://www.reddit.com/r/redditdev/comments/1txd5mm/
22. Reddit v. Perplexity, motion to dismiss rejected (Reuters, 2026-07-31) — https://www.reuters.com/legal/litigation/perplexity-ai-loses-bid-toss-reddit-lawsuit-over-data-scraping-2026-07-31/
23. Reddit sues Perplexity (Reuters, 2025-10-22) — https://www.reuters.com/world/reddit-sues-perplexity-scraping-data-train-ai-system-2025-10-22/
