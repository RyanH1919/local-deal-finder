import os
from dotenv import load_dotenv

load_dotenv()

# Reddit API credentials (loaded from .env)
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "local-deal-finder/1.0")

# Anthropic API key (loaded from .env)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Subreddits to scrape — add or remove here without touching pipeline logic
SUBREDDITS = [
    "toronto",
    "torontofood",
    "mississauga",
    "GTA",
    "deals",
]

# Keywords for pre-AI filter — post must contain at least one (case-insensitive)
KEYWORDS = [
    "deal",
    "deals",
    "discount",
    "off",
    "free",
    "freebie",
    "special",
    "promo",
    "promotion",
    "bogo",
    "buy one get one",
    "limited time",
    "today only",
    "opening",
    "grand opening",
    "happy hour",
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
DATABASE_PATH = "deals.db"

# Hours before a limited_time deal is marked expired
EXPIRY_HOURS = 48
