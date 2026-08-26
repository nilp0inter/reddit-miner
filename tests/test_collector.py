"""Collector: a pass queues submissions and comments, dedupes on rerun, and a
failing topic never kills the loop."""

from __future__ import annotations

import time

from genflow_miner.collector import CollectorLoop, run_pass
from genflow_miner.store import Store

from conftest import FakeComment, FakeReddit, FakeSubmission


def sub(id, title="Wan 2.2 workflow", **kw):
    return FakeSubmission(
        id=id,
        title=title,
        selftext=kw.pop("selftext", "my ComfyUI workflow JSON"),
        permalink=f"/r/comfyui/comments/{id}/wan_22_workflow/",
        subreddit=kw.pop("subreddit", "comfyui"),
        created_utc=kw.pop("created_utc", 1750000000.0),
        comments=kw.pop("comments", ()),
        over_18=kw.pop("over_18", False),
        **kw,
    )


def comment(id, body="use RIFE for frame interpolation"):
    return FakeComment(
        id=id,
        body=body,
        created_utc=1750000100.0,
        permalink=f"/r/comfyui/comments/abc123/comment/{id}/",
    )


def test_run_pass_queues_submission_and_comments(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("wan", "Wan 2.2", "comfyui")
    reddit = FakeReddit(
        {
            "comfyui": [
                sub(
                    "abc123",
                    comments=(comment("c1"), comment("c2", body="[deleted]")),
                )
            ]
        }
    )
    inserted, failed = run_pass(store, reddit, store.enabled_topics())
    assert failed == 0
    # submission + one live comment; the [deleted] comment is skipped
    assert inserted == 2
    rows = store.claim_pending(10)
    assert {r["reddit_id"] for r in rows} == {"t3_abc123", "t1_c1"}
    sub_row = next(r for r in rows if r["kind"] == "submission")
    assert sub_row["topic_name"] == "wan"
    assert sub_row["title"] == "Wan 2.2 workflow"
    assert sub_row["subreddit"] == "comfyui"


def test_run_pass_dedupes_on_second_run(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("wan", "Wan 2.2", "comfyui")
    reddit = FakeReddit({"comfyui": [sub("abc123", comments=(comment("c1"),))]})
    assert run_pass(store, reddit, store.enabled_topics())[0] == 2
    # Reddit serves the same results again on the next poll
    assert run_pass(store, reddit, store.enabled_topics())[0] == 0
    assert store.pending_count() == 2


def test_run_pass_preserves_nsfw_items_and_context(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("ud", "ComfyUI", "unstable_diffusion")
    media_url = "https://i.redd.it/nsfw-workflow.png"
    reddit = FakeReddit(
        {
            "unstable_diffusion": [
                sub(
                    "nsfw1",
                    over_18=True,
                    subreddit="unstable_diffusion",
                    comments=(comment("cnsfw"),),
                    url=media_url,
                    post_hint="image",
                ),
                sub("ok1", subreddit="unstable_diffusion"),
            ]
        }
    )
    fetched: list[str] = []

    def fetcher(url: str) -> tuple[bytes, str]:
        fetched.append(url)
        return b"NSFW workflow media", "image/png"

    inserted, _ = run_pass(
        store,
        reddit,
        store.enabled_topics(),
        media_dir=tmp_path / "media",
        fetcher=fetcher,
    )
    assert inserted == 3

    rows = store.claim_pending(10)
    assert [row["reddit_id"] for row in rows] == [
        "t3_nsfw1",
        "t1_cnsfw",
        "t3_ok1",
    ]
    assert {row["reddit_id"]: row["is_nsfw"] for row in rows} == {
        "t3_nsfw1": 1,
        "t1_cnsfw": 1,
        "t3_ok1": 0,
    }
    nsfw_submission = next(row for row in rows if row["reddit_id"] == "t3_nsfw1")
    assert nsfw_submission["media"][0]["uri"] == "media://1"
    assert fetched == [media_url]

def test_run_pass_topic_failure_isolated(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("good", "TRELLIS", "comfyui")
    store.add_topic("bad", "HunyuanVideo", "broken")

    class Boom:
        def search(self, *a, **kw):
            raise ConnectionError("reddit 503")

    class Reddit:
        def __init__(self):
            self.subs = {"comfyui": FakeReddit({"comfyui": [sub("s1")]})}

        def subreddit(self, name):
            if name == "broken":
                return Boom()
            return FakeSubredditproxy(self.subs["comfyui"].subreddit(name))

    class FakeSubredditproxy:
        def __init__(self, inner):
            self._inner = inner

        def search(self, *a, **kw):
            return self._inner.search(*a, **kw)

    inserted, failed = run_pass(store, Reddit(), store.enabled_topics())
    assert failed == 1
    assert inserted == 1
    assert store.pending_count() == 1


def test_collector_loop_polls_periodically(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("wan", "Wan 2.2", "comfyui")
    reddit = FakeReddit({"comfyui": [sub("abc123", comments=(comment("c1"),))]})
    loop = CollectorLoop(store, reddit, interval=0.2)
    loop.start()
    try:
        deadline = time.monotonic() + 5
        while store.pending_count() < 2 and time.monotonic() < deadline:
            time.sleep(0.02)
        assert store.pending_count() == 2
        # second poll: same results, nothing new (dedupe)
        time.sleep(0.5)
        assert store.pending_count() == 2
    finally:
        loop.stop()
    assert not loop._thread.is_alive()


def test_collector_loop_survives_failing_source(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("wan", "Wan 2.2", "comfyui")

    class FlakyReddit:
        def __init__(self):
            self.calls = 0

        def subreddit(self, name):
            self.calls += 1
            raise ConnectionError("reddit down")

    flaky = FlakyReddit()
    loop = CollectorLoop(store, flaky, interval=0.1)
    loop.start()
    try:
        deadline = time.monotonic() + 5
        while flaky.calls < 3 and time.monotonic() < deadline:
            time.sleep(0.02)
        assert flaky.calls >= 3, "loop kept polling after repeated failures"
    finally:
        loop.stop()
    assert not loop._thread.is_alive()
