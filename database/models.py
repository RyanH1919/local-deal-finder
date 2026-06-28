CREATE_SEEN_URLS_TABLE = """
CREATE TABLE IF NOT EXISTS seen_urls (
    url     TEXT PRIMARY KEY,
    seen_at DATETIME NOT NULL
)
"""

CREATE_DEALS_TABLE = """
CREATE TABLE IF NOT EXISTS deals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name    TEXT,
    deal_description TEXT NOT NULL,
    price_deal       TEXT,
    price_original   TEXT,
    discount_label   TEXT,
    min_spend        TEXT,
    expires          TEXT,
    products         TEXT,
    geohash          TEXT,
    vs_peers         TEXT,
    category         TEXT NOT NULL DEFAULT 'other',
    scope            TEXT NOT NULL DEFAULT 'online',
    source_type      TEXT NOT NULL DEFAULT 'social',
    source_name      TEXT NOT NULL DEFAULT 'reddit',
    location         TEXT,
    lat              REAL,
    lng              REAL,
    source_url       TEXT NOT NULL UNIQUE,
    subreddit        TEXT,
    posted_at        DATETIME,
    fetched_at       DATETIME NOT NULL,
    urgency          TEXT NOT NULL DEFAULT 'unknown',
    content_hash     TEXT,
    ai_processed     BOOLEAN NOT NULL DEFAULT 0,
    is_expired       BOOLEAN NOT NULL DEFAULT 0
)
"""

# Flow 2 grid crawl — discovered businesses (dedupe + per-business scrape cache).
CREATE_BUSINESSES_TABLE = """
CREATE TABLE IF NOT EXISTS businesses (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id        TEXT NOT NULL UNIQUE,
    name            TEXT,
    website         TEXT,
    lat             REAL,
    lng             REAL,
    category        TEXT,
    geohash         TEXT,
    discovered_at   DATETIME NOT NULL,
    last_scraped_at DATETIME
)
"""

# Flow 2 grid crawl — per-cell crawl log (the grid cache from flow2_discussion D).
CREATE_CRAWLED_AREAS_TABLE = """
CREATE TABLE IF NOT EXISTS crawled_areas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    cell_id    TEXT NOT NULL,
    lat        REAL,
    lng        REAL,
    radius_m   INTEGER,
    categories TEXT,
    crawled_at DATETIME NOT NULL
)
"""

# Flow 2 grid crawl — monthly Google Maps spend ledger (the budget cap).
CREATE_API_SPEND_TABLE = """
CREATE TABLE IF NOT EXISTS api_spend (
    month TEXT PRIMARY KEY,
    usd   REAL NOT NULL DEFAULT 0
)
"""