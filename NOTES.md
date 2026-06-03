# Local Deal Finder — How It Works

A plain-English explanation of each file as it gets built.

---

## Pivot: Food-only → All GTA Deals

Originally this app targeted food/restaurant deals only. We pivoted to **all deal types** after finding that GTA food deal subreddits are not very active. The new scope:

- **Subreddits:** r/TorontoDeals, r/frugalcanada, r/canadiandeals (replacing r/toronto)
- **Categories:** Food & Drink, Electronics & Tech, Clothing & Fashion, Home & Garden, Health & Beauty, Entertainment, Other
- **Scope:** Online/Canada-wide deals are included alongside local GTA deals
- **Classifier:** Upgraded from 3 labels (yes/no/uncertain) to 5 labels that also capture online vs local
- **Extractor:** Now outputs a `category` field and uses Haiku's `scope` signal to inform extraction

---

## config.py

Central place for all settings. Changing subreddits, keywords, schedule times, or expiry rules happens here — no other files need to be touched.

- `SUBREDDITS` — The three subreddits we scrape: r/TorontoDeals, r/frugalcanada, r/canadiandeals. Previously just r/toronto (food-only era).
- `KEYWORDS` — The pre-AI filter list. Covers deal language, promotions, retail events, electronics, budget language, and food. Broadened from food-only during the pivot.
- `POSTS_PER_SUBREDDIT` — 100 posts fetched per subreddit per run.
- `SCHEDULE_TIMES` — Pipeline runs at 6am, 11am, 4pm, 9pm daily.
- `DATABASE_PATH` — Points to `data/deals.db`.
- `EXPIRY_HOURS` — 48 hours before a `limited_time` deal is auto-expired.

---

## collector/reddit.py

Fetches posts from Reddit without needing an API key, using Reddit's public RSS feeds.

- `fetch_posts(subreddit)` — Makes one HTTP request to `reddit.com/r/{subreddit}/new/.rss` and parses the XML response. Reddit's RSS format uses the Atom namespace, which is why we pass `RSS_NS` to the XML parser to tell it where to look. For each post it extracts: title, body, URL, subreddit name, and timestamp.

- `collect_all()` — Loops through all subreddits defined in `config.py` and calls `fetch_posts` on each. If one subreddit fails (e.g. Reddit is slow), the rest still run. Returns one flat list of all posts combined.

**Result:** Up to 300 posts (100 per subreddit × 3 subreddits), each a plain Python dict representing one Reddit post.

---

## filter/keyword.py

A cheap pre-AI filter that removes posts with no deal language before any API calls are made. Saves money.

- `_PATTERNS` — A list of compiled regex patterns built once at import time from the keywords in `config.py`. Compiling upfront is faster than re-compiling on every post.

- `passes_filter(post)` — Combines the post title and body into one string, then checks if any keyword pattern matches. Uses `\b` word boundaries so "free" matches "free coffee" but not "freedom". Case-insensitive.

- `filter_posts(posts)` — Runs `passes_filter` on every post and keeps only the ones that pass. Prints how many survived.

**Result:** Roughly 30-60 posts out of 300 that contain deal-related language, ready for AI classification.

---

## ai/classifier.py

Sends each filtered post to Claude Haiku to make two cheap decisions: is this a deal, and is it online or local? Haiku is fast and cheap — we use it here because both decisions are simple binary calls that don't need Sonnet's power.

- `SYSTEM_PROMPT` — Tells Haiku what counts as a deal across all categories (not just food), what to reject (posts asking for deals, not sharing them), and how to distinguish online/Canada-wide deals from local GTA ones.

- `classify_post(post)` — Sends one post to Haiku with `max_tokens=10`. Returns one of five labels: `yes_online`, `yes_local`, `uncertain_online`, `uncertain_local`, or `no`.

- `classify_posts(posts)` — Loops through all filtered posts. Splits each label on `_` to get the deal verdict (`yes`/`no`/`uncertain`) and the scope (`online`/`local`). Adds `scope` directly to the post dict so Sonnet has that info without re-deciding it. Returns the same three-bucket dict (`yes`, `no`, `uncertain`) — the scheduler doesn't need to change.

**Result:** Posts split into three groups, each post now carrying a `scope` field. Only `yes` and `uncertain` move forward to the extractor — `no` posts are discarded.

---

## ai/extractor.py

Sends confirmed and uncertain posts to Claude Sonnet for full deal extraction. Sonnet is more capable than Haiku so it gets the harder job of pulling structured data out of a messy Reddit post.

- `SYSTEM_PROMPT` — Tells Sonnet exactly what JSON fields to return and what each one means. Being very specific here is important because the output goes straight into the database — it needs to be valid JSON every time.

- `extract_post(post)` — Sends one post to Sonnet with `max_tokens=300` (enough for the full JSON response). Strips markdown code blocks if Sonnet wraps its response in them, then parses the JSON. Staples on `source_url`, `subreddit`, and `posted_at` from the original post since those come from the collector, not the AI. Returns `None` if parsing fails.

- `extract_posts(posts)` — Loops through all `yes` and `uncertain` posts from the classifier. Only keeps results where `is_deal` is `true` — Sonnet gets a second chance to reject a post that Haiku incorrectly approved.

**Result:** A clean list of deal dicts with all fields filled in, ready to save to the database.

---

## database/models.py

Holds the SQL string that creates the deals table. Kept separate so the schema definition is in one obvious place and easy to change.

- `source_url` has a `UNIQUE` constraint — this is the database-level duplicate guard. Even if the same post somehow gets through twice, SQLite will reject the second insert.

---

## database/db.py

All the functions for reading and writing to the SQLite database.

- `get_connection()` — Opens a connection to the database file. `row_factory = sqlite3.Row` makes rows behave like dicts so you can do `row["business_name"]` instead of `row[0]`.

- `init_db()` — Creates the deals table if it doesn't exist yet. Safe to call every time the app starts.

- `url_exists()` / `filter_new_posts()` — Deduplication before the AI. Checks if a post's URL is already in the database. Called after collection so we never send a post to Claude that we've already processed.

- `save_deal()` / `save_deals()` — Saves extracted deals. `INSERT OR IGNORE` means if a duplicate somehow slips through anyway, it's silently skipped instead of crashing.

- `get_active_deals()` — Returns all non-expired deals sorted newest first. This is what the API calls to serve the frontend.

- `mark_expired(deal_id)` — Marks one deal as expired when the user dismisses it from the feed.

- `expire_old_deals(expiry_hours)` — Automatically marks all `limited_time` deals as expired after 48 hours.

---

## scheduler/jobs.py

Wires all the pipeline steps together and runs them automatically on a schedule using APScheduler.

- `run_pipeline()` — The full pipeline in order: collect → deduplicate → keyword filter → classify → extract → save → expire old deals. This is the function that gets called 4 times a day. Notice deduplication (`filter_new_posts`) happens right after collection and before any AI calls, so we never waste tokens on posts we've already processed.

- `start_scheduler()` — Initializes the database, registers `run_pipeline` as a cron job for each time in `config.py` (6am, 11am, 4pm, 9pm), then starts the scheduler. `BlockingScheduler` means it runs in the foreground and keeps the process alive. Ctrl+C stops it cleanly.

**Result:** Running `python main.py` starts the scheduler and the full pipeline runs automatically at meal times.

---

## api/routes.py

A FastAPI backend that serves deal data from the database to the frontend over HTTP.

- `CORSMiddleware` — Allows the React frontend (running on port 5173) to make requests to this API (running on port 8000). Without this, the browser would block the requests for security reasons.

- `GET /deals` — Returns all active non-expired deals as JSON. Accepts optional query parameters: `?location=Mississauga` filters by location, `?urgency=limited_time` filters by urgency. Both can be combined.

- `POST /deals/{deal_id}/dismiss` — Marks a deal as expired when the user clicks dismiss on the frontend. The `{deal_id}` in the URL is the deal's database ID.

**Result:** A running API that the frontend can fetch deals from and send dismiss actions to.

---
