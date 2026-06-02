import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from config import SUBREDDITS, REDDIT_USER_AGENT

REDDIT_BASE = "https://www.reddit.com"
HEADERS = {"User-Agent": REDDIT_USER_AGENT}
RSS_NS = "http://www.w3.org/2005/Atom"


def fetch_posts(subreddit: str) -> list[dict]:
    url = f"{REDDIT_BASE}/r/{subreddit}/new/.rss"
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()

    root = ET.fromstring(response.text)
    posts = []
    for entry in root.findall(f"{{{RSS_NS}}}entry"):
        title = entry.findtext(f"{{{RSS_NS}}}title", "")
        link = entry.find(f"{{{RSS_NS}}}link").get("href", "")
        content = entry.findtext(f"{{{RSS_NS}}}content", "")
        published = entry.findtext(f"{{{RSS_NS}}}published", "")

        posted_at = None
        if published:
            posted_at = datetime.fromisoformat(published.replace("Z", "+00:00"))

        posts.append({
            "title": title,
            "body": content,
            "source_url": link,
            "subreddit": subreddit,
            "posted_at": posted_at,
        })
    return posts


def collect_all() -> list[dict]:
    all_posts = []
    for subreddit in SUBREDDITS:
        try:
            posts = fetch_posts(subreddit)
            all_posts.extend(posts)
            print(f"[collector] {subreddit}: {len(posts)} posts fetched")
        except Exception as e:
            print(f"[collector] {subreddit}: failed — {e}")
    return all_posts
