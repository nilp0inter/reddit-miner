"""Downloaded media stays local and is read through MCP resources."""

from __future__ import annotations

import base64

from mcp import Client

from reddit_miner.collector import run_pass
from reddit_miner.reddit_source import collect_topic
from reddit_miner.server import build_server
from reddit_miner.store import Store

from conftest import FakeReddit, FakeSubmission, make_item


def test_submission_media_is_downloaded_and_queued_as_resource(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("images", "ComfyUI", "comfyui")
    image_url = "https://i.redd.it/comfy-workflow.png"
    reddit = FakeReddit(
        {
            "comfyui": [
                FakeSubmission(
                    id="media1",
                    title="Workflow image",
                    selftext="",
                    permalink="/r/comfyui/comments/media1/workflow/",
                    subreddit="comfyui",
                    created_utc=1_750_000_000.0,
                    url=image_url,
                    post_hint="image",
                )
            ]
        }
    )
    fetched: list[str] = []

    def fetcher(url: str) -> tuple[bytes, str]:
        fetched.append(url)
        return b"PNG media", "image/png"

    inserted, failed = run_pass(
        store,
        reddit,
        store.enabled_topics(),
        media_dir=tmp_path / "media",
        fetcher=fetcher,
    )
    assert (inserted, failed) == (1, 0)
    assert fetched == [image_url]

    item = store.claim_pending(10)[0]
    assert set(item["media"][0]) == {"id", "uri", "mime_type"}
    assert item["media"][0]["uri"] == "media://1"
    assert item["media"][0]["mime_type"] == "image/png"

    media = store.get_media(item["media"][0]["id"])
    assert media is not None
    assert "local_path" not in item["media"][0]
    assert (tmp_path / "media" / "t3_media1-0.png").read_bytes() == b"PNG media"

    inserted, failed = run_pass(
        store,
        reddit,
        store.enabled_topics(),
        media_dir=tmp_path / "media",
        fetcher=fetcher,
    )
    assert (inserted, failed) == (0, 0)
    assert fetched == [image_url]


def test_extractor_supports_reddit_video_and_gallery_without_external_urls():
    video_url = "https://v.redd.it/clip/DASH_720.mp4"
    gallery_url = "https://preview.redd.it/gallery-image.png"
    submission = FakeSubmission(
        id="media2",
        title="Video workflow",
        selftext="",
        permalink="/r/comfyui/comments/media2/video/",
        subreddit="comfyui",
        created_utc=1_750_000_000.0,
        url="https://example.invalid/untrusted.jpg",
        media={"reddit_video": {"fallback_url": video_url}},
        media_metadata={"x": {"s": {"u": gallery_url}}},
    )
    reddit = FakeReddit({"comfyui": [submission]})
    topic = {"name": "video", "query": "video", "subreddit": "comfyui"}

    item = next(collect_topic(reddit, topic))
    assert item.media_urls == (video_url, gallery_url)


async def test_media_resource_reads_binary_without_exposing_local_path(tmp_path):
    store = Store(tmp_path / "db.sqlite3")
    store.add_topic("seed", "workflow", "comfyui")
    store.insert_items([make_item("t3_media", topic="seed")])
    path = tmp_path / "media" / "seed.webp"
    path.parent.mkdir()
    path.write_bytes(b"WEBP media")
    assert store.add_media(
        "t3_media",
        "https://i.redd.it/seed.webp",
        "image/webp",
        str(path),
    )

    media_id = store.claim_pending(10)[0]["media"][0]["id"]
    server = build_server(store)
    async with Client(server) as client:
        result = await client.read_resource(f"media://{media_id}")

    content = result.contents[0]
    assert content.mime_type == "application/octet-stream"
    assert base64.b64decode(content.blob) == b"WEBP media"
