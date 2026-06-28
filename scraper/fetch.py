"""HTTP fetching for the scraper.

Turns a URL into a `PageContext`: status, content-type, decoded HTML, and a parsed
BeautifulSoup tree. Pure I/O — it does not decide a page's *type* (that's
`classify.py`) and it never raises (failures come back as `PageType.ERROR`).
"""

import time

import requests

from .types import PageContext, PageType

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 8           # seconds per request
RETRIES = 1           # extra attempts after the first (transient failures only)
RETRY_BACKOFF = 1.0   # seconds between attempts
_TRANSIENT = (429, 500, 502, 503, 504)   # worth a retry; other non-200s are permanent


def make_soup(html: str):
    """Parse HTML with lxml if it's installed, else the stdlib parser.

    The fallback means the scraper still runs on a machine without lxml — it's a
    recommended dependency for speed/robustness, not a hard requirement.
    """
    from bs4 import BeautifulSoup
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")


def fetch_page(url: str, business_name: str = "") -> PageContext:
    """Fetch one URL, retrying once on a timeout / connection error / transient 5xx.

    Always returns a `PageContext`; never raises. Many "errors" in a crawl are just
    network blips, so a single cheap retry recovers a fair share of them.
    """
    ctx = PageContext(url=url, business_name=business_name)

    for attempt in range(RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        except Exception as e:                 # timeout, connection reset, DNS, etc.
            ctx.error = str(e)
            if attempt < RETRIES:
                time.sleep(RETRY_BACKOFF)
                continue
            ctx.page_type = PageType.ERROR
            return ctx

        ctx.status = resp.status_code
        ctx.content_type = resp.headers.get("Content-Type", "").lower()

        if resp.status_code in _TRANSIENT and attempt < RETRIES:
            ctx.error = f"HTTP {resp.status_code}"
            time.sleep(RETRY_BACKOFF)
            continue                            # server hiccup / rate limit — try again
        if resp.status_code != 200:
            ctx.page_type = PageType.ERROR
            ctx.error = f"HTTP {resp.status_code}"
            return ctx

        # Only parse bodies that look like HTML; classify() types the rest from the
        # content-type / URL we've recorded here.
        if "html" in ctx.content_type or "xml" in ctx.content_type or not ctx.content_type:
            ctx.html = resp.text
            ctx.soup = make_soup(resp.text)
        return ctx

    return ctx   # unreachable, but keeps the function total
