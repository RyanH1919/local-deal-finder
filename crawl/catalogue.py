"""Flow 2 — per-cell catalogue crawl.

Crawls ONE grid cell on demand: discover businesses across categories, scrape the
ones due for a refresh, extract structured deals, and persist — with per-cell and
per-business caching, yield metrics, and a monthly Google-spend cap. Does not touch
the scheduler. See docs/flow2_grid_design.md and docs/cost_model.md.
"""

import hashlib
import math
from urllib.parse import urlparse

from ai.extractor import extract_website_deal, get_token_counts, reset_token_counts
from database.db import (
    area_recently_crawled, business_due_for_scrape, get_content_hash,
    get_deals_in_cell, init_db, mark_business_scraped, record_crawled_area,
    save_deals, update_peer_savings, upsert_business,
)
from scraper.metrics import ScrapeMetrics
from scraper.website import scrape_business_website
from search.places import find_nearby, get_place_website
from crawl.compare import annotate_peer_savings
from crawl.grid import BUSINESS_TTL_DAYS, CATEGORIES, CELL_TTL_DAYS, cell_for_point
from crawl.metrics import CrawlMetrics
from crawl import budget

MAX_EXTRACT_CHARS = 8000   # cap on the combined per-business text sent to the AI


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
    if budget.remaining() <= 0:
        print(f"[budget] monthly cap reached (${budget.spent_this_month():.2f} / "
              f"${budget.MONTHLY_CAP_USD:.0f}) — skipping cell {cid}")
        return {"cell_id": cid, "skipped": "budget"}

    reset_token_counts()
    scrape_metrics = ScrapeMetrics()
    yield_metrics = CrawlMetrics(cid)
    run_cost = 0.0

    # 1. Discover businesses across categories (dedupe by place_id).
    discovered = {}
    for category in categories:
        if not budget.can_afford("nearby"):
            print("[budget] cap reached — stopping category discovery")
            break
        try:
            found = find_nearby(cell["lat"], cell["lng"], category, radius_m=radius_m)
        except Exception as e:
            print(f"[crawl]   places error for '{category}': {e}")
            continue
        run_cost += budget.record("nearby", max(1, math.ceil(len(found) / 20)))
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

    # 2. Scrape businesses that are due (per-business cache + budget cap).
    all_deals = []
    for pid, p in discovered.items():
        if not force and not business_due_for_scrape(pid, BUSINESS_TTL_DAYS):
            yield_metrics.record_cached()
            continue
        if not budget.can_afford("details"):
            print("[budget] cap reached — stopping business scrape")
            break
        website = get_place_website(pid)
        run_cost += budget.record("details")
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
        if posts:
            # Combine the business's deal pages into ONE extraction: scrape more pages
            # per site without multiplying Haiku calls, give the AI the full pricing
            # picture, and get one deal per business (no per-page duplication).
            combined = "\n\n----\n\n".join(post["body"] for post in posts)[:MAX_EXTRACT_CHARS]
            new_hash = hashlib.md5(combined.encode("utf-8")).hexdigest()
            if get_content_hash(website) != new_hash:   # unchanged -> skip AI + save
                deal = extract_website_deal(
                    {"body": combined, "source_url": website}, business_name=p["name"],
                    location=p.get("address", ""), lat=p["lat"], lng=p["lng"],
                    domain=domain, content_hash=new_hash, use_haiku=True,
                )
                deal["geohash"] = cid   # stamp the cell for "deals in my cell" retrieval
                all_deals.append(deal)
                if deal["ai_processed"]:
                    yield_metrics.record_deal(p["category"])
        mark_business_scraped(pid)
        yield_metrics.record_scraped()

    # 3. Persist deals + record the crawl for the cell cache.
    save_deals(all_deals)
    record_crawled_area(cid, cell["lat"], cell["lng"], radius_m, ",".join(categories))

    # 3b. Peer pricing as a post-crawl job (not per API request): compare every deal
    # now in the cell — including businesses cached from earlier runs, so the medians
    # are complete — and persist the vs_peers annotations for the frontend to read.
    cell_deals = get_deals_in_cell(cid)
    annotate_peer_savings(cell_deals)
    update_peer_savings(cell_deals)
    print(f"[crawl] peer savings annotated for {len(cell_deals)} deals in cell {cid}")

    # 4. Summaries.
    in_tok, out_tok = get_token_counts()
    print(scrape_metrics.summary())
    print(yield_metrics.summary())
    print(f"[crawl] cell {cid} done — tokens in={in_tok} out={out_tok}")
    print(f"[budget] maps ~${run_cost:.2f} this run | month ${budget.spent_this_month():.2f} / "
          f"${budget.MONTHLY_CAP_USD:.0f} (${budget.remaining():.2f} left)\n")

    return {"cell_id": cid, "skipped": False, "maps_cost_run": round(run_cost, 2),
            **yield_metrics.as_dict(),
            "scrape_metrics": scrape_metrics.as_dict()}
