#!/usr/bin/env bash
# Activate the SQLite FTS5 migration on the live server.
#
# Run once after pulling the new indexer/app code. Assumes data/search.db
# has already been populated by running `./venv/bin/python3 indexer.py`.
#
# Usage: sudo ./migrate_sqlite.sh

set -euo pipefail
cd "$(dirname "$0")"

if [[ $EUID -ne 0 ]]; then
    echo "This script needs sudo (systemctl, chown, find in root-owned dirs)."
    exec sudo "$0" "$@"
fi

echo "--- 1/4 Verifying SQLite DB exists ---"
if [[ ! -f data/search.db ]]; then
    echo "ERROR: data/search.db missing. Run ./venv/bin/python3 indexer.py first."
    exit 1
fi
chown www-data:www-data data/search.db
ls -lh data/search.db

echo "--- 2/4 Restarting gunicorn onto SQLite-backed app ---"
systemctl restart mediasearch
sleep 2
systemctl is-active mediasearch && echo "mediasearch: active"

echo "--- 3/4 Gzipping existing HTML pages (skip already-gzipped) ---"
before=$(du -sm data/pages | cut -f1)
find data/pages -type f -name page.html -exec gzip -9 {} +
after=$(du -sm data/pages | cut -f1)
echo "data/pages: ${before} MB -> ${after} MB"

echo "--- 4/4 Removing old JSON index (replaced by SQLite) ---"
if [[ -d data/index ]]; then
    rm -rf data/index
    echo "removed data/index"
fi

echo "--- Done ---"
du -sh data/search.db data/pages
