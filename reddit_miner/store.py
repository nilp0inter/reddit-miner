"""SQLite persistence for reddit-miner.

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
    query       TEXT,                   -- NULL: collect all new posts
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
    is_nsfw     INTEGER NOT NULL DEFAULT 0,
    first_seen  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    state       TEXT NOT NULL DEFAULT 'pending'  -- 'pending' | 'delivered'
        CHECK (state IN ('pending', 'delivered')),
    delivered_at TEXT,
    FOREIGN KEY (topic_name) REFERENCES search_topics (name)
);
CREATE INDEX IF NOT EXISTS idx_items_state ON items (state);

CREATE TABLE IF NOT EXISTS media (
    id          INTEGER PRIMARY KEY,
    reddit_id   TEXT NOT NULL,
    source_url  TEXT NOT NULL,
    mime_type   TEXT NOT NULL,
    local_path  TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (reddit_id, source_url),
    FOREIGN KEY (reddit_id) REFERENCES items (reddit_id)
);
CREATE INDEX IF NOT EXISTS idx_media_reddit_id ON media (reddit_id);

CREATE TABLE IF NOT EXISTS links (
    id          INTEGER PRIMARY KEY,
    reddit_id   TEXT NOT NULL,
    url         TEXT NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (reddit_id, url),
    FOREIGN KEY (reddit_id) REFERENCES items (reddit_id)
);
CREATE INDEX IF NOT EXISTS idx_links_reddit_id ON links (reddit_id);
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
    media_urls: tuple[str, ...] = ()
    links: tuple[str, ...] = ()
    is_nsfw: bool = False

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
            self._migrate_schema(conn)

    @staticmethod
    def _migrate_schema(conn: sqlite3.Connection) -> None:
        item_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(items)")
        }
        if "is_nsfw" not in item_columns:
            conn.execute(
                "ALTER TABLE items"
                " ADD COLUMN is_nsfw INTEGER NOT NULL DEFAULT 0"
            )

        topic_columns = {
            row["name"]: row for row in conn.execute(
                "PRAGMA table_info(search_topics)"
            )
        }
        query_col = topic_columns.get("query")
        if query_col is not None and query_col["notnull"]:
            # Legacy schema made query NOT NULL. Rebuild the table so
            # monitoring topics (query NULL) can be stored. Rows preserved.
            conn.executescript(
                "CREATE TABLE search_topics_v2 ("
                " name TEXT PRIMARY KEY,"
                " query TEXT,"
                " subreddit TEXT NOT NULL,"
                " enabled INTEGER NOT NULL DEFAULT 1,"
                " created_at TEXT NOT NULL DEFAULT"
                " (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))"
                ");"
                "INSERT INTO search_topics_v2"
                " (name, query, subreddit, enabled, created_at)"
                " SELECT name, query, subreddit, enabled, created_at"
                " FROM search_topics;"
                "DROP TABLE search_topics;"
                "ALTER TABLE search_topics_v2 RENAME TO search_topics;"
            )

    # -- topics ------------------------------------------------------------

    def add_topic(
        self, name: str, query: str | None, subreddit: str = "all"
    ) -> None:
        """Insert a search topic. `query` None monitors all new posts.
        Raises sqlite3.IntegrityError on duplicate name."""
        with _connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO search_topics (name, query, subreddit)"
                " VALUES (?, ?, ?)",
                (name, query, subreddit),
            )
    def remove_topic(self, name: str) -> bool:
        """Delete a topic. Collected items survive; `topic_name` stays as a
        historical label. Returns False when the name does not exist."""
        with _connect(self.db_path) as conn:
            cur = conn.execute(
                "DELETE FROM search_topics WHERE name = ?", (name,)
            )
        return cur.rowcount == 1

    def set_topic_enabled(self, name: str, enabled: bool) -> bool:
        """Enable or disable polling for one topic. Returns False when the
        name does not exist."""
        with _connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE search_topics SET enabled = ? WHERE name = ?",
                (int(enabled), name),
            )
        return cur.rowcount == 1

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
                int(item.is_nsfw),
            )
            for item in items
        ]
        link_rows = [
            (item.reddit_id, url) for item in items for url in item.links
        ]
        with _connect(self.db_path) as conn:
            cur = conn.executemany(
                "INSERT INTO items (reddit_id, kind, title, body, permalink,"
                " subreddit, created_utc, topic_name, is_nsfw)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
                " ON CONFLICT (reddit_id) DO NOTHING",
                rows,
            )
            if link_rows:
                conn.executemany(
                    "INSERT INTO links (reddit_id, url)"
                    " VALUES (?, ?)"
                    " ON CONFLICT (reddit_id, url) DO NOTHING",
                    link_rows,
                )
            return cur.rowcount

    # -- media ---------------------------------------------------------------

    def media_urls(self, reddit_id: str) -> set[str]:
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT source_url FROM media WHERE reddit_id = ?",
                (reddit_id,),
            ).fetchall()
        return {row["source_url"] for row in rows}

    def add_media(
        self,
        reddit_id: str,
        source_url: str,
        mime_type: str,
        local_path: str,
    ) -> bool:
        with _connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO media (reddit_id, source_url, mime_type, local_path)"
                " VALUES (?, ?, ?, ?)"
                " ON CONFLICT (reddit_id, source_url) DO NOTHING",
                (reddit_id, source_url, mime_type, local_path),
            )
        return cursor.rowcount == 1

    def get_media(self, media_id: int) -> dict[str, Any] | None:
        with _connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, reddit_id, source_url, mime_type, local_path"
                " FROM media WHERE id = ?",
                (media_id,),
            ).fetchone()
        return dict(row) if row is not None else None

    def _attach_media(
        self, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not items:
            return items

        reddit_ids = [item["reddit_id"] for item in items]
        placeholders = ", ".join("?" for _ in reddit_ids)
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT id, reddit_id, mime_type FROM media"
                f" WHERE reddit_id IN ({placeholders}) ORDER BY id",
                reddit_ids,
            ).fetchall()

        by_reddit_id: dict[str, list[dict[str, Any]]] = {
            reddit_id: [] for reddit_id in reddit_ids
        }
        for row in rows:
            by_reddit_id[row["reddit_id"]].append(
                {
                    "id": row["id"],
                    "uri": f"media://{row['id']}",
                    "mime_type": row["mime_type"],
                }
            )
        for item in items:
            item["media"] = by_reddit_id[item["reddit_id"]]
        return items

    def _attach_links(
        self, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not items:
            return items

        reddit_ids = [item["reddit_id"] for item in items]
        placeholders = ", ".join("?" for _ in reddit_ids)
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT reddit_id, url FROM links"
                f" WHERE reddit_id IN ({placeholders}) ORDER BY id",
                reddit_ids,
            ).fetchall()

        by_reddit_id: dict[str, list[str]] = {
            reddit_id: [] for reddit_id in reddit_ids
        }
        for row in rows:
            by_reddit_id[row["reddit_id"]].append(row["url"])
        for item in items:
            item["links"] = by_reddit_id[item["reddit_id"]]
        return items

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
                " created_utc, topic_name, is_nsfw, first_seen"
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
        return self._attach_links(self._attach_media([dict(row) for row in rows]))

    def pending_count(self) -> int:
        with _connect(self.db_path) as conn:
            (count,) = conn.execute(
                "SELECT COUNT(*) FROM items WHERE state = 'pending'"
            ).fetchone()
        return int(count)
