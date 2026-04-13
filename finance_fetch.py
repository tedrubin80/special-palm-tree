"""Fetch stock quotes for media/film tickers from Finnhub."""

import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

TICKERS = ["DIS", "NFLX", "WBD", "PARA", "CMCSA", "SONY", "AMC", "IMAX", "CNK", "LGF.A"]
FINNHUB_URL = "https://finnhub.io/api/v1/quote"
OUTPUT_PATH = Path(__file__).parent / "data" / "finance.json"
ENV_PATH = Path(__file__).parent / ".env"

logger = logging.getLogger(__name__)


def load_env(path):
    """Minimal .env loader — no external deps."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def fetch_quote(symbol, api_key):
    """Return Finnhub quote dict, or None on failure."""
    try:
        resp = requests.get(
            FINNHUB_URL,
            params={"symbol": symbol, "token": api_key},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("Failed to fetch %s: %s", symbol, e)
        return None


def main():
    load_env(ENV_PATH)
    api_key = os.environ.get("FINNHUB_API_KEY")
    if not api_key:
        logger.error("FINNHUB_API_KEY not set")
        sys.exit(1)

    quotes = []
    for symbol in TICKERS:
        data = fetch_quote(symbol, api_key)
        if not data or data.get("c") in (None, 0):
            continue
        current = data["c"]
        prev_close = data.get("pc") or current
        change = current - prev_close
        pct = (change / prev_close * 100) if prev_close else 0.0
        quotes.append({
            "symbol": symbol,
            "price": round(current, 2),
            "change": round(change, 2),
            "pct": round(pct, 2),
        })
        time.sleep(0.1)  # stay well under 60/min rate limit

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "quotes": quotes,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2))
    logger.info("Wrote %d quotes to %s", len(quotes), OUTPUT_PATH)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    main()
