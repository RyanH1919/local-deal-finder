"""
Flow 2 runner — dev/testing tool only. Not part of the production scheduled pipeline.

Usage: python main.py --search --item "pizza" --address "123 Main St, Mississauga"
"""

import hashlib
from urllib.parse import urlparse
from search.geocoder import geocode
from search.places import find_nearby, get_place_website
from search.deal_finder import find_deals_for_business
from ai.extractor import extract_website_deal, reset_token_counts, get_token_counts
from database.db import init_db, save_deals, get_content_hash


def run_search(item: str, address: str, radius_m: int = 10000):
    print(f'\n[search] searching for "{item}" near "{address}"...\n')

    try:
        lat, lng = geocode(address)
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
    reset_token_counts()
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
            # for this URL, the deals haven't changed — skip it (no AI, no save).
            new_hash = hashlib.md5(post["body"].encode("utf-8")).hexdigest()
            if get_content_hash(post["source_url"]) == new_hash:
                print(f"[search] '{name}' — unchanged since last crawl, skipping")
                continue

            # New/changed page — send the scraped text to Haiku for a clean deal.
            deal = extract_website_deal(
                post,
                business_name=name,
                location=place["address"],
                lat=place["lat"],
                lng=place["lng"],
                domain=domain,
                content_hash=new_hash,
                use_haiku=True,
            )
            tag = "deal" if deal["ai_processed"] else "no deal"
            print(f"[search] '{name}' — {tag}: {deal['deal_description'][:60]}")
            all_deals.append(deal)

    save_deals(all_deals)
    in_tok, out_tok = get_token_counts()
    deal_count = sum(1 for d in all_deals if d["ai_processed"])
    non_deal_count = len(all_deals) - deal_count
    print(f"[search] tokens used — input={in_tok} output={out_tok}")
    print(f"[search] done — {len(all_deals)} rows saved/updated "
          f"({deal_count} deals, {non_deal_count} non-deals) from Flow 2\n")

    # Pretty, human-readable summary of the deals saved this run.
    _display(item, address, all_deals)


def _price_line(d: dict) -> str:
    """Build a compact price string from extracted deal fields.

    Website deals don't carry price fields yet, so this returns "" and the
    PRICE line is hidden. It lights up automatically once price extraction is
    added to the website flow (the fields already exist on the Reddit path).
    """
    parts = []
    if d.get("price_deal"):
        parts.append(d["price_deal"])
    if d.get("price_original"):
        parts.append(f"was {d['price_original']}")
    if d.get("discount_label"):
        parts.append(d["discount_label"])
    if d.get("min_spend"):
        parts.append(f"min. {d['min_spend']}")
    return "  ·  ".join(parts)


def _source_label(url: str) -> str:
    if not url:
        return "unknown source"
    if "reddit.com" in url:
        # extract subreddit if present: /r/TorontoDeals/...
        import re
        m = re.search(r"/r/([^/]+)", url)
        return f"reddit.com/r/{m.group(1)}" if m else "reddit.com"
    # strip scheme and www, show just the domain
    import re
    domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    return domain


def _urgency_label(urgency: str, expires: str) -> str:
    label = {"limited_time": "[!] limited time", "ongoing": "[ok] ongoing"}.get(urgency, "[?] timing unknown")
    if expires:
        label += f" ({expires})"
    return label


def _display(item: str, address: str, deals: list):
    deals_found = [d for d in deals if d.get("ai_processed")]

    print("\n" + "=" * 62)
    print(f'  {item.upper()} DEALS  ·  {address}')
    print("=" * 62)

    if not deals_found:
        print("  No deals found at nearby businesses right now.\n")
    else:
        for d in deals_found:
            print(f"\n  [DEAL] {d.get('business_name', 'Unknown')}")
            if d.get("location"):
                print(f"         {d['location']}")

            price_str = _price_line(d)
            if price_str:
                print("")
                print(f"         PRICE  {price_str}")

            print("")
            print(f"         {d.get('deal_description', 'Deal available')}")
            print("")
            urgency_str = _urgency_label(d.get("urgency", "unknown"), d.get("expires"))
            source_str = _source_label(d.get("source_url", ""))
            category = d.get("category", "other")
            print(f"         [{category}]  {urgency_str}  ·  {source_str}")
            print(f"         " + "-" * 50)

    print("\n" + "=" * 62 + "\n")
