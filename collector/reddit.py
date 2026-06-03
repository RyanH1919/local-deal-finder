"""
Reddit data collector — fetches posts via PRAW (authenticated) or RSS (no auth).

Two collection methods, used in priority order:
1. PRAW (OAuth API) — up to 100 posts per subreddit, clean data, requires API keys
2. RSS feed (reddit.com/r/{sub}/new/.rss) — fallback, ~25 posts, no auth needed

PRAW is preferred because it returns more posts and markdown body text.
RSS is the zero-config fallback that works without any API credentials.

Rate limiting is built in — 2-second delay between subreddit requests to
avoid Reddit's throttling. HTTP requests retry up to 3 times with
exponential backoff on failure.
"""

import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from config import (
    SUBREDDITS, REDDIT_USER_AGENT, REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET, POSTS_PER_SUBREDDIT,
)
from collector.clean import strip_html

REDDIT_BASE = "https://www.reddit.com"
HEADERS = {"User-Agent": REDDIT_USER_AGENT}
RSS_NS = "http://www.w3.org/2005/Atom"

# Rate limiting
REQUEST_DELAY = 2  # seconds between subreddit requests
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # exponential backoff multiplier


def _request_with_retry(url: str, params: dict = None) -> requests.Response:
    """Make an HTTP GET request with retry logic and exponential backoff.

    Retries on 429 (rate limited), 5xx (server errors), and connection errors.
    Raises after MAX_RETRIES failures.
    """
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


# ---------------------------------------------------------------------------
# PRAW collector (primary) — up to 100 posts, requires Reddit API credentials
# ---------------------------------------------------------------------------

_praw_reddit = None  # lazily initialized


def _get_praw():
    """Lazily initialize the PRAW Reddit instance. Returns None if creds missing."""
    global _praw_reddit
    if _praw_reddit is not None:
        return _praw_reddit

    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        return None

    try:
        import praw
        _praw_reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT,
        )
        return _praw_reddit
    except Exception as e:
        print(f"[collector] PRAW init failed: {e}")
        return None


def fetch_posts_praw(subreddit: str, limit: int = None) -> list[dict]:
    """Fetch posts from Reddit via PRAW (authenticated OAuth API).

    Returns up to `limit` posts with clean markdown body text.
    Requires REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET in .env.
    """
    reddit = _get_praw()
    if reddit is None:
        raise RuntimeError("PRAW not available — missing API credentials")

    if limit is None:
        limit = min(POSTS_PER_SUBREDDIT, 100)

    sub = reddit.subreddit(subreddit)
    posts = []
    for submission in sub.new(limit=limit):
        # Skip stickied/pinned mod posts — they're never deals
        if submission.stickied:
            continue

        posted_at = None
        if submission.created_utc:
            posted_at = datetime.fromtimestamp(submission.created_utc, tz=timezone.utc)

        posts.append({
            "title": submission.title or "",
            "body": submission.selftext or "",  # PRAW gives markdown, already clean
            "source_url": f"{REDDIT_BASE}{submission.permalink}",
            "subreddit": subreddit,
            "posted_at": posted_at,
        })
    return posts


# ---------------------------------------------------------------------------
# RSS feed collector (fallback) — ~25 posts per subreddit, no auth needed
# ---------------------------------------------------------------------------

def fetch_posts_rss(subreddit: str) -> list[dict]:
    """Fetch posts from Reddit's public RSS feed (Atom format).

    Endpoint: reddit.com/r/{subreddit}/new/.rss
    Returns ~25 posts. Body content is HTML — stripped to plain text.
    No API credentials required.
    """
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
            "body": strip_html(content),  # Clean HTML → plain text
            "source_url": link,
            "subreddit": subreddit,
            "posted_at": posted_at,
        })
    return posts


# ---------------------------------------------------------------------------
# Main collection function
# ---------------------------------------------------------------------------

def fetch_posts(subreddit: str) -> list[dict]:
    """Fetch posts from a subreddit. Tries PRAW first, falls back to RSS."""
    try:
        posts = fetch_posts_praw(subreddit)
        if posts:
            return posts
    except Exception as e:
        print(f"[collector] {subreddit}: PRAW failed ({e}), falling back to RSS...")

    return fetch_posts_rss(subreddit)


def collect_all(limit_subreddits: int = None) -> list[dict]:
    """Collect posts from all configured subreddits with rate limiting."""
    all_posts = []

    # Log which method we're using
    praw_available = _get_praw() is not None
    method = "PRAW (authenticated)" if praw_available else "RSS (no auth)"
    print(f"[collector] using {method}")

    subreddits = SUBREDDITS[:limit_subreddits] if limit_subreddits else SUBREDDITS

    for i, subreddit in enumerate(subreddits):
        try:
            posts = fetch_posts(subreddit)
            all_posts.extend(posts)
            print(f"[collector] {subreddit}: {len(posts)} posts fetched")
        except Exception as e:
            print(f"[collector] {subreddit}: failed — {e}")

        # Rate limit: wait between requests (skip delay after last subreddit)
        if i < len(subreddits) - 1:
            time.sleep(REQUEST_DELAY)

    print(f"[collector] total: {len(all_posts)} posts from {len(subreddits)} subreddits")
    return all_posts
