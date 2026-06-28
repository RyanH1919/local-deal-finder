import math
import time
import requests
from config import GOOGLE_API_KEY

NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

MAX_RESULTS = 60   # Google returns at most 3 pages of 20


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Straight-line distance in metres between two lat/lng points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def format_distance(metres: float) -> str:
    if metres < 1000:
        return f"{int(metres)}m"
    return f"{metres / 1000:.1f}km"


_FOOD_TYPES = {
    "burger", "burgers", "pizza", "sandwich", "sandwiches", "taco", "tacos",
    "chicken", "wings", "fries", "hot dog", "hot dogs", "sub", "subs",
    "wrap", "wraps", "poutine", "shawarma", "kebab", "noodle", "noodles",
    "ramen", "sushi", "dim sum", "dumpling", "dumplings", "curry", "rice",
    "breakfast", "brunch", "lunch", "dinner", "steak", "fish", "seafood",
    "salad", "soup", "bbq", "barbecue", "donuts", "donut", "bagel", "bagels",
}


def _is_food_item(item: str) -> bool:
    """True if any word in the search term is a known food keyword."""
    words = item.lower().split()
    return any(word in _FOOD_TYPES for word in words)


def _to_place(p: dict, origin_lat: float, origin_lng: float) -> dict:
    loc = p["geometry"]["location"]
    dist = _haversine_m(origin_lat, origin_lng, loc["lat"], loc["lng"])
    return {
        "name": p["name"],
        "address": p.get("vicinity", ""),
        "lat": loc["lat"],
        "lng": loc["lng"],
        "place_id": p["place_id"],
        "rating": p.get("rating"),
        "distance_m": dist,
        "distance_label": format_distance(dist),
    }


def _fetch_places(lat: float, lng: float, keyword: str, radius_m: int,
                  place_type: str = None, max_results: int = MAX_RESULTS) -> list:
    """Paginated Nearby Search. Returns raw Google place dicts (up to max_results).

    Google needs a short delay before a `next_page_token` becomes valid.
    """
    params = {"location": f"{lat},{lng}", "radius": radius_m, "keyword": keyword, "key": GOOGLE_API_KEY}
    if place_type:
        params["type"] = place_type
    results = []

    while True:
        response = requests.get(NEARBY_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        status = data.get("status")
        if status not in ("OK", "ZERO_RESULTS"):
            raise ValueError(f"Places API error: {status} — {data.get('error_message', '')}")

        results.extend(data.get("results", []))

        token = data.get("next_page_token")
        if not token or len(results) >= max_results:
            break
        time.sleep(2)  # token isn't valid immediately after the previous page
        params = {"pagetoken": token, "key": GOOGLE_API_KEY}

    return results


def find_nearby(lat: float, lng: float, item: str, radius_m: int = 3000,
                max_results: int = MAX_RESULTS) -> list:
    """Businesses near lat/lng matching `item`, sorted by distance ascending.

    Pages through the Nearby Search results (up to `max_results`, Google's hard cap
    is 60). For food items a second search with type 'meal_takeaway' is merged in
    so chains like McDonald's, Burger King, etc. are included alongside sit-down
    restaurants.
    """
    raw = _fetch_places(lat, lng, item, radius_m, max_results=max_results)

    if _is_food_item(item):
        try:
            raw += _fetch_places(lat, lng, item, radius_m,
                                 place_type="meal_takeaway", max_results=max_results)
        except ValueError:
            pass  # don't fail the main search if the extra call errors

    # Deduplicate by place_id, keeping first occurrence.
    seen = set()
    places = []
    for p in raw:
        pid = p["place_id"]
        if pid in seen:
            continue
        seen.add(pid)
        places.append(_to_place(p, lat, lng))

    places.sort(key=lambda x: x["distance_m"])
    return places[:max_results]


def get_place_website(place_id: str) -> str:
    """Fetch the website URL for a place via the Places Details API. None if not listed."""
    params = {"place_id": place_id, "fields": "website", "key": GOOGLE_API_KEY}
    try:
        resp = requests.get(DETAILS_URL, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("website")
    except Exception:
        return None
