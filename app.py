"""Flask web interface for the search engine."""

import json
import re
from pathlib import Path

from flask import Flask, render_template, request
from markupsafe import Markup

from indexer import Indexer

app = Flask(__name__)

FINANCE_PATH = Path(__file__).parent / "data" / "finance.json"

# Load index once at startup
indexer = Indexer()
try:
    indexer.load()
except FileNotFoundError:
    print("Warning: No index found. Run indexer.py first.")


def load_finance():
    """Read current quotes from disk on each request — file is tiny."""
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

    # Bold the matching terms
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        snippet = pattern.sub(lambda m: f"<b>{m.group()}</b>", snippet)

    return Markup(snippet)


@app.route("/")
def home():
    query = request.args.get("q", "").strip()
    results = []

    if query:
        terms = indexer.filter_stop_words(indexer.tokenize(query))
        scores = {}
        for term in terms:
            for url, title, score in indexer.index.get(term, []):
                if url not in scores:
                    scores[url] = {"score": 0, "title": title}
                scores[url]["score"] += score

        results = []
        for url, info in scores.items():
            doc = indexer.documents.get(url, {})
            snippet_source = doc.get("snippet_source", "")
            snippet = make_snippet(snippet_source, terms) if snippet_source else ""
            results.append({
                "url": url,
                "title": info["title"],
                "score": round(info["score"], 2),
                "snippet": snippet,
            })
        results.sort(key=lambda r: r["score"], reverse=True)

    page = request.args.get("page", 1, type=int)
    per_page = 10
    total = len(results)
    start = (page - 1) * per_page
    paginated = results[start:start + per_page]
    total_pages = (total + per_page - 1) // per_page

    finance = load_finance()
    return render_template("search.html", query=query, results=paginated,
                           page=page, total=total, total_pages=total_pages,
                           finance=finance)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
