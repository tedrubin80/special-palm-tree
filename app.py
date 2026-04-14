"""Flask web interface for the search engine."""

import json
import re
from pathlib import Path

from flask import Flask, g, render_template, request
from markupsafe import Markup

import config
import indexer

app = Flask(__name__)

FINANCE_PATH = Path(__file__).parent / "data" / "finance.json"


def get_db():
    """Open a SQLite connection scoped to the current request."""
    if "db" not in g:
        g.db = indexer.connect(config.DB_PATH)
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def load_finance():
    try:
        return json.loads(FINANCE_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"quotes": []}


def make_snippet(text, terms, max_len=200):
    """Extract a snippet from text centered on the first matching term."""
    text_lower = text.lower()
    best_pos = -1
    for term in terms:
        pos = text_lower.find(term)
        if pos != -1:
            best_pos = pos
            break

    if best_pos == -1:
        snippet = text[:max_len]
    else:
        start = max(0, best_pos - max_len // 2)
        snippet = text[start:start + max_len]
        if start > 0:
            snippet = "..." + snippet
        if start + max_len < len(text):
            snippet = snippet + "..."

    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        snippet = pattern.sub(lambda m: f"<b>{m.group()}</b>", snippet)

    return Markup(snippet)


@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 10
    results = []
    total = 0

    if query:
        conn = get_db()
        rows, total = indexer.search(
            conn, query, limit=per_page, offset=(page - 1) * per_page
        )
        terms = [t.lower() for t in re.findall(r"[a-z0-9]+", query.lower())]
        for r in rows:
            snippet_source = r["snippet_source"] or ""
            snippet = make_snippet(snippet_source, terms) if snippet_source else ""
            # FTS5 bm25 returns negative numbers; smaller == better. Flip to
            # a positive "relevance" display.
            results.append({
                "url": r["url"],
                "title": r["title"],
                "score": round(-r["rank_score"], 2),
                "snippet": snippet,
            })

    total_pages = (total + per_page - 1) // per_page
    finance = load_finance()
    return render_template("search.html", query=query, results=results,
                           page=page, total=total, total_pages=total_pages,
                           finance=finance)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
