"""
Deal finder — scrapes a business's own website for deal content.
"""

from scraper.website import scrape_business_website


def find_deals_for_business(business_name: str, website_url: str = None) -> list:
    """
    Scrape a business website for deal content.
    Returns a list of post-like dicts ready for the pipeline.
    """
    if not website_url:
        return []
    print(f"[deal_finder] scraping {website_url}")
    return scrape_business_website(website_url, business_name)

