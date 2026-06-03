import requests
from config import GOOGLE_API_KEY

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


def geocode(address: str) -> tuple:
    """Convert a street address to (lat, lng). Raises ValueError if not found."""
    params = {"address": address, "key": GOOGLE_API_KEY}
    response = requests.get(GEOCODE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    if data["status"] != "OK" or not data.get("results"):
        raise ValueError(f"Could not geocode '{address}' — Google returned: {data.get('status')}")
    loc = data["results"][0]["geometry"]["location"]
    return loc["lat"], loc["lng"]
