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