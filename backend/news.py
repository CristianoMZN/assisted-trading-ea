"""Configurable RSS news collection with explicit empty and failure states."""

from __future__ import annotations

import email.utils
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from urllib.parse import urlsplit


MAX_FEED_BYTES = 2_000_000
MAX_ITEMS_PER_SOURCE = 10
DEFAULT_KEYWORDS = {
    "WIN": ("win", "ibovespa", "bovespa", "ibov", "b3", "ações brasileiras", "selic", "copom", "juros", "brasil"),
    "WDO": ("wdo", "dólar", "dollar", "usd/brl", "usdbrl", "câmbio", "selic", "copom", "fed", "federal reserve", "brasil", "payroll"),
}


@dataclass(frozen=True)
class NewsItem:
    title: str
    summary: str
    published_at: str | None
    source: str


@dataclass(frozen=True)
class NewsSourceResult:
    status: str
    source: str
    observed_at: str
    valid_until: str
    items: tuple[NewsItem, ...]
    summary: str

    def as_evidence(self) -> dict:
        return {
            "type": "news",
            "status": self.status,
            "source": self.source,
            "observed_at": self.observed_at,
            "valid_until": self.valid_until,
            "summary": self.summary,
            "data": [asdict(item) for item in self.items],
        }


def configured_feed_urls() -> list[str]:
    return [value.strip() for value in os.getenv("NEWS_RSS_URLS", "").split(",") if value.strip()][:5]


def _source_name(url: str) -> str:
    parsed = urlsplit(url)
    return parsed.hostname or "configured-news-source"


def _fetch(url: str, timeout_seconds: float) -> bytes:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("news feeds must use HTTPS without embedded credentials")
    request = urllib.request.Request(url, headers={"User-Agent": "AssistedTradingBackend/0.1"})
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        data = response.read(MAX_FEED_BYTES + 1)
    if len(data) > MAX_FEED_BYTES:
        raise ValueError("news feed exceeded size limit")
    return data


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(element: ET.Element, *names: str) -> str:
    expected = {name.lower() for name in names}
    for child in element.iter():
        if child is element or _tag_name(child.tag) not in expected:
            continue
        value = " ".join(part.strip() for part in child.itertext() if part.strip())
        if value:
            return value
    return ""


def _published_at(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = email.utils.parsedate_to_datetime(value)
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _feed_entries(data: bytes) -> list[tuple[str, str, str | None]]:
    root = ET.fromstring(data)
    entries = [node for node in root.iter() if _tag_name(node.tag) in ("item", "entry")]
    result = []
    for entry in entries:
        title = _child_text(entry, "title")
        summary = _child_text(entry, "description", "summary", "content")
        published = _child_text(entry, "pubdate", "published", "updated", "date")
        if title:
            result.append((title[:500], summary[:1500], _published_at(published)))
    return result


class RSSNewsAdapter:
    def __init__(
        self,
        feed_urls: list[str] | None = None,
        *,
        timeout_seconds: float = 4.0,
        transport: Callable[[str, float], bytes] = _fetch,
        keywords: dict[str, tuple[str, ...]] | None = None,
    ):
        self.feed_urls = feed_urls if feed_urls is not None else configured_feed_urls()
        self.timeout_seconds = timeout_seconds
        self.transport = transport
        self.keywords = keywords or DEFAULT_KEYWORDS

    def collect(self, logical_symbol: str) -> list[NewsSourceResult]:
        observed = datetime.now(timezone.utc)
        collected_at = observed.isoformat().replace("+00:00", "Z")
        expiry = (observed + timedelta(minutes=15)).isoformat().replace("+00:00", "Z")
        if logical_symbol not in ("WIN", "WDO"):
            raise ValueError("logical_symbol must be WIN or WDO")
        if not self.feed_urls:
            return [NewsSourceResult("not_configured", "configuration", collected_at, expiry, (), "Nenhuma fonte de notícias configurada.")]

        terms = tuple(term.casefold() for term in self.keywords.get(logical_symbol, ()))
        results = []
        for url in self.feed_urls:
            source = _source_name(url)
            try:
                raw = self.transport(url, self.timeout_seconds)
                entries = _feed_entries(raw)
                relevant = []
                for title, summary, published_at in entries:
                    text = f"{title} {summary}".casefold()
                    if terms and not any(term in text for term in terms):
                        continue
                    relevant.append(NewsItem(title, re.sub(r"\s+", " ", summary).strip(), published_at, source))
                    if len(relevant) >= MAX_ITEMS_PER_SOURCE:
                        break
                if relevant:
                    summaries = " | ".join(item.title for item in relevant)
                    results.append(NewsSourceResult("available", source, collected_at, expiry, tuple(relevant), summaries[:2000]))
                else:
                    results.append(NewsSourceResult("empty", source, collected_at, expiry, (), "Fonte consultada; nenhuma notícia pertinente encontrada."))
            except Exception:
                results.append(NewsSourceResult("unavailable", source, collected_at, expiry, (), "Fonte de notícias indisponível."))
        return results
