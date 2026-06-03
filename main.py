import sys
import argparse
from database.db import init_db

if __name__ == "__main__":
    if "--search" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--search", action="store_true")
        parser.add_argument("--item", required=True, help='What to search for, e.g. "pizza"')
        parser.add_argument("--address", required=True, help='Your address, e.g. "2020 Shady Glen Rd, Toronto"')
        parser.add_argument("--radius", type=int, default=3000, help="Search radius in metres (default 3000)")
        args = parser.parse_args()
        from search.runner import run_search
        run_search(args.item, args.address, radius_m=args.radius)
    elif "--now" in sys.argv or "--test" in sys.argv:
        from scheduler.jobs import run_pipeline
        init_db()
        run_pipeline(test_mode="--test" in sys.argv)
    else:
        from scheduler.jobs import start_scheduler
        start_scheduler()
