from apscheduler.schedulers.blocking import BlockingScheduler
from collector.reddit import collect_all
from filter.keyword import filter_posts
from ai.classifier import classify_posts
from ai.extractor import extract_posts
from database.db import init_db, filter_new_posts, save_deals, expire_old_deals
from config import SCHEDULE_TIMES, EXPIRY_HOURS


def run_pipeline():
    print("\n[pipeline] starting run...")
    posts = collect_all()
    posts = filter_new_posts(posts)
    posts = filter_posts(posts)
    classified = classify_posts(posts)
    deals = extract_posts(classified["yes"] + classified["uncertain"])
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