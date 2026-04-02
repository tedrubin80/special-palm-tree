#!/usr/bin/env bash
# Run a full crawl + reindex cycle.
# Usage: ./run_crawl.sh [seed_file]
# Cron example: 0 2 * * * /path/to/special-palm-tree/run_crawl.sh >> /tmp/crawl.log 2>&1

set -euo pipefail
cd "$(dirname "$0")"

echo "=== Crawl started at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

python crawler.py "$@"
python indexer.py

echo "=== Crawl finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
