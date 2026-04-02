# Film News Search Engine & Seed Crawler

A simple search engine built from scratch: crawl film news websites, build an inverted index, and search the results.

## Architecture

```
seeds/film_news.txt   →   crawler.py   →   data/pages/   →   indexer.py   →   data/index/   →   search.py
     (seed URLs)          (fetch HTML)      (raw pages)      (build index)    (inverted index)    (query)
```

## Quick Start

```bash
pip install -r requirements.txt

# 1. Crawl seed sites
python crawler.py

# 2. Build the search index
python indexer.py

# 3. Search
python search.py "oscar nominations"
```

## Configuration

Edit `config.py` to adjust crawl depth, delay, max pages, and user agent.

## Adding Seeds

Add URLs to `seeds/film_news.txt` (one per line, `#` for comments).
