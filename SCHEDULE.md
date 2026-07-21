# MediaSearch Crawl Schedule

Canonical reference for the automated crawl and data-fetch jobs.
Install or reinstall with: `crontab /var/www/media/crontab.txt`

## Status

**Crawler disabled 2026-07-21.** All four jobs are commented out in the live
`www-data` crontab and in `crontab.txt`. Data backed up under `backups/`.
Public surface replaced by the static showcase in `demo/`.

The Flask `mediasearch.service` may still be running; stop it when ready:
```bash
sudo systemctl stop mediasearch
sudo systemctl disable mediasearch
```

To re-enable crawl jobs (not recommended):
```bash
sudo crontab -u www-data /var/www/media/crontab.txt   # after uncommenting
```

---

## Jobs (historical)

### Breaking news — every 2 hours
```
0 */2 * * * /var/www/media/run_crawl.sh breaking
```
- Seed file: `seeds/breaking.txt`
- Max pages per domain: 50 | Depth: 2
- Log: `data/logs/breaking.log`

### Daily sources — 2 AM UTC
```
0 2 * * * /var/www/media/run_crawl.sh daily
```
- Seed file: `seeds/daily.txt`
- Max pages per domain: 100 | Depth: 3
- Log: `data/logs/daily.log`

### Weekly sources — Sunday 3 AM UTC
```
0 3 * * 0 /var/www/media/run_crawl.sh weekly
```
- Seed file: `seeds/weekly.txt`
- Max pages per domain: 150 | Depth: 3
- Log: `data/logs/weekly.log`

### Stock ticker refresh — 3× per weekday
```
0 13,17,21 * * 1-5 cd /var/www/media && ./venv/bin/python3 finance_fetch.py
```
- Tickers: DIS, NFLX, WBD, PARA, CMCSA, SONY, AMC, IMAX, CNK, LGF.A
- Output: `data/finance.json`
- Log: `data/logs/finance.log`

---

## Backups (2026-07-21)

| Archive | Contents |
|---------|----------|
| `backups/mediasearch-index-20260721.tar.gz` | `search.db`, logs, seeds (~22 MB) |
| `backups/mediasearch-pages-20260721.tar.gz` | pages HTML + db + logs + seeds (~251 MB) |

Final index: **3,358** FTS documents · **6,744** stored page dirs · **24** domains.
