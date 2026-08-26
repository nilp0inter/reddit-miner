"""Shared fakes: no network, no PRAW, no real Reddit credentials."""

from __future__ import annotations

from genflow_miner.store import Item


class FakeComment:
    def __init__(self, id, body, created_utc, permalink):
        self.id = id
        self.body = body
        self.created_utc = created_utc
        self.permalink = permalink


class FakeCommentForest:
    def __init__(self, comments):
        self._comments = comments

    def replace_more(self, limit=None):
        pass

    def list(self):
        return self._comments



class FakeSubredditRef:
    """Minimal PRAW submission.subreddit proxy."""

    def __init__(self, display_name):
        self.display_name = display_name


class FakeSubmission:
    def __init__(
        self,
        id,
        title,
        selftext,
        permalink,
        subreddit,
        created_utc,
        comments=(),
        over_18=False,
        url="",
        post_hint=None,
        media=None,
        media_metadata=None,
    ):
        self.id = id
        self.title = title
        self.selftext = selftext
        self.permalink = permalink
        self.subreddit = (
            subreddit
            if hasattr(subreddit, "display_name")
            else FakeSubredditRef(subreddit)
        )
        self.created_utc = created_utc
        self.over_18 = over_18
        self.comments = FakeCommentForest(list(comments))
        self.url = url
        self.post_hint = post_hint
        self.media = media
        self.media_metadata = media_metadata


class FakeSubreddit:
    def __init__(self, submissions):
        self._submissions = list(submissions)

    def search(self, query, limit=None, sort=None):
        return iter(self._submissions)


class FakeReddit:
    """Programmable stand-in for praw.Reddit. Each call to search() returns the
    submissions configured for that subreddit, then repeats them on the next
    poll (simulating Reddit serving the same results again)."""

    def __init__(self, submissions_by_sub):
        self._by_sub = {k: list(v) for k, v in submissions_by_sub.items()}
        self.search_calls = []

    def subreddit(self, name):
        self.search_calls.append(name)
        return FakeSubreddit(self._by_sub.get(name, []))


def make_item(reddit_id, topic="t", kind="submission", **over):
    base = dict(
        reddit_id=reddit_id,
        kind=kind,
        title="A ComfyUI workflow",
        body="workflow JSON inside",
        permalink=f"https://www.reddit.com/r/comfyui/comments/{reddit_id}/",
        subreddit="comfyui",
        created_utc=1750000000.0,
        topic_name=topic,
    )
    base.update(over)
    return Item(**base)
