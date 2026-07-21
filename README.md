# Film News Search Engine & Seed Crawler — Archive

MediaSearch crawled film-news sites, built a SQLite FTS5 index, and served
search results at mediasearch.online. **Crawler and search UI shut down
2026-07-21.** The public surface is now the static showcase in `demo/`.

## Showcase

```bash
# Local preview
cd demo && python3 -m http.server 8080
# → http://127.0.0.1:8080
```

Deploy configs: `vercel.json` (static demo) · `railway.toml` / `Procfile` (Flask).

## Architecture (historical)

```
seeds/*.txt  →  crawler.py  →  data/pages/  →  indexer.py  →  data/search.db  →  search UI
```

## Backups

See `backups/` and `SCHEDULE.md`. Crawl cron is disabled for user `www-data`.
