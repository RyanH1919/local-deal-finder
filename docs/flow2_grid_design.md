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
- `deals` is **unchanged**. Retrieval uses the `lat`/`lng` it already stores (§6); a
  `geohash` column on `deals` is a Phase-2 indexing optimization, not required.

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

## 6. Retrieval (user → their cell's deals)
A DB read, **no crawl, no API cost**:
- User location → `(lat, lng)`.
- **Now:** bounding-box query on the `lat`/`lng` already stored on deals.
- **Phase 2:** add a `geohash` column + index; match by geohash prefix for O(1)
  "deals in cell E3" lookups, and extend `GET /deals` with a location filter.

## 7. Cost model
Requests per full sweep ≈ `cells × categories × pages`. GTA ≈ 7,000 km².
- geohash-6 (~1 km): ~7,000 cells — too many to sweep often.
- ~2 km cells: ~1,800 cells — a sane starting point; caching + rotation keep it under the
  $200/mo Maps credit.
- Start uniform, **measure where a `(cell, category)` hits the 60 cap, and subdivide only
  those** (density-adaptive) rather than shrinking the whole grid.

## 8. Phasing
- **Phase 1 (this PR):** `crawl/grid.py` (geohash + cell generation + config), the
  `businesses` + `crawled_areas` tables and DB functions, Places pagination, `crawl_cell()`,
  the `--crawl` CLI for one cell, and offline tests. **Scheduler untouched.**
- **Phase 2:** cron sweep over cells (rotation + discovery limits), geohash retrieval +
  `GET /deals` location filter, density-adaptive subdivision, and the Tier-3 scraper
  extractors (Playwright / PDF / vision).

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
