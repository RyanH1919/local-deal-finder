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
    elif "--crawl" in sys.argv:
        parser = argparse.ArgumentParser()
        parser.add_argument("--crawl", action="store_true")
        parser.add_argument("--address", help="Address to resolve to a grid cell")
        parser.add_argument("--lat", type=float, help="Cell latitude (use with --lng)")
        parser.add_argument("--lng", type=float, help="Cell longitude (use with --lat)")
        parser.add_argument("--radius", type=int, default=None, help="Override the cell radius (metres)")
        parser.add_argument("--categories", default=None, help="Comma-separated category overrides")
        parser.add_argument("--force", action="store_true", help="Ignore the cell/business cache")
        args = parser.parse_args()
        if args.address:
            from search.geocoder import geocode
            lat, lng = geocode(args.address)
        elif args.lat is not None and args.lng is not None:
            lat, lng = args.lat, args.lng
        else:
            parser.error("provide --address, or both --lat and --lng")
        cats = [c.strip() for c in args.categories.split(",")] if args.categories else None
        from crawl.catalogue import crawl_cell
        crawl_cell(lat, lng, radius_m=args.radius, categories=cats, force=args.force)
    elif "--now" in sys.argv or "--test" in sys.argv:
        from scheduler.jobs import run_pipeline
        init_db()
        run_pipeline(test_mode="--test" in sys.argv)
    else:
        from scheduler.jobs import start_scheduler
        start_scheduler()
