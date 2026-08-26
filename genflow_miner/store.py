"""SQLite persistence for genflow-miner.

One database file holds search topics and the collected items queue.
Connections are short-lived: every storage operation opens its own connection
with WAL and a busy timeout, so the collector thread and MCP request threads
never share a connection.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS search_topics (
    name        TEXT PRIMARY KEY,
    query       TEXT NOT NULL,
    subreddit   TEXT NOT NULL,
    enabled     INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS items (
    reddit_id   TEXT PRIMARY KEY,       -- t3_xxx / t1_xxx, global dedupe key
    kind        TEXT NOT NULL,          -- 'submission' | 'comment'
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,          -- selftext for submissions, body for comments
    permalink   TEXT NOT NULL,
    subreddit   TEXT NOT NULL,
    created_utc REAL NOT NULL,          -- item creation time (epoch seconds)
    topic_name  TEXT NOT NULL,
    first_seen  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    state       TEXT NOT NULL DEFAULT 'pending'  -- 'pending' | 'delivered'
        CHECK (state IN ('pending', 'delivered')),
    delivered_at TEXT,
    FOREIGN KEY (topic_name) REFERENCES search_topics (name)
);
CREATE INDEX IF NOT EXISTS idx_items_state ON items (state);
"""


@dataclass(frozen=True)
class Item:
    """A collected Reddit submission or comment, distilled for AI processing."""

    reddit_id: str
    kind: str
    title: str
    body: str
    permalink: str
    subreddit: str
    created_utc: float
    topic_name: str


def _connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


class Store:
    """SQLite-backed persistence. One instance per process; thread-safe via
    per-operation connections."""

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        with _connect(self.db_path) as conn:
            conn.executescript(SCHEMA)

    # -- topics ------------------------------------------------------------

    def add_topic(self, name: str, query: str, subreddit: str = "all") -> None:
        """Insert a search topic. Raises sqlite3.IntegrityError on duplicate name."""
        with _connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO search_topics (name, query, subreddit) VALUES (?, ?, ?)",
                (name, query, subreddit),
            )

    def list_topics(self) -> list[dict[str, Any]]:
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT name, query, subreddit, enabled, created_at"
                " FROM search_topics ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    def enabled_topics(self) -> list[dict[str, Any]]:
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT name, query, subreddit FROM search_topics"
                " WHERE enabled = 1 ORDER BY name"
            ).fetchall()
        return [dict(row) for row in rows]

    # -- items ---------------------------------------------------------------

    def insert_items(self, items: list[Item]) -> int:
        """Insert new items; existing reddit_ids are ignored (dedupe).

        Returns the number of rows actually inserted.
        """
        if not items:
            return 0
        rows = [
            (
                item.reddit_id,
                item.kind,
                item.title,
                item.body,
                item.permalink,
                item.subreddit,
                item.created_utc,
                item.topic_name,
            )
            for item in items
        ]
        with _connect(self.db_path) as conn:
            cur = conn.executemany(
                "INSERT INTO items (reddit_id, kind, title, body, permalink,"
                " subreddit, created_utc, topic_name)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (reddit_id) DO NOTHING",
                rows,
            )
            return cur.rowcount

    def claim_pending(self, limit: int) -> list[dict[str, Any]]:
        """Atomically select pending items and mark them delivered.

        Runs as one BEGIN IMMEDIATE transaction so two concurrent callers can
        never receive the same row. Each item is delivered at most once: if the
        consumer crashes after claiming, those items are not re-delivered.
        """
        conn = _connect(self.db_path)
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                "SELECT reddit_id, kind, title, body, permalink, subreddit,"
                " created_utc, topic_name, first_seen"
                " FROM items WHERE state = 'pending'"
                " ORDER BY rowid LIMIT ?",
                (limit,),
            ).fetchall()
            ids = [row["reddit_id"] for row in rows]
            if ids:
                conn.executemany(
                    "UPDATE items SET state = 'delivered',"
                    " delivered_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
                    " WHERE reddit_id = ?",
                    [(reddit_id,) for reddit_id in ids],
                )
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def pending_count(self) -> int:
        with _connect(self.db_path) as conn:
            (count,) = conn.execute(
                "SELECT COUNT(*) FROM items WHERE state = 'pending'"
            ).fetchone()
        return int(count)
