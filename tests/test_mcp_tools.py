"""MCP tools: all three capabilities via the in-memory SDK client."""

from __future__ import annotations

import json

import pytest

from reddit_miner.server import build_server
from reddit_miner.store import Store

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
            "add_topic",
            "list_topics",
            "remove_topic",
            "set_topic_enabled",
            "get_unprocessed_results",
        }

        res = await client.call_tool(
            "add_topic",
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
            "add_topic", {"name": "video", "query": "HunyuanVideo"}
        )

        res = await client.call_tool("list_topics", {})
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
        await client.call_tool("add_topic", {"name": "a", "query": "q"})
        res = await client.call_tool("add_topic", {"name": "a", "query": "q"})


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
async def test_add_monitor_topic_without_query(store):
    from mcp import Client

    server = build_server(store)
    async with Client(server) as client:
        res = await client.call_tool(
            "add_topic", {"name": "monitor", "subreddit": "python"}
        )
        assert not res.is_error
        payload = json.loads(res.content[0].text)
        assert payload["topic"]["query"] is None
        assert payload["topic"]["subreddit"] == "python"
        res = await client.call_tool("list_topics", {})
        payload = json.loads(res.content[0].text)
        assert any(
            t["name"] == "monitor" and t["query"] is None for t in payload["topics"]
        )


async def test_add_topic_empty_query_rejected(store):
    from mcp import Client

    server = build_server(store)
    async with Client(server) as client:
        res = await client.call_tool("add_topic", {"name": "bad", "query": "  "})
        assert res.is_error
        assert "query must not be empty" in res.content[0].text


async def test_remove_topic_via_mcp(store):
    from mcp import Client

    server = build_server(store)
    async with Client(server) as client:
        await client.call_tool("add_topic", {"name": "t", "query": "q"})
        store.insert_items([make_item("t3_keep", topic="t")])
        res = await client.call_tool("remove_topic", {"name": "t"})
        assert not res.is_error
        payload = json.loads(res.content[0].text)
        assert payload["removed"] == "t"
        res = await client.call_tool("list_topics", {})
        payload = json.loads(res.content[0].text)
        assert payload["topics"] == []
        # items survive removal
        assert store.pending_count() == 1
        res = await client.call_tool("remove_topic", {"name": "missing"})
        assert res.is_error
        assert "not found" in res.content[0].text


async def test_set_topic_enabled_via_mcp(store):
    from mcp import Client

    server = build_server(store)
    async with Client(server) as client:
        await client.call_tool("add_topic", {"name": "a", "query": "qa"})
        await client.call_tool("add_topic", {"name": "b", "query": "qb"})
        res = await client.call_tool(
            "set_topic_enabled", {"name": "a", "enabled": False}
        )
        assert not res.is_error
        topics = store.enabled_topics()
        assert len(topics) == 1 and topics[0]["name"] == "b"
        res = await client.call_tool(
            "set_topic_enabled", {"name": "a", "enabled": True}
        )
        assert len(store.enabled_topics()) == 2
        res = await client.call_tool(
            "set_topic_enabled", {"name": "missing", "enabled": False}
        )
        assert res.is_error
        assert "not found" in res.content[0].text


async def test_claim_includes_links_via_mcp(store):
    from mcp import Client

    store.insert_items(
        [
            make_item(
                "t3_lnk",
                body="see https://example.com/x",
                links=("https://example.com/x",),
            )
        ]
    )
    server = build_server(store)
    async with Client(server) as client:
        res = await client.call_tool("get_unprocessed_results", {"limit": 5})
        payload = json.loads(res.content[0].text)
        assert payload["items"][0]["links"] == ["https://example.com/x"]
