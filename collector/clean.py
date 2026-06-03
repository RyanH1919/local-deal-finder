"""
HTML cleaning utilities for raw Reddit post content.

RSS feeds and Reddit's JSON API return post bodies with HTML markup.
Sending raw HTML to Claude wastes tokens and hurts extraction accuracy.
This module strips it down to clean plain text before any AI processing.
"""

import re
from html import unescape


def strip_html(raw: str) -> str:
    """Remove HTML tags and decode entities from a string.

    Handles Reddit-style HTML: <p>, <a>, <br>, <strong>, <em>,
    HTML entities like &amp; &lt; &gt;, and markdown artifacts
    left behind by Reddit's rendering.

    Args:
        raw: A string potentially containing HTML markup.

    Returns:
        Clean plain text with normalized whitespace.
    """
    if not raw:
        return ""

    text = raw

    # Replace <br> and <br/> with newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Replace </p> and </div> with newlines (block-level boundaries)
    text = re.sub(r"</(?:p|div|li|tr)>", "\n", text, flags=re.IGNORECASE)

    # Strip all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities (&amp; → &, &#39; → ', etc.)
    text = unescape(text)

    # Collapse multiple newlines into max two
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple spaces/tabs into one
    text = re.sub(r"[ \t]+", " ", text)

    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)

    return text.strip()
