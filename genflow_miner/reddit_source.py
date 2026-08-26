"""Reddit source: PRAW search over saved topics. Read-only, official API only."""

from __future__ import annotations

import html
import logging
import os
from collections.abc import Iterator

from .store import Item

log = logging.getLogger(__name__)

# Fetch at most this many submissions per topic per poll, and at most this many
# comments per submission. Keeps a poll sweep inside the free-tier budget.
SEARCH_LIMIT = 100
COMMENT_LIMIT = 200


MEDIA_HOST_SUFFIXES = (".redd.it", ".redditmedia.com", ".redditstatic.com")
MEDIA_SUFFIXES = (
    ".avif",
    ".gif",
    ".jpeg",
    ".jpg",
    ".mp4",
    ".png",
    ".webm",
    ".webp",
)

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

    Deleted and removed bodies are skipped. NSFW status is preserved on each
    collected item. Errors here are caught by the caller per topic.
    """
    subreddit = reddit.subreddit(topic["subreddit"])
    for submission in subreddit.search(topic["query"], limit=SEARCH_LIMIT, sort="new"):
        is_nsfw = bool(getattr(submission, "over_18", False))
        yield Item(
            reddit_id=f"t3_{submission.id}",
            kind="submission",
            title=submission.title or "",
            body=submission.selftext or "",
            permalink=f"https://www.reddit.com{submission.permalink}",
            subreddit=submission.subreddit.display_name,
            created_utc=float(submission.created_utc),
            topic_name=topic["name"],
            is_nsfw=is_nsfw,
            media_urls=extract_media_urls(submission),
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
                is_nsfw=is_nsfw,
            )


def extract_media_urls(submission) -> tuple[str, ...]:
    """Return safe Reddit-hosted image and video URLs for one submission."""
    candidates: list[str] = []

    url = _clean_url(getattr(submission, "url", None))
    post_hint = getattr(submission, "post_hint", None)
    if url and (
        post_hint in {"image", "hosted:video", "rich:video"}
        or _has_media_suffix(url)
    ):
        candidates.append(url)

    media = getattr(submission, "media", None)
    if isinstance(media, dict):
        reddit_video = media.get("reddit_video")
        if isinstance(reddit_video, dict):
            fallback_url = _clean_url(reddit_video.get("fallback_url"))
            if fallback_url:
                candidates.append(fallback_url)

    metadata = getattr(submission, "media_metadata", None)
    if isinstance(metadata, dict):
        for asset in metadata.values():
            if not isinstance(asset, dict):
                continue
            source = asset.get("s")
            if not isinstance(source, dict):
                continue
            for key in ("u", "gif", "mp4"):
                candidate = _clean_url(source.get(key))
                if candidate:
                    candidates.append(candidate)

    return tuple(
        dict.fromkeys(candidate for candidate in candidates if _is_reddit_media_url(candidate))
    )


def _clean_url(value) -> str | None:
    if not isinstance(value, str):
        return None
    return html.unescape(value)


def _has_media_suffix(url: str) -> bool:
    return url.split("?", 1)[0].lower().endswith(MEDIA_SUFFIXES)


def _is_reddit_media_url(url: str) -> bool:
    from urllib.parse import urlsplit

    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    return parsed.scheme == "https" and hostname.lower().endswith(MEDIA_HOST_SUFFIXES)
