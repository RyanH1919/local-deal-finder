# Flow 2 — Geographic Grid Catalogue Crawl (Design)

Builds on [`flow2_discussion.md`](flow2_discussion.md) (Decisions A/B/D + the `crawled_areas`
/ `businesses` schema) and the new `scraper/` strategy router. It turns the per-point
`--search` dev tool into a **scheduled, GTA-wide catalogue** collected cell-by-cell.

> **Scope of this doc:** the full design. **Phase 1 (implemented now)** is single-cell
> crawl on demand — `python main.py --crawl --address "..."` — with the **scheduler left
> off**. Phase 2 wires it into the cron sweep.

## 1. Why a grid (and not a radius around the user)
- **No user-triggered crawls.** Live Maps/AI calls per user burn our keys (Decision A:
  backend-only). So we *precompute* a catalogue; user search is a cheap DB read.
- **Coverage is capped by Google Places, not by area.** A Nearby search returns at most
  20/page, 60 total, ranked by prominence. If a `(cell, category)` has more matches than
  that, the long tail is silently dropped. The only way to capture *all* deals in an area
  is to make each cell small enough that one query stays under the cap. → a grid of small
  cells, each crawled fully; the union is GTA coverage.

## 2. Cell model
- **Cell id = geohash** — compact, and prefixes nest (a geohash-5 cell contains 32
  geohash-6 cells), which makes "which cell is this user in?" a string operation. This is
  the efficient version of the `A1/B2` idea.
  - geohash-5 ≈ 4.9 km × 4.9 km
  - **geohash-6 ≈ 1.2 km × 0.6 km ← default** (matches the doc's "~1 km area")
- **Cell → Places query:** center `(lat, lng)` + a covering `radius ≈ half the cell
  diagonal`, so the circle covers the cell. Neighboring circles overlap → we dedupe
  businesses by `place_id`.
- **Grid generation:** step `(lat, lng)` across the GTA bounding box by the cell size;
  each step is a cell. GTA bbox ≈ `lat 43.40–44.00, lng -80.00 to -79.00` (configurable).

## 3. Data model
New tables (from Decision F's schema):
```
businesses     (id, place_id UNIQUE, name, website, lat, lng,
                category, geohash, discovered_at, last_scraped_at)
crawled_areas  (id, cell_id, lat, lng, radius_m, categories, crawled_at)
```
- `businesses` → discovery (coverage grows over time), dedupe by `place_id`, and the
  per-business scrape cache (`last_scraped_at`).
- `crawled_areas` → the per-cell grid cache (Decision D).
- `deals` gained `products` (a JSON list of `{name, price, price_original, discount, vs_peers}`),
  plus `price_deal`, `discount_label`, and `geohash` columns. Pre-existing DBs self-heal via
  `_migrate_deals` on `init_db` (no manual rebuild).

## 4. Per-cell crawl flow
For a cell (center `lat/lng`, `radius_m`, `geohash`):
1. For each **category keyword** (`pizza`, `grocery store`, …):
   1. Places Nearby, **paginated up to 60** → candidate businesses.
   2. Upsert into `businesses` (dedupe by `place_id`; tag `category`, `geohash`).
2. For each business with a website **not scraped within `BUSINESS_TTL_DAYS`**:
   1. `scrape_business_website(website, name, metrics=shared)` — the Tier router.
   2. For each new/changed page (`content_hash`): `extract_website_deal` (Haiku) → a deal
      (its `lat`/`lng` place it in the cell).
   3. Stamp `businesses.last_scraped_at`.
3. `save_deals(deals)`; `record_crawled_area(geohash, …)`.
4. Print a **cell summary**: businesses found / scraped / cache-skipped, deals saved, and
   the scraper coverage metrics (`needs_render` / `needs_pdf` / `needs_vision`).

## 5. Caching (Decision D)
- **Per-cell:** skip a cell crawled within `CELL_TTL_DAYS` (default 7) unless `--force`.
- **Per-business:** skip scraping a site scraped within `BUSINESS_TTL_DAYS` (default 7).
- **Per-page:** `content_hash` (already on `deals`) avoids re-running Haiku on unchanged pages.

These three layers are what keep the binding cost (Anthropic Haiku per page) bounded.

## 6. Retrieval (user → their cell's deals) — IMPLEMENTED
A DB read, **no crawl, no API cost**:
- Deals are stamped with their cell `geohash` at crawl time.
- `GET /deals?lat=<>&lng=<>` resolves the point to its cell; `?cell=<geohash>` takes one
  directly. Backed by `db.get_deals_in_cell()` (prefix match, so a coarser cell includes
  its sub-cells). The `category`/`scope`/`urgency`/`location` filters still combine.

## 6a. Peer pricing ("how much am I saving") — IMPLEMENTED
Menu pages rarely state a regular price, so a saving is computed by comparison **within the
cell's catalogue** (`crawl/compare.py`) — never a regional average, never fabricated:
- **per business:** entry price vs the cell's other businesses → deal `vs_peers`
  (e.g. "from $10.99 — ~8% below 1 nearby").
- **per item:** same category+size across businesses → `products[i].vs_peers`.
- no comparable peer → no `vs_peers` (price-only). It sharpens as the catalogue densifies.

## 7. Cost model
Requests per full sweep ≈ `cells × categories × pages`. GTA ≈ 7,000 km².
- geohash-6 (~1 km): ~7,000 cells — too many to sweep often.
- ~2 km cells: ~1,800 cells — a sane starting point; caching + rotation keep it under the
  $200/mo Maps credit.
- Start uniform, **measure where a `(cell, category)` hits the 60 cap, and subdivide only
  those** (density-adaptive) rather than shrinking the whole grid.

## 8. Phasing
- **Phase 1 — DONE (this PR):** `crawl/grid.py` (geohash + cell generation + config),
  `businesses` + `crawled_areas` tables + DB functions, Places pagination, `crawl_cell()`,
  the `--crawl` CLI for one cell, and a committed offline suite (`tests/test_flow2.py`).
  **The scheduler is still untouched.**
- **Also shipped on top of Phase 1:**
  - per-tenant **product lists** (`deals.products`) + structured `price_deal` / `discount_label`
  - **Playwright** SPA rendering (`render_spa`; opt-in via `playwright install chromium`)
  - **geohash retrieval** — `GET /deals?lat=&lng=` / `?cell=` (§6)
  - **peer pricing** — each deal scored vs its cell (`vs_peers`, §6a)
  - **self-healing migration** — old DBs backfill missing columns on `init_db`
- **Phase 2 — remaining:** cron sweep over all GTA cells (rotation + discovery limits),
  density-adaptive subdivision, real Tier-3 PDF/vision extractors, and mirroring the
  structured fields onto the Reddit (Flow 1) path.

## 9. Testing one cell (no scheduler)
```
python main.py --crawl --address "2160 Shady Glen Rd, Toronto"
```
Geocodes the address, resolves its cell, crawls that **one** cell across the default
categories, and prints the cell summary. Re-running shows cache hits. The scheduler is not
started and is not modified.

## 10. Open questions (still live, from flow2_discussion)
- Cache TTL `N` (starting at 7 days).
- The category keyword list (starting small — see `crawl/grid.py`).
- Discovery limit / rotation once `businesses` grows to GTA scale.
- Uniform grid vs density-adaptive subdivision.
