"""MCP tools: all three capabilities via the in-memory SDK client."""

from __future__ import annotations

import json

import pytest

from genflow_miner.server import build_server
from genflow_miner.store import Store

from conftest import make_item


@pytest.fixture()
def store(tmp_path):
    return Store(tmp_path / "db.sqlite3")


async def test_add_list_topics(store):
    from mcp import Client

    server = build_server(store)
    async with Client(server) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        assert tools == {
            "add_search_topic",
            "list_search_topics",
            "get_unprocessed_results",
        }

        res = await client.call_tool(
            "add_search_topic",
            {"name": "comfyui-3d", "query": "TRELLIS OR Hunyuan3D", "subreddit": "comfyui"},
        )
        assert not res.is_error
        payload = json.loads(res.content[0].text)
        assert payload["topic"] == {
            "name": "comfyui-3d",
            "query": "TRELLIS OR Hunyuan3D",
            "subreddit": "comfyui",
        }

        # default subreddit is 'all'
        await client.call_tool(
            "add_search_topic", {"name": "video", "query": "HunyuanVideo"}
        )

        res = await client.call_tool("list_search_topics", {})
        payload = json.loads(res.content[0].text)
        assert [
            (topic["name"], topic["query"], topic["subreddit"])
            for topic in payload["topics"]
        ] == [
            ("comfyui-3d", "TRELLIS OR Hunyuan3D", "comfyui"),
            ("video", "HunyuanVideo", "all"),
        ]


async def test_add_duplicate_topic_returns_tool_error(store):
    from mcp import Client

    server = build_server(store)
    async with Client(server) as client:
        await client.call_tool("add_search_topic", {"name": "a", "query": "q"})
        res = await client.call_tool("add_search_topic", {"name": "a", "query": "q"})
        assert res.is_error
        assert "already exists" in res.content[0].text


async def test_get_unprocessed_results_claims_at_most_once(store):
    from mcp import Client

    store.insert_items([make_item(f"t3_{i}") for i in range(3)])
    server = build_server(store)
    async with Client(server) as client:
        res = await client.call_tool(
            "get_unprocessed_results", {"limit": 2}
        )
        payload = json.loads(res.content[0].text)
        assert [item["reddit_id"] for item in payload["items"]] == [
            "t3_0",
            "t3_1",
        ]

        res = await client.call_tool("get_unprocessed_results", {"limit": 2})
        payload = json.loads(res.content[0].text)
        assert [item["reddit_id"] for item in payload["items"]] == ["t3_2"]

        res = await client.call_tool("get_unprocessed_results", {"limit": 2})
        payload = json.loads(res.content[0].text)
        assert payload["items"] == []


async def test_get_unprocessed_results_bad_limit(store):
    from mcp import Client

    store.insert_items([make_item("t3_1")])
    server = build_server(store)
    async with Client(server) as client:
        res = await client.call_tool("get_unprocessed_results", {"limit": 0})
        assert res.is_error
