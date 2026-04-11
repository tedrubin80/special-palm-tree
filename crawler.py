"""Web crawler that fetches pages starting from seed URLs."""

import hashlib
import json
import logging
import os
import re
import time
from collections import deque
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from robotexclusionrulesparser import RobotExclusionRulesParser

import config

logger = logging.getLogger(__name__)


class Crawler:
    """Breadth-first web crawler with robots.txt support."""

    def __init__(self, seed_file=None, max_pages=None, max_depth=None):
        self.seed_file = seed_file or config.DEFAULT_SEED_FILE
        self.max_pages = max_pages or config.MAX_PAGES_PER_DOMAIN
        self.max_depth = max_depth or config.MAX_DEPTH
        self.visited = set()
        self.queue = deque()  # (url, depth)
        self.robots_cache = {}  # domain -> RobotExclusionRulesParser
        self.domain_last_request = {}  # domain -> timestamp
        self.content_fingerprints = []  # SimHash fingerprints of seen pages
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT})
        os.makedirs(config.PAGES_DIR, exist_ok=True)

    # --- URL normalization ---

    # Query params that are tracking/noise, not content-affecting
    STRIP_PARAMS = re.compile(
        r"^(utm_|fbclid|gclid|ref|source|mc_|oly_|spm|vero_)"
    )

    @classmethod
    def normalize_url(cls, url):
        """Normalize a URL to reduce trivial duplicates."""
        parsed = urlparse(url)
        # Lowercase scheme and host
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        # Strip trailing slash from path (except root)
        path = parsed.path.rstrip("/") or "/"
        # Sort query params, drop tracking params
        params = parse_qs(parsed.query, keep_blank_values=True)
        filtered = {
            k: v for k, v in sorted(params.items())
            if not cls.STRIP_PARAMS.match(k)
        }
        query = urlencode(filtered, doseq=True) if filtered else ""
        # Drop fragment
        return urlunparse((scheme, netloc, path, "", query, ""))

    # --- Content fingerprinting (SimHash) ---

    @staticmethod
    def _simhash(text, hashbits=64):
        """Compute a SimHash fingerprint from text tokens."""
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        v = [0] * hashbits
        for token in tokens:
            h = int(hashlib.md5(token.encode()).hexdigest(), 16)
            for i in range(hashbits):
                if h & (1 << i):
                    v[i] += 1
                else:
                    v[i] -= 1
        fingerprint = 0
        for i in range(hashbits):
            if v[i] > 0:
                fingerprint |= (1 << i)
        return fingerprint

    @staticmethod
    def _hamming_distance(a, b):
        """Count differing bits between two integers."""
        return bin(a ^ b).count("1")

    def _is_near_duplicate(self, text, threshold=3):
        """Check if text is a near-duplicate of already-seen content."""
        fp = self._simhash(text)
        for seen_fp in self.content_fingerprints:
            if self._hamming_distance(fp, seen_fp) <= threshold:
                return True
        self.content_fingerprints.append(fp)
        return False

    # --- Seed loading ---

    def load_seeds(self):
        """Load seed URLs from the seed file into the queue."""
        with open(self.seed_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    self.queue.append((self.normalize_url(line), 0))
        logger.info("Loaded %d seed URLs", len(self.queue))

    # --- Robots.txt ---

    def _get_robots_parser(self, url):
        domain = urlparse(url).netloc
        if domain not in self.robots_cache:
            parser = RobotExclusionRulesParser()
            robots_url = f"{urlparse(url).scheme}://{domain}/robots.txt"
            try:
                resp = self.session.get(robots_url, timeout=config.REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    parser.parse(resp.text)
                else:
                    parser.parse("")  # allow everything if no robots.txt
            except requests.RequestException:
                parser.parse("")
            self.robots_cache[domain] = parser
        return self.robots_cache[domain]

    def _is_allowed(self, url):
        if not config.RESPECT_ROBOTS_TXT:
            return True
        parser = self._get_robots_parser(url)
        return parser.is_allowed(config.USER_AGENT, url)

    # --- Polite delay ---

    def _polite_delay(self, url):
        domain = urlparse(url).netloc
        last = self.domain_last_request.get(domain, 0)
        elapsed = time.time() - last
        if elapsed < config.CRAWL_DELAY:
            time.sleep(config.CRAWL_DELAY - elapsed)
        self.domain_last_request[domain] = time.time()

    # --- Fetch & parse ---

    def fetch(self, url):
        """Fetch a URL and return the response, or None on failure."""
        try:
            self._polite_delay(url)
            resp = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return None
            return resp
        except requests.RequestException as e:
            logger.warning("Error fetching %s: %s", url, e)
            return None

    def extract_links(self, url, html):
        """Extract absolute URLs from an HTML page."""
        soup = BeautifulSoup(html, "lxml")
        links = set()
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            absolute = urljoin(url, href)
            parsed = urlparse(absolute)
            # Only follow http/https, strip fragments
            if parsed.scheme in ("http", "https"):
                clean = self.normalize_url(absolute)
                links.add(clean)
        return links

    def save_page(self, url, html, metadata):
        """Save fetched page content and metadata to disk."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        page_dir = os.path.join(config.PAGES_DIR, url_hash)
        os.makedirs(page_dir, exist_ok=True)

        with open(os.path.join(page_dir, "page.html"), "w", encoding="utf-8") as f:
            f.write(html)
        with open(os.path.join(page_dir, "metadata.json"), "w") as f:
            json.dump(metadata, f, indent=2)

    # --- Main crawl loop ---

    def crawl(self):
        """Run the breadth-first crawl."""
        self.load_seeds()
        pages_crawled = 0

        while self.queue:
            url, depth = self.queue.popleft()

            if url in self.visited:
                continue
            if depth > self.max_depth:
                continue
            if not self._is_allowed(url):
                logger.debug("Blocked by robots.txt: %s", url)
                continue

            logger.info("[%d] Depth %d: %s", pages_crawled + 1, depth, url)
            resp = self.fetch(url)
            if resp is None:
                continue

            self.visited.add(url)

            # Parse and check for near-duplicate content
            html = resp.text
            soup = BeautifulSoup(html, "lxml")
            # Extract visible text for fingerprinting
            text_content = soup.get_text(separator=" ", strip=True)
            if self._is_near_duplicate(text_content):
                logger.info("Skipped (near-duplicate): %s", url)
                continue

            pages_crawled += 1
            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            metadata = {
                "url": url,
                "title": title,
                "depth": depth,
                "status_code": resp.status_code,
                "content_length": len(html),
                "crawled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self.save_page(url, html, metadata)

            # Discover new links
            if depth < self.max_depth:
                for link in self.extract_links(url, html):
                    if link not in self.visited:
                        self.queue.append((link, depth + 1))

            if pages_crawled >= self.max_pages:
                logger.info("Reached max pages limit (%d)", self.max_pages)
                break

        logger.info("Crawl complete. %d pages fetched.", pages_crawled)
        return pages_crawled


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    crawler = Crawler()
    crawler.crawl()
