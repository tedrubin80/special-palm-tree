"""SQLite FTS5 inverted index built from crawled pages."""

import gzip
import json
import logging
import os
import re
import sqlite3

from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY,
    url           TEXT UNIQUE NOT NULL,
    title         TEXT,
    body          TEXT,
    snippet_source TEXT,
    source_type   TEXT DEFAULT 'web',
    crawled_at    TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
    title, body,
    content='documents',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO fts(fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
END;
CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO fts(fts, rowid, title, body) VALUES('delete', old.id, old.title, old.body);
    INSERT INTO fts(rowid, title, body) VALUES (new.id, new.title, new.body);
END;
"""


def connect(db_path=None):
    """Open a SQLite connection with FTS5 schema applied."""
    db_path = db_path or config.DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def extract_text(html):
    """Strip tags and return visible text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def read_page_html(page_dir):
    """Read either page.html.gz or page.html from a page directory."""
    gz_path = os.path.join(page_dir, "page.html.gz")
    plain_path = os.path.join(page_dir, "page.html")
    if os.path.exists(gz_path):
        with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as f:
            return f.read()
    if os.path.exists(plain_path):
        with open(plain_path, encoding="utf-8", errors="replace") as f:
            return f.read()
    return None


def upsert_document(conn, url, title, body, snippet_source, crawled_at, source_type="web"):
    """Insert or replace a document row; FTS5 stays in sync via triggers."""
    conn.execute("DELETE FROM documents WHERE url = ?", (url,))
    conn.execute(
        "INSERT INTO documents (url, title, body, snippet_source, source_type, crawled_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (url, title, body, snippet_source, source_type, crawled_at),
    )


def rebuild(conn=None):
    """Scan crawled pages and rebuild the FTS5 index from scratch."""
    if not os.path.isdir(config.PAGES_DIR):
        logger.warning("No crawled pages found. Run the crawler first.")
        return 0

    owns_conn = conn is None
    if owns_conn:
        conn = connect()

    conn.execute("DELETE FROM documents")
    conn.execute("INSERT INTO fts(fts) VALUES('rebuild')")

    count = 0
    for page_hash in os.listdir(config.PAGES_DIR):
        page_dir = os.path.join(config.PAGES_DIR, page_hash)
        if not os.path.isdir(page_dir):
            continue
        meta_path = os.path.join(page_dir, "metadata.json")
        if not os.path.exists(meta_path):
            continue

        html = read_page_html(page_dir)
        if html is None:
            continue

        with open(meta_path) as f:
            meta = json.load(f)

        url = meta["url"]
        title = meta.get("title", "") or ""
        body = extract_text(html)
        snippet_source = body[:500]
        crawled_at = meta.get("crawled_at", "")

        upsert_document(conn, url, title, body, snippet_source, crawled_at)
        count += 1

    conn.commit()
    logger.info("Indexed %d documents into %s", count, config.DB_PATH)
    if owns_conn:
        conn.close()
    return count


def search(conn, query, limit=10, offset=0):
    """Run a BM25-ranked FTS5 search. Title matches weighted 10x body."""
    # Escape FTS5 metacharacters from user input — keep it simple, treat the
    # whole query as a single bag of terms
    safe = re.sub(r'["\(\)\*:]', " ", query).strip()
    if not safe:
        return [], 0
    # Tokenise and rejoin to get OR-over-terms behaviour
    terms = safe.split()
    match_expr = " OR ".join(terms)

    rows = conn.execute(
        """
        SELECT d.url, d.title, d.snippet_source,
               bm25(fts, 10.0, 1.0) AS rank_score
        FROM fts
        JOIN documents d ON d.id = fts.rowid
        WHERE fts MATCH ?
        ORDER BY rank_score
        LIMIT ? OFFSET ?
        """,
        (match_expr, limit, offset),
    ).fetchall()

    total = conn.execute(
        "SELECT count(*) FROM fts WHERE fts MATCH ?", (match_expr,)
    ).fetchone()[0]

    return rows, total


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    rebuild()
