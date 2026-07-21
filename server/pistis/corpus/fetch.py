"""Fetch manifest sources into a snapshot.

GOV.UK entries use the official Content API (structured JSON, OGL v3.0).
HTML entries (FCA / MoneyHelper) are reduced to main-content text. Stdlib
only — no requests/bs4 on this box. Network code stays out of unit tests;
the pure reducers below are fixture-tested.
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from html.parser import HTMLParser

# Browser-equivalent headers: some official sites 403 clients that send no
# Accept header. MoneyHelper's WAF blocks non-browser TLS stacks entirely —
# those entries stay in the manifest but need a licensed/approved feed, not a
# workaround (see SESSION_HANDOFF).
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}
GOVUK_API = "https://www.gov.uk/api/content"
FETCH_DELAY_SECONDS = 0.5

_BLOCK_TAGS = frozenset(
    "p li h1 h2 h3 h4 h5 h6 td th dt dd figcaption caption".split()
)
_SKIP_TAGS = frozenset("script style noscript svg iframe form nav header footer aside".split())


class _TextExtractor(HTMLParser):
    """Collects readable text, scoped to <main> when the page has one."""

    def __init__(self, scope_to_main: bool) -> None:
        super().__init__(convert_charrefs=True)
        self._scope_to_main = scope_to_main
        self._in_main = not scope_to_main
        self._skip_depth = 0
        self._lines: list[str] = []
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "main":
            self._in_main = True
        if tag in _SKIP_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "main" and self._scope_to_main:
            self._in_main = False
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._in_main and not self._skip_depth and data.strip():
            self._buffer.append(data)

    def _flush(self) -> None:
        line = re.sub(r"\s+", " ", " ".join(self._buffer)).strip()
        self._buffer = []
        if line:
            self._lines.append(line)

    def text(self) -> str:
        self._flush()
        sentences = [
            line if line[-1] in ".!?:" else f"{line}."
            for line in self._lines
        ]
        return " ".join(sentences)


def strip_html(html: str) -> str:
    extractor = _TextExtractor(scope_to_main="<main" in html)
    extractor.feed(html)
    return extractor.text()


def _html_of(value) -> str | None:
    """GOV.UK body fields are either an HTML string or a list of
    {content_type, content} renditions."""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item.get("content_type") == "text/html":
                return item.get("content")
    return None


def govuk_text(payload: dict) -> tuple[str, str | None]:
    """Reduce a GOV.UK Content API payload to text + source update date."""
    details = payload.get("details", {})
    chunks: list[str] = []

    def add(value) -> None:
        html = _html_of(value)
        if html and html.strip():
            chunks.append(html)

    add(details.get("body"))
    for part in details.get("parts") or []:
        title = part.get("title")
        if title:
            chunks.append(f"<h2>{title}</h2>")
        add(part.get("body"))
    for key in ("introductory_paragraph", "more_information", "what_you_need_to_know"):
        add(details.get(key))

    updated = payload.get("public_updated_at")
    return strip_html("\n".join(chunks)), (updated[:10] if updated else None)


def _get(url: str, allowed_prefixes: tuple[str, ...]) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        # Redirects are followed automatically — re-check the FINAL host so a
        # compromised or misconfigured source can't bounce the fetch off the
        # allowlist.
        final = response.geturl()
        if not final.startswith(allowed_prefixes):
            raise ValueError(f"redirected outside the allowed hosts: {final}")
        return response.read()


def fetch_entry_text(kind: str, locator: str) -> tuple[str, str | None]:
    """Fetch one manifest entry. Returns (text, last_updated)."""
    from pistis.corpus.manifest import ALLOWED_HTML_HOSTS

    time.sleep(FETCH_DELAY_SECONDS)
    if kind == "govuk":
        raw = _get(f"{GOVUK_API}{locator}", ("https://www.gov.uk/",))
        return govuk_text(json.loads(raw.decode("utf-8")))
    return strip_html(_get(locator, ALLOWED_HTML_HOSTS).decode("utf-8", errors="replace")), None
