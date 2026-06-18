"""Flow 2 — per-cell catalogue crawl.

Crawls ONE grid cell on demand: discover businesses across categories, scrape the
ones due for a refresh, extract structured deals, and persist — with per-cell and
per-business caching, and yield metrics. Does not touch the scheduler. See
docs/flow2_grid_design.md.
"""

import hashlib
from urllib.parse import urlparse

from ai.extractor import extract_website_deal, get_token_counts, reset_token_counts
from database.db import (
    area_recently_crawled, business_due_for_scrape, get_content_hash, init_db,
    mark_business_scraped, record_crawled_area, save_deals, upsert_business,
)
from scraper.metrics import ScrapeMetrics
from scraper.website import scrape_business_website
from search.places import find_nearby, get_place_website
from crawl.grid import BUSINESS_TTL_DAYS, CATEGORIES, CELL_TTL_DAYS, cell_for_point
from crawl.metrics import CrawlMetrics


def crawl_cell(lat: float, lng: float, radius_m: int = None,
               categories: list = None, force: bool = False) -> dict:
    """Crawl the single grid cell containing (lat, lng). Returns a summary dict."""
    cell = cell_for_point(lat, lng)
    cid = cell["cell_id"]
    radius_m = radius_m or cell["radius_m"]
    categories = categories or CATEGORIES

    print(f"\n[crawl] cell {cid} @ ({cell['lat']:.4f}, {cell['lng']:.4f}) r={radius_m}m "
          f"— categories: {', '.join(categories)}")

    init_db()
    if not force and area_recently_crawled(cid, CELL_TTL_DAYS):
        print(f"[crawl] cell {cid} crawled within {CELL_TTL_DAYS}d — skipping (use --force)")
        return {"cell_id": cid, "skipped": True}

    reset_token_counts()
    scrape_metrics = ScrapeMetrics()
    yield_metrics = CrawlMetrics(cid)

    # 1. Discover businesses across categories (dedupe by place_id).
    discovered = {}
    for category in categories:
        try:
            found = find_nearby(cell["lat"], cell["lng"], category, radius_m=radius_m)
        except Exception as e:
            print(f"[crawl]   places error for '{category}': {e}")
            continue
        print(f"[crawl]   '{category}': {len(found)} businesses")
        yield_metrics.record_query(category, len(found))
        for p in found:
            discovered.setdefault(p["place_id"], {**p, "category": category})
    yield_metrics.set_businesses(len(discovered))
    for pid, p in discovered.items():
        upsert_business({
            "place_id": pid, "name": p["name"], "website": None,
            "lat": p["lat"], "lng": p["lng"], "category": p["category"], "geohash": cid,
        })

    # 2. Scrape businesses that are due (per-business cache).
    all_deals = []
    for pid, p in discovered.items():
        if not force and not business_due_for_scrape(pid, BUSINESS_TTL_DAYS):
            yield_metrics.record_cached()
            continue
        website = get_place_website(pid)
        upsert_business({
            "place_id": pid, "name": p["name"], "website": website,
            "lat": p["lat"], "lng": p["lng"], "category": p["category"], "geohash": cid,
        })
        if not website:
            mark_business_scraped(pid)        # nothing to scrape; respect TTL next cycle
            yield_metrics.record_cached()
            continue

        posts = scrape_business_website(website, p["name"], metrics=scrape_metrics)
        domain = urlparse(website).netloc
        for post in posts:
            new_hash = hashlib.md5(post["body"].encode("utf-8")).hexdigest()
            if get_content_hash(post["source_url"]) == new_hash:
                continue   # unchanged since last crawl — skip AI + save
            deal = extract_website_deal(
                post, business_name=p["name"], location=p.get("address", ""),
                lat=p["lat"], lng=p["lng"], domain=domain,
                content_hash=new_hash, use_haiku=True,
            )
            all_deals.append(deal)
            if deal["ai_processed"]:
                yield_metrics.record_deal(p["category"])
        mark_business_scraped(pid)
        yield_metrics.record_scraped()

    # 3. Persist deals + record the crawl for the cell cache.
    save_deals(all_deals)
    record_crawled_area(cid, cell["lat"], cell["lng"], radius_m, ",".join(categories))

    # 4. Summaries.
    in_tok, out_tok = get_token_counts()
    print(scrape_metrics.summary())
    print(yield_metrics.summary())
    print(f"[crawl] cell {cid} done — tokens in={in_tok} out={out_tok}\n")

    return {"cell_id": cid, "skipped": False,
            **yield_metrics.as_dict(),
            "scrape_metrics": scrape_metrics.as_dict()}
