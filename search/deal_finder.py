"""
Deal finder — searches multiple sources for deals about a specific business.

Sources (in priority order):
1. Business website  — scraped directly, highest signal quality
2. Reddit RSS search — organic community mentions, no auth, no 403s
"""

import time
import requests
import xml.etree.ElementTree as ET
from collector.clean import strip_html
from scraper.website import scrape_business_website
from config import REDDIT_USER_AGENT

HEADERS = {"User-Agent": REDDIT_USER_AGENT}
REDDIT_RSS_URL = "https://www.reddit.com/search.rss"
DEAL_TERMS = "deal OR promo OR promotion OR coupon OR free OR discount OR opening OR special OR offer"


def _search_reddit_rss(business_name: str) -> list:
    """Search Reddit via RSS (no auth, doesn't 403 like the JSON API)."""
    params = {"q": f'"{business_name}" ({DEAL_TERMS})', "limit": 5, "sort": "new"}
    try:
        resp = requests.get(REDDIT_RSS_URL, headers=HEADERS, params=params, timeout=10)
        if resp.status_code == 429:
            print(f"[deal_finder] Reddit rate limited for '{business_name}', skipping")
            return []
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        posts = []
        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", "", ns)
            content = entry.findtext("atom:content", "", ns) or ""
            link_el = entry.find("atom:link", ns)
            url = link_el.attrib.get("href", "") if link_el is not None else ""
            author_el = entry.find("atom:author/atom:name", ns)
            subreddit = author_el.text.split("/")[-1] if author_el is not None else "reddit"
            posts.append({
                "title": title,
                "body": strip_html(content)[:500],
                "source_url": url,
                "subreddit": subreddit,
                "posted_at": None,
            })
        return posts
    except Exception as e:
        print(f"[deal_finder] Reddit RSS failed for '{business_name}': {e}")
        return []
    finally:
        time.sleep(1)  # respect Reddit rate limit


def find_deals_for_business(business_name: str, website_url: str = None) -> list:
    """
    Collect deal candidates for a business from all sources.
    Returns a deduplicated list of post-like dicts for the AI pipeline.
    """
    posts = []
    seen_urls = set()

    def _add(new_posts):
        for p in new_posts:
            if p["source_url"] and p["source_url"] not in seen_urls:
                seen_urls.add(p["source_url"])
                posts.append(p)

    # Source 1: business website (scrape directly)
    if website_url:
        print(f"[deal_finder] scraping {website_url}")
        _add(scrape_business_website(website_url, business_name))

    # Source 2: Reddit RSS
    _add(_search_reddit_rss(business_name))

    return posts

