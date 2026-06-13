# Flow 2 — Design Discussion

A checklist of decisions for Flow 2 (Google Maps + website scraping). Started by Ryan + Claude on 2026-06-13; reviewed and answered by Noah (Ryan's cousin) shortly after. Most items are now resolved; remaining open items are flagged below.

## Context recap

The project has two flows that both feed the same SQLite DB:

- **Flow 1 — Reddit (built):** RSS-driven scheduled pipeline. Pulls posts from 5 deal subreddits 4×/day, keyword-filters, sends through Haiku classifier (batched) → Sonnet extractor → DB → FastAPI `GET /deals`.
- **Flow 2 — Maps + websites (early):** Currently `python main.py --search --item X --address Y`. Google Geocoding → Places Nearby → for each business, scrape its website with BeautifulSoup → run through (today) the Reddit AI pipeline → print results. **Does not save to DB yet.**

Flow 2 was started by Noah while Ryan was working on other parts. Some pieces were added that don't match the long-term vision (Reddit RSS lookup inside Flow 2, user-triggered `--search` CLI, PRAW collector in Flow 1).

## Cost picture (the constraint driving most decisions)

- **Google Maps:** free tier ($200/mo credit) covers our usage at hobbyist scale. Not a binding cost.
- **Anthropic (Claude):** this IS the binding cost.
  - Haiku: ~$0.001–0.01 per page
  - Sonnet: ~$0.01–0.05 per Reddit post
- Implication: the question for Flow 2 is "how many Claude calls do we make per crawl?", not "how do we save Google calls?"

## Vision agreed

- Two flows stay architecturally separate but write to the **same `deals.db`**.
- Users **never trigger AI/Maps calls themselves** — those would burn our API keys. Backend triggers only.
- Flow 1 keeps its Reddit prompts. Flow 2 will get its own prompts (or no AI at first).
- Flow 2 runs less often than Flow 1's 4×/day.

---

## Decisions

### A. Who triggers Flow 2? ✅ DECIDED

**Scheduled backend crawl over a fixed list of GTA areas. No user triggers.**

- ❌ On account creation — rejected (still a user-action cost vector)
- ✅ Scheduled backend crawl, GTA-scoped
- ❌ User-driven search with quota — rejected
- Google Maps free tier ($200/mo) is comfortably enough for GTA-scoped scheduled crawls at our scale.

### B. How does Flow 2 pick what to crawl? ✅ DECIDED

**Fixed list of search prompts × neighbourhoods, fed to Google Maps. Discovered businesses get persisted so coverage grows over time.**

- Prompts look like `"pizza near {neighbourhood}"`, `"electronics store near {neighbourhood}"`, etc.
- Each prompt returns a set of businesses + websites → those websites become scrape targets.
- **Automated discovery:** newly found businesses are added to a persistent collection each cycle. Over time the system stops re-discovering the same set and accumulates coverage.
- **Category tagging:** derived from the search prompt itself (we already searched "pizza", so it's `food`). No dedicated classifier needed in v1.
- Lightweight category classifier can be added later if the prompt-derived tags prove too coarse.

### C. Does Flow 2 use AI? ✅ DECIDED (phased)

**Phase 1: no AI — store raw scraped text and validate end-to-end. Phase 2: Haiku-only extraction once we see real volume.**

- ✅ Start with raw scraped text in the DB. Frontend can render snippets.
- ✅ Layer in Haiku extraction once we have volume + cost numbers.
- ❌ Skip the classifier stage — the scraper already keyword-filters pages.
- ❌ Sonnet not needed for Flow 2.

### D. Caching strategy ✅ DECIDED

**Both layers.**

- ✅ **Location grid cache:** skip Maps re-query for the same ~1 km area if crawled within last N days.
- ✅ **Per-business cache:** skip re-scraping a website if processed within last N days.
- N value to be tuned with cadence (see E).

### E. Re-crawl cadence ✅ DECIDED (tentative)

**Start daily. Monitor cost + freshness for 1–2 weeks. Dial back to weekly if needed.**

- Daily gives freshest data.
- Cadence is downstream of Anthropic budget (open question 4) — revisit once that's set.

### F. Schema changes ✅ DECIDED (with Noah's hierarchical model)

Noah flagged that a flat `source` enum (`reddit | website`) won't scale if we add Twitter/Facebook/etc. later. **Adopted hierarchical source model:**

```
source_type:  "social" | "website"
source_name:  "reddit" | "twitter" | <domain name> | ...
```

Mapping:
- Reddit deal → `source_type = "social"`, `source_name = "reddit"`
- Scraped website deal → `source_type = "website"`, `source_name = "joespizza.com"`
- Future Twitter deal → `source_type = "social"`, `source_name = "twitter"`

Schema additions to `deals` table:
- [ ] Add `source_type TEXT NOT NULL` (`social` | `website`)
- [ ] Add `source_name TEXT NOT NULL` (platform name or domain)
- [ ] Make `subreddit` nullable (only populated when `source_name = reddit`)
- [ ] Add `lat REAL`, `lng REAL` for Flow 2 deals
- [ ] Add `last_crawled_at DATETIME` for cache lookups

New table for businesses (supports automated discovery + per-business cache from D):
- [ ] `businesses` table: `(id, name, website, lat, lng, category, discovered_at, last_scraped_at)`

New table for crawl grid cache (supports grid cache from D):
- [ ] `crawled_areas` table: `(id, lat, lng, radius_m, search_prompt, crawled_at)`

---

## Still-open questions

1. **Monthly Anthropic budget cap?** This is the single biggest variable left. It drives the Phase 2 AI rollout in C and the cadence in E.
2. **Cache TTLs:** what's the actual N for "don't re-crawl this area within N days" and "don't re-scrape this site within N days"? Suggest starting at 7 days and tuning.
3. **Discovery limit:** once the `businesses` table grows, do we scrape every known business every cycle, or rotate through them? At GTA scale this could be thousands.

---

## Resolved open questions (from previous round)

- **Broad vs. deep coverage?** → Start broad across the GTA, deepen later in high-demand areas once we have user data.
- **User in an uncovered area?** → Sees nothing. No live crawls triggered by users.
- **`--search` CLI?** → Keep as a dev/testing tool only. Clearly separate it from the production scheduled path.

---

## Cleanup items (no discussion — just do)

- [ ] Delete PRAW path from `collector/reddit.py` (Noah added it; Reddit doesn't permit API anymore, RSS is what we actually use)
- [ ] Delete Reddit RSS call inside `search/deal_finder.py` (Flow 2 must not touch Reddit)
- [ ] Keep `search/runner.py` + `--search` CLI but mark them clearly as dev-only

---

## Things we're explicitly NOT deciding yet

- Frontend (waits until Flow 2 persists to DB)
- Deal deduplication across flows (same restaurant deal surfacing on Reddit + scraped from site)
- User accounts, auth, persistence of search history
- Deployment / hosting

---

> "I'm sure details will inevitably change but I think this is the rough idea of it." — Noah

_Generated 2026-06-13 from Ryan + Claude session. Updated same day with Noah's responses. Update further as decisions evolve._
