#!/usr/bin/env bash
# Run a crawl + reindex cycle for a specific tier.
# Usage: ./run_crawl.sh <breaking|daily|weekly|all>
#
# Cron examples:
#   0 */2 * * *  /var/www/media/run_crawl.sh breaking
#   0 2 * * *    /var/www/media/run_crawl.sh daily
#   0 3 * * 0    /var/www/media/run_crawl.sh weekly

set -euo pipefail
cd "$(dirname "$0")"

VENV="./venv/bin/python3"
TIER="${1:-all}"
LOG_DIR="./data/logs"
mkdir -p "$LOG_DIR"

run_tier() {
    local seed_file="$1"
    local max_pages="$2"
    local max_depth="$3"
    local name="$4"

    echo "--- $name crawl started at $(date -u +%Y-%m-%dT%H:%M:%SZ) ---"
    $VENV crawler.py --seed-file "$seed_file" --max-pages "$max_pages" --max-depth "$max_depth"
    echo "--- $name crawl finished at $(date -u +%Y-%m-%dT%H:%M:%SZ) ---"
}

case "$TIER" in
    breaking)
        run_tier seeds/breaking.txt 50 2 "Breaking"
        ;;
    daily)
        run_tier seeds/daily.txt 100 3 "Daily"
        ;;
    weekly)
        run_tier seeds/weekly.txt 150 3 "Weekly"
        ;;
    all)
        run_tier seeds/breaking.txt 50 2 "Breaking"
        run_tier seeds/daily.txt 100 3 "Daily"
        run_tier seeds/weekly.txt 150 3 "Weekly"
        ;;
    *)
        echo "Usage: $0 <breaking|daily|weekly|all>"
        exit 1
        ;;
esac

# Always rebuild the index after crawling
echo "--- Rebuilding index at $(date -u +%Y-%m-%dT%H:%M:%SZ) ---"
$VENV indexer.py

# Reload gunicorn so it picks up the new index
systemctl restart mediasearch 2>/dev/null || true

echo "--- Done at $(date -u +%Y-%m-%dT%H:%M:%SZ) ---"
