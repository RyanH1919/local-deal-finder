from apscheduler.schedulers.blocking import BlockingScheduler
from collector.reddit import collect_all
from filter.keyword import filter_posts
from ai.classifier import classify_posts
from ai.extractor import extract_posts
from database.db import init_db, filter_unseen_posts, mark_urls_seen, save_deals, expire_old_deals
from config import SCHEDULE_TIMES, EXPIRY_HOURS


def run_pipeline(test_mode: bool = False):
    print("\n[pipeline] starting run..." + (" [TEST MODE]" if test_mode else ""))
    posts = collect_all(limit_subreddits=1 if test_mode else None)
    posts = filter_unseen_posts(posts)
    posts = filter_posts(posts)
    mark_urls_seen(posts)
    classified = classify_posts(posts)
    candidates = (
        classified.get("yes_local", []) +
        classified.get("yes_online", []) +
        classified.get("uncertain_local", []) +
        classified.get("uncertain_online", [])
    )
    if test_mode:
        candidates = candidates[:5]  # max 5 extractor calls in test mode
    deals = extract_posts(candidates, use_haiku=test_mode)
    save_deals(deals)
    expire_old_deals(EXPIRY_HOURS)
    print(f"[pipeline] done — {len(deals)} new deals saved\n")


def start_scheduler():
    init_db()
    scheduler = BlockingScheduler()
    for time in SCHEDULE_TIMES:
        scheduler.add_job(run_pipeline, "cron", hour=time["hour"], minute=time["minute"])
    print("[scheduler] running — pipeline scheduled at 6am, 11am, 4pm, 9pm")
    print("[scheduler] press Ctrl+C to stop")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("[scheduler] stopped")