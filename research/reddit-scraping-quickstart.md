# Reddit Scraping: Quickstart (Verified 2026-08-26)

Scope: read-only research access to Reddit data with the free user-tier API
and a Python wrapper.

## 1. Decision: use PRAW

Use **PRAW** (Python Reddit API Wrapper). Do not use snoowrap.

| | PRAW | snoowrap |
|---|---|---|
| Language | Python | JavaScript (Node.js) |
| Status | Active. Version 8.0.3 on PyPI. Python 3.10+. | Archived by its author in 2024. No maintenance since ~2021. |
| Source | https://github.com/praw-dev/praw | https://github.com/not-an-aardvark/snoowrap |

Note: snoowrap is not a Python wrapper. It is a JavaScript wrapper. Its
repository is archived, and its own issue tracker reports the project as dead
(issue #330).

PRAW follows the Reddit API rules internally. It handles rate-limit waits for
you. You do not need `sleep` calls in your code.

## 2. Why the official API (and not raw scraping)

Reddit closed the old scraping paths in 2025-2026:

- Unauthenticated requests to `reddit.com/...*.json` now return 403. This
  "JSON trick" is dead.
- `robots.txt` disallows unauthenticated crawlers.
- Reddit sued Perplexity in October 2025 for "industrial-scale" scraping. In
  July 2026 a federal judge rejected Perplexity's motion to dismiss.
  Contractual "terms of access" are now an active legal front.

The free user-tier API is the safe path. It is rate-limited, but legal and
stable for research.

## 3. Free tier limits

- 100 queries per minute (QPM) with OAuth, per account.
- 10 QPM without OAuth. This path is irrelevant now because unauthenticated
  access is blocked.
- Limits are averaged over a 10-minute window. Short bursts above 100 QPM are
  tolerated.
- Commercial tiers start near $12,000 per month. Not needed for research.

At a sustained ~100 QPM, one account can pull roughly 6,000 listings per hour.
Each listing returns up to 100 items. That is enough for most research corpora
if you run collection over hours or days.

## 4. Setup procedure

1. Create a Reddit account, or use an existing one.
2. Go to `https://www.reddit.com/prefs/apps`.
3. Click "create another app...".
4. Select the **script** type.
5. Fill in a name, a redirect URI (use `http://localhost:8080` for scripts),
   and save.
6. Record the `client_id` (under the app name) and the `client_secret`.
7. Install PRAW in the project:

```sh
uv add praw
```

8. Create a `praw.ini` file next to the script, or pass credentials directly:

```ini
[bot1]
client_id=YOUR_CLIENT_ID
client_secret=YOUR_CLIENT_SECRET
password=YOUR_PASSWORD
username=YOUR_USERNAME
```

Do not commit `praw.ini` or the secret to git.

## 5. Minimal read-only example

```python
import praw

reddit = praw.Reddit(
    client_id="CLIENT_ID",
    client_secret="CLIENT_SECRET",
    password="PASSWORD",
    user_agent="research:reddit-miner:v0.2 (by u/YOUR_USERNAME)",
    username="USERNAME",
)

# Latest 100 posts from a subreddit
for submission in reddit.subreddit("comfyui").new(limit=100):
    print(submission.created_utc, submission.score, submission.title)

# All comments on one post
submission = reddit.submission(id="5e1az9")
submission.comments.replace_more(limit=None)
for comment in submission.comments.list():
    print(comment.created_utc, comment.score, comment.body)

# Keyword search
for submission in reddit.subreddit("comfyui").search("TRELLIS", limit=100):
    print(submission.title)

# Live stream of new posts
for submission in reddit.subreddit("comfyui").stream.submissions():
    print(submission.title)
```

PRAW returns objects lazily. Attribute access triggers one API call. PRAW
caches the result on the object. Access the same attribute twice, and you pay
one call, not two.

Use a descriptive `user_agent`. Reddit blocks generic or missing user agents.
The format `platform:app-id:version (by u/username)` follows the Reddit API
rules.

## 6. Alternatives inside Python

- **asyncpraw**: the official async version. Use it inside `asyncio` programs.
  Same features as PRAW. https://asyncpraw.readthedocs.io/
- **Direct OAuth requests**: use `requests` with `grant_type=password` for
  token fetch. More work, no benefit for research scripts.
- **RSS feeds**: `https://www.reddit.com/r/{sub}/.rss` still works without
  auth. Sub-100-item snapshots only. Verified live 2026-08-26 (HTTP 200 for
  r/comfyui and r/StableDiffusionUI), but aggressively rate-limited per IP
  (HTTP 429 under light parallel probing). Useful as a cheap change detector,
  nothing more.

## 7. Bulk and historical data (no scraping needed)

For historical corpora, do not replay the API. Use archives:

- **Arctic Shift**: maintained Pushshift successor. Dumps cover 2005 to early
  2024. Offers bulk downloads, an API, and a web interface.
  https://github.com/ArthurHeitmann/arctic_shift
- **PullPush**: Pushshift-like search API. Soft limit ~15 requests per minute,
  hard limit ~30, long-term ~1,000 per hour. https://pullpush.io/

Plan: pull history from Arctic Shift or PullPush. Then top up recent months
through PRAW. This split keeps you far below the 100 QPM cap.

## 8. Terms-of-service constraints

The Reddit Data API Terms and the User Agreement apply to the free tier:

- Do not use API data to train AI models without a separate license.
- Do not resell or redistribute raw API data.
- Stay within the documented rate limits.
- Keep the user agent honest.

Read the current terms before publishing results:
`https://support.reddit.com/agreements` and the Reddit Developer Platform docs
at `https://developers.reddit.com`.

## 9. Sources

- PRAW README (install + quickstart): https://praw.readthedocs.io/
- PRAW repository: https://github.com/praw-dev/praw
- PyPI praw 8.0.3: https://pypi.org/project/praw/
- snoowrap repository (archived): https://github.com/not-an-aardvark/snoowrap
- snoowrap "almost dead" issue:
  https://github.com/not-an-aardvark/snoowrap/issues/330
- Rate limit announcement:
  https://www.reddit.com/r/redditdev/comments/14nbw6g/
- Unauthenticated JSON 403 reports:
  https://www.reddit.com/r/redditdev/comments/1txd5mm/
- Arctic Shift: https://github.com/ArthurHeitmann/arctic_shift
- PullPush: https://pullpush.io/
- Reddit v. Perplexity (Reuters, 2026-07-31):
  https://www.reuters.com/legal/litigation/perplexity-ai-loses-bid-toss-reddit-lawsuit-over-data-scraping-2026-07-31/
- Reddit v. Perplexity (Reuters, 2025-10-22):
  https://www.reuters.com/world/reddit-sues-perplexity-scraping-data-train-ai-system-2025-10-22/
