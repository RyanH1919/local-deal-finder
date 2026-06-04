import os
from dotenv import load_dotenv

load_dotenv()

# Reddit API credentials (loaded from .env)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "windows:local-deal-finder:v1.0 (by /u/RunDue5981)")

# Anthropic API key (loaded from .env)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Google Maps API key (Geocoding + Places APIs)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Google Custom Search Engine ID — create at https://programmablesearchengine.google.com/
# Set it to "Search the entire web", then copy the cx value here
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Subreddits to scrape — add or remove here without touching pipeline logic
SUBREDDITS = [
    # Deal communities
    "TorontoDeals",
    "frugalcanada",
    "canadiandeals",
    "deals",
    # Food-focused
    "torontofood",
]

# Keywords for pre-AI filter — post must contain at least one (case-insensitive)
KEYWORDS = [
    # Deal language
    "deal", "deals", "discount", "discounted", "sale", "clearance", "markdown",
    # Percentage/price off
    "% off", "percent off", "half off", "half price",
    # Free stuff
    "free", "freebie", "freebies", "complimentary", "on the house",
    # Promotions
    "promo", "promotion", "promotional", "offer", "coupon", "voucher", "code",
    # Buy one get one
    "bogo", "buy one get one", "buy 1 get 1", "b1g1",
    # Time-sensitive
    "limited time", "limited offer", "today only", "this week only",
    "while supplies last", "while it lasts", "ends soon", "last chance",
    "flash sale", "one day only", "weekend only",
    # Openings
    "opening", "grand opening", "soft opening", "now open",
    # Food deals
    "happy hour", "lunch special", "dinner special", "early bird",
    "prix fixe", "set menu", "all you can eat", "ayce", "buffet",
    "takeout deal", "pickup deal", "dine in deal",
    # Loyalty / rewards
    "loyalty", "reward", "rewards", "points", "membership",
    # Quantity deals
    "2 for 1", "two for one", "twofer", "combo", "bundle", "multipack",
    # Shipping
    "free delivery", "free shipping", "no delivery fee",
    # Electronics / tech
    "open box", "refurbished", "price drop", "price match",
    # Budget language
    "cheap", "budget", "affordable", "inexpensive", "best value",
    "under $10", "under $20", "under $50", "under $100",
    # Retail events
    "black friday", "cyber monday", "boxing day", "prime day",
    "back to school", "seasonal sale", "overstock", "liquidation",
]

# How many posts to fetch per subreddit per run
POSTS_PER_SUBREDDIT = 100

# Schedule times (24-hour format)
SCHEDULE_TIMES = [
    {"hour": 6,  "minute": 0},   # Morning
    {"hour": 11, "minute": 0},   # Lunch
    {"hour": 16, "minute": 0},   # Dinner
    {"hour": 21, "minute": 0},   # Late night
]

# Database file path
DATABASE_PATH = "data/deals.db"

# Hours before a limited_time deal is marked expired
EXPIRY_HOURS = 48
