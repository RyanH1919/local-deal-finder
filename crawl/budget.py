"""Google Maps spend tracking + a soft monthly cap.

Keeps us under Google's $200/mo free credit: every paid Places call is costed and
accumulated per month in the `api_spend` table, and the crawl stops making paid
calls once the month's spend nears the cap. Costs are conservative list-price
estimates. All functions are resilient — budget bookkeeping must never break a crawl.
"""

from database.db import add_api_spend, api_spend_this_month

MONTHLY_CAP_USD = 180.0   # headroom under Google's $200/mo free credit

# Conservative list prices (USD per call).
COST_USD = {
    "nearby": 0.032,    # Places Nearby Search, per page
    "details": 0.017,   # Place Details (website lookup), per call
    "geocode": 0.005,   # Geocoding, per call
}


def cost(kind: str, n: int = 1) -> float:
    return COST_USD.get(kind, 0.0) * n


def record(kind: str, n: int = 1) -> float:
    """Charge `n` calls of `kind` to this month's ledger; return the $ added."""
    amount = cost(kind, n)
    if amount:
        try:
            add_api_spend(amount)
        except Exception:
            pass   # never let cost bookkeeping break a crawl
    return amount


def spent_this_month() -> float:
    try:
        return api_spend_this_month()
    except Exception:
        return 0.0


def remaining() -> float:
    return MONTHLY_CAP_USD - spent_this_month()


def can_afford(kind: str, n: int = 1) -> bool:
    """True if this month's budget still has room for `n` calls of `kind`."""
    return remaining() >= cost(kind, n)
