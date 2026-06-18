from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from database.models import (
    CREATE_BUSINESSES_TABLE,
    CREATE_CRAWLED_AREAS_TABLE,
    CREATE_DEALS_TABLE,
    CREATE_SEEN_URLS_TABLE,
)
from config import DATABASE_PATH


# Every column the current deals schema declares. Used to backfill any that a
# pre-existing table is missing — SQLite has no ADD COLUMN IF NOT EXISTS, so an
# old DB (created before content_hash / scope / price_deal / ... existed) would
# otherwise crash queries that reference the newer columns.
_EXPECTED_DEAL_COLUMNS = {
    "business_name": "TEXT", "deal_description": "TEXT", "category": "TEXT",
    "scope": "TEXT", "source_type": "TEXT", "source_name": "TEXT",
    "location": "TEXT", "lat": "REAL", "lng": "REAL", "source_url": "TEXT",
    "subreddit": "TEXT", "posted_at": "DATETIME", "fetched_at": "DATETIME",
    "urgency": "TEXT", "content_hash": "TEXT", "ai_processed": "BOOLEAN",
    "is_expired": "BOOLEAN", "price_deal": "TEXT", "discount_label": "TEXT",
    "products": "TEXT", "geohash": "TEXT",
}


def _migrate_deals(conn):
    """Backfill missing deal columns onto a pre-existing table. No-op once present."""
    existing = {r["name"] for r in conn.execute("PRAGMA table_info(deals)")}
    for name, coltype in _EXPECTED_DEAL_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE deals ADD COLUMN {name} {coltype}")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_DEALS_TABLE)
        conn.execute(CREATE_SEEN_URLS_TABLE)
        conn.execute(CREATE_BUSINESSES_TABLE)
        conn.execute(CREATE_CRAWLED_AREAS_TABLE)
        _migrate_deals(conn)


def url_exists(source_url: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM deals WHERE source_url = ?", (source_url,)).fetchone()
        return row is not None


def get_content_hash(source_url: str) -> str | None:
    """Return the stored content_hash for a URL, or None if we've never saved it."""
    with get_connection() as conn:
        row = conn.execute("SELECT content_hash FROM deals WHERE source_url = ?", (source_url,)).fetchone()
        return row["content_hash"] if row else None


def filter_unseen_posts(posts: list[dict]) -> list[dict]:
    """Keep only posts whose URL isn't already in seen_urls (Flow 1 crawl log)."""
    with get_connection() as conn:
        new_posts = []
        for post in posts:
            row = conn.execute("SELECT 1 FROM seen_urls WHERE url = ?", (post["source_url"],)).fetchone()
            if row is None:
                new_posts.append(post)
    skipped = len(posts) - len(new_posts)
    print(f"[db] {len(new_posts)} unseen posts (skipped {skipped} already processed)")
    return new_posts


def mark_urls_seen(posts: list[dict]):
    """Log these URLs so they're never sent to the AI again."""
    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO seen_urls (url, seen_at) VALUES (?, ?)",
            [(post["source_url"], now) for post in posts]
        )
    print(f"[db] marked {len(posts)} URLs as seen")


def save_deal(deal: dict):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO deals
                (business_name, deal_description, price_deal, discount_label, products, geohash,
                 category, scope, source_type, source_name,
                 location, lat, lng, source_url, subreddit, posted_at, fetched_at, urgency,
                 content_hash, ai_processed, is_expired)
            VALUES
                (:business_name, :deal_description, :price_deal, :discount_label, :products, :geohash,
                 :category, :scope, :source_type, :source_name,
                 :location, :lat, :lng, :source_url, :subreddit, :posted_at, :fetched_at, :urgency,
                 :content_hash, :ai_processed, 0)
            ON CONFLICT(source_url) DO UPDATE SET
                deal_description = excluded.deal_description,
                price_deal       = excluded.price_deal,
                discount_label   = excluded.discount_label,
                products         = excluded.products,
                geohash          = excluded.geohash,
                category         = excluded.category,
                urgency          = excluded.urgency,
                content_hash     = excluded.content_hash,
                ai_processed     = excluded.ai_processed,
                fetched_at       = excluded.fetched_at,
                is_expired       = 0
        """, {
            **deal,
            "fetched_at":    datetime.now(timezone.utc),
            "category":      deal.get("category", "other"),
            "scope":         deal.get("scope", "online"),
            "source_type":   deal.get("source_type", "social"),
            "source_name":   deal.get("source_name", "reddit"),
            "lat":           deal.get("lat"),
            "lng":           deal.get("lng"),
            "subreddit":     deal.get("subreddit"),
            "content_hash":  deal.get("content_hash"),
            "ai_processed":  deal.get("ai_processed", False),
            "price_deal":     deal.get("price_deal"),
            "discount_label": deal.get("discount_label"),
            "products":       deal.get("products"),
            "geohash":        deal.get("geohash"),
        })


def save_deals(deals: list[dict]):
    for deal in deals:
        save_deal(deal)
    print(f"[db] {len(deals)} rows saved to db")


def get_active_deals() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM deals
            WHERE is_expired = 0
            AND ai_processed = 1
            ORDER BY fetched_at DESC
        """).fetchall()
        return [dict(row) for row in rows]


def get_deals_in_cell(geohash: str) -> list[dict]:
    """Active deals in a geohash cell (prefix match, so a coarser cell includes
    its sub-cells). This is the "deals in my cell" query for the frontend."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM deals
            WHERE is_expired = 0
            AND ai_processed = 1
            AND geohash LIKE ? || '%'
            ORDER BY fetched_at DESC
        """, (geohash,)).fetchall()
        return [dict(row) for row in rows]


def mark_expired(deal_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE deals SET is_expired = 1 WHERE id = ?", (deal_id,))


def expire_old_deals(expiry_hours: int):
    with get_connection() as conn:
        conn.execute("""
            UPDATE deals
            SET is_expired = 1
            WHERE urgency = 'limited_time'
            AND is_expired = 0
            AND fetched_at <= datetime('now', ? || ' hours')
        """, (f"-{expiry_hours}",))


# --------------------------------------------------------------------------- #
# Flow 2 grid crawl — businesses + crawled_areas
# --------------------------------------------------------------------------- #

def _parse_dt(val) -> datetime:
    """Parse a stored datetime (sqlite returns ISO strings); assume UTC if naive."""
    dt = val if isinstance(val, datetime) else datetime.fromisoformat(str(val))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def upsert_business(b: dict):
    """Insert or update a discovered business, deduped by place_id."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO businesses
                (place_id, name, website, lat, lng, category, geohash, discovered_at)
            VALUES
                (:place_id, :name, :website, :lat, :lng, :category, :geohash, :discovered_at)
            ON CONFLICT(place_id) DO UPDATE SET
                name     = excluded.name,
                website  = COALESCE(excluded.website, businesses.website),
                lat      = excluded.lat,
                lng      = excluded.lng,
                category = COALESCE(businesses.category, excluded.category),
                geohash  = excluded.geohash
        """, {
            "place_id":      b["place_id"],
            "name":          b.get("name"),
            "website":       b.get("website"),
            "lat":           b.get("lat"),
            "lng":           b.get("lng"),
            "category":      b.get("category"),
            "geohash":       b.get("geohash"),
            "discovered_at": datetime.now(timezone.utc),
        })


def business_due_for_scrape(place_id: str, ttl_days: int) -> bool:
    """True if the business has never been scraped or was scraped > ttl_days ago."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT last_scraped_at FROM businesses WHERE place_id = ?", (place_id,)
        ).fetchone()
    if row is None or row["last_scraped_at"] is None:
        return True
    return datetime.now(timezone.utc) - _parse_dt(row["last_scraped_at"]) > timedelta(days=ttl_days)


def mark_business_scraped(place_id: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE businesses SET last_scraped_at = ? WHERE place_id = ?",
            (datetime.now(timezone.utc), place_id),
        )


def record_crawled_area(cell_id: str, lat: float, lng: float, radius_m: int, categories: str):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO crawled_areas (cell_id, lat, lng, radius_m, categories, crawled_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cell_id, lat, lng, radius_m, categories, datetime.now(timezone.utc)))


def area_recently_crawled(cell_id: str, ttl_days: int) -> bool:
    """True if this cell was crawled within the last ttl_days."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT MAX(crawled_at) AS last FROM crawled_areas WHERE cell_id = ?", (cell_id,)
        ).fetchone()
    if row is None or row["last"] is None:
        return False
    return datetime.now(timezone.utc) - _parse_dt(row["last"]) <= timedelta(days=ttl_days)