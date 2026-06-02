# Local Deal Finder — How It Works

A plain-English explanation of each file as it gets built.

---

## collector/reddit.py

Fetches posts from Reddit without needing an API key, using Reddit's public RSS feeds.

- `fetch_posts(subreddit)` — Makes one HTTP request to `reddit.com/r/{subreddit}/new/.rss` and parses the XML response. Reddit's RSS format uses the Atom namespace, which is why we pass `RSS_NS` to the XML parser to tell it where to look. For each post it extracts: title, body, URL, subreddit name, and timestamp.

- `collect_all()` — Loops through all subreddits defined in `config.py` and calls `fetch_posts` on each. If one subreddit fails (e.g. Reddit is slow), the rest still run. Returns one flat list of all posts combined.

**Result:** A list of 125 plain Python dicts (25 per subreddit), each representing one Reddit post.

---

## filter/keyword.py

A cheap pre-AI filter that removes posts with no deal language before any API calls are made. Saves money.

- `_PATTERNS` — A list of compiled regex patterns built once at import time from the keywords in `config.py`. Compiling upfront is faster than re-compiling on every post.

- `passes_filter(post)` — Combines the post title and body into one string, then checks if any keyword pattern matches. Uses `\b` word boundaries so "free" matches "free coffee" but not "freedom". Case-insensitive.

- `filter_posts(posts)` — Runs `passes_filter` on every post and keeps only the ones that pass. Prints how many survived.

**Result:** ~25-35 posts out of 125 that contain deal-related language, ready for AI classification.

---

## ai/classifier.py

Sends each filtered post to Claude Haiku to decide if it's a food deal. Haiku is fast and cheap — we use it here because the decision is simple (yes/no/uncertain).

- `SYSTEM_PROMPT` — The instruction we give Haiku before showing it any post. Defines what counts as a food deal and tells it to respond with exactly one word. This keeps responses short and costs minimal tokens.

- `classify_post(post)` — Sends one post to Haiku with `max_tokens=10` (a single word never exceeds that). Returns `"yes"`, `"no"`, or `"uncertain"`.

- `classify_posts(posts)` — Loops through all filtered posts and sorts them into three buckets: yes, no, uncertain. Returns a dict with all three lists. The `yes` and `uncertain` posts get passed to Sonnet next.

**Result:** Posts split into three groups. Only `yes` and `uncertain` move forward to the extractor — `no` posts are discarded.

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
