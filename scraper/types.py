"""Shared types for the website scraper package.

The scraper turns a business website into "post-like" dicts — the same shape Flow 1
produces from Reddit — so the existing AI extractor (`extract_website_deal`) and the
DB layer don't need to change.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class PageType(str, Enum):
    """How a fetched page should be handled. Decided by `classify()`."""
    STATIC_HTML = "static_html"   # server-rendered HTML — parse it now
    SPA = "spa"                   # JS-rendered shell — needs a browser (Tier 3)
    PDF = "pdf"                   # linked PDF, e.g. a menu — needs pdf text (Tier 3)
    IMAGE = "image"               # image flyer — needs vision (Tier 3)
    NON_HTML = "non_html"         # some other content type we don't handle
    ERROR = "error"               # fetch failed / non-200


@dataclass
class PageContext:
    """Everything we know about one fetched URL, passed between the stages."""
    url: str
    business_name: str = ""
    status: Optional[int] = None
    content_type: str = ""
    html: str = ""
    soup: Any = None              # BeautifulSoup, or None for non-HTML / fetch errors
    page_type: PageType = PageType.STATIC_HTML
    error: Optional[str] = None


@dataclass
class DealText:
    """A page worth sending to the AI. Mirrors the Reddit "post" contract exactly."""
    title: str
    body: str
    source_url: str
    subreddit: str = "website"
    posted_at: Optional[str] = None

    def as_post(self) -> dict:
        return {
            "title": self.title,
            "body": self.body,
            "source_url": self.source_url,
            "subreddit": self.subreddit,
            "posted_at": self.posted_at,
        }
