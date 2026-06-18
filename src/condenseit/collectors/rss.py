"""RSS and Atom feed collection with optional file-based caching."""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import feedparser
import httpx
import trafilatura

from condenseit.collectors.feed_dates import parse_feed_entry_date
from condenseit.collectors.health import collect_with_health
from condenseit.config import FeedConfig
from condenseit.fetch_headers import digest_fetch_headers
from condenseit.store.database import ContentStore

logger = logging.getLogger(__name__)

# Matches og:image or twitter:image meta tags in any attribute order.
# Group 1 captures the content value.
_OG_IMAGE_RE = re.compile(
    r'<meta\b[^>]*\bproperty=["\']og:image["\'][^>]*\bcontent=["\']([^"\']+)["\']'
    r'|<meta\b[^>]*\bcontent=["\']([^"\']+)["\'][^>]*\bproperty=["\']og:image["\']'
    r'|<meta\b[^>]*\bname=["\']twitter:image["\'][^>]*\bcontent=["\']([^"\']+)["\']'
    r'|<meta\b[^>]*\bcontent=["\']([^"\']+)["\'][^>]*\bname=["\']twitter:image["\']',
    re.IGNORECASE,
)


def _extract_og_image(html_text: str) -> str | None:
    """Return the first og:image or twitter:image URL found in ``html_text``."""
    match = _OG_IMAGE_RE.search(html_text)
    if not match:
        return None
    for group in match.groups():
        if group:
            return group.strip()
    return None


@dataclass
class CollectedArticle:
    url: str
    title: str
    content: str
    source: str
    category: str
    published_at: str
    content_hash: str
    image_url: str | None = field(default=None)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "category": self.category,
            "content_hash": self.content_hash,
            "published_at": self.published_at,
            "collected_at": datetime.now(UTC).isoformat(),
            "image_url": self.image_url,
        }


class RSSCollector:
    def __init__(
        self,
        feeds: list[FeedConfig],
        *,
        cache_enabled: bool = False,
        cache_dir: str | Path = "",
        cache_ttl_minutes: int = 60,
        force_refresh: bool = False,
    ) -> None:
        self.feeds = feeds
        self.fetch_headers = digest_fetch_headers()
        self.client = httpx.Client(
            timeout=30.0,
            follow_redirects=True,
            headers=self.fetch_headers,
        )
        self._cache_enabled = cache_enabled
        self._cache_dir = Path(cache_dir) if cache_dir else Path()
        self._cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._force_refresh = force_refresh

    @staticmethod
    def _cache_short_hash(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def _cache_paths(self, url: str) -> tuple[Path, Path]:
        h = self._cache_short_hash(url)
        return self._cache_dir / f"{h}.xml", self._cache_dir / f"{h}.meta.json"

    def _cached_read(self, url: str) -> str | None:
        """Return cached feed XML if within TTL, or None to force re-fetch."""
        if not self._cache_enabled or self._force_refresh:
            return None
        xml_path, meta_path = self._cache_paths(url)
        if not xml_path.is_file() or not meta_path.is_file():
            return None
        try:
            meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(meta["cached_at"])
            if datetime.now(UTC) - cached_at.replace(tzinfo=UTC) < self._cache_ttl:
                logger.info("Feed cache HIT: %s", url)
                return xml_path.read_text(encoding="utf-8")
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            pass
        return None

    def _cached_write(self, url: str, text: str, etag: str = "", last_modified: str = "") -> None:
        if not self._cache_enabled:
            return
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        xml_path, meta_path = self._cache_paths(url)
        xml_path.write_text(text, encoding="utf-8")
        meta_path.write_text(
            json.dumps({
                "url": url,
                "cached_at": datetime.now(UTC).isoformat(),
                "etag": etag,
                "last_modified": last_modified,
            }),
            encoding="utf-8",
        )
        logger.info("Feed cache WRITE: %s", url)

    # ------------------------------------------------------------------
    # Article page cache (full text extracted by trafilatura)
    # ------------------------------------------------------------------
    @property
    def _article_cache_dir(self) -> Path:
        return self._cache_dir / "articles"

    def _article_cache_path(self, url: str) -> Path:
        h = self._cache_short_hash(url)
        return self._article_cache_dir / f"{h}.json"

    def _article_cached_read(self, url: str) -> tuple[str, str | None] | None:
        """Return (extracted_text, image_url_or_None) if cache hit within TTL."""
        if not self._cache_enabled or self._force_refresh:
            return None
        path = self._article_cache_path(url)
        if not path.is_file():
            return None
        try:
            meta: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(meta["cached_at"])
            if datetime.now(UTC) - cached_at.replace(tzinfo=UTC) < self._cache_ttl:
                logger.info("Article cache HIT: %s", url)
                return meta["text"], meta.get("image_url")
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            pass
        return None

    def _article_cached_write(self, url: str, text: str, image_url: str | None = None) -> None:
        if not self._cache_enabled:
            return
        self._article_cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._article_cache_path(url)
        path.write_text(
            json.dumps({
                "url": url,
                "cached_at": datetime.now(UTC).isoformat(),
                "text": text,
                "image_url": image_url,
            }),
            encoding="utf-8",
        )
        logger.info("Article cache WRITE: %s", url)

    def collect_feed_results(
        self,
        total: int = 0,
    ) -> list[tuple[FeedConfig, list[CollectedArticle], str | None]]:
        """Per-feed collection; ``error`` is None on success."""
        out: list[tuple[FeedConfig, list[CollectedArticle], str | None]] = []
        for idx, feed in enumerate(self.feeds, start=1):
            logger.info("Feed %d/%d: %s", idx, total, feed.url)
            items, (_url, error, _count) = collect_with_health(
                feed.url,
                lambda feed=feed: self._collect_feed(feed),
                log_label=f"Failed to collect feed {feed.url}",
            )
            out.append((feed, items, error))
        return out

    def collect_all(self) -> list[CollectedArticle]:
        articles: list[CollectedArticle] = []
        for _feed, items, _err in self.collect_feed_results():
            articles.extend(items)
        return articles

    def _collect_feed(self, feed: FeedConfig) -> list[CollectedArticle]:
        parsed = feedparser.parse(self._fetch_feed_text(feed.url))
        source_title = parsed.feed.get("title", feed.url)
        items: list[CollectedArticle] = []

        for entry in parsed.entries[:15]:
            link = entry.get("link")
            if not link:
                continue
            title = entry.get("title", "Untitled")
            content, image_url = self._extract_content(link, entry)
            if not content.strip():
                continue
            published = self._parse_published(entry)
            items.append(
                CollectedArticle(
                    url=link,
                    title=title,
                    content=content,
                    source=source_title,
                    category=feed.category,
                    published_at=published,
                    content_hash=ContentStore.content_hash(content),
                    image_url=image_url,
                ),
            )
        return items

    def _fetch_feed_text(self, url: str) -> str:
        cached = self._cached_read(url)
        if cached is not None:
            return cached

        response = self.client.get(url)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 403:
                raise
            return self._fetch_feed_text_with_urllib(url, exc)

        self._cached_write(
            url,
            response.text,
            etag=response.headers.get("etag", ""),
            last_modified=response.headers.get("last-modified", ""),
        )
        return response.text

    def _fetch_feed_text_with_urllib(
        self,
        url: str,
        original_exc: httpx.HTTPStatusError,
    ) -> str:
        logger.info("RSS feed %s returned 403 via httpx; retrying with urllib", url)
        request = Request(url, headers=self.fetch_headers)
        try:
            with urlopen(request, timeout=30.0) as response:
                body = response.read()
                encoding = response.headers.get_content_charset() or "utf-8"
        except (OSError, URLError) as exc:
            raise original_exc from exc
        text = body.decode(encoding, errors="replace")
        self._cached_write(url, text)
        return text

    # Minimum character threshold for RSS embed content to be considered
    # "full-text". Feeds like wechat2rss already embed full articles in
    # ``content:encoded`` or ``summary/description``. If the embed content
    # meets this threshold the article page is NOT fetched, saving bandwidth
    # and latency.
    _FULLTEXT_THRESHOLD = 200

    def _extract_content(
        self,
        url: str,
        entry: feedparser.FeedParserDict,
    ) -> tuple[str, str | None]:
        """Extract article content from RSS embed or fetch the page.

        Checks embed sources in order:
        1. ``content:encoded`` (feedparser → ``entry.content``) – common for
           full-text feeds like wechat2rss, Medium, etc.
        2. ``summary`` / ``description``

        If the best available embed content meets ``_FULLTEXT_THRESHOLD``
        chars the page is **not** fetched.  The embed content is passed
        through ``trafilatura`` to strip HTML noise and produce clean
        text, reducing LLM token usage.

        ``image_url`` is the first ``og:image`` or ``twitter:image`` found
        on the fetched page, or ``None`` when unavailable.
        """
        # --- Step 1: check RSS embed for full-text ---
        # Priority 1: content:encoded (feedparser exposes via entry.content)
        embed_text = ""
        content_list = entry.get("content", [])
        if content_list:
            # content is a list of dicts; take the first one's value
            embed_text = content_list[0].get("value", "") or ""

        # Priority 2: summary / description (only if content:encoded is empty)
        if not embed_text:
            embed_text = entry.get("summary", "") or entry.get("description", "")

        if isinstance(embed_text, str):
            embed_text = embed_text.strip()
        else:
            embed_text = str(embed_text).strip()

        if len(embed_text) >= self._FULLTEXT_THRESHOLD:
            logger.debug(
                "Full-text RSS embed for %s (%d chars), skipping fetch",
                url,
                len(embed_text),
            )
            # Clean HTML noise from embed content to reduce LLM token usage
            cleaned = trafilatura.extract(
                embed_text,
                include_comments=False,
            )
            if cleaned:
                return cleaned, None
            # trafilatura returned nothing; fall through to fetch
            logger.debug(
                "trafilatura returned empty for embed %s, will fetch page",
                url,
            )

        # --- Step 2: check article page cache ---
        cached = self._article_cached_read(url)
        if cached is not None:
            return cached

        # --- Step 3: fetch article page ---
        image_url: str | None = None
        try:
            page = self.client.get(url)
            page.raise_for_status()
            image_url = _extract_og_image(page.text)
            extracted = trafilatura.extract(
                page.text,
                include_comments=False,
            )
            if extracted:
                self._article_cached_write(url, extracted, image_url)
                return extracted, image_url
        except Exception as exc:
            logger.debug("article fetch failed for %s: %s", url, exc)

        # --- Step 4: fallback to RSS embed ---
        return embed_text, image_url

    @staticmethod
    def _parse_published(entry: feedparser.FeedParserDict) -> str:
        return parse_feed_entry_date(entry)


def collect_rss_feeds(feeds: list[FeedConfig]) -> list[dict[str, str]]:
    return [a.to_dict() for a in RSSCollector(feeds).collect_all()]
