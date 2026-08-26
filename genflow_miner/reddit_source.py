"""Reddit source: PRAW search over saved topics. Read-only, official API only."""

from __future__ import annotations

import logging
import os
from collections.abc import Iterator

from .store import Item

log = logging.getLogger(__name__)

# Fetch at most this many submissions per topic per poll, and at most this many
# comments per submission. Keeps a poll sweep inside the free-tier budget.
SEARCH_LIMIT = 100
COMMENT_LIMIT = 200


def build_reddit():
    """Build a read-only PRAW Reddit instance from environment credentials.

    Requires REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT.
    """
    import praw  # deferred: tests use fakes and never import it

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get(
        "REDDIT_USER_AGENT",
        "research:genflow-miner:v0.1 (script, read-only)",
    )
    missing = [
        n
        for n, v in (
            ("REDDIT_CLIENT_ID", client_id),
            ("REDDIT_CLIENT_SECRET", client_secret),
        )
        if not v
    ]
    if missing:
        raise RuntimeError(
            f"missing environment variables: {', '.join(missing)}"
        )
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        check_for_updates=False,
    )


def collect_topic(reddit, topic: dict) -> Iterator[Item]:
    """Yield items for one topic: matching submissions and their comments.

    NSFW submissions (over_18) are excluded at ingestion. Deleted/removed
    bodies are skipped. Errors here are caught by the caller per topic.
    """
    subreddit = reddit.subreddit(topic["subreddit"])
    for submission in subreddit.search(topic["query"], limit=SEARCH_LIMIT, sort="new"):
        if getattr(submission, "over_18", False):
            continue
        yield Item(
            reddit_id=f"t3_{submission.id}",
            kind="submission",
            title=submission.title or "",
            body=submission.selftext or "",
            permalink=f"https://www.reddit.com{submission.permalink}",
            subreddit=submission.subreddit.display_name,
            created_utc=float(submission.created_utc),
            topic_name=topic["name"],
        )
        submission.comments.replace_more(limit=0)
        for comment in submission.comments.list():
            body = getattr(comment, "body", None)
            if not body or body in ("[deleted]", "[removed]"):
                continue
            yield Item(
                reddit_id=f"t1_{comment.id}",
                kind="comment",
                title=submission.title or "",
                body=body,
                permalink=f"https://www.reddit.com{comment.permalink}",
                subreddit=submission.subreddit.display_name,
                created_utc=float(comment.created_utc),
                topic_name=topic["name"],
            )
