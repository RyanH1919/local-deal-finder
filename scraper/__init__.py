"""Website scraper package.

Public entry point is `scrape_business_website` (see `scraper/website.py`).
Internals are split into fetch → classify → extractors, with `metrics` for coverage.
"""

from .website import scrape_business_website  # noqa: F401

__all__ = ["scrape_business_website"]
