"""HTTP fetching for the scraper.

Turns a URL into a `PageContext`: status, content-type, decoded HTML, and a parsed
BeautifulSoup tree. This stage is pure I/O — it does not decide a page's *type*
(that's `classify.py`) and it never raises (failures come back as `PageType.ERROR`).
"""

import requests

from .types import PageContext, PageType

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 8  # seconds per request


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
    """Fetch one URL. Always returns a `PageContext`; never raises."""
    ctx = PageContext(url=url, business_name=business_name)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except Exception as e:
        ctx.page_type = PageType.ERROR
        ctx.error = str(e)
        return ctx

    ctx.status = resp.status_code
    ctx.content_type = resp.headers.get("Content-Type", "").lower()

    if resp.status_code != 200:
        ctx.page_type = PageType.ERROR
        ctx.error = f"HTTP {resp.status_code}"
        return ctx

    # Only parse bodies that look like HTML. Non-HTML (pdf/image/etc.) is left for
    # classify() to type from the content-type / URL we've recorded here.
    if "html" in ctx.content_type or "xml" in ctx.content_type or not ctx.content_type:
        ctx.html = resp.text
        ctx.soup = make_soup(resp.text)

    return ctx
