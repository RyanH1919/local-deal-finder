"""Flow 2 — per-cell catalogue crawl.

Crawls ONE grid cell on demand: discover businesses across categories, scrape the
ones due for a refresh, extract deals, and persist — with per-cell and per-business
caching. Does not touch the scheduler. See docs/flow2_grid_design.md.
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
    metrics = ScrapeMetrics()

    # 1. Discover businesses across categories (dedupe by place_id).
    discovered = {}
    for category in categories:
        try:
            found = find_nearby(cell["lat"], cell["lng"], category, radius_m=radius_m)
        except Exception as e:
            print(f"[crawl]   places error for '{category}': {e}")
            continue
        print(f"[crawl]   '{category}': {len(found)} businesses")
        for p in found:
            discovered.setdefault(p["place_id"], {**p, "category": category})
    for pid, p in discovered.items():
        upsert_business({
            "place_id": pid, "name": p["name"], "website": None,
            "lat": p["lat"], "lng": p["lng"], "category": p["category"], "geohash": cid,
        })

    # 2. Scrape businesses that are due (per-business cache).
    all_deals, scraped, cached = [], 0, 0
    for pid, p in discovered.items():
        if not force and not business_due_for_scrape(pid, BUSINESS_TTL_DAYS):
            cached += 1
            continue
        website = get_place_website(pid)
        upsert_business({
            "place_id": pid, "name": p["name"], "website": website,
            "lat": p["lat"], "lng": p["lng"], "category": p["category"], "geohash": cid,
        })
        if not website:
            mark_business_scraped(pid)   # nothing to scrape; respect TTL next cycle
            continue

        posts = scrape_business_website(website, p["name"], metrics=metrics)
        domain = urlparse(website).netloc
        for post in posts:
            new_hash = hashlib.md5(post["body"].encode("utf-8")).hexdigest()
            if get_content_hash(post["source_url"]) == new_hash:
                continue   # unchanged since last crawl — skip AI + save
            all_deals.append(extract_website_deal(
                post, business_name=p["name"], location=p.get("address", ""),
                lat=p["lat"], lng=p["lng"], domain=domain,
                content_hash=new_hash, use_haiku=True,
            ))
        mark_business_scraped(pid)
        scraped += 1

    # 3. Persist deals + record the crawl for the cell cache.
    save_deals(all_deals)
    record_crawled_area(cid, cell["lat"], cell["lng"], radius_m, ",".join(categories))

    # 4. Summary.
    in_tok, out_tok = get_token_counts()
    deal_count = sum(1 for d in all_deals if d["ai_processed"])
    print(metrics.summary())
    print(f"[crawl] cell {cid} done — {len(discovered)} businesses "
          f"({scraped} scraped, {cached} cached), {deal_count} deals saved, "
          f"tokens in={in_tok} out={out_tok}\n")
    return {
        "cell_id": cid, "skipped": False, "businesses": len(discovered),
        "scraped": scraped, "cached": cached, "deals": deal_count,
        "metrics": metrics.as_dict(),
    }
