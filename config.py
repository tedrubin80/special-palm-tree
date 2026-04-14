"""Crawler configuration."""

import os

# --- Crawl Behavior ---
USER_AGENT = "MediaSearchBot/0.1 (+https://mediasearch.online)"
REQUEST_TIMEOUT = 10  # seconds
CRAWL_DELAY = 2  # seconds between requests to the same domain
MAX_PAGES_PER_DOMAIN = 100
MAX_DEPTH = 3
RESPECT_ROBOTS_TXT = True

# --- Storage ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
INDEX_DIR = os.path.join(DATA_DIR, "index")
PAGES_DIR = os.path.join(DATA_DIR, "pages")
DB_PATH = os.path.join(DATA_DIR, "search.db")

# --- Seeds ---
SEEDS_DIR = os.path.join(os.path.dirname(__file__), "seeds")
DEFAULT_SEED_FILE = os.path.join(SEEDS_DIR, "film_news.txt")
