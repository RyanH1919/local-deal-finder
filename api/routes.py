from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import get_active_deals, get_deals_in_cell, mark_expired

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/deals")
def get_deals(location: str = None, urgency: str = None, scope: str = None,
              category: str = None, lat: float = None, lng: float = None, cell: str = None):
    # Location-scoped retrieval: a geohash `cell` directly, or a `lat`/`lng` we
    # resolve to its cell. Falls back to all active deals when no location is given.
    if cell:
        deals = get_deals_in_cell(cell)
    elif lat is not None and lng is not None:
        from crawl.grid import cell_id
        deals = get_deals_in_cell(cell_id(lat, lng))
    else:
        deals = get_active_deals()
    if location:
        deals = [d for d in deals if d.get("location") and location.lower() in d["location"].lower()]
    if urgency:
        deals = [d for d in deals if d.get("urgency") == urgency]
    if scope:
        deals = [d for d in deals if d.get("scope") == scope]
    if category:
        deals = [d for d in deals if d.get("category") == category]
    return deals


@app.post("/deals/{deal_id}/dismiss")
def dismiss_deal(deal_id: int):
    mark_expired(deal_id)
    return {"success": True}
