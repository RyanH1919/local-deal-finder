"""
Flow 2 runner — dev/testing tool only. Not part of the production scheduled pipeline.

Usage: python main.py --search --item "pizza" --address "123 Main St, Mississauga"
"""

import hashlib
from urllib.parse import urlparse
from search.geocoder import geocode
from search.places import find_nearby, get_place_website
from search.deal_finder import find_deals_for_business
from database.db import init_db, save_deals, get_content_hash


def run_search(item: str, address: str, radius_m: int = 3000):
    print(f'\n[search] searching for "{item}" near "{address}"...\n')

    try:
        lat, lng = geocode(address)
        print(f"[search] resolved to {lat:.5f}, {lng:.5f}")
    except ValueError as e:
        print(f"[search] ERROR: {e}")
        return

    try:
        places = find_nearby(lat, lng, item, radius_m=radius_m)
    except ValueError as e:
        print(f"[search] Places API ERROR: {e}")
        return

    if not places:
        print(f"[search] No '{item}' businesses found within {radius_m // 1000}km.")
        return

    print(f"[search] {len(places)} places found — scraping each for deals...\n")

    init_db()
    all_deals = []

    for place in places[:10]:
        name = place["name"]
        website = get_place_website(place["place_id"])

        if not website:
            print(f"[search] '{name}' — no website listed, skipping")
            continue

        print(f"[search] '{name}' — {website}")
        posts = find_deals_for_business(name, website_url=website)

        if not posts:
            print(f"[search] '{name}' — no deal pages found")
            continue

        domain = urlparse(website).netloc
        for post in posts:
            # Fingerprint the scraped text. If it matches what we already stored
            # for this URL, the deals haven't changed — skip it.
            new_hash = hashlib.md5(post["body"].encode("utf-8")).hexdigest()
            if get_content_hash(post["source_url"]) == new_hash:
                print(f"[search] '{name}' — unchanged since last crawl, skipping")
                continue

            all_deals.append({
                "business_name":    name,
                "deal_description": post["body"][:300],
                "category":         item,
                "scope":            "local",
                "source_type":      "website",
                "source_name":      domain,
                "location":         place["address"],
                "lat":              place["lat"],
                "lng":              place["lng"],
                "source_url":       post["source_url"],
                "subreddit":        None,
                "posted_at":        None,
                "urgency":          "unknown",
                "content_hash":     new_hash,
            })

    save_deals(all_deals)
    print(f"[search] done — {len(all_deals)} deals saved/updated from Flow 2\n")
