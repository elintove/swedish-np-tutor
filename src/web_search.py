from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Dict, List
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str


class DuckDuckGoLiteSearchClient:
    """
    No-key web search fallback using DuckDuckGo's lightweight HTML endpoint.

    This is fine for a small university prototype, but an official search API is
    more reliable for production or high-volume use.
    """

    def __init__(
        self,
        *,
        base_url: str = "https://html.duckduckgo.com/html/",
        timeout_s: float = 20.0,
    ):
        self.base_url = base_url
        self.timeout_s = timeout_s

    def search(self, query: str, *, max_results: int = 5) -> List[WebSearchResult]:
        q = query.strip()
        if not q:
            return []

        url = f"{self.base_url}?q={quote_plus(q)}"
        request = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; SwedishNPTutor/1.0)",
            },
            method="GET",
        )

        try:
            with urlopen(request, timeout=self.timeout_s) as response:
                html = response.read().decode("utf-8", errors="replace")
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Web search failed: HTTP {error.code}: {body}") from error
        except URLError as error:
            raise RuntimeError(f"Web search failed: {error.reason}") from error

        parser = _DuckDuckGoLiteParser()
        parser.feed(html)
        return parser.results[: max(1, min(max_results, 10))]


class _DuckDuckGoLiteParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results: List[WebSearchResult] = []
        self._current: Dict[str, str] | None = None
        self._capture_title = False
        self._capture_snippet = False

    def handle_starttag(self, tag: str, attrs: List[tuple[str, str | None]]) -> None:
        attr = {k: v or "" for k, v in attrs}
        classes = set(attr.get("class", "").split())

        if tag == "a" and "result__a" in classes:
            self._current = {"title": "", "url": self._clean_url(attr.get("href", "")), "snippet": ""}
            self._capture_title = True
        elif self._current is not None and "result__snippet" in classes:
            self._capture_snippet = True

    def handle_data(self, data: str) -> None:
        if self._current is None:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._capture_title:
            self._current["title"] = (self._current["title"] + " " + text).strip()
        elif self._capture_snippet:
            self._current["snippet"] = (self._current["snippet"] + " " + text).strip()

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title:
            self._capture_title = False
            if self._current and self._current.get("title") and self._current.get("url"):
                self.results.append(
                    WebSearchResult(
                        title=self._current["title"],
                        url=self._current["url"],
                        snippet=self._current.get("snippet", ""),
                    )
                )
        elif self._capture_snippet and tag in {"a", "div"}:
            self._capture_snippet = False
            self._current = None

    def _clean_url(self, href: str) -> str:
        if not href:
            return ""
        parsed = urlparse(href)
        if parsed.path.startswith("/l/"):
            uddg = parse_qs(parsed.query).get("uddg", [""])[0]
            return unquote(uddg) if uddg else href
        return href
