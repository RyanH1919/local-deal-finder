from search.geocoder import geocode
from search.places import find_nearby, get_place_website
from search.deal_finder import find_deals_for_business
from ai.classifier import classify_post
from ai.extractor import extract_post


def run_search(item: str, address: str, radius_m: int = 10000):
    print(f'\nSearching for "{item}" near "{address}"...\n')

    # 1. Geocode the address
    try:
        lat, lng = geocode(address)
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

    results = []
    for place in places[:10]:  # cap at 10 to control API cost
        name = place["name"]
        website = get_place_website(place["place_id"])

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

    _display(item, address, results)


def _price_line(d: dict) -> str:
    """Build a compact price string from extracted deal fields."""
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
    domain = re.sub(r"^https?://(www\.)?" , "", url).split("/")[0]
    return domain


def _urgency_label(urgency: str, expires: str) -> str:
    label = {"limited_time": "[!] limited time", "ongoing": "[ok] ongoing"}.get(urgency, "[?] timing unknown")
    if expires:
        label += f" ({expires})"
    return label


def _display(item: str, address: str, results: list):
    deals_found = [r for r in results if r["deal"]]

    print("\n" + "=" * 62)
    print(f'  {item.upper()} DEALS  ·  {address}')
    print("=" * 62)

    if not deals_found:
        print("  No deals found at nearby businesses right now.\n")
    else:
        for r in deals_found:
            p = r["place"]
            d = r["deal"]
            rating = f"  ★{p['rating']}" if p.get("rating") else ""
            print(f"\n  [DEAL] {p['name']}  —  {p['distance_label']} away{rating}")
            print(f"         {p['address']}")

            price_str = _price_line(d)
            if price_str:
                print(f"")
                print(f"         PRICE  {price_str}")

            print(f"")
            print(f"         {d.get('deal_description', 'Deal available')}")
            print(f"")
            urgency_str = _urgency_label(d.get("urgency", "unknown"), d.get("expires"))
            source_str = _source_label(d.get("source_url", ""))
            category = d.get("category", "other")
            print(f"         [{category}]  {urgency_str}  ·  {source_str}")
            print(f"         " + "-" * 50)


    print("\n" + "=" * 62 + "\n")
