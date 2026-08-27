"""MCP server (streamable HTTP) plus CLI entry point.

The server exposes five tools: add_topic, list_topics, remove_topic,
set_topic_enabled, get_unprocessed_results. A collector thread runs in
the same process.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import logging
import sqlite3
import sys

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError

from .collector import CollectorLoop
from .reddit_source import build_reddit
from .store import Store

log = logging.getLogger(__name__)


def build_server(store: Store) -> MCPServer:
    """Build the MCP server with the five public tools."""
    server = MCPServer(
        name="reddit-miner",
        title="reddit-miner",
        description=(
            "Collect community knowledge from Reddit"
            " and hand it to an AI for distillation."
        ),
        version="0.2.0",
    )

    @server.tool(
        name="add_topic",
        description=(
            "Add a topic for the collector to poll."
            " `query` is optional: when omitted the collector ingests every"
            " new post in `subreddit`; when given it searches that subreddit."
            " `subreddit` defaults to 'all' (site-wide)."
        ),
    )
    def add_topic(
        name: str, query: str | None = None, subreddit: str = "all"
    ) -> dict[str, object]:
        name = name.strip()
        subreddit = subreddit.strip()
        if query is None:
            normalized_query: str | None = None
        else:
            if not isinstance(query, str):
                raise ToolError("query must be a string or null")
            normalized_query = query.strip()
            if not normalized_query:
                raise ToolError("query must not be empty when provided")
        if not name or not subreddit:
            raise ToolError("name and subreddit must not be empty")
        try:
            store.add_topic(name, normalized_query, subreddit)
        except sqlite3.IntegrityError:
            raise ToolError(f"topic name already exists: {name}") from None
        return {
            "topic": {
                "name": name,
                "query": normalized_query,
                "subreddit": subreddit,
            }
        }

    @server.tool(
        name="list_topics",
        description=(
            "List all saved topics with their queries and subreddits."
            " A null query means the topic monitors every new post in its"
            " subreddit."
        ),
    )
    def list_topics() -> dict[str, object]:
        return {"topics": store.list_topics()}

    @server.tool(
        name="remove_topic",
        description="Delete a saved topic. Collected items keep their topic_name.",
    )
    def remove_topic(name: str) -> dict[str, object]:
        name = name.strip()
        if not name:
            raise ToolError("name must not be empty")
        if not store.remove_topic(name):
            raise ToolError(f"topic not found: {name}")
        return {"removed": name}

    @server.tool(
        name="set_topic_enabled",
        description="Enable or disable polling for a saved topic.",
    )
    def set_topic_enabled(name: str, enabled: bool) -> dict[str, object]:
        name = name.strip()
        if not name:
            raise ToolError("name must not be empty")
        if not isinstance(enabled, bool):
            raise ToolError("enabled must be a boolean")
        if not store.set_topic_enabled(name, enabled):
            raise ToolError(f"topic not found: {name}")
        return {"topic": {"name": name, "enabled": enabled}}

    @server.tool(
        name="get_unprocessed_results",
        description=(
            "Claim up to `limit` collected items (submissions and comments)"
            " that have not been delivered for AI distillation yet."
            " Items are marked delivered atomically, so each item is returned"
            " at most once across all callers. If the consumer crashes after"
            " claiming, those items are NOT redelivered (at-most-once)."
        ),
    )
    def get_unprocessed_results(limit: int = 20) -> dict[str, object]:
        if limit < 1 or limit > 500:
            raise ToolError("limit must be between 1 and 500")
        return {"items": store.claim_pending(limit)}

    @server.resource(
        "media://{media_id}",
        description="Read a collected image or video by its MCP media URI.",
        mime_type="application/octet-stream",
    )
    def read_media(media_id: str) -> bytes:
        try:
            media = store.get_media(int(media_id))
        except ValueError:
            media = None
        if media is None:
            raise ResourceNotFoundError(f"media does not exist: {media_id}")

        try:
            return Path(media["local_path"]).read_bytes()
        except OSError as exc:
            raise ResourceNotFoundError(
                f"media file is unavailable: {media_id}"
            ) from exc

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reddit-miner",
        description=(
            "Reddit community-knowledge collector with an MCP server"
            " (streamable HTTP)."
        ),
    )
    parser.add_argument(
        "--db", default="reddit-miner.sqlite3", help="SQLite database path"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="MCP HTTP bind host (default 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="MCP HTTP bind port (default 8000)"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=600.0,
        help="collector poll interval in seconds (default 600)",
    )
    parser.add_argument(
        "--media-dir",
        default="reddit-media",
        help="local directory for downloaded image and video files",
    )
    parser.add_argument(
        "--log-level", default="INFO", help="log level (default INFO)"
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    store = Store(args.db)

    try:
        reddit = build_reddit()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    server = build_server(store)
    collector = CollectorLoop(
        store, reddit, args.poll_interval, media_dir=args.media_dir
    )
    collector.start()
    log.info(
        "reddit-miner: MCP on http://%s:%d/mcp, poll interval %ss, db %s",
        args.host,
        args.port,
        args.poll_interval,
        args.db,
    )
    try:
        server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port,
        )
    finally:
        collector.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
