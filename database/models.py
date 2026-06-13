CREATE_DEALS_TABLE = """
CREATE TABLE IF NOT EXISTS deals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name    TEXT,
    deal_description TEXT NOT NULL,
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
    is_expired       BOOLEAN NOT NULL DEFAULT 0
)
"""
