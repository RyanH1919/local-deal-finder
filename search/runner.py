from search.geocoder import geocode
from search.places import find_nearby, get_place_website
from search.deal_finder import find_deals_for_business
from ai.classifier import classify_post
from ai.extractor import extract_post


def run_search(item: str, address: str, radius_m: int = 3000):
    print(f'\nSearching for "{item}" near "{address}"...\n')

    # 1. Geocode the address
    try:
        lat, lng = geocode(address)
        print(f"[search] resolved to {lat:.5f}, {lng:.5f}")
    except ValueError as e:
        print(f"[search] ERROR: {e}")
        return

    # 2. Find nearby businesses
    try:
        places = find_nearby(lat, lng, item, radius_m=radius_m)
    except ValueError as e:
        print(f"[search] Places API ERROR: {e}")
        return

    if not places:
        print(f"[search] No '{item}' businesses found within {radius_m // 1000}km.")
        return

    print(f"[search] {len(places)} places found — checking each for deals...\n")

    results = []
    for place in places[:10]:  # cap at 10 to control API cost
        name = place["name"]

        # Fetch the business's own website from Places Details API
        website = get_place_website(place["place_id"])
        if website:
            print(f"[search] checking '{name}' — {website}")
        else:
            print(f"[search] checking '{name}' — no website listed")

        # Search all sources for deals
        posts = find_deals_for_business(name, website_url=website)
        deal = None

        for post in posts:
            label = classify_post(post)
            if label in ("yes_local", "yes_online", "uncertain_local", "uncertain_online"):
                extracted = extract_post(post, use_haiku=True)
                if extracted and extracted.get("is_deal"):
                    deal = {**extracted, "source_url": post["source_url"], "subreddit": post["subreddit"]}
                    break

        results.append({"place": place, "deal": deal})

    # 4. Display results
    _display(item, address, results)


def _display(item: str, address: str, results: list):
    deals_found = [r for r in results if r["deal"]]
    no_deals = [r for r in results if not r["deal"]]

    print("\n" + "=" * 60)
    print(f'  {item.upper()} deals near {address}')
    print("=" * 60)

    if not deals_found:
        print("  No deals found at nearby businesses right now.\n")
    else:
        for r in deals_found:
            p = r["place"]
            d = r["deal"]
            print(f"\n  [DEAL] {p['name']}  —  {p['distance_label']} away")
            print(f"         {p['address']}")
            print(f"         {d.get('deal_description', 'Deal available')}")
            urgency = d.get("urgency", "unknown")
            category = d.get("category", "")
            print(f"         [{category}] [{urgency}]  |  reddit.com source")

    if no_deals:
        print(f"\n  Nearby with no deal found:")
        for r in no_deals:
            p = r["place"]
            rating = f"  ★{p['rating']}" if p.get("rating") else ""
            print(f"    • {p['name']}  —  {p['distance_label']}{rating}")

    print("\n" + "=" * 60 + "\n")
