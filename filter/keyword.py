import re
from config import KEYWORDS

_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in KEYWORDS]


def passes_filter(post: dict) -> bool:
    text = post["title"] + " " + post["body"]
    return any(pattern.search(text) for pattern in _PATTERNS)


def filter_posts(posts: list[dict]) -> list[dict]:
    matched = [post for post in posts if passes_filter(post)]
    print(f"[filter] {len(matched)} / {len(posts)} posts passed keyword filter")
    return matched
