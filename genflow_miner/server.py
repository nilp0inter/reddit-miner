"""MCP server (streamable HTTP) plus CLI entry point.

The server exposes exactly three tools: add_search_topic, list_search_topics,
get_unprocessed_results. A collector thread runs in the same process.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .collector import CollectorLoop
from .reddit_source import build_reddit
from .store import Store

log = logging.getLogger(__name__)


def build_server(store: Store) -> MCPServer:
    """Build the MCP server with the three public tools."""
    server = MCPServer(
        name="genflow-miner",
        title="genflow-miner",
        description=(
            "Collect ComfyUI/Stable Diffusion workflow knowledge from Reddit"
            " and hand it to an AI for distillation."
        ),
        version="0.1.0",
    )

    @server.tool(
        name="add_search_topic",
        description=(
            "Add a saved Reddit search topic the collector will poll."
            " `subreddit` defaults to 'all' (site-wide search)."
        ),
    )
    def add_search_topic(
        name: str, query: str, subreddit: str = "all"
    ) -> dict[str, object]:
        name = name.strip()
        query = query.strip()
        subreddit = subreddit.strip()
        if not name or not query or not subreddit:
            raise ToolError("name, query, and subreddit must not be empty")
        try:
            store.add_topic(name, query, subreddit)
        except sqlite3.IntegrityError:
            raise ToolError(f"topic name already exists: {name}") from None
        return {
            "topic": {"name": name, "query": query, "subreddit": subreddit}
        }

    @server.tool(
        name="list_search_topics",
        description="List all saved search topics with their queries and subreddits.",
    )
    def list_search_topics() -> dict[str, object]:
        return {"topics": store.list_topics()}

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

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="genflow-miner",
        description=(
            "Reddit workflow-knowledge collector with an MCP server"
            " (streamable HTTP)."
        ),
    )
    parser.add_argument(
        "--db", default="genflow-miner.sqlite3", help="SQLite database path"
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
    collector = CollectorLoop(store, reddit, args.poll_interval)
    collector.start()
    log.info(
        "genflow-miner: MCP on http://%s:%d/mcp, poll interval %ss, db %s",
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
