# Local Deal Finder — How It Works

A plain-English explanation of each file as it gets built.

---

## Pivot: Food-only → All GTA Deals

Originally this app targeted food/restaurant deals only. We pivoted to **all deal types** after finding that GTA food deal subreddits are not very active. The new scope:

- **Subreddits:** 4 active subreddits — r/frugalcanada, r/canadiandeals, r/deals, r/torontofood. Community subreddits and r/TorontoDeals were removed after testing showed they were low-activity with posts 1+ years old.
- **Categories:** food, grocery, electronics, services, clothing, software, other
- **Scope:** Online/Canada-wide deals are included alongside local GTA deals — Haiku classifies which is which
- **Classifier:** Upgraded from 3 labels (yes/no/uncertain) to 5 labels that also capture online vs local, and now batches 10 posts per API call
- **Extractor:** Receives scope as a hint, outputs category + scope, token usage tracked
- **Database:** Added `scope` and `category` columns to the deals table

---

## config.py

Central place for all settings. Changing subreddits, keywords, schedule times, or expiry rules happens here — no other files need to be touched.

- `SUBREDDITS` — 4 active Canadian deal subreddits. r/TorontoDeals and community subs removed after testing — they had posts 1+ years old.
- `KEYWORDS` — The pre-AI filter list. Covers deal language, promotions, retail events, electronics, budget language, and food.
- `MAX_POST_AGE_DAYS` — Posts older than this (60 days) are dropped before keyword filter and AI. Prevents old stale deals from ever entering the pipeline.
- `SUBREDDITS_PER_RUN` — How many subreddits to hit per pipeline run. Each returns up to 25 posts (Reddit's hard RSS cap), so 4 subreddits = 100 posts total. Controls how long collection takes: (SUBREDDITS_PER_RUN - 1) × 61 seconds.
- `SCHEDULE_TIMES` — Pipeline runs at 6am, 11am, 4pm, 9pm daily.
- `DATABASE_PATH` — Points to `data/deals.db`.
- `EXPIRY_HOURS` — 48 hours before a `limited_time` deal is auto-expired.
- `GOOGLE_API_KEY` / `GOOGLE_CSE_ID` — Reserved for future Google Maps / Custom Search integration.

---

## collector/reddit.py

Fetches posts from Reddit without needing an API key, using Reddit's public RSS feeds.

- `fetch_posts(subreddit)` — Makes one HTTP request to `reddit.com/r/{subreddit}/new/.rss` and parses the XML response. Reddit's RSS format uses the Atom namespace, which is why we pass `RSS_NS` to the XML parser to tell it where to look. For each post it extracts: title, body, URL, subreddit name, and timestamp.

- `collect_all(limit_subreddits)` — Loops through all subreddits defined in `config.py` and calls `fetch_posts` on each. If one subreddit fails (e.g. Reddit is slow), the rest still run. `limit_subreddits` caps how many subreddits are hit — used in test mode to keep costs low. Returns one flat list of all posts combined.

**Result:** Up to 100 posts (25 per subreddit × 4 subreddits), each a plain Python dict representing one Reddit post. Collection takes ~3 minutes in production due to the 61-second delay between subreddit requests.

---

## filter/keyword.py

A cheap pre-AI filter that removes posts before any API calls are made. Two checks run in order — recency first, then keywords. Saves money.

- `_PATTERNS` — A list of compiled regex patterns built once at import time from the keywords in `config.py`. Compiling upfront is faster than re-compiling on every post.

- `is_recent(post)` — Checks if the post's `posted_at` is within `MAX_POST_AGE_DAYS` (60 days). If `posted_at` is missing (Flow 2 website posts have no date), it passes through. If the date can't be parsed for any reason, it passes through — we'd rather include an edge case than silently drop it.

- `passes_filter(post)` — Combines the post title and body into one string, then checks if any keyword pattern matches. Uses `\b` word boundaries so "free" matches "free coffee" but not "freedom". Case-insensitive.

- `filter_posts(posts)` — Runs recency check first, then keyword filter on what's left. Prints how many were dropped for age and how many survived keywords.

**Result:** Recent, deal-language posts only — ready for AI classification. Old posts are dropped here, not by AI.

**Open issue:** `unknown` and `ongoing` urgency deals never auto-expire. A post that makes it through this filter could sit in the DB forever. Needs a solution before the frontend is built — see memory note.

---

## ai/classifier.py

Sends filtered posts to Claude Haiku in batches to make two cheap decisions per post: is this a deal, and is it online or local?

- `BATCH_SIZE = 10` — Instead of one API call per post, we send 10 posts at once in a single call. Haiku reads all 10 and responds with one label per line. This cuts API call overhead by 10x.

- `VALID_LABELS` — A set of the five allowed labels. Any response from Haiku that doesn't match falls back to `uncertain_local` so the pipeline never crashes on a bad response.

- `SYSTEM_PROMPT` — Tells Haiku what counts as a deal across all categories, what to reject (questions, full-price purchases, general discussion), and how to tell online from local. Shows it the exact output format expected.

- `_classify_batch(posts)` — Sends up to 10 posts as one numbered message, parses the numbered response line by line, returns a list of labels in the same order.

- `classify_post(post)` — Single-post wrapper around `_classify_batch` for convenience.

- `classify_posts(posts)` — Runs all posts through batched classification. Splits each label on `_` to extract deal verdict and scope, attaches `scope` to each post dict, and sorts into 5 buckets. Prints token usage at the end.

**Result:** Posts in 5 buckets (yes_online, yes_local, uncertain_online, uncertain_local, no), each post carrying a `scope` field. The scheduler combines all yes + uncertain buckets and passes them to the extractor.

---

## ai/extractor.py

Sends confirmed and uncertain posts to Claude Sonnet for full deal extraction. Receives the `scope` pre-determined by Haiku so it doesn't waste effort re-deciding it.

- `SYSTEM_PROMPT` — Tells Sonnet what JSON fields to return, what each category means, and how scope should influence the location field (local = try harder to find a neighbourhood; online = leave location null unless explicitly mentioned).

- `extract_post(post, use_haiku)` — Prepends `Scope: local/online` to the post content before sending to Sonnet. Strips markdown code blocks if Sonnet wraps its response, then parses the JSON. Staples on `source_url`, `subreddit`, `posted_at`, and `scope` from the original post. Returns `None` if JSON parsing fails. `use_haiku=True` swaps Sonnet for Haiku — used in test mode to save cost.

- `extract_posts(posts, use_haiku)` — Loops through all yes + uncertain posts. Skips any where `is_deal` is false — Sonnet gets a second chance to reject posts Haiku incorrectly passed. Tracks and prints total token usage.

**Output fields per deal:** `is_deal`, `category` (food/grocery/electronics/services/clothing/software/other), `business_name`, `deal_description`, `location`, `urgency`, `source_url`, `subreddit`, `posted_at`, `scope`.

**Result:** A clean list of deal dicts with all fields filled in, ready to save to the database.

---

## database/models.py — `seen_urls` table (Flow 1 crawl log)

A tiny table with two columns: `url` (PRIMARY KEY) and `seen_at` (timestamp). Its only job is to remember every URL that was sent to the AI — including posts Haiku rejected as "NO".

**Why it exists:** Without this, every post Haiku rejects never lands in `deals`, so the dedup check against `deals` misses it, and it gets re-fetched and re-classified on every single pipeline run forever — wasted API cost.

**Flow 1 only.** Flow 2 deliberately does NOT use this table. Flow 2 uses `content_hash` to decide whether to reprocess a website URL — it _wants_ to re-visit a URL if the page content has changed. `seen_urls` would block that.

**How it works in the pipeline:**
1. Fetch posts → `filter_unseen_posts()` checks `seen_urls`, drops anything already there
2. Keyword filter runs on what's left
3. `mark_urls_seen()` logs those URLs into `seen_urls` right before Haiku
4. Haiku classifies → Sonnet extracts → saved to `deals`

Result: a URL is processed by AI exactly once, whether it becomes a deal or gets rejected.

---

## database/models.py

Holds the SQL string that creates the deals table. Kept separate so the schema definition is in one obvious place and easy to change.

- `source_url` has a `UNIQUE` constraint — this is the database-level duplicate guard, and the key both flows dedup against.
- `category` defaults to `'other'` and `scope` defaults to `'online'` so old rows stay valid if the schema ever changes again.
- **Source columns (Noah's hierarchical model):** `source_type` (`social` | `website`) + `source_name` (`reddit` or a domain like `joespizza.com`). Lets us add Twitter/etc. later without changing the schema. Defaults to `social`/`reddit` so Flow 1 deals don't need to set them.
- **Location columns:** `lat` / `lng` (REAL, nullable) — only Flow 2 deals have coordinates from Google Places. Flow 1 leaves them NULL.
- `subreddit` is nullable — only Flow 1 (Reddit) deals have one. Flow 2 website deals leave it NULL.
- `content_hash` (nullable) — an MD5 fingerprint of the scraped page text, used by Flow 2 to detect when a business's deals have actually changed. Flow 1 leaves it NULL.

**Note:** If you already have a `deals.db`, delete it and let the app recreate it — the schema has changed and there is no automatic migration.

---

## database/db.py

All the functions for reading and writing to the SQLite database.

- `get_connection()` — Opens a connection to the database file. `row_factory = sqlite3.Row` makes rows behave like dicts so you can do `row["business_name"]` instead of `row[0]`.

- `init_db()` — Creates the deals table if it doesn't exist yet. Safe to call every time the app starts.

- `url_exists()` / `filter_new_posts()` — Deduplication before the AI. Checks if a post's URL is already in the database. Called after collection so we never send a post to Claude that we've already processed.

- `get_content_hash(source_url)` — Returns the stored `content_hash` for a URL, or None if we've never saved it. Flow 2 uses this to compare a freshly scraped page against what we saw last time.

- `save_deal()` / `save_deals()` — Saves a deal. Uses an **upsert** (`INSERT ... ON CONFLICT(source_url) DO UPDATE`): if the URL is new it inserts, if the URL already exists it updates the deal fields with the fresh content. This matters for Flow 2 — when a business updates the deals at the same URL, we update the row instead of ignoring it. Every field has a `.get()` fallback so a missing key never crashes the insert.

- `get_active_deals()` — Returns all non-expired deals sorted newest first. This is what the API calls to serve the frontend.

- `mark_expired(deal_id)` — Marks one deal as expired when the user dismisses it from the feed.

- `expire_old_deals(expiry_hours)` — Automatically marks all `limited_time` deals as expired after 48 hours.

---

## scheduler/jobs.py

Wires all the pipeline steps together and runs them automatically on a schedule using APScheduler.

- `run_pipeline(test_mode)` — The full pipeline in order: collect → deduplicate → keyword filter → classify → extract → save → expire old deals. In `test_mode`, it limits to 1 subreddit, caps extraction at 5 posts, and uses Haiku instead of Sonnet — cheap and fast for verifying the pipeline works. The scheduler handles the 5-bucket classifier output by merging all yes + uncertain buckets before passing to the extractor.

- `start_scheduler()` — Initializes the database, registers `run_pipeline` as a cron job for each time in `config.py` (6am, 11am, 4pm, 9pm), then starts the scheduler. `BlockingScheduler` means it runs in the foreground and keeps the process alive. Ctrl+C stops it cleanly.

**Result:** Running `python main.py` starts the scheduler and the full pipeline runs automatically 4 times a day.

---

## api/routes.py

A FastAPI backend that serves deal data from the database to the frontend over HTTP.

- `CORSMiddleware` — Allows the React frontend (running on port 5173) to make requests to this API (running on port 8000). Without this, the browser would block the requests for security reasons.

- `GET /deals` — Returns all active non-expired deals as JSON. Accepts optional query parameters: `?location=Mississauga`, `?urgency=limited_time`, `?scope=local`, `?category=electronics`. All filters can be combined.

- `POST /deals/{deal_id}/dismiss` — Marks a deal as expired when the user clicks dismiss on the frontend. The `{deal_id}` in the URL is the deal's database ID.

**Result:** A running API that the frontend can fetch deals from and send dismiss actions to.

---

# Flow 2 — Google Maps + Website Scraping

A second, separate pipeline that writes to the **same `deals.db`**. Flow 1 (Reddit) finds community-posted deals; Flow 2 goes straight to local businesses' own websites. See `docs/flow2_discussion.md` for the design decisions behind it.

**Phase 1 (current):** no AI — raw scraped text goes to the DB so we can validate the pipeline end-to-end.
**Phase 2 (later):** add Haiku extraction to turn raw text into clean deal descriptions.

The whole flow today is a **dev/testing tool** triggered manually via `python main.py --search --item X --address Y`. The production version will be a scheduled backend crawl over fixed GTA areas (not built yet).

---

## search/geocoder.py

- `geocode(address)` — Calls the Google Geocoding API to turn a street address into `(lat, lng)` coordinates. Raises `ValueError` if the address can't be resolved.

---

## search/places.py

Talks to the Google Places API to find businesses near a point.

- `find_nearby(lat, lng, item, radius_m)` — Returns businesses matching `item` (e.g. "pizza") within `radius_m`, each with name, address, coordinates, `place_id`, and distance. Sorted nearest-first.
- `get_place_website(place_id)` — Second API call that fetches a business's website URL from the Places Details API. Returns None if the business has no website listed.
- `_haversine_m()` / `format_distance()` — Helpers to compute straight-line distance between two coordinates and format it for display.

---

## scraper/website.py

Crawls a business's own website looking for deal content. Uses `requests` + BeautifulSoup.

- `scrape_business_website(url, business_name)` — Visits the homepage, follows up to `MAX_PAGES` links that look deal-related (`/specials`, `/offers`, etc., same domain only), and returns post-like dicts for any page with deal signals. The page text is cleaned (scripts/nav/footer stripped) and capped at 3000 chars.
- JS-heavy sites (React/Vue SPAs) return limited content — Playwright could be added later for those.

---

## search/deal_finder.py

- `find_deals_for_business(business_name, website_url)` — Thin wrapper that scrapes the business website and returns the results. (Previously also searched Reddit RSS — removed, since Flow 1 already covers Reddit and Flow 2 must not touch it.)

---

## search/runner.py — Flow 2 orchestrator (dev-only)

Ties Flow 2 together: geocode → find nearby businesses → scrape each website → save to DB.

- `run_search(item, address, radius_m)` — For each of the (up to 10) nearest businesses: fetches its website, scrapes deal pages, then builds a deal dict from what we already know (business name, coordinates, address from Google; category from the search term). **No AI in Phase 1** — the scraped text becomes the `deal_description` directly.

- **Change detection via content hash:** before saving each scraped page, it computes `md5(page_text)` and compares it to the stored `content_hash` for that URL via `get_content_hash()`. If the hash matches, the deals haven't changed — it skips the page entirely (and later, skips the AI call). If the hash is new or different, it saves/updates the deal. This is what stops us re-processing unchanged websites every crawl.

**Result:** Running the `--search` CLI scrapes nearby businesses and writes Flow 2 deals (with `source_type="website"`) into the same `deals.db` that the API serves.

---