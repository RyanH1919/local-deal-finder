# Local Deal Finder — How It Works

A plain-English explanation of each file as it gets built.

---

## Pivot: Food-only → All GTA Deals

Originally this app targeted food/restaurant deals only. We pivoted to **all deal types** after finding that GTA food deal subreddits are not very active. The new scope:

- **Subreddits:** 10 subreddits — community ones (r/toronto, r/askTO, r/mississauga, r/brampton, r/GTA) + deal communities (r/TorontoDeals, r/frugalcanada, r/canadiandeals, r/deals) + food-focused (r/torontofood)
- **Categories:** food, grocery, electronics, services, clothing, software, other
- **Scope:** Online/Canada-wide deals are included alongside local GTA deals — Haiku classifies which is which
- **Classifier:** Upgraded from 3 labels (yes/no/uncertain) to 5 labels that also capture online vs local, and now batches 10 posts per API call
- **Extractor:** Receives scope as a hint, outputs category + scope, token usage tracked
- **Database:** Added `scope` and `category` columns to the deals table

---

## config.py

Central place for all settings. Changing subreddits, keywords, schedule times, or expiry rules happens here — no other files need to be touched.

- `SUBREDDITS` — 10 subreddits covering GTA community posts, Canadian deal communities, and food-focused subs.
- `KEYWORDS` — The pre-AI filter list. Covers deal language, promotions, retail events, electronics, budget language, and food.
- `POSTS_PER_SUBREDDIT` — 100 posts fetched per subreddit per run (up to 1000 total).
- `SCHEDULE_TIMES` — Pipeline runs at 6am, 11am, 4pm, 9pm daily.
- `DATABASE_PATH` — Points to `data/deals.db`.
- `EXPIRY_HOURS` — 48 hours before a `limited_time` deal is auto-expired.
- `GOOGLE_API_KEY` / `GOOGLE_CSE_ID` — Reserved for future Google Maps / Custom Search integration.

---

## collector/reddit.py

Fetches posts from Reddit without needing an API key, using Reddit's public RSS feeds.

- `fetch_posts(subreddit)` — Makes one HTTP request to `reddit.com/r/{subreddit}/new/.rss` and parses the XML response. Reddit's RSS format uses the Atom namespace, which is why we pass `RSS_NS` to the XML parser to tell it where to look. For each post it extracts: title, body, URL, subreddit name, and timestamp.

- `collect_all(limit_subreddits)` — Loops through all subreddits defined in `config.py` and calls `fetch_posts` on each. If one subreddit fails (e.g. Reddit is slow), the rest still run. `limit_subreddits` caps how many subreddits are hit — used in test mode to keep costs low. Returns one flat list of all posts combined.

**Result:** Up to 1000 posts (100 per subreddit × 10 subreddits), each a plain Python dict representing one Reddit post.

---

## filter/keyword.py

A cheap pre-AI filter that removes posts with no deal language before any API calls are made. Saves money.

- `_PATTERNS` — A list of compiled regex patterns built once at import time from the keywords in `config.py`. Compiling upfront is faster than re-compiling on every post.

- `passes_filter(post)` — Combines the post title and body into one string, then checks if any keyword pattern matches. Uses `\b` word boundaries so "free" matches "free coffee" but not "freedom". Case-insensitive.

- `filter_posts(posts)` — Runs `passes_filter` on every post and keeps only the ones that pass. Prints how many survived.

**Result:** Roughly 50-150 posts out of 1000 that contain deal-related language, ready for AI classification.

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

## database/models.py

Holds the SQL string that creates the deals table. Kept separate so the schema definition is in one obvious place and easy to change.

- `source_url` has a `UNIQUE` constraint — this is the database-level duplicate guard. Even if the same post somehow gets through twice, SQLite will reject the second insert.
- `category` defaults to `'other'` and `scope` defaults to `'online'` so old rows stay valid if the schema ever changes again.

**Note:** If you already have a `deals.db`, delete it and let the app recreate it — the schema has changed and there is no automatic migration.

---

## database/db.py

All the functions for reading and writing to the SQLite database.

- `get_connection()` — Opens a connection to the database file. `row_factory = sqlite3.Row` makes rows behave like dicts so you can do `row["business_name"]` instead of `row[0]`.

- `init_db()` — Creates the deals table if it doesn't exist yet. Safe to call every time the app starts.

- `url_exists()` / `filter_new_posts()` — Deduplication before the AI. Checks if a post's URL is already in the database. Called after collection so we never send a post to Claude that we've already processed.

- `save_deal()` / `save_deals()` — Saves extracted deals including `category` and `scope`. `INSERT OR IGNORE` means if a duplicate somehow slips through, it's silently skipped instead of crashing. Both fields have `.get()` fallbacks so a missing key never causes a crash.

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