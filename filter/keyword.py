import re
from datetime import datetime, timezone
from config import KEYWORDS, MAX_POST_AGE_DAYS

_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in KEYWORDS]


def passes_filter(post: dict) -> bool:
    text = post["title"] + " " + post["body"]
    return any(pattern.search(text) for pattern in _PATTERNS)


def is_recent(post: dict) -> bool:
    posted_at = post.get("posted_at")
    if not posted_at:
        return True  # no date = assume recent (Flow 2 website posts)
    try:
        if isinstance(posted_at, str):
            posted_at = datetime.fromisoformat(posted_at)
        if posted_at.tzinfo is None:
            posted_at = posted_at.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - posted_at).days
        return age_days <= MAX_POST_AGE_DAYS
    except Exception:
        return True  # if we can't parse the date, don't drop it


def filter_posts(posts: list[dict]) -> list[dict]:
    recent = [post for post in posts if is_recent(post)]
    matched = [post for post in recent if passes_filter(post)]
    skipped_old = len(posts) - len(recent)
    if skipped_old:
        print(f"[filter] skipped {skipped_old} posts older than {MAX_POST_AGE_DAYS} days")
    print(f"[filter] {len(matched)} / {len(recent)} posts passed keyword filter")
    return matched
