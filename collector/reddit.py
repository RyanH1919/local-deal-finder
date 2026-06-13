"""
Reddit data collector — fetches posts via public RSS feeds, no auth required.

Endpoint: reddit.com/r/{subreddit}/new/.rss
Returns up to 25 posts per subreddit (hard Reddit cap on RSS feeds).
Rate limit: Reddit enforces 1 request/minute globally across all feeds — we wait
61 seconds between subreddit requests (1s buffer over the 60s limit). HTTP
requests retry up to 3 times with exponential backoff.
"""

import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from config import SUBREDDITS, REDDIT_USER_AGENT, SUBREDDITS_PER_RUN
from collector.clean import strip_html

REDDIT_BASE = "https://www.reddit.com"
HEADERS = {"User-Agent": REDDIT_USER_AGENT}
RSS_NS = "http://www.w3.org/2005/Atom"

REQUEST_DELAY = 61  # Reddit enforces 1 req/min globally; 61s gives a 1s buffer
MAX_RETRIES = 3
RETRY_BACKOFF = 2


def _request_with_retry(url: str, params: dict = None) -> requests.Response:
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, params=params, timeout=15)

            if response.status_code == 429:
                wait = RETRY_BACKOFF ** (attempt + 1)
                print(f"[collector] rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                wait = RETRY_BACKOFF ** (attempt + 1)
                print(f"[collector] server error {response.status_code}, retrying in {wait}s...")
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response

        except requests.exceptions.ConnectionError:
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF ** (attempt + 1)
                print(f"[collector] connection error, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    raise requests.exceptions.RetryError(f"Failed after {MAX_RETRIES} attempts: {url}")


def fetch_posts(subreddit: str) -> list[dict]:
    """Fetch posts from a subreddit via RSS. Returns up to ~25 posts."""
    url = f"{REDDIT_BASE}/r/{subreddit}/new/.rss"
    response = _request_with_retry(url)

    root = ET.fromstring(response.text)
    posts = []
    for entry in root.findall(f"{{{RSS_NS}}}entry"):
        title = entry.findtext(f"{{{RSS_NS}}}title", "")
        link_elem = entry.find(f"{{{RSS_NS}}}link")
        link = link_elem.get("href", "") if link_elem is not None else ""
        content = entry.findtext(f"{{{RSS_NS}}}content", "")
        published = entry.findtext(f"{{{RSS_NS}}}published", "")

        posted_at = None
        if published:
            posted_at = datetime.fromisoformat(published.replace("Z", "+00:00"))

        posts.append({
            "title": title,
            "body": strip_html(content),
            "source_url": link,
            "subreddit": subreddit,
            "posted_at": posted_at,
        })
    return posts


def collect_all(limit_subreddits: int = SUBREDDITS_PER_RUN) -> list[dict]:
    """Collect posts from configured subreddits with rate limiting."""
    print(f"[collector] using RSS (no auth)")
    all_posts = []
    subreddits = SUBREDDITS[:limit_subreddits]

    for i, subreddit in enumerate(subreddits):
        try:
            posts = fetch_posts(subreddit)
            all_posts.extend(posts)
            print(f"[collector] {subreddit}: {len(posts)} posts fetched")
        except Exception as e:
            print(f"[collector] {subreddit}: failed — {e}")

        if i < len(subreddits) - 1:
            time.sleep(REQUEST_DELAY)

    print(f"[collector] total: {len(all_posts)} posts from {len(subreddits)} subreddits")
    return all_posts
