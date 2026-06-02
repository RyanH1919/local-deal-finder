from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import get_active_deals, mark_expired

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/deals")
def get_deals(location: str = None, urgency: str = None):
    deals = get_active_deals()
    if location:
        deals = [d for d in deals if d.get("location") and location.lower() in d["location"].lower()]
    if urgency:
        deals = [d for d in deals if d.get("urgency") == urgency]
    return deals


@app.post("/deals/{deal_id}/dismiss")
def dismiss_deal(deal_id: int):
    mark_expired(deal_id)
    return {"success": True}
