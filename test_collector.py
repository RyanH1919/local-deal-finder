"""Quick test to verify the collector improvements work."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from collector.clean import strip_html
from collector.reddit import fetch_posts_rss, fetch_posts, collect_all


def test_html_cleaner():
    """Test that HTML stripping produces clean text."""
    print("=" * 60)
    print("TEST: HTML Cleaner")
    print("=" * 60)

    cases = [
        (
            '<p>50% off all pizzas at <a href="http://example.com">Pizza Nova</a> today only!</p>',
            '50% off all pizzas at Pizza Nova today only!'
        ),
        (
            '&amp; get a free drink with any combo &gt; $15',
            '& get a free drink with any combo > $15'
        ),
        (
            '<p>First line</p><p>Second line</p>',
            'First line\nSecond line'
        ),
        (
            'No HTML here, just plain text',
            'No HTML here, just plain text'
        ),
        (
            '',
            ''
        ),
        (
            'Line one<br>Line two<br/>Line three',
            'Line one\nLine two\nLine three'
        ),
    ]

    passed = 0
    for raw, expected in cases:
        result = strip_html(raw)
        ok = result == expected
        passed += ok
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] strip_html({raw[:50]}...)")
        if not ok:
            print(f"    Expected: {repr(expected)}")
            print(f"    Got:      {repr(result)}")

    print(f"\n  {passed}/{len(cases)} tests passed\n")
    return passed == len(cases)


def test_rss_collector():
    """Test fetching posts from one subreddit via RSS feed."""
    print("=" * 60)
    print("TEST: RSS Collector (r/toronto)")
    print("=" * 60)

    try:
        posts = fetch_posts_rss("toronto")
        print(f"  Fetched {len(posts)} posts\n")
        for i, post in enumerate(posts[:2]):
            print(f"  Post {i + 1}:")
            print(f"    Title:   {post['title'][:70]}")
            body_preview = post['body'][:100] if post['body'] else "(empty)"
            print(f"    Body:    {body_preview}")
            print(f"    URL:     {post['source_url']}")
            # Check that body is NOT HTML
            if post['body'] and '<p>' in post['body']:
                print(f"    HTML stripped: NO (still has <p> tags!)")
            else:
                print(f"    HTML stripped: YES")
            print()
        return len(posts) > 0
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False


def test_fallback_logic():
    """Test that fetch_posts falls back to RSS when PRAW is unavailable."""
    print("=" * 60)
    print("TEST: Fallback Logic (PRAW -> RSS)")
    print("=" * 60)

    try:
        posts = fetch_posts("torontofood")
        print(f"  Fetched {len(posts)} posts via fallback")
        print(f"  Method used: {'PRAW' if len(posts) > 25 else 'RSS (expected without API keys)'}")
        print()
        return len(posts) > 0
    except Exception as e:
        print(f"  FAILED: {e}\n")
        return False


if __name__ == "__main__":
    results = []
    results.append(("HTML Cleaner", test_html_cleaner()))
    results.append(("RSS Collector", test_rss_collector()))
    results.append(("Fallback Logic", test_fallback_logic()))

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
    print()
