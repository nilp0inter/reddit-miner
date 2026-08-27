"""Download supported Reddit media to local storage.

Media files stay local. MCP clients receive resource URIs, never local paths.
"""

from __future__ import annotations

import logging
import mimetypes
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from .store import Item, Store

log = logging.getLogger(__name__)

MEDIA_HOST_SUFFIXES = (".redd.it", ".redditmedia.com", ".redditstatic.com")
MAX_MEDIA_BYTES = 50 * 1024 * 1024
FetchMedia = Callable[[str], tuple[bytes, str]]


def fetch_media(url: str) -> tuple[bytes, str]:
    """Download one Reddit-hosted image or video with a bounded response size."""
    if not _is_reddit_media_url(url):
        raise ValueError("media URL is not a Reddit-owned HTTPS URL")

    request = Request(
        url,
        headers={"User-Agent": "reddit-miner/0.2 media collector"},
    )
    with urlopen(request, timeout=30) as response:
        if not _is_reddit_media_url(response.geturl()):
            raise ValueError("media redirect left Reddit-owned HTTPS URLs")

        mime_type = response.headers.get_content_type()
        if not mime_type.startswith(("image/", "video/")):
            raise ValueError(f"unsupported media type: {mime_type}")

        content_length = response.headers.get("Content-Length")
        if content_length is not None:
            try:
                too_large = int(content_length) > MAX_MEDIA_BYTES
            except ValueError:
                too_large = False
            if too_large:
                raise ValueError("media exceeds download limit")

        chunks: list[bytes] = []
        total = 0
        while chunk := response.read(64 * 1024):
            total += len(chunk)
            if total > MAX_MEDIA_BYTES:
                raise ValueError("media exceeds download limit")
            chunks.append(chunk)

    return b"".join(chunks), mime_type


def persist_media(
    store: Store,
    item: Item,
    media_dir: str | Path,
    fetcher: FetchMedia = fetch_media,
) -> int:
    """Download media URLs for one submission and record local files.

    Failed downloads leave the text item queued. A later poll can retry because
    only completed downloads create a media row.
    """
    if not item.media_urls:
        return 0

    directory = Path(media_dir)
    known_urls = store.media_urls(item.reddit_id)
    stored = 0

    for ordinal, url in enumerate(dict.fromkeys(item.media_urls)):
        if url in known_urls:
            continue
        try:
            content, mime_type = fetcher(url)
        except Exception:
            log.exception("media download failed for %s", url)
            continue

        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{item.reddit_id}-{ordinal}{_suffix(url, mime_type)}"
        temporary = path.with_suffix(path.suffix + ".part")
        temporary.write_bytes(content)
        temporary.replace(path)

        if store.add_media(item.reddit_id, url, mime_type, str(path)):
            stored += 1
            known_urls.add(url)
        else:
            path.unlink(missing_ok=True)

    return stored


def _is_reddit_media_url(url: str) -> bool:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    return parsed.scheme == "https" and hostname.lower().endswith(MEDIA_HOST_SUFFIXES)


def _suffix(url: str, mime_type: str) -> str:
    suffix = mimetypes.guess_extension(mime_type)
    if suffix == ".jpe":
        return ".jpg"
    if suffix:
        return suffix

    candidate = Path(urlsplit(url).path).suffix.lower()
    return candidate if candidate else ".bin"
