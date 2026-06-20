"""Geographic grid for the Flow 2 catalogue crawl.

Divides the GTA into geohash cells; each cell becomes one Places query area.
See docs/flow2_grid_design.md.
"""

import math

# --- Grid configuration (tune here) ---
GEOHASH_PRECISION = 6                          # ~1.2km x 0.6km cells
GTA_BBOX = (43.40, -80.00, 44.00, -79.00)      # (min_lat, min_lng, max_lat, max_lng)

# Category keywords fed to Google Places — one Nearby query each, per cell.
CATEGORIES = [
    "restaurant",
    "cafe",
    "grocery store",
    "electronics store",
    "clothing store",
]

# Cache time-to-live, in days (Decision D in flow2_discussion.md).
CELL_TTL_DAYS = 7
BUSINESS_TTL_DAYS = 7

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def geohash_encode(lat: float, lng: float, precision: int = GEOHASH_PRECISION) -> str:
    """Standard geohash encoding of a point to `precision` base-32 chars."""
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    out, bit, ch, even = [], 0, 0, True
    while len(out) < precision:
        if even:  # even bit -> longitude
            mid = (lng_lo + lng_hi) / 2
            if lng > mid:
                ch = (ch << 1) | 1
                lng_lo = mid
            else:
                ch = ch << 1
                lng_hi = mid
        else:     # odd bit -> latitude
            mid = (lat_lo + lat_hi) / 2
            if lat > mid:
                ch = (ch << 1) | 1
                lat_lo = mid
            else:
                ch = ch << 1
                lat_hi = mid
        even = not even
        bit += 1
        if bit == 5:
            out.append(_BASE32[ch])
            bit, ch = 0, 0
    return "".join(out)


def geohash_bounds(gh: str):
    """Return (min_lat, min_lng, max_lat, max_lng) of a geohash cell."""
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    even = True
    for c in gh:
        cd = _BASE32.index(c)
        for mask in (16, 8, 4, 2, 1):
            if even:
                mid = (lng_lo + lng_hi) / 2
                if cd & mask:
                    lng_lo = mid
                else:
                    lng_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if cd & mask:
                    lat_lo = mid
                else:
                    lat_hi = mid
            even = not even
    return lat_lo, lng_lo, lat_hi, lng_hi


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def cell_id(lat: float, lng: float, precision: int = GEOHASH_PRECISION) -> str:
    """The geohash cell id a point falls in."""
    return geohash_encode(lat, lng, precision)


def cell_for_point(lat: float, lng: float, precision: int = GEOHASH_PRECISION) -> dict:
    """Resolve a point to its cell: id, canonical center, and a covering radius (m)
    for a Google Places Nearby search (center→corner distance, rounded up)."""
    gh = geohash_encode(lat, lng, precision)
    min_lat, min_lng, max_lat, max_lng = geohash_bounds(gh)
    c_lat = (min_lat + max_lat) / 2
    c_lng = (min_lng + max_lng) / 2
    radius = _haversine_m(c_lat, c_lng, max_lat, max_lng)  # center to NE corner
    return {
        "cell_id": gh,
        "lat": c_lat,
        "lng": c_lng,
        "radius_m": int(math.ceil(radius)),
    }


def iter_cells(bbox=GTA_BBOX, precision: int = GEOHASH_PRECISION) -> list:
    """All geohash cells covering a bounding box (Phase 2 sweep helper)."""
    min_lat, min_lng, max_lat, max_lng = bbox
    # cell size in degrees, from the cell at the bbox center
    s_lat, s_lng, n_lat, n_lng = geohash_bounds(
        geohash_encode((min_lat + max_lat) / 2, (min_lng + max_lng) / 2, precision)
    )
    d_lat = max(n_lat - s_lat, 1e-6)
    d_lng = max(n_lng - s_lng, 1e-6)

    seen, cells = set(), []
    lat = min_lat
    while lat <= max_lat:
        lng = min_lng
        while lng <= max_lng:
            gh = geohash_encode(lat, lng, precision)
            if gh not in seen:
                seen.add(gh)
                cells.append(cell_for_point(lat, lng, precision))
            lng += d_lng
        lat += d_lat
    return cells


# Curated high-value GTA commercial areas — the crawl covers THESE, not the whole
# map. This is what keeps a full sweep ~$45 instead of ~$2,500 (see docs/cost_model.md).
KEY_AREAS = [
    ("Toronto - Yonge & Dundas",        43.6561, -79.3802),
    ("Toronto - Bloor & Yonge",         43.6709, -79.3863),
    ("Toronto - Yonge & Eglinton",      43.7064, -79.3986),
    ("Toronto - Yonge & Sheppard",      43.7615, -79.4111),
    ("Scarborough Town Centre",         43.7765, -79.2570),
    ("Etobicoke - Sherway Gardens",     43.6116, -79.5570),
    ("Mississauga - Square One",        43.5930, -79.6420),
    ("Mississauga - Cooksville",        43.5780, -79.6230),
    ("Brampton - Bramalea City Centre", 43.7150, -79.7110),
    ("Markham - Markville",             43.8600, -79.3200),
    ("Vaughan - Vaughan Mills",         43.8250, -79.5380),
    ("Richmond Hill - Yonge",           43.8800, -79.4380),
    ("Oakville - Downtown",             43.4450, -79.6680),
    ("Pickering - Town Centre",         43.8350, -79.0890),
]


def iter_key_area_cells(radius_km: float = 1.5, precision: int = GEOHASH_PRECISION) -> list:
    """Cells covering the curated KEY_AREAS only — the under-budget coverage set.

    Far fewer cells than the full grid (~180 vs ~10,000), which is what keeps Google
    spend under the monthly cap. The scheduled sweep (Phase 2) iterates these.
    """
    seen, cells = set(), []
    for _name, lat, lng in KEY_AREAS:
        d_lat = radius_km / 111.0
        d_lng = radius_km / (111.0 * math.cos(math.radians(lat)))
        bbox = (lat - d_lat, lng - d_lng, lat + d_lat, lng + d_lng)
        for c in iter_cells(bbox, precision):
            if c["cell_id"] not in seen:
                seen.add(c["cell_id"])
                cells.append(c)
    return cells
