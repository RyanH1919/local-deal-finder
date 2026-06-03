"""
Business website scraper — visits a business's own website and finds deal/special content.

Strategy:
1. Visit the homepage
2. Look for links that smell like deal pages (/specials, /deals, /offers, /promotions, etc.)
3. Follow those links (same domain only, max MAX_PAGES total)
4. Extract clean text from any page with deal signals
5. Return post-like dicts for the AI pipeline

Uses requests + BeautifulSoup. Works for ~80% of restaurant sites (static or server-rendered).
JS-heavy sites (React/Vue SPAs) will get limited content — Playwright can be added later for those.
"""

import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DEAL_KEYWORDS = {
    "deal", "deals", "special", "specials", "offer", "offers",
    "promo", "promotion", "promotions", "discount", "coupon",
    "happy-hour", "happyhour", "happy+hour", "savings", "sale",
}

MAX_PAGES = 4   # max pages to visit per business site
TIMEOUT = 8     # seconds per request


def _same_domain(base: str, href: str) -> bool:
    return urlparse(base).netloc == urlparse(urljoin(base, href)).netloc


def _has_deal_signal(text: str, href: str = "") -> bool:
    combined = (text + " " + href).lower()
    return any(kw in combined for kw in DEAL_KEYWORDS)


def _clean_text(soup: BeautifulSoup) -> str:
    """Strip navigation/scripts and return readable page text."""
    for tag in soup(["script", "style", "nav", "footer", "header", "meta", "noscript"]):
        tag.decompose()
    return " ".join(soup.stripped_strings)[:3000]


def scrape_business_website(url: str, business_name: str) -> list:
    """
    Crawl a business website for deal content.
    Returns a list of post-like dicts (title, body, source_url, subreddit, posted_at).
    """
    visited = set()
    queue = [url]
    results = []

    while queue and len(visited) < MAX_PAGES:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        try:
            resp = requests.get(current, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            if resp.status_code != 200:
                continue
            # Skip non-HTML responses
            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue
        except Exception as e:
            print(f"[scraper] failed {current}: {e}")
            continue

        soup = BeautifulSoup(resp.text, "lxml")
        text = _clean_text(soup)

        if _has_deal_signal(text):
            page_title = soup.title.string.strip() if soup.title else business_name
            results.append({
                "title": f"{business_name} — {page_title}",
                "body": text,
                "source_url": current,
                "subreddit": "website",
                "posted_at": None,
            })

        # Enqueue deal-looking links on same domain
        if len(visited) < MAX_PAGES:
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                link_text = a.get_text()
                if _has_deal_signal(link_text, href) and _same_domain(url, href):
                    abs_url = urljoin(url, href).split("?")[0]  # drop query strings
                    if abs_url not in visited:
                        queue.append(abs_url)

    return results
