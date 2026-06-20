"""Business website scraper — orchestrator.

Crawls a business's own site for deal content and returns "post-like" dicts for the
AI pipeline. The crawl is a small same-domain breadth-first walk (max MAX_PAGES);
each page is fetched, classified, and routed to an extractor, and every outcome is
recorded for coverage metrics.

Public API (kept stable so search/deal_finder.py + search/runner.py don't change):
    scrape_business_website(url, business_name) -> list[dict]
"""

from collections import deque
from urllib.parse import urljoin, urlparse

from .classify import classify
from .extractors import extract_deals, should_follow_link
from .fetch import fetch_page
from .metrics import ScrapeMetrics

MAX_PAGES = 8   # max pages to visit per business site (the AI call is per-business, not per-page)


def scrape_business_website(url: str, business_name: str,
                            metrics: ScrapeMetrics = None) -> list:
    """Crawl a business website for deal content.

    Returns a list of post-like dicts: {title, body, source_url, subreddit, posted_at}.
    Pass a shared `metrics` to aggregate coverage across many sites (e.g. a future
    scheduled crawl); when omitted, a per-site summary is printed.
    """
    standalone = metrics is None
    metrics = metrics or ScrapeMetrics()
    metrics.record_site()

    visited = set()
    queue = deque([url])
    results = []

    while queue and len(visited) < MAX_PAGES:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        ctx = fetch_page(current, business_name)
        ctx.page_type = classify(ctx)

        # Discover links from the pristine soup BEFORE extraction — extraction may
        # strip nav/header/footer, which is exactly where menu/deal links live.
        if ctx.soup is not None and len(visited) < MAX_PAGES:
            for link in _discover_links(ctx.soup, url):
                if link not in visited:
                    queue.append(link)

        deals, outcome = extract_deals(ctx)
        metrics.record_page(outcome, len(deals))
        results.extend(d.as_post() for d in deals)

    if standalone:
        print(metrics.summary())
    return results


def _discover_links(soup, base_url: str) -> list:
    """Same-domain links whose text/href suggest deals, menus, or specials."""
    out = []
    base_netloc = urlparse(base_url).netloc
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        if not should_follow_link(a.get_text(" ", strip=True), href):
            continue
        abs_url = urljoin(base_url, href).split("?")[0].split("#")[0]
        if urlparse(abs_url).netloc == base_netloc:
            out.append(abs_url)
    return out
