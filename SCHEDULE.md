# MediaSearch Crawl Schedule

Canonical reference for the automated crawl and data-fetch jobs.
Install or reinstall with: `crontab /var/www/search/crontab.txt`

## Status

**Crawler disabled 2026-05-16.** All four jobs below are commented out in the live crontab.
The index and existing data are untouched; the Flask service is still running.

To re-enable all jobs:
```bash
crontab -l | sed 's/^# DISABLED: //' | crontab -
```

To disable again:
```bash
crontab -l | sed 's|^\(0 .*/var/www/search/.*\)|# DISABLED: \1|' | crontab -
```

---

## Jobs

### Breaking news — every 2 hours
```
0 */2 * * * /var/www/search/run_crawl.sh breaking
```
- Seed file: `seeds/breaking.txt` (9 sources — THR-class, high churn)
- Max pages per domain: 50 | Depth: 2
- Log: `data/logs/breaking.log`

### Daily sources — 2 AM UTC
```
0 2 * * * /var/www/search/run_crawl.sh daily
```
- Seed file: `seeds/daily.txt` (22 sources — genre, review, awards sites)
- Max pages per domain: 100 | Depth: 3
- Log: `data/logs/daily.log`

### Weekly sources — Sunday 3 AM UTC
```
0 3 * * 0 /var/www/search/run_crawl.sh weekly
```
- Seed file: `seeds/weekly.txt` (20 sources — sci-fi, horror, international)
- Max pages per domain: 150 | Depth: 3
- Log: `data/logs/weekly.log`

### Stock ticker refresh — 3× per weekday
```
0 13,17,21 * * 1-5 cd /var/www/search && ./venv/bin/python3 finance_fetch.py
```
- Tickers: DIS, NFLX, WBD, PARA, CMCSA, SONY, AMC, IMAX, CNK, LGF.A (Finnhub free tier)
- Times: 9 AM, 1 PM, 5 PM ET (approx — server runs UTC)
- Output: `data/finance.json`
- Log: `data/logs/finance.log`

---

## Notes

- Each crawl tier runs `indexer.py` and restarts `mediasearch.service` on completion.
- Crawl delay is per-domain (2 s), not global — multi-domain runs parallelize naturally.
- Page-cap hits (`Reached max pages limit`) in logs are expected, not errors.
- Finnhub free tier: 60 req/min. Current 10-ticker list with 0.1 s delay is well within limits.
