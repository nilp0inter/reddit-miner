"""Long-running collector: periodically polls every enabled topic and queues
new items. One topic failing never stops the loop."""

from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from .media import FetchMedia, fetch_media, persist_media

from .reddit_source import collect_topic
from .store import Store

log = logging.getLogger(__name__)


def run_pass(
    store: Store,
    reddit,
    topics: list[dict],
    *,
    media_dir: str | Path = "media",
    fetcher: FetchMedia = fetch_media,
) -> tuple[int, int]:
    """One collection pass. Per-topic failures are logged and skipped.

    Returns (inserted_count, failed_topics).
    """
    inserted = 0
    failed = 0
    for topic in topics:
        try:
            items = list(collect_topic(reddit, topic))
            new = store.insert_items(items)
            for item in items:
                persist_media(store, item, media_dir, fetcher)
        except Exception:
            failed += 1
            log.exception("topic fetch failed: %s", topic["name"])
            continue
        if new:
            log.info("topic %s: queued %d new items", topic["name"], new)
        inserted += new
    return inserted, failed


class CollectorLoop:
    """Background thread that runs run_pass every interval seconds."""

    def __init__(
        self,
        store: Store,
        reddit,
        interval: float,
        media_dir: str | Path = "media",
        fetcher: FetchMedia = fetch_media,
    ):
        self.store = store
        self.reddit = reddit
        self.interval = interval
        self.media_dir = media_dir
        self.fetcher = fetcher
        self.stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.wake_event = threading.Event()

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run, name="collector", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.wake_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)

    def run_once(self) -> tuple[int, int]:
        return run_pass(
            self.store,
            self.reddit,
            self.store.enabled_topics(),
            media_dir=self.media_dir,
            fetcher=self.fetcher,
        )

    def _run(self) -> None:
        while not self.stop_event.is_set():
            started = time.monotonic()
            try:
                self.run_once()
            except Exception:
                # run_pass already isolates per-topic failures; this guards the
                # topic listing itself (e.g. transient DB error).
                log.exception("collection pass crashed; retrying next interval")
            elapsed = time.monotonic() - started
            self.wake_event.wait(timeout=max(0.0, self.interval - elapsed))
            self.wake_event.clear()
