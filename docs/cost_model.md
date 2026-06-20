# Flow 2 — Staying under Google's $200/mo (cost model)

**Goal:** keep Google Maps spend under the **$200/month free credit**. Two-part philosophy,
both implemented:

1. **Cover only key areas**, not the whole GTA grid.
2. **A hard monthly cap** — the crawl stops making paid calls as it nears the budget.

## Why the naive grid is too expensive
Full GTA ≈ 7,000 km² ÷ ~0.7 km² geohash-6 cells ≈ **~10,000 cells**. At ~$0.25/cell
(5 categories: Nearby + Place Details) that's **~$2,500 per full sweep** — ~12× the free
credit. The dominant cost is **Place Details** (~$0.017 × ~100k businesses ≈ $1,700) just to
fetch each website.

## 1. Key areas only — `crawl/grid.py`
`KEY_AREAS` is a curated list of ~14 high-value GTA commercial nodes (Yonge–Dundas,
Yonge & Eglinton, Square One, STC, Vaughan Mills, …). `iter_key_area_cells()` yields just the
cells around them (**~180**, not 10,000). The scheduled sweep (Phase 2) iterates these.

- One full **key-areas** sweep ≈ **~$45** (180 cells × ~$0.25). Comfortably under $200.

## 2. Monthly spend cap — `crawl/budget.py` + `api_spend` table
- Every paid Places call is costed (`COST_USD`) and accumulated per month in `api_spend`.
- `MONTHLY_CAP_USD = $180` (headroom under $200).
- `crawl_cell` checks `budget.remaining()` and **stops making paid calls** when the cap is
  near: it skips a cell entirely if exhausted, and stops adding categories / scraping
  businesses mid-cell once `can_afford()` is false. So we can never blow past the budget.
- Every crawl prints: `[budget] maps ~$X this run | month $Y / $180 ($Z left)`.

## 3. Cadence + caching
- **Weekly**, not daily (the 7-day per-cell cache enforces it).
- **Rotation** (Phase 2): spread the key-area cells across the week so no single day spikes.
- **Per-business website cache** (`businesses.website`): Place Details is paid **once** per
  business, then reused on every re-crawl.
- **Per-page `content_hash`**: unchanged pages skip the AI entirely.

## Cost ceiling, by the numbers
| Mode | Cells | ~Cost/sweep |
|---|---|---|
| Full GTA grid | ~10,000 | ~$2,500 ❌ |
| **Key areas only** | ~180 | **~$45** ✅ |
| Key areas, weekly, websites cached | ~180 | ~$45 first / ~$30 after ✅ |

…with the **$180 hard cap** as the backstop.

## Driving it toward zero (roadmap)
- **Places API (New) `websiteUri` field mask** → the website comes back with the search;
  **drop Place Details entirely** (removes the ~$1,700-at-scale line; big saver for key areas too).
- **OpenStreetMap discovery** → find businesses + websites for **$0**; use Google only for gaps.

Together these can take Google spend toward **near-zero**, with the cap as insurance.
