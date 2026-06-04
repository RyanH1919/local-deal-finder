import sqlite3
from datetime import datetime, timezone
from database.models import CREATE_DEALS_TABLE
from config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute(CREATE_DEALS_TABLE)


def url_exists(source_url: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM deals WHERE source_url = ?", (source_url,)).fetchone()
        return row is not None


def filter_new_posts(posts: list[dict]) -> list[dict]:
    new_posts = [post for post in posts if not url_exists(post["source_url"])]
    print(f"[db] {len(new_posts)} new posts (skipped {len(posts) - len(new_posts)} duplicates)")
    return new_posts


def save_deal(deal: dict):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO deals
                (business_name, deal_description, category, scope, location, source_url, subreddit, posted_at, fetched_at, urgency, is_expired)
            VALUES
                (:business_name, :deal_description, :category, :scope, :location, :source_url, :subreddit, :posted_at, :fetched_at, :urgency, 0)
        """, {**deal, "fetched_at": datetime.now(timezone.utc), "category": deal.get("category", "other"), "scope": deal.get("scope", "online")})


def save_deals(deals: list[dict]):
    for deal in deals:
        save_deal(deal)
    print(f"[db] {len(deals)} deals saved")


def get_active_deals() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM deals
            WHERE is_expired = 0
            ORDER BY fetched_at DESC
        """).fetchall()
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