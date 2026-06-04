CREATE_DEALS_TABLE = """
CREATE TABLE IF NOT EXISTS deals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    business_name    TEXT,
    deal_description TEXT NOT NULL,
    category         TEXT NOT NULL DEFAULT 'other',
    scope            TEXT NOT NULL DEFAULT 'online',
    location         TEXT,
    source_url       TEXT NOT NULL UNIQUE,
    subreddit        TEXT NOT NULL,
    posted_at        DATETIME,
    fetched_at       DATETIME NOT NULL,
    urgency          TEXT NOT NULL DEFAULT 'unknown',
    is_expired       BOOLEAN NOT NULL DEFAULT 0
)
"""
