"""Store: persistence, dedupe, and atomic claim semantics."""

from __future__ import annotations

import sqlite3

import threading

import pytest

from reddit_miner.store import Store

from conftest import make_item


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "test.sqlite3")


def test_insert_and_dedupe_by_reddit_id(store):
    store.insert_items([make_item("t3_1"), make_item("t3_2")])
    # second insert of the same ids inserts nothing
    assert store.insert_items([make_item("t3_1"), make_item("t3_2")]) == 0
    # different id inserts fine
    assert store.insert_items([make_item("t3_3")]) == 1
    assert store.pending_count() == 3


def test_claim_marks_delivered_no_duplicates(store):
    store.insert_items([make_item(f"t3_{i}") for i in range(5)])
    first = store.claim_pending(3)
    assert [r["reddit_id"] for r in first] == ["t3_0", "t3_1", "t3_2"]
    second = store.claim_pending(3)
    assert [r["reddit_id"] for r in second] == ["t3_3", "t3_4"]
    assert store.claim_pending(3) == []
    assert store.pending_count() == 0


def test_claim_fields_and_ordering(store):
    store.insert_items(
        [
            make_item("t3_b", body="b"),
            make_item("t3_a", body="a", kind="comment"),
        ]
    )
    rows = store.claim_pending(10)
    # insertion order preserved (first_seen, then reddit_id)
    assert [r["reddit_id"] for r in rows] == ["t3_b", "t3_a"]
    row = rows[0]
    assert set(row) == {
        "reddit_id",
        "kind",
        "title",
        "body",
        "permalink",
        "subreddit",
        "created_utc",
        "topic_name",
        "is_nsfw",
        "first_seen",
        "media",
        "links",
    }
    assert row["kind"] == "submission"
    assert row["body"] == "b"


def test_claim_concurrent_callers_get_disjoint_rows(store):
    store.insert_items([make_item(f"t3_{i}") for i in range(40)])

    results: list[list[str]] = []
    lock = threading.Lock()

    def claim():
        rows = store.claim_pending(20)
        with lock:
            results.append([r["reddit_id"] for r in rows])

    threads = [threading.Thread(target=claim) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    flat = [rid for chunk in results for rid in chunk]
    assert len(flat) == 40, "every row claimed exactly once"
    assert len(set(flat)) == 40, "no row delivered twice"
    assert store.pending_count() == 0


def test_add_topic_duplicate_name_rejected(store):
    store.add_topic("comfyui-3d", "TRELLIS OR Hunyuan3D", "comfyui")
    with pytest.raises(Exception):
        store.add_topic("comfyui-3d", "another query", "all")


def test_enabled_topics(store):
    store.add_topic("a", "qa", "comfyui")
    store.add_topic("b", "qb", "all")
    topics = store.enabled_topics()
    assert [(t["name"], t["query"], t["subreddit"]) for t in topics] == [
        ("a", "qa", "comfyui"),
        ("b", "qb", "all"),
    ]


def test_store_reopens_and_keeps_pending_queue(store, tmp_path):
    store.add_topic("t", "q", "all")
    store.insert_items([make_item("t3_1")])
    # simulate restart: a new Store over the same file
    reopened = Store(tmp_path / "test.sqlite3")
    assert reopened.pending_count() == 1
    rows = reopened.claim_pending(10)
    assert [r["reddit_id"] for r in rows] == ["t3_1"]
    assert reopened.pending_count() == 0


def test_claim_limit_zero_returns_empty(store):
    store.insert_items([make_item("t3_1")])
    assert store.claim_pending(0) == []
    assert store.pending_count() == 1


def test_store_migrates_legacy_items_with_nsfw_default(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE items (
                reddit_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                permalink TEXT NOT NULL,
                subreddit TEXT NOT NULL,
                created_utc REAL NOT NULL,
                topic_name TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                state TEXT NOT NULL,
                delivered_at TEXT
            );
            INSERT INTO items VALUES (
                't3_legacy', 'submission', 'title', 'body', 'url',
                'comfyui', 1.0, 'legacy', '2026-01-01T00:00:00Z',
                'pending', NULL
            );
            """
        )

    store = Store(path)
    row = store.claim_pending(10)[0]
    assert row["reddit_id"] == "t3_legacy"
    assert row["is_nsfw"] == 0
def test_add_monitor_topic_with_null_query(store):
    store.add_topic("monitor", None, "python")
    topics = store.list_topics()
    assert len(topics) == 1
    assert topics[0]["name"] == "monitor"
    assert topics[0]["query"] is None
    assert topics[0]["subreddit"] == "python"
    assert store.enabled_topics()[0]["query"] is None


def test_remove_topic_keeps_items(store):
    store.add_topic("t", "q", "all")
    store.insert_items([make_item("t3_x", topic="t"), make_item("t3_y", topic="t")])
    assert store.remove_topic("t") is True
    assert store.list_topics() == []
    rows = store.claim_pending(10)
    assert {r["reddit_id"] for r in rows} == {"t3_x", "t3_y"}
    assert store.remove_topic("t") is False


def test_set_topic_enabled_toggles_visibility(store):
    store.add_topic("a", "qa", "all")
    store.add_topic("b", "qb", "all")
    assert len(store.enabled_topics()) == 2
    assert store.set_topic_enabled("a", False) is True
    enabled = store.enabled_topics()
    assert len(enabled) == 1 and enabled[0]["name"] == "b"
    assert store.set_topic_enabled("a", True) is True
    assert len(store.enabled_topics()) == 2
    assert store.set_topic_enabled("missing", False) is False


def test_claim_includes_links(store):
    item = make_item(
        "t3_links", links=("https://example.com/a", "https://example.com/b")
    )
    store.insert_items([item])
    rows = store.claim_pending(10)
    assert rows[0]["links"] == ["https://example.com/a", "https://example.com/b"]
    # Deduped link insertion for a second item
    second = make_item("t3_links2", links=("https://example.com/a",))
    store.insert_items([second])
    rows = store.claim_pending(10)
    assert rows[0]["links"] == ["https://example.com/a"]


def test_store_migrates_legacy_query_not_null(tmp_path):
    path = tmp_path / "legacy_query.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE search_topics (
                name TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                subreddit TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            );
            INSERT INTO search_topics (name, query, subreddit) VALUES ('old', 'q', 'all');
            """
        )
    store = Store(path)
    topics = store.list_topics()
    assert any(t["name"] == "old" and t["query"] == "q" for t in topics)
    store.add_topic("monitor", None, "python")
    assert any(t["name"] == "monitor" and t["query"] is None for t in store.list_topics())
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        notnull = next(
            r for r in conn.execute("PRAGMA table_info(search_topics)") if r["name"] == "query"
        )["notnull"]
        assert notnull == 0
